# app/main.py
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
import shutil, uuid, os
from pathlib import Path
from .resume_loader import load_resume
from .resume_parser import parse_resume_with_llm, heuristic_parse
from .resume_rag import create_resume_rag
from .agent_core import build_resume_agent
from .config import settings
from langchain_chroma import Chroma
from tempfile import gettempdir
from langchain_openai import OpenAIEmbeddings, AzureOpenAIEmbeddings
from fastapi.middleware.cors import CORSMiddleware
from .integrations.dynamic_learning import get_learning_resources
from .integrations.dynamic_salary import get_salary_for_role

app = FastAPI(title="AI Career Coach", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

USER_DB = {}

# Upload endpoint
@app.post("/upload_resume/")
async def upload_resume(file: UploadFile = File(...), user_id: str = Form(None)):
    if user_id is None:
        user_id = str(uuid.uuid4())

    temp_dir = gettempdir()
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"{user_id}_{file.filename}")

    with open(temp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    docs = load_resume(temp_path)
    text = "\n\n".join([d.page_content for d in docs])

    try:
        parsed = parse_resume_with_llm(text).dict()
    except Exception:
        parsed = heuristic_parse(text).dict()

    # Build RAG store and persist
    store = create_resume_rag(docs, user_id)

    USER_DB[user_id] = {
        "chroma": settings.CHROMA_PERSIST_DIR,
        "parsed": parsed
    }

    return {"user_id": user_id, "parsed_resume": parsed}


@app.post("/chat/{user_id}")
async def chat(user_id: str, payload: dict):
    if user_id not in USER_DB:
        return {"error": "Upload resume first"}

    # Embedding selection
    if settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_API_KEY:
        embeddings = AzureOpenAIEmbeddings(
            azure_deployment=settings.AZURE_EMBEDDING_DEPLOYMENT_NAME or "text-embedding-3-small",
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
        )
    else:
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    chroma = Chroma(
        collection_name=f"user_{user_id}",
        embedding_function=embeddings,
        persist_directory=USER_DB[user_id]["chroma"]
    )

    agent = build_resume_agent(chroma)

    question = payload.get("message", "") or ""
    engine_context = payload.get("engine_context", "")

    # Invoke agent (synchronous); returns stable dict
    try:
        result = agent.invoke({"question": question, "engine_context": engine_context})
    except Exception as e:
        # fail-safe: return polite error
        return {"answer": f"Internal error invoking agent: {e}"}

    answer = result.get("answer", "")
    intent = result.get("intent", "general")
    engine_used = result.get("engine_context_used", None)
    learning_plan = result.get("learning_plan", None)
    source_documents = result.get("source_documents", [])

    # Post-enrich learning/salary only for relevant queries (still safe)
    parsed_resume = USER_DB[user_id].get("parsed", {})
    job_title = parsed_resume.get("job_title") or question

    # If user asked about learning/salary, add top links (non-breaking)
    if any(w in question.lower() for w in ["learn", "career", "job", "path", "salary", "course"]):
        try:
            learning = get_learning_resources(job_title)
            salary = get_salary_for_role(job_title)
        except Exception:
            learning = []
            salary = {}

        if learning:
            answer += "\n\n**Recommended Learning Paths:**"
            for c in learning:
                answer += f"\n- [{c.get('title')}]({c.get('url')}) ({c.get('platform','Unknown')})"

        if salary and salary.get("average_salary"):
            answer += (
                f"\n\n💰 **Average Salary in {salary.get('location','N/A')}:** "
                f"{salary.get('average_salary')} (Source: {salary.get('source','N/A')})"
            )

    # Always return consistent JSON-friendly structure
    return {
        "answer": answer,
        "intent": intent,
        "engine_context_used": engine_used,
        "learning_plan": learning_plan,
        "source_documents": source_documents,
    }


# Serve frontend
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
