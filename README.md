# GovLetter-RAG (MVP)

GovLetter-RAG is a retrieval-augmented generation (RAG) service that prepares
legally grounded draft letters for Polish public administration. The service is
implemented as a FastAPI application that orchestrates document retrieval,
prompt assembly, LLM invocation and rigorous post-processing.

## Features

- FastAPI service exposing `GET /healthz` and `POST /generate-draft`
- Retrieval layer powered by **sentence-transformers** embeddings and a local
  **FAISS** index with heuristic reranking for binding laws and document
  recency
- Hybrid legal-aware chunking that respects articles/paragraphs and token
  budgets (~1000 tokens with 150-token overlap)
- Prompt builder applying system rules, JSON-schema hints, and PII masking prior
  to calling the LLM
- Post-processing that validates JSON schema compliance, enforces ≥2 citations,
  checks legal basis, flags duplicates (RapidFuzz) and surfaces RODO risks
- CLI ingestion pipeline (`python -m app.ingest`) for PDFs/TXTs with YAML
  sidecars to build the FAISS index

## Project layout

```
app/
├── chunking.py            # Hybrid legal chunking utilities
├── config.py              # Environment-driven configuration
├── ingest.py              # CLI for document ingestion
├── logging_config.py      # Structured logging setup
├── main.py                # FastAPI entrypoint
├── postprocessing.py      # Output validation & risk checks
├── prompting.py           # Prompt assembly + PII masking
├── retrieval.py           # FAISS retrieval + reranking
├── schemas.py             # Pydantic models & JSON contracts
└── services/
    └── llm_client.py      # OpenAI chat completion client
```

Supporting directories:

- `app/store/` – Persisted FAISS index (`index.faiss`) and fragment metadata
  (`meta.json`)
- `data/docs/` – Source documents (`*.pdf`/`*.txt`) with accompanying
  `*.meta.yaml` metadata files

## Getting started

1. **Create and activate a virtual environment** (Python 3.11):

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables** by copying the template and filling in
   credentials:

   ```bash
   cp .env.example .env
   # Edit .env to provide OPENAI_API_KEY and other overrides
   ```

## Ingesting documents

Prepare at least two legal documents (PDF or UTF-8 TXT) along with YAML metadata
files containing fields such as `doc_id`, `tytul`, `data_dokumentu` (ISO date)
and `is_binding_law`. Example metadata file `ustawa.meta.yaml`:

```yaml
doc_id: ustawa-abc
tytul: Ustawa o przykładach
data_dokumentu: 2023-02-15
is_binding_law: true
```

Place the pairs into `data/docs/` and run the ingestion command to populate the
FAISS index and metadata store:

```bash
python -m app.ingest --docs data/docs --store app/store
```

This generates `app/store/index.faiss` and `app/store/meta.json` referenced by
the API service.

## Running the API service

Launch the development server with auto-reload:

```bash
uvicorn app.main:app --reload --port 8000
```

- `GET /healthz` – liveness check
- `POST /generate-draft` – generate a draft letter

### Sample request payload

```json
{
  "query": "Proszę o przygotowanie odpowiedzi na wniosek dotyczący udostępnienia informacji publicznej.",
  "case_meta": {
    "case_id": "ABC-123",
    "applicant_type": "osoba fizyczna"
  },
  "template_hint": "ack",
  "history": []
}
```

If `context_docs` is omitted, the service performs retrieval using the FAISS
index. When fragments are supplied explicitly via `context_docs`, retrieval is
skipped and the provided fragments are used directly.

## Draft validation & risk reporting

The service enforces several guardrails before returning a draft:

- Output **must** contain at least two citations and a non-empty `legal_basis`
  section (violations produce a 502 error)
- Duplicate drafts are detected against the `history` payload using RapidFuzz
  token-set similarity; matches populate `risks.duplicate_of`
- Regex-based PII detection runs both on outbound prompts and on the generated
  body, setting `risks.risk_rodo` when detected

## Security and privacy considerations

- Only the minimal redacted information (query, selected fragments, case
  metadata) is sent to the LLM provider
- `.env` stores credentials locally; consider moving to a secret manager for
  production
- Logging excludes raw document text and PII, recording only operational
  metadata (request ID, timing, fragment IDs, risk flags)

## Evaluation roadmap

The MVP targets:

- Retrieval: Recall@12 ≥ 0.9 on curated evaluation queries
- Generation: ≥90% drafts passing automated JSON/citation/legal_basis checks
- Latency: 8–12s p50 end-to-end (LLM dependent)

Future enhancements include migrating to Qdrant, integrating cross-encoder
reranking, function-calling outputs, advanced PII detection (spaCy/Presidio),
and OCR support for scanned PDFs.
