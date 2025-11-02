from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import shutil, uuid
from pathlib import Path
from .resume_loader import load_resume
from .resume_parser import parse_resume_with_llm, heuristic_parse
from .resume_rag import create_resume_rag
from .agent_core import build_resume_agent
from .config import settings
from langchain_chroma import Chroma
from tempfile import gettempdir
import os
from langchain_openai import OpenAIEmbeddings, AzureOpenAIEmbeddings
from fastapi.middleware.cors import CORSMiddleware


# === FastAPI Setup ===
app = FastAPI(title="AI Career Coach", version="1.0")

#app.mount("/static", StaticFiles(directory="app/static"), name="static")
#app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

# Allow frontend JS calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory user DB (user_id → Chroma + parsed resume)
USER_DB = {}


# @app.get("/")
# async def root():
#     return FileResponse("app/static/index.html")

# === Resume Upload Endpoint ===
@app.post("/upload_resume/")
async def upload_resume(file: UploadFile = File(...), user_id: str = Form(None)):
    if user_id is None:
        user_id = str(uuid.uuid4())

    temp_dir = gettempdir()  # automatically picks a valid temp dir (Windows/Linux/macOS)
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"{user_id}_{file.filename}")

    with open(temp_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)
    

    docs = load_resume(temp_path)
    text = "\n\n".join([d.page_content for d in docs])
    try:
        parsed = parse_resume_with_llm(text).dict()
    except Exception:
        parsed = heuristic_parse(text).dict()
    store = create_resume_rag(docs, user_id)
    USER_DB[user_id] = {"chroma": settings.CHROMA_PERSIST_DIR, "parsed": parsed}
    return {"user_id": user_id, "parsed_resume": parsed}

# === Chat Endpoint ===
@app.post("/chat/{user_id}")
async def chat(user_id: str, payload: dict):
    if user_id not in USER_DB:
        return {"error": "Upload resume first"}
    
    # Use the same embedding model used during resume upload
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
        persist_directory=USER_DB[user_id]["chroma"])
    

    agent = build_resume_agent(chroma)

    # result = agent.run(payload.get("message"))
    # return {"answer": result}
    response = agent.invoke({"question": payload.get("message")})
    return {"answer": response["answer"]}

# === Serve Frontend (keep last!) ===
# This serves your frontend (index.html, main.js, style.css, etc.)
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")