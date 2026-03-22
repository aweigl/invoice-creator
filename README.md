# invoice-creator

Starter app for building a CSV-to-invoice workflow with:

- Vue 3
- TypeScript
- FastAPI

The current codebase is still a starter, but the project direction is now documented around a clear MVP:

- user uploads a CSV
- one row becomes one invoice
- backend validates the file
- app previews invoice data
- backend generates one PDF per row
- user downloads a ZIP

## Project Docs

- [MVP PRD](/Users/aweigl/Desktop/Projects/invoice-creator/docs/mvp-prd.md)
- [FastAPI Learning Guide](/Users/aweigl/Desktop/Projects/invoice-creator/docs/fastapi-learning-guide.md)

If your main goal is to learn FastAPI while building this product, start with the learning guide and then use the PRD as the implementation target.

## Structure

- `frontend`: Vue + TypeScript app powered by Vite
- `backend`: FastAPI app
- `docs`: product and architecture documentation

## Frontend

```bash
nvm use
cd frontend
npm install
npm run dev
```

The frontend runs on `http://localhost:5173`.

If `npm` complains about a missing ICU library, make sure your shell is using the Node version from `.nvmrc` before running the frontend commands.

During development, Vite proxies `/api` and `/health` requests to the FastAPI server on `http://127.0.0.1:8000`, which avoids browser CORS issues.

## Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The backend runs on `http://localhost:8000`.

The backend CORS setup accepts local frontend origins such as `localhost` and `127.0.0.1` on any port for development.

## Current API

- `GET /health`
- `POST /api/invoices/preview`

Example request:

```json
{
  "customerName": "Acme GmbH",
  "invoiceNumber": "INV-2026-001",
  "items": [
    {
      "description": "Design work",
      "quantity": 8,
      "unitPrice": 75
    }
  ]
}
```

## Planned MVP API

The documented target API for the next iteration is:

- `GET /health`
- `POST /api/csv/validate`
- `POST /api/invoices/preview`
- `POST /api/invoices/generate`
