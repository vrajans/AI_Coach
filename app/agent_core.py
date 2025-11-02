import json
from pathlib import Path
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_classic.chains import ConversationalRetrievalChain
from langchain_classic.memory import ConversationBufferMemory
from langchain_core.prompts import PromptTemplate
from .config import settings

def build_resume_agent(chroma_store, mode="resume_coach"):
    """
    Builds a multi-persona AI Career Coach:
    - Reads prompt from /prompts/<mode>.txt
    - Loads domain/skill metadata from JSON
    - Adapts responses based on detected user domain
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
        input_variables=["context", "chat_history", "question"],
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

        def invoke(self, inputs):
            question = inputs.get("question", "")
            # Retrieve potential context
            retrieved_docs = self.retriever.invoke(question)
            
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
            detected_domain = detect_domain(resume_context)
            recommendations = self.skill_meta.get(detected_domain, {}).get("recommended_skills", [])
            
            # Else, pass the question to the main conversational chain
            try:
                return self.base_chain.invoke(inputs)
            except Exception as e:
                response = {"answer": f"Sorry, an internal error occurred: {e}", "source_documents": []}
            
            # Optionally, add dynamic coaching prompt after resume upload
            if "resume" in question.lower() or "start" in question.lower():
                suggestion = ", ".join(recommendations[:3]) if recommendations else "your professional skills"
                response["answer"] += (
                    f"\n\n🚀 Let's begin your learning journey! "
                    f"Would you like me to assess your current level in {suggestion}?"
                )

            return response

    return ContextAwareAgent(agent, retriever)