# FastAPI Learning Guide For This Project

## Why FastAPI Fits This App

FastAPI is a strong choice here because it gives us:

- clear request and response models with Pydantic
- automatic validation
- automatic OpenAPI docs
- simple file upload handling
- good structure for building API-first backends

For this invoice app, FastAPI will mainly handle:

- receiving uploaded CSV files
- validating incoming data
- returning structured JSON responses
- streaming ZIP downloads back to the browser

## How To Think About FastAPI

In this project, the backend should be split into three layers:

1. Routes
2. Schemas
3. Services

### Routes

Routes define API endpoints such as:

- `POST /api/csv/validate`
- `POST /api/invoices/preview`
- `POST /api/invoices/generate`

The route should stay thin:

- receive input
- call service functions
- return a response

### Schemas

Schemas are Pydantic models that define what data is allowed.

Examples for this project:

- invoice row model
- validation error model
- preview response model

Schemas are one of the best parts of FastAPI, because they make the contract explicit and self-documenting.

### Services

Services hold business logic.

Examples for this project:

- parse CSV
- validate rows
- calculate totals
- generate PDFs
- build ZIP archive

This keeps `main.py` small and makes the code easier to test.

## What You Already Have

The current backend already demonstrates the basic FastAPI pattern in [backend/app/main.py](/Users/aweigl/Desktop/Projects/invoice-creator/backend/app/main.py).

It already includes:

- a FastAPI app instance
- CORS middleware
- Pydantic request models
- a health endpoint
- a simple invoice preview endpoint

That means the foundation is already good for learning the next steps.

## FastAPI Concepts To Learn First

### 1. Request Models

FastAPI uses Pydantic models to validate incoming JSON.

Current example:

- `InvoiceItem`
- `InvoicePreviewRequest`

Why this matters:

- you get typed Python objects
- invalid payloads are rejected automatically
- error responses are generated for you

### 2. Response Models

You can also define models for outgoing data.

That helps keep API responses:

- consistent
- documented
- easier for the frontend to rely on

For this app, response models would be useful for:

- validation summaries
- preview payloads
- generation results

### 3. File Uploads

For CSV upload, you will learn `UploadFile` and `File`.

Typical pattern:

```python
from fastapi import File, UploadFile

@app.post("/api/csv/validate")
async def validate_csv(file: UploadFile = File(...)):
    ...
```

This is important because the app's main input is a user-uploaded CSV file.

### 4. Dependency Injection

FastAPI supports dependencies with `Depends`.

You do not need this immediately for the MVP, but it becomes useful later for:

- config loading
- database sessions
- authentication

For now, you can keep things simple and introduce dependencies only when needed.

### 5. Streaming Responses

When the app generates a ZIP file, you may want to return it using:

- `StreamingResponse`
- or `Response` with the correct media type

That is the FastAPI concept most relevant to the download step.

## Suggested Learning Path In This Repo

### Step 1. Read The Existing App

Study [backend/app/main.py](/Users/aweigl/Desktop/Projects/invoice-creator/backend/app/main.py) and identify:

- where the routes are
- where the request models are
- how the JSON response is returned

### Step 2. Extract Schemas

Move the inline Pydantic classes from `main.py` into `app/schemas.py`.

You will learn:

- how to organize FastAPI projects
- how imports are structured
- how to separate API contracts from route logic

### Step 3. Add CSV Validation Endpoint

Build `POST /api/csv/validate`.

You will learn:

- file upload handling
- CSV parsing with Python's `csv` module
- structured validation responses

### Step 4. Add Service Modules

Create service files for parsing and validation.

You will learn:

- how to keep routes thin
- how to test business logic separately from HTTP handling

### Step 5. Add Preview And Generation Models

Expand the preview endpoint so it works with the actual invoice-row schema instead of the current demo payload.

You will learn:

- model design
- response shaping
- keeping frontend and backend in sync

### Step 6. Add PDF And ZIP Generation

Generate PDFs from validated invoice data and return a ZIP download.

You will learn:

- binary responses
- content types
- in-memory file handling

## Suggested FastAPI File Structure

```text
backend/app/
  main.py
  config.py
  schemas.py
  services/
    csv_parser.py
    validator.py
    invoice_calculator.py
    pdf_renderer.py
    zip_bundle.py
```

This structure is simple enough for learning but scalable enough for real work.

## Example FastAPI Flow For CSV Validation

This is the mental model to keep in mind:

1. Route receives `UploadFile`
2. Route reads file contents
3. CSV parser converts rows to Python dictionaries
4. Validator checks required fields and values
5. Route returns a structured JSON summary

That means FastAPI itself is not doing all the work. It is the HTTP layer around your business logic.

## Best Practices For This Project

- keep route functions short
- move calculation logic into service functions
- define explicit Pydantic models
- return consistent error shapes
- avoid putting PDF generation logic directly in route handlers
- write pure functions where possible for easier testing

## FastAPI Features You Can Ignore For Now

To learn faster, do not overload yourself with everything at once.

You can safely postpone:

- background tasks
- WebSockets
- authentication
- database integration
- ORM setup
- advanced dependency injection

For the MVP, file upload, validation, JSON responses, and download responses are the key things.

## Practical Next Build Order

If you want to learn by doing, build in this order:

1. define invoice row and validation response schemas
2. implement CSV upload endpoint
3. implement validation service
4. connect frontend upload UI
5. implement preview endpoint with real invoice row data
6. implement PDF generation
7. implement ZIP download

## What To Focus On As A Beginner

If your goal is to learn FastAPI quickly, focus on these questions:

- how does FastAPI turn request data into Python objects?
- where should validation live?
- what belongs in a route versus a service?
- how do you return files and downloads?

If you get those right, the rest will feel much easier.
