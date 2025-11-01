from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_classic.chains import ConversationalRetrievalChain
from langchain_classic.memory import ConversationBufferMemory
from langchain_core.prompts import PromptTemplate
from .config import settings

def build_resume_agent(chroma_store):
    retriever = chroma_store.as_retriever(search_kwargs={"k": 4})

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

    memory = ConversationBufferMemory(
        memory_key="chat_history", 
        return_messages=True,
        output_key="answer"
    )

    # Custom Prompt — restrict to context-only answers
    template = """
    You are an **AI Career Transformation Coach**.

    Your mission:
    - Help users move from their current skill level → to expert level.
    - Analyze their resume, identify current expertise and learning gaps.
    - Recommend clear, structured next steps — each as small, achievable goals.
    - Engage interactively (offer options, e.g., “Would you like to start with SQL Optimization or Azure Data Factory?”).
    - Track their learning progress in conversation.
    - Use the context only (resume + chat history).

    **Rules:**
    - Stay focused on career, skills, and professional growth.
    - Never answer outside of career or learning context.
    - Respond in a motivational, mentor-like tone.
    - If the question is unrelated to resume, job profile, career development, learning context , or skills, respond with:
      "I'm sorry, I can only answer questions related to your resume, learning context, job profile, or career advice."

    Context:
    {context}

    Chat History:
    {chat_history}

    Question:
    {question}

    Your Response:
    """

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

    # Wrapper to add context check before invoking the model
    class ContextAwareAgent:
        def __init__(self, base_chain, retriever):
            self.base_chain = base_chain
            self.retriever = retriever

        def invoke(self, inputs):
            question = inputs.get("question", "")
            # Retrieve potential context
            retrieved_docs = self.retriever.invoke(question)
            
            # If no relevant documents, skip LLM call
            if not retrieved_docs:
                return {
                    "answer": (
                        "I'm sorry, I can only answer questions related to your resume, "
                        "job profile, or career advice."
                    ),
                    "source_documents": []
                }
            
            # Else, pass the question to the main conversational chain
            return self.base_chain.invoke(inputs)

    return ContextAwareAgent(agent, retriever)