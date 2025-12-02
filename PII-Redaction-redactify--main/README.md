# PII Redactor - Local Only

Features:
- Regex + spaCy NER PII detection
- Text redaction (placeholder, mask, blackout, whiteout)
- Visual PDF redaction (layout preserved using PyMuPDF)
- Batch redaction (.txt and .pdf)
- Streamlit UI + FastAPI backend 

## Installation

pip install -r requirements.txt
python -m spacy download en_core_web_sm

## Running Streamlit

streamlit run ui/web/app.py

## Running API

uvicorn api.main:app --reload
