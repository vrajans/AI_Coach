import json
from pathlib import Path
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_classic.chains import ConversationalRetrievalChain
from langchain_classic.memory import ConversationBufferMemory
from langchain_core.prompts import PromptTemplate
from .config import settings

from app.engines.role_mapper import get_primary_occupation, heuristic_map
from app.engines.skill_gap import compute_skill_gaps, summarize_gaps
from app.engines.learning_builder import build_learning_plan,  get_salary_insight

def build_resume_agent(chroma_store, mode="resume_coach"):
    """
    Builds the full Career Transformation Engine Agent.
    Includes:
    Resume → Occupation mapping
    Skill gap detection
    Dynamic learning plan creation
    Dynamic salary insights
    RAG retrieval + memory
    """

    base_dir = Path(__file__).parent
    prompts_dir = base_dir / "prompts"
    skills_path = base_dir / "skills_metadata.json"

    # === Load Prompt ===
    prompt_file = prompts_dir / f"{mode}.txt"
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
    with open(prompt_file, "r", encoding="utf-8") as f:
        template = f.read()

    # === Load Skills Metadata ===
    with open(skills_path, "r", encoding="utf-8") as f:
        skill_meta = json.load(f)    


    # === Vector Retriever ===
    retriever = chroma_store.as_retriever(search_kwargs={"k": 4})

    # === LLM Setup ===
    if settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_API_KEY:
        llm = AzureChatOpenAI(
            azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            temperature=0.2)
    elif settings.OPENAI_API_KEY:
        llm = ChatOpenAI(model=settings.MODEL_NAME, temperature=0.2)
    else:
        raise ValueError(
            "No valid LLM configuration found. Please set either Azure OpenAI or OpenAI API credentials.")

    # === Conversation Memory ===
    memory = ConversationBufferMemory(
        memory_key="chat_history", 
        return_messages=True,
        output_key="answer"
    )

    custom_prompt = PromptTemplate(
        input_variables=["context", "chat_history", "question","engine_context"],
        template=template,
    )

    # Build the Conversational Retrieval Chain with the custom prompt
    agent = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory,
        combine_docs_chain_kwargs={"prompt": custom_prompt},
        return_source_documents=True,
        verbose=True,
    )

    # === Domain Detection Helper ===
    def detect_domain(text):
        text_lower = text.lower()
        for domain, meta in skill_meta.items():
            if any(kw in text_lower for kw in meta.get("keywords", [])):
                return domain
        return "generic"

    # Wrapper to add context check before invoking the model
    class ContextAwareAgent:
        def __init__(self, base_chain, retriever):
            self.base_chain = base_chain
            self.retriever = retriever
            self.skill_meta = skill_meta

        def build_engine_context(self, parsed_resume):
            """
            Career Transformation Engine
            Converts parsed resume → mapped occupation → gaps → learning plan → salary
            """

            # 1) Occupation Mapping (AI Domain Classification)
            primary_key, occ_meta = get_primary_occupation(parsed_resume)
            all_matches = heuristic_map(parsed_resume, top_n=5)

            # 2) Skill Gaps
            gaps = compute_skill_gaps(parsed_resume, occ_meta)
            missing_top = summarize_gaps(gaps, top_n=5)

            # 3) Learning Plan (6-month default)
            learning_plan = build_learning_plan(gaps, occ_meta, timeframe_months=6)

            # 4) Salary Insights
            salary = get_salary_insight(occ_meta, location="US")

            # === Full engine context ===
            engine_context = {
                "occupation_primary": primary_key,
                "occupation_matches": all_matches,
                "occupation_meta": occ_meta,
                "resume_skill_gaps": gaps,
                "skill_gaps_top": missing_top,
                "learning_plan": learning_plan,
                "salary_insight": salary,
            }

            return engine_context


        def invoke(self, inputs):
            """
            Accepts multiple fields (question, engine_context, context)
            but merges everything into ONE final question string
            because ConversationalRetrievalChain only accepts ONE input key.
            """

            question = inputs.get("question", "")
            engine_ctx = inputs.get("engine_context", None)
            external_ctx = inputs.get("context", "")  # optional frontend-injected

            # Retrieve potential context
            retrieved_docs = self.retriever.invoke(question) or []
            
            # If no relevant documents, skip LLM call
            if not retrieved_docs:
                return {
                    "answer": (
                        "I'm sorry, I can only help with your career growth, "
                        "skills, or learning recommendations."
                    ),
                    "source_documents": []
                }

            resume_context = " ".join([doc.page_content for doc in retrieved_docs])
            #detected_domain = detect_domain(resume_context)
            #recommendations = self.skill_meta.get(detected_domain, {}).get("recommended_skills", [])
            
            merged_question = (
                 f"USER QUESTION:\n{question}\n\n"
                 f"ENGINE CONTEXT:\n{engine_ctx}\n\n"
                 f"RAG RESUME CONTEXT:\n{resume_context}\n\n"
                 f"EXTERNAL CONTEXT (if any):\n{external_ctx}"
            )

            # Pass only ONE input key
            try:
                response = self.base_chain.invoke({"question": merged_question})
            except Exception as e:
                return {"answer": f"Sorry, an internal error occurred: {e}", "source_documents": []}

            return response

            #parsed_resume = inputs.get("parsed_resume")

            #engine_context = {}

            # if parsed_resume:
            #     try:
            #         engine_context = self.build_engine_context(parsed_resume)
            #     except Exception:
            #         engine_context = {"error": f"engine_context_failure: {e}"}
            
            # # Now call LLM with expanded prompt
            # try:
            #     result = self.base_chain.invoke({
            #         "context": resume_context,
            #         "chat_history": [],  # memory injected automatically
            #         "question": question,
            #         "engine_context": json.dumps(engine_context, indent=2)
            #     })

            #     return result
            # except Exception as e:
            #     return {
            #         "answer": f"Internal error in agent: {str(e)}",
            #         "source_documents": []
            #     }
            
            # # Optionally, add dynamic coaching prompt after resume upload
            # if "resume" in question.lower() or "start" in question.lower():
            #     suggestion = ", ".join(recommendations[:3]) if recommendations else "your professional skills"
            #     response["answer"] += (
            #         f"\n\n🚀 Let's begin your learning journey! "
            #         f"Would you like me to assess your current level in {suggestion}?"
            #     )

            # return response

    return ContextAwareAgent(agent, retriever)