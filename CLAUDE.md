# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PDFReader is a Spring Boot application that acts as a **Java backend proxy** to a separate Python-based PDF parsing service. It exposes a REST API for uploading, querying, and managing PDF documents, forwarding parse requests to the Python service and storing document metadata in MySQL.

## Architecture

Two-service architecture — this repo is the **Java gateway** only:

1. **This Spring Boot app** (port 8080) — REST API, file upload proxy, document metadata storage via JPA/MySQL
2. **External Python parser service** (configured via `parser.service.url`, default `http://localhost:5000`) — performs actual PDF parsing. Must be running independently.

Request flow: `Client → PdfController → PdfParserService → (RestTemplate) → Python service → response`

The Java service does **not** parse PDFs itself. It proxies file uploads to the Python service and relays responses.

## Build Commands

```bash
./gradlew build
./gradlew test
./gradlew test --tests "org.pdfreader.pdfreader.PdfReaderApplicationTests"
./gradlew bootRun
./gradlew clean
```

## Tech Stack

- Spring Boot 2.6.13, Java 8, Gradle
- Spring Data JPA + MySQL 8 (Hibernate dialect: `MySQL8Dialect`)
- Lombok (annotation processor)
- `RestTemplate` for HTTP calls to Python service
- JUnit 5 via spring-boot-starter-test

## Key Configuration

All in `application.yml`, overridable via env vars:

- `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD` — database connection
- `PARSER_SERVICE_URL` — base URL of the Python parser service
- Max file upload: 100MB (`spring.servlet.multipart`)
- JPA `ddl-auto: update` (schema auto-updates on startup)

## API Endpoints

All under `/api/v1`:

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/upload` | Upload PDF (proxied to Python service) |
| GET | `/status/{docId}` | Query parse status |
| GET | `/content/{docId}` | Get parsed content (filter by `contentType`, `page`) |
| GET | `/documents` | List all documents |
| DELETE | `/document/{docId}` | Delete document |

## Package Layout

Base package: `org.pdfreader.pdfreader`

- `controller/PdfController` — REST endpoints
- `service/PdfParserService` — proxies requests to Python service, uses `PdfDocumentRepository` for document listing
- `entity/PdfDocument`, `entity/PdfContent` — JPA entities (`pdf_document`, `pdf_content` tables)
- `repository/` — Spring Data JPA interfaces
- `dto/ParseResponse`, `dto/ContentResponse` — response DTOs
- `config/ParserConfig` — `RestTemplate` bean + parser URL config
