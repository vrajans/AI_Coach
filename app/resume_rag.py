from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, AzureOpenAIEmbeddings
from langchain_chroma import Chroma
from .config import settings

def create_resume_rag(docs, user_id: str):
    """
    Creates a vector store from the user's resume using either Azure or OpenAI embeddings.
    """
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    chunks = splitter.split_documents(docs)

    # ✅ Prefer Azure OpenAI embeddings if available
    if settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_API_KEY:
        embeddings = AzureOpenAIEmbeddings(
            azure_deployment=settings.AZURE_EMBEDDING_DEPLOYMENT_NAME or "text-embedding-3-small",
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
        )
    # ✅ Fallback to standard OpenAI embeddings
    elif settings.OPENAI_API_KEY:
        embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    else:
        raise ValueError(
            "No valid embedding configuration found. Set either Azure OpenAI or OpenAI API credentials."
        )

    # Create and persist Chroma vector store
    store = Chroma.from_documents(
        chunks,
        embeddings,
        collection_name=f"user_{user_id}",
        persist_directory=settings.CHROMA_PERSIST_DIR,
    )
    #store.persist()
    return store