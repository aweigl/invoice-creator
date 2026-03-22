# Invoice Creator MVP PRD

## Goal

Build a web app that lets a user upload a CSV file and generate one invoice PDF per row.

This MVP is optimized for simplicity:

- One CSV row equals one invoice
- CSV only
- One fixed invoice template
- Download only
- No user accounts
- No template database

## Problem Statement

The user has invoice data in a spreadsheet and wants to avoid creating invoices manually one by one.

The app should:

- accept structured CSV data
- validate it before invoice generation
- preview what will be generated
- create a PDF invoice for every valid row
- package the PDFs into a ZIP for download

## MVP Scope

### In Scope

- CSV upload
- CSV parsing
- header validation
- row-level validation
- invoice preview
- PDF generation
- ZIP download
- fixed sender details
- fixed invoice layout

### Out Of Scope

- Excel `.xlsx` upload
- multiple line items per invoice
- login and authentication
- saved invoice history
- email sending
- multiple invoice templates
- customer database
- template database

## Primary User Story

As an operations user, I want to upload a CSV of invoice rows and receive a ZIP file of invoice PDFs, so I can create invoices in bulk without manual repetition.

## Workflow

1. User opens the app.
2. User uploads a CSV file.
3. App validates required columns and row values.
4. App shows a summary:
   - number of rows found
   - number of valid rows
   - number of invalid rows
5. If validation fails, the app shows row-specific errors and blocks generation.
6. If validation passes, the app shows a sample invoice preview for one row.
7. User clicks generate.
8. App creates one PDF per row and returns a ZIP file.

## CSV Schema

The first version should use a required, fixed schema.

### Required Columns

- `invoice_number`
- `invoice_date`
- `due_date`
- `customer_name`
- `customer_address`
- `item_description`
- `quantity`
- `unit_price`
- `tax_rate`
- `currency`

### Example CSV

```csv
invoice_number,invoice_date,due_date,customer_name,customer_address,item_description,quantity,unit_price,tax_rate,currency
INV-2026-001,2026-03-22,2026-04-05,Acme GmbH,"Musterstrasse 1, 10115 Berlin",Design work,8,75.00,19,EUR
INV-2026-002,2026-03-22,2026-04-05,Globex AG,"Hauptstrasse 5, 20095 Hamburg",Consulting,4,120.00,19,EUR
```

## Validation Rules

Validation should happen in two phases.

### File-Level Validation

- uploaded file must be a `.csv`
- file must contain a header row
- all required columns must exist
- file must contain at least one data row

### Row-Level Validation

- `invoice_number` must be present and non-empty
- `invoice_date` must be a valid date in `YYYY-MM-DD`
- `due_date` must be a valid date in `YYYY-MM-DD`
- `customer_name` must be present
- `customer_address` must be present
- `item_description` must be present
- `quantity` must be a number greater than `0`
- `unit_price` must be a number greater than or equal to `0`
- `tax_rate` must be a number greater than or equal to `0`
- `currency` must be a supported code such as `EUR` or `USD`

### Business Rules

- generation is blocked if any row is invalid
- invoice numbers are supplied by the CSV, not auto-generated
- totals are calculated by the app, not trusted from the file

## Invoice Calculations

For each row:

- `net_amount = quantity * unit_price`
- `tax_amount = net_amount * (tax_rate / 100)`
- `gross_amount = net_amount + tax_amount`

Values should be rounded consistently for display and PDF output.

## Fixed Template Content

The PDF template should contain:

- sender business name
- sender business address
- sender email and tax information
- invoice number
- invoice date
- due date
- customer name
- customer address
- single line item
- subtotal
- tax rate and tax amount
- grand total

Sender details can be stored in backend settings for now.

## UI Screens

### 1. Upload Screen

- file picker
- short explanation of required CSV schema
- downloadable sample CSV in a later iteration

### 2. Validation Results Screen

- upload summary
- required column status
- invalid row list
- clear error messages tied to row numbers

### 3. Preview Screen

- rendered preview of one invoice
- summary of how many invoices will be generated
- generate button

### 4. Result Screen

- success message
- number of invoices generated
- ZIP download button

## API Design For MVP

The frontend is Vue and the backend is FastAPI.

Suggested backend endpoints:

- `GET /health`
- `POST /api/csv/validate`
- `POST /api/invoices/preview`
- `POST /api/invoices/generate`

### `POST /api/csv/validate`

Purpose:

- accept the uploaded CSV
- parse the rows
- validate schema and values
- return structured validation results

Example response shape:

```json
{
  "filename": "invoices.csv",
  "totalRows": 2,
  "validRows": 2,
  "invalidRows": 0,
  "errors": []
}
```

### `POST /api/invoices/preview`

Purpose:

- accept one validated invoice row
- compute totals
- return preview data for rendering

### `POST /api/invoices/generate`

Purpose:

- accept validated rows
- generate all invoice PDFs
- package them into a ZIP
- return the ZIP as a download response

## Backend Architecture

Suggested backend modules:

- `app/main.py`
- `app/schemas.py`
- `app/services/csv_parser.py`
- `app/services/validator.py`
- `app/services/invoice_calculator.py`
- `app/services/pdf_renderer.py`
- `app/services/zip_bundle.py`
- `app/config.py`

Responsibilities:

- `schemas.py`: Pydantic models for requests and responses
- `csv_parser.py`: CSV reading and normalization
- `validator.py`: schema and business rule validation
- `invoice_calculator.py`: totals and tax calculations
- `pdf_renderer.py`: convert invoice data into PDF bytes
- `zip_bundle.py`: collect PDFs into a ZIP archive

## Frontend Architecture

Suggested frontend responsibilities:

- upload CSV file
- call validation endpoint
- display validation errors
- request preview data
- request ZIP generation
- trigger browser download

Potential Vue components:

- `CsvUploadForm`
- `ValidationSummary`
- `ValidationErrorTable`
- `InvoicePreviewCard`
- `DownloadResult`

## Non-Functional Requirements

- validation errors should be easy to understand
- app should handle at least small and medium CSV files reliably
- totals must be deterministic and accurate
- generated filenames should be predictable
- failures should not partially generate broken downloads

## Success Criteria

The MVP is successful if a user can:

- upload a valid CSV
- understand any invalid rows quickly
- preview a sample invoice
- download a ZIP containing one PDF per row

## Post-MVP Ideas

- support `.xlsx`
- support multiple line items per invoice
- save sender profiles
- save invoice templates
- email delivery
- invoice history
- column mapping UI for flexible CSV formats
