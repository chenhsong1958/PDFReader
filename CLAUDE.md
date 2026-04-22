# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PDFReader is a two-service PDF document parsing system:

1. **Java Spring Boot** (port 9090) — REST API gateway, proxies requests to Python service
2. **Python FastAPI** (port 5000) — PDF parsing engine with OCR support, located in `pdf-parser-service/`

Both services share the same MySQL database. The Java service does not parse PDFs — it forwards uploads to the Python service via `RestTemplate`.

## Build & Run Commands

**Java Service:**
```bash
./gradlew build
./gradlew test
./gradlew bootRun
```

**Python Service:**
```bash
cd pdf-parser-service
pip install -r requirements.txt
python main.py
# or: uvicorn main:app --host 0.0.0.0 --port 5000
```

**Database:**
```bash
mysql -u root -p < sql/init.sql
```

## Architecture

```
Client → Java (9090) → Python (5000) → MySQL
                ↓
         RestTemplate proxy
```

**Java** (`org.pdfreader.pdfreader`):
- `controller/PdfController` — REST endpoints, proxies to Python
- `service/PdfParserService` — HTTP client to Python service
- `entity/` — JPA entities (PdfDocument, PdfContent)
- `config/ParserConfig` — RestTemplate bean + parser URL config

**Python** (`pdf-parser-service/app/`):
- `api/routes.py` — FastAPI endpoints, background task processing
- `services/pdf_parser.py` — Core parsing: PyMuPDF + pdfplumber for text, PaddleOCR for images
- `models/` — SQLAlchemy models (PdfDocument, PdfContent, KeyConfig, KeyData)

## Key Configuration

**Java** (`application.yml`):
- `MYSQL_HOST/PORT/DATABASE/USER/PASSWORD` — database
- `PARSER_SERVICE_URL` — Python service URL (default `http://localhost:5000`)
- Server port: 9090

**Python** (`.env` or env vars):
- `MYSQL_HOST/PORT/DATABASE/USER/PASSWORD` — database
- `OCR_ENABLED`, `OCR_LANG` (default `ch`), `OCR_USE_GPU`
- `UPLOAD_DIR` (default `./uploads`)

## API Endpoints

All under `/api/v1` on both services:

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/upload` | Upload PDF (async parsing in background) |
| GET | `/status/{docId}` | Query parse status |
| GET | `/content/{docId}` | Get parsed content (filter: `contentType`, `page`) |
| GET | `/key-values/{docId}` | Get extracted key-value pairs |
| GET | `/documents` | List all documents |
| DELETE | `/document/{docId}` | Delete document |
| POST | `/reparse/{docId}` | Re-parse existing document |
| GET/POST/PUT/DELETE | `/keys` | Keyword config CRUD |

## Database Tables

- `pdf_document` — document metadata, status, page count
- `pdf_content` — extracted text/tables per page
- `key_config` — user-defined keywords for extraction (e.g., "物料编码" with aliases)
- `key_data` — extracted key-value results
- `pdf_document_relation` — document relationships (main/sub drawings)

## PDF Parsing Flow

1. Upload → Python saves file, creates `PdfDocument` (status: pending)
2. Background task: classify pages (text vs image based on text threshold)
3. Text pages: pdfplumber extracts text/tables
4. Image pages: PaddleOCR extracts text, detects table structures
5. Extract key-values from text, tables, and OCR spatial data
6. Save to `pdf_content` and `key_data`, update status to completed/failed
