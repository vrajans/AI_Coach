from pathlib import Path
from langchain_core.documents import Document
import docx2txt
from PyPDF2 import PdfReader

def load_pdf(path: str):
    reader = PdfReader(path)
    return [Document(page_content=p.extract_text() or "", metadata={"source": path}) for p in reader.pages]

def load_docx(path: str):
    text = docx2txt.process(path)
    return [Document(page_content=text, metadata={"source": path})]

def load_resume(file_path: str):
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return load_pdf(file_path)
    elif ext in (".docx", ".doc"):
        return load_docx(file_path)
    else:
        raise ValueError(f"Unsupported resume format: {ext}")
