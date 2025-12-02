import os
import logging
import logging.config

import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import RedactRequest, RedactResponse, SpanSchema
from core.pipeline import redact_text


def setup_logging():
    cfg_path = os.path.join("configs", "logging.yaml")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            os.makedirs("logs", exist_ok=True)
            logging.config.dictConfig(config)
        except Exception as e:
            print(f"[logging] Failed to load logging.yaml: {e}")
            logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.INFO)


setup_logging()
logger = logging.getLogger("api")

app = FastAPI(
    title="PII Redactor",
    version="0.1.0",
    description="PII redaction using regex + spaCy NER (no external LLMs).",
)

# Allow React dev server and your future domain
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://redactify.xyz",          # adjust later to your actual frontend URL
    "https://www.redactify.xyz",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/redact", response_model=RedactResponse)
def redact(req: RedactRequest) -> RedactResponse:
    logger.info("Received /redact request")
    redacted, spans = redact_text(
        text=req.text,
        policy_path=req.policy_name,
        mode=req.mode,
    )
    span_schemas = [
        SpanSchema(
            start=s.start,
            end=s.end,
            ent=s.ent,
            conf=s.conf,
            source=s.source,
            replacement=s.replacement,
        )
        for s in spans
    ]
    return RedactResponse(redacted_text=redacted, spans=span_schemas)
