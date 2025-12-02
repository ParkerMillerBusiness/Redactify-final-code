import sys
from pathlib import Path
import io
import zipfile

import fitz  # PyMuPDF
import streamlit as st

# Make project root importable (so core/ and api/ work)
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pipeline import redact_text
from core.policy import load_policy
from core.redact_pdf import redact_pdf_bytes



def extract_text_from_pdf_bytes(data: bytes) -> str:
    """Extract plain text from a PDF (one big string)."""
    doc = fitz.open(stream=data, filetype="pdf")
    texts = []
    for page in doc:
        texts.append(page.get_text("text"))
    doc.close()
    return "\n\n".join(texts)


st.set_page_config(
    page_title="Redactify – PII Redactor",
    layout="wide",
)

st.title("🔒 Redactify – PII Redaction Demo")
st.caption("Regex + spaCy NER • Local-only • No external LLMs")

# --------------------------------------------------------------------
# Sidebar configuration
# --------------------------------------------------------------------
st.sidebar.header("Settings")

policy_path = st.sidebar.text_input(
    "Policy file path",
    value="configs/policy.yaml",
    help="Path to the YAML policy file.",
)

policy_ok = True
policy = None
entity_choices = []
try:
    policy = load_policy(policy_path)
    entity_choices = sorted(policy.entities.keys())
except Exception as e:
    policy_ok = False
    st.sidebar.error(f"Failed to load policy: {e}")

mode = st.sidebar.selectbox(
    "Redaction mode",
    options=["placeholder", "mask", "blackout", "whiteout"],
    index=0,
    help=(
        "placeholder: PERSON_1, ADDRESS_1, ...\n"
        "mask: j***e@domain.com, (***) ***-1234\n"
        "blackout: █ characters over PII\n"
        "whiteout: spaces over PII"
    ),
)

if entity_choices:
    selected_entities = st.sidebar.multiselect(
        "PII categories to redact",
        options=entity_choices,
        default=entity_choices,
        help="Uncheck an entity type to leave it untouched in the output.",
    )
else:
    selected_entities = []

st.sidebar.markdown("---")

operation_mode = st.sidebar.radio(
    "Processing mode",
    options=["Single document", "Batch files"],
    index=0,
    help="Single document: paste text or upload 1 file.\nBatch: upload multiple .txt/.pdf files.",
)

show_span_table = st.sidebar.checkbox("Show PII span table", value=True)

# --------------------------------------------------------------------
# SINGLE DOCUMENT MODE
# --------------------------------------------------------------------
if operation_mode == "Single document":
    st.subheader("Single document redaction")

    input_mode = st.radio(
        "Input source",
        options=["Text box", "Text file"],
        index=0,
    )

    default_text = (
        "Patient John Doe visited St. Mary Hospital in Austin on 05/21/1984.\n"
        "Contact: john.doe@clinic.org, phone: (555) 123-4567.\n"
        "SSN: 123-45-6789. Card: 4111-1111-1111-1111."
    )

    user_text = ""

    if input_mode == "Text box":
        user_text = st.text_area(
            "Input text",
            value=default_text,
            height=250,
            help="Paste or type the text you want to redact.",
        )
    else:
        # keep extracted text and PDF bytes across reruns
        if "uploaded_text" not in st.session_state:
            st.session_state["uploaded_text"] = ""
        if "uploaded_pdf_bytes" not in st.session_state:
            st.session_state["uploaded_pdf_bytes"] = None
        if "uploaded_suffix" not in st.session_state:
            st.session_state["uploaded_suffix"] = None

        uploaded = st.file_uploader(
            "Upload a .txt or .pdf file",
            type=["txt", "pdf"],
            help="Upload a plain text file or a PDF. PDFs will be converted to text.",
        )

        if uploaded is not None:
            suffix = Path(uploaded.name).suffix.lower()
            st.session_state["uploaded_suffix"] = suffix

            if suffix == ".pdf":
                data = uploaded.read()
                st.session_state["uploaded_pdf_bytes"] = data
                try:
                    text = extract_text_from_pdf_bytes(data)
                except Exception as e:
                    st.error(f"Failed to extract text from PDF: {e}")
                    text = ""
            else:
                # plain text file
                st.session_state["uploaded_pdf_bytes"] = None
                text = uploaded.read().decode("utf-8", errors="ignore")

            st.session_state["uploaded_text"] = text
            user_text = text

            if not text.strip() and suffix == ".pdf":
                st.warning(
                    "No text could be extracted from this PDF. "
                    "It may be a scanned/image-only document."
                )
            else:
                st.text_area(
                    "Preview of uploaded text (first 5000 chars)",
                    value=(text[:5000] if text else ""),
                    height=250,
                )
        else:
            user_text = st.session_state.get("uploaded_text", "")
            if not user_text:
                st.info("Upload a .txt or .pdf file to get started.")


    col_btn, _ = st.columns([1, 5])
    with col_btn:
        run_btn = st.button("🔧 Redact", type="primary", use_container_width=True)

    redacted_text = ""
    spans = []
    redacted_pdf_bytes = None  # NEW

    if run_btn:
        if not policy_ok:
            st.error("Cannot run redaction because policy failed to load. Check sidebar.")
        elif not user_text.strip():
            st.warning("Please enter or upload some text first.")
        else:
            with st.spinner("Redacting..."):
                allowed = selected_entities if selected_entities else []
                redacted_text, spans = redact_text(
                    text=user_text,
                    policy_path=policy_path,
                    mode=mode,
                    allowed_entities=allowed,
                )

                # If original was a PDF and we're in a visual mode, build a redacted PDF
                if (
                    st.session_state.get("uploaded_suffix") == ".pdf"
                    and st.session_state.get("uploaded_pdf_bytes") is not None
                    and mode in ("blackout", "whiteout")
                ):
                    try:
                        redacted_pdf_bytes = redact_pdf_bytes(
                            st.session_state["uploaded_pdf_bytes"],
                            policy_path=policy_path,
                            mode=mode,
                        )
                    except Exception as e:
                        st.error(f"Failed to visually redact PDF: {e}")
                        redacted_pdf_bytes = None

            st.success(f"Redaction complete. Detected {len(spans)} PII spans (after filtering).")

            col_orig, col_red = st.columns(2)

            with col_orig:
                st.subheader("Original")
                st.code(user_text, language="text")

            with col_red:
                st.subheader("Redacted")
                st.code(
                    redacted_text or "No changes (check PII selection & mode).",
                    language="text",
                )

            # Text download (for inspection)
            if redacted_text:
                st.download_button(
                    label="⬇️ Download redacted text",
                    data=redacted_text,
                    file_name="redacted.txt",
                    mime="text/plain",
                )

            # PDF download (layout-preserving blackout/whiteout)
            if redacted_pdf_bytes:
                st.download_button(
                    label="⬇️ Download redacted PDF",
                    data=redacted_pdf_bytes,
                    file_name="redacted.pdf",
                    mime="application/pdf",
                )

            if show_span_table and spans:
                st.markdown("### Detected PII spans")
                rows = []
                for s in spans:
                    rows.append(
                        {
                            "start": s.start,
                            "end": s.end,
                            "entity": s.ent,
                            "source": s.source,
                            "confidence": round(s.conf, 3),
                            "original": user_text[s.start:s.end],
                            "replacement": s.replacement,
                        }
                    )
                st.dataframe(rows, use_container_width=True)


