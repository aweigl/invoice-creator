# invoice-creator

Starter app for building a CSV-to-invoice workflow with:

- Vue 3
- TypeScript
- FastAPI

The current codebase is still a starter, but the project direction is now documented around a clear MVP:

- user uploads a CSV
- user reviews and edits each row
- backend validates the edited rows
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
- `sample-data`: example CSV files

## Start Both Servers

From the project root:

```bash
nvm use
npm install
npm run dev
```

This starts the frontend and backend together.

## Production Shape

For production deployment, the Vue frontend is built into `frontend/dist` and served by FastAPI.

That means a single deployed service can handle:

- the web UI
- the API endpoints
- PDF generation

This is the simplest shape for Railway, because only one service needs to be deployed.

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
uvicorn app.main:app --reload --reload-dir app --port 8000
```

The backend runs on `http://localhost:8000`.

The backend CORS setup accepts local frontend origins such as `localhost` and `127.0.0.1` on any port for development.

## Single-Service Production Run

To test the production-style flow locally:

```bash
cd /Users/aweigl/Desktop/Projects/invoice-creator/frontend
npm run build

cd /Users/aweigl/Desktop/Projects/invoice-creator/backend
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

After the frontend build exists, FastAPI serves the built app from `frontend/dist`.

## Current Workflow

1. Upload a CSV file in the frontend.
2. Edit the parsed rows before invoice creation.
3. Validate the current row data against the backend pricing schema.
4. Generate a ZIP containing one invoice PDF per valid row.

The current CSV schema is shown in [sample-data/invoice-pricing-example.csv](/Users/aweigl/Desktop/Projects/invoice-creator/sample-data/invoice-pricing-example.csv).

## Railway

The repository now includes a root [Dockerfile](/Users/aweigl/Desktop/Projects/invoice-creator/Dockerfile) that:

1. builds the Vue frontend
2. installs the Python backend and WeasyPrint system dependencies
3. serves the built frontend through FastAPI

This lets Railway deploy the repo as a single service.

## Current API

- `GET /health`
- `POST /api/csv/validate`
- `POST /api/invoices/validate-rows`
- `POST /api/invoices/generate`
- `POST /api/invoices/generate-single`
