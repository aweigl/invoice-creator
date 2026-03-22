# invoice-creator

Starter app with:

- Vue 3
- TypeScript
- FastAPI

## Structure

- `frontend`: Vue + TypeScript app powered by Vite
- `backend`: FastAPI app with a simple invoice endpoint

## Frontend

```bash
nvm use
cd frontend
npm install
npm run dev
```

The frontend runs on `http://localhost:5173`.

If `npm` complains about a missing ICU library, make sure your shell is using the
Node version from `.nvmrc` before running the frontend commands.

During development, Vite proxies `/api` and `/health` requests to the FastAPI
server on `http://127.0.0.1:8000`, which avoids browser CORS issues.

## Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The backend runs on `http://localhost:8000`.

The backend CORS setup accepts local frontend origins such as `localhost` and
`127.0.0.1` on any port for development.

## API

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