# --------------------------------------------------------------------
# BATCH FILE MODE
# --------------------------------------------------------------------
else:
    st.subheader("Batch redaction for multiple .txt/.pdf files")

    uploaded_files = st.file_uploader(
        "Upload one or more .txt or .pdf files",
        type=["txt", "pdf"],
        accept_multiple_files=True,
        help="Each file will be processed independently with the same policy/mode/PII categories. PDFs are converted to text.",
    )

    run_batch_btn = st.button("🔧 Redact batch", type="primary")

    if run_batch_btn:
        if not policy_ok:
            st.error("Cannot run redaction because policy failed to load. Check sidebar.")
        elif not uploaded_files:
            st.warning("Please upload at least one file.")
        else:
            allowed = selected_entities if selected_entities else []
            results = []

            with st.spinner("Redacting batch..."):
                for file in uploaded_files:
                    suffix = Path(file.name).suffix.lower()

                    if suffix == ".pdf":
                        data = file.read()
                        try:
                            raw = extract_text_from_pdf_bytes(data)
                        except Exception as e:
                            st.error(f"Failed to extract text from PDF {file.name}: {e}")
                            raw = ""
                    else:
                        raw = file.read().decode("utf-8", errors="ignore")

                    redacted_text, spans = redact_text(
                        text=raw,
                        policy_path=policy_path,
                        mode=mode,
                        allowed_entities=allowed,
                    )

                    total_spans = len(spans)
                    by_ent = {}
                    for s in spans:
                        by_ent[s.ent] = by_ent.get(s.ent, 0) + 1

                    results.append(
                        {
                            "filename": file.name,
                            "original_text": raw,
                            "redacted_text": redacted_text,
                            "spans": spans,
                            "total_spans": total_spans,
                            "by_ent": by_ent,
                        }
                    )

            if not results:
                st.info("No results produced (files may have been empty).")
            else:
                st.success(f"Batch redaction complete for {len(results)} file(s).")

                summary_rows = []
                for r in results:
                    ent_summary = ", ".join(
                        f"{ent}:{count}" for ent, count in sorted(r["by_ent"].items())
                    )
                    summary_rows.append(
                        {
                            "filename": r["filename"],
                            "total_spans": r["total_spans"],
                            "entities": ent_summary,
                        }
                    )

                st.markdown("### Batch summary")
                st.dataframe(summary_rows, use_container_width=True)

                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    for r in results:
                        base = Path(r["filename"]).stem
                        out_name = f"{base}_redacted.txt"
                        zf.writestr(out_name, r["redacted_text"])
                zip_buffer.seek(0)

                st.download_button(
                    label="⬇️ Download all redacted files (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name="redacted_batch.zip",
                    mime="application/zip",
                )

                first = results[0]
                st.markdown("### Preview of first redacted file")
                col_o, col_r = st.columns(2)
                with col_o:
                    st.caption(f"Original – {first['filename']}")
                    st.code(first["original_text"], language="text")
                with col_r:
                    st.caption(f"Redacted – {first['filename']}")
                    st.code(first["redacted_text"], language="text")
