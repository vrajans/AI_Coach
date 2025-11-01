# AI Coach MVP

Resume-first AI Coach MVP using FastAPI + LangChain + Streamlit.

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY="your-key"
```

## Run
```bash
uvicorn app.main:app --reload --port 8000
streamlit run ui/app_ui.py
```

Then open http://localhost:8501
