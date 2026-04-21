# AGENTS.md

## Critical Setup

- **Python service must be running separately** at `http://localhost:5000` (configurable via `PARSER_SERVICE_URL`)
- **MySQL must be accessible** — both Java and Python services use MySQL (same database: `pdf_reader`)
- Server runs on port **9090** (not 8080)

## Commands

```bash
./gradlew build          # Build JAR
./gradlew bootRun        # Run application (port 9090)
./gradlew test           # Run all tests
./gradlew test --tests "org.pdfreader.pdfreader.PdfReaderApplicationTests"  # Single test
./gradlew clean          # Clean build
```

## Key Facts

- This is a **proxy service only** — does NOT parse PDFs itself
- Request flow: `Client → PdfController → PdfParserService → Python service`
- JPA `ddl-auto: update` — schema auto-creates/updates on startup
- Lombok annotation processor required for IDE
- Java 8 compatibility (`sourceCompatibility: '1.8'`)
- Python service uses FastAPI + PaddleOCR + pdfplumber

## Configuration

| Env Variable | Default | Purpose |
|--------------|---------|---------|
| MYSQL_HOST | localhost | Database host |
| MYSQL_PORT | 3306 | Database port |
| MYSQL_DATABASE | pdf_reader | Database name |
| MYSQL_USER | root | Database user |
| MYSQL_PASSWORD | Zhang123456!@ | Database password |
| PARSER_SERVICE_URL | http://localhost:5000 | Python service URL |

## API Endpoints

All under `/api/v1`:
- `POST /upload` — Upload PDF (proxied to Python)
- `GET /status/{docId}` — Query parse status
- `GET /content/{docId}` — Get parsed content
- `GET /documents` — List all documents
- `DELETE /document/{docId}` — Delete document