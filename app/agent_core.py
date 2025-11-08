# app/agent_core.py
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableMap
from langchain_classic.memory import ConversationBufferMemory
from .config import settings

# === Import engines ===
from app.engines.role_mapper import get_primary_occupation, heuristic_map
from app.engines.skill_gap import compute_skill_gaps, summarize_gaps
from app.engines.learning_builder import build_learning_plan, get_salary_insight


def _serialize_docs(docs) -> List[Dict[str, Any]]:
    """Turn langchain Document objects into simple dicts safe for JSON."""
    out = []
    for d in docs or []:
        try:
            out.append({"page_content": getattr(d, "page_content", str(d)), "metadata": getattr(d, "metadata", {})})
        except Exception:
            out.append({"page_content": str(d), "metadata": {}})
    return out


def build_resume_agent(chroma_store, mode: str = "resume_coach"):
    """
    INTENT-AWARE Career Agent
    - Uses RAG and local engines (role_mapper, skill_gap, learning_builder)
    - Returns a stable dict with keys:
      { answer, intent, source_documents, engine_context_used, learning_plan }
    """

    base_dir = Path(__file__).parent
    prompts_dir = base_dir / "prompts"
    skills_path = base_dir / "skills_metadata.json"

    template = (prompts_dir / f"{mode}.txt").read_text(encoding="utf-8")
    skill_meta = json.loads(skills_path.read_text(encoding="utf-8"))

    # === LLM selection ===
    if settings.AZURE_OPENAI_API_KEY and settings.AZURE_OPENAI_ENDPOINT:
        llm = AzureChatOpenAI(
            azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            temperature=0.2,
        )
    else:
        llm = ChatOpenAI(model=settings.MODEL_NAME, temperature=0.2)

    # === Memory ===
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,
        output_key="answer"
    )

    # === Prompt Template ===
    prompt = PromptTemplate(
        input_variables=[
            "context",
            "chat_history",
            "question",
            "engine_context"
        ],
        template=template,
    )

    # === Runnable chain that returns string ===
    llm_chain = (
        RunnableMap({
            "context": lambda x: x["context"],
            "chat_history": lambda x: memory.load_memory_variables({}).get("chat_history", ""),
            "question": lambda x: x["question"],
            "engine_context": lambda x: x["engine_context"],
        })
        | prompt
        | llm
        | StrOutputParser()  # always get raw text
    )

    # === Domain detector ===
    def detect_domain(text: str) -> str:
        if not text:
            return "generic"
        txt = text.lower()
        for domain, meta in skill_meta.items():
            if any(kw in txt for kw in meta.get("keywords", [])):
                return domain
        return "generic"

    # === Agent wrapper ===
    class ContextAwareAgent:
        def invoke(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
            question: str = inputs.get("question", "") or ""
            explicit_engine_ctx = inputs.get("engine_context", "")

            # Step 1: RAG retrieval (safe - returns [] if nothing)
            try:
                docs = chroma_store.similarity_search(question, k=4)
            except Exception:
                docs = []

            resume_context = "\n\n".join([getattr(d, "page_content", str(d)) for d in (docs or [])]) if docs else ""

            # Step 2: domain detection
            domain = detect_domain(resume_context)

            # Step 3: occupation mapping (defensive)
            try:
                occ = get_primary_occupation(resume_context) or heuristic_map(resume_context)
            except Exception:
                occ = ("general professional", {})

            if isinstance(occ, tuple):
                occupation_key = occ[0]
                occupation_meta = occ[1] if len(occ) > 1 else {}
            else:
                occupation_key = str(occ)
                occupation_meta = {}

            # Step 4: compute gaps (defensive)
            try:
                # compute_skill_gaps expects parsed_resume or resume-like structure; call defensively.
                gaps = compute_skill_gaps(resume_context, occupation_meta)  # some engines accept string/parsed - they are defensive in your code
                gap_summary = summarize_gaps(gaps)
            except Exception:
                gaps = []
                gap_summary = []

            # Step 5: learning plan
            try:
                learning_plan = build_learning_plan(gaps=gaps, occupation_meta=occupation_meta)
            except TypeError:
                # older signature fallback (if build_learning_plan expects domain/occupation/skill_gaps)
                try:
                    learning_plan = build_learning_plan(domain=domain, occupation=occupation_key, skill_gaps=gaps)
                except Exception:
                    learning_plan = {}
            except Exception:
                learning_plan = {}

            # Step 6: salary
            try:
                salary = get_salary_insight(occupation_meta)
            except Exception:
                # if engine expects a string occupation, try with occupation_key
                try:
                    salary = get_salary_insight({"canonical": occupation_key})
                except Exception:
                    salary = {}

            # Step 7: engine payload (plain python types)
            engine_payload = {
                "domain": domain,
                "primary_occupation": occupation_key,
                "occupation_meta": occupation_meta,
                "skill_gaps": gap_summary,
                "learning_plan": learning_plan,
                "salary": salary,
            }
            if explicit_engine_ctx:
                engine_payload["user_engine_context"] = explicit_engine_ctx

            # Step 8: run LLM chain (we asked for raw string)
            try:
                # pass engine_context as JSON string for readability in the prompt
                engine_ctx_str = json.dumps(engine_payload, default=str, indent=2)
            except Exception:
                engine_ctx_str = str(engine_payload)

            try:
                llm_result_text: str = llm_chain.invoke({
                    "context": resume_context,
                    "question": question,
                    "engine_context": engine_ctx_str
                }) or ""
            except Exception as e:
                # last-resort LLM fallback
                llm_result_text = f"Error generating response: {e}"

            # Step 9: attempt to parse structured JSON from LLM if it returns one
            intent = "general"
            answer_text = llm_result_text

            # Try 1: find JSON object in text and parse
            parsed_json: Optional[Dict[str, Any]] = None
            try:
                # crude: locate first { and last } and parse substring
                start = llm_result_text.find("{")
                end = llm_result_text.rfind("}")
                if start != -1 and end != -1 and end > start:
                    candidate = llm_result_text[start:end + 1]
                    parsed_json = json.loads(candidate)
            except Exception:
                parsed_json = None

            if parsed_json and isinstance(parsed_json, dict):
                intent = parsed_json.get("intent") or parsed_json.get("mode") or parsed_json.get("type") or intent
                answer_text = parsed_json.get("answer") or parsed_json.get("response") or answer_text

            else:
                # Try 2: simple prefix parser "Intent: X" at top
                # example: "Intent: career\n\nAnswer: ...."
                txt_lines = llm_result_text.strip().splitlines()
                if txt_lines:
                    first = txt_lines[0].strip()
                    if first.lower().startswith("intent:"):
                        _, v = first.split(":", 1)
                        intent = v.strip().lower()
                        # answer = rest of text after blank line
                        rest = "\n".join(txt_lines[1:]).strip()
                        if rest.lower().startswith("answer:"):
                            answer_text = rest.split(":", 1)[1].strip()
                        else:
                            answer_text = rest or answer_text

                # Try 3: heuristics - if resume_context exists or docs returned -> career
                if intent == "general":
                    career_words = ["resume", "career", "skills", "job", "salary", "role", "learning", "cv", "experience"]
                    if docs and any(word in question.lower() or word in resume_context.lower() for word in career_words):
                        intent = "career"

            # Step 10: persist in memory
            try:
                memory.save_context({"question": question}, {"answer": answer_text})
            except Exception:
                pass

            # Step 11: prepare stable response
            return {
                "answer": answer_text,
                "intent": intent,
                "source_documents": _serialize_docs(docs),
                "engine_context_used": engine_payload,
                "learning_plan": learning_plan,
            }

    return ContextAwareAgent()
