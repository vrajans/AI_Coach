import re
from pydantic import BaseModel
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from typing import List, Dict
from .config import settings

class ExperienceItem(BaseModel):
    company: str | None = None
    role: str | None = None
    start: str | None = None
    end: str | None = None
    bullets: List[str] = []

class ResumeSchema(BaseModel):
    full_name: str | None = None
    email: str | None = None
    title: str | None = None
    summary: str | None = None
    skills: List[str] = []
    experience: List[ExperienceItem] = []
    education: List[Dict] = []

parser = PydanticOutputParser(pydantic_object=ResumeSchema)
chat_prompt = ChatPromptTemplate.from_template(
    "You are a resume parser. Extract structured JSON following ResumeSchema. Resume:\n{resume_text}\nReturn JSON only."
)

def parse_resume_with_llm(resume_text: str) -> ResumeSchema:
    """
    Parses resume text using either Azure OpenAI or OpenAI, depending on available environment variables.
    """
    # Prefer Azure if configured
    if settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_API_KEY:
        llm = AzureChatOpenAI(
            azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            temperature=0,
        )
    # Fallback to OpenAI
    elif settings.OPENAI_API_KEY:
        llm = ChatOpenAI(model=settings.MODEL_NAME, temperature=0)
    else:
        raise ValueError(
            "No valid LLM configuration found. Set either Azure OpenAI or OpenAI API credentials."
        )

    # Run the prompt
    msgs = chat_prompt.format_messages(resume_text=resume_text)
    resp = llm.invoke(msgs)
    return parser.parse(resp.content)

def heuristic_parse(resume_text: str) -> ResumeSchema:
    """
    Simple regex-based parsing when LLM is unavailable.
    """
    r = ResumeSchema()
    lines = resume_text.splitlines()
    r.full_name = lines[0].strip().title() if lines else None
    email = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", resume_text)
    r.email = email.group(0) if email else None
    return r