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

Set these environment variables before starting the backend:

```bash
export APP_BASIC_AUTH_USERNAME="dein-benutzername"
export APP_BASIC_AUTH_PASSWORD="ein-langes-zufaelliges-passwort"
```

The backend also auto-loads a project-root `.env` file, so local `yarn dev` works even when terminal env-file injection is disabled.

Every route except `GET /health` is protected with HTTP Basic Auth.
When you load the FastAPI-served app, the browser will show its native username/password prompt before the page loads.
When you run the frontend separately with Vite in development, the first protected API request will trigger that prompt.
For local development, the root `dev` command sets `APP_DISABLE_BASIC_AUTH=true` for the backend process so `yarn dev` works without a browser login prompt.

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

The current CSV schema is shown in [sample-data/invoice-pricing-example.csv](/Users/aweigl/Desktop/Projects/invoice-creator/sample-data/invoice-pricing-example.csv). The sample uses semicolons as the CSV separator.

## Docker

The repository now includes a root [Dockerfile](/Users/aweigl/Desktop/Projects/invoice-creator/Dockerfile) that:

1. builds the Vue frontend
2. installs the Python backend and WeasyPrint system dependencies
3. serves the built frontend through FastAPI

This lets the app run as a single container for platforms like Coolify or Railway.

To test it locally:

```bash
docker build -t invoice-creator .
docker run --rm -p 8000:8000 invoice-creator
```

Or with Compose:

```bash
docker compose up --build
```

Then open `http://localhost:8000`.

## Coolify

Use the repo as a Dockerfile-based application or a Compose-based application.

Recommended setup in Coolify:

1. Select the repository and choose the root [Dockerfile](/Users/aweigl/Desktop/Projects/invoice-creator/Dockerfile).
2. Set the container port to `8000`.
3. Keep the default start command from the image.
4. No persistent volume is required for the current app.

If you prefer Docker Compose in Coolify, point it at [docker-compose.yml](/Users/aweigl/Desktop/Projects/invoice-creator/docker-compose.yml).

The container has a built-in health check that calls `GET /health`, which matches the existing app health endpoint.

## Railway

The same [Dockerfile](/Users/aweigl/Desktop/Projects/invoice-creator/Dockerfile) also works for Railway, and the existing [railway.json](/Users/aweigl/Desktop/Projects/invoice-creator/railway.json) still points Railway at that image build.

## Access Control And Rate Limits

The app now uses in-memory HTTP Basic Auth and minimal credential-scoped rate limiting inside FastAPI.
This is intentionally not based on IP allowlisting, because home internet connections often use dynamic public IP addresses.
Local auth bypass is controlled only by the explicit `APP_DISABLE_BASIC_AUTH=true` env flag, which is enabled by the local backend dev script and should stay unset in production.

Protected routes:

- all frontend routes and built assets served by FastAPI
- all `/api/*` endpoints

Open route:

- `GET /health`

Default limits:

- failed or missing auth on protected routes: `10/min`
- `POST /api/invoices/generate` and `POST /api/invoices/generate-single`: shared `2/min`
- `POST /api/csv/validate` and `POST /api/invoices/validate-rows`: shared `8/min`
- `GET /api/address/autocomplete` and `POST /api/address/resolve-distance`: shared `20/min`

## Current API

- `GET /health`
- `POST /api/csv/validate`
- `POST /api/invoices/validate-rows`
- `POST /api/invoices/generate`
- `POST /api/invoices/generate-single`
