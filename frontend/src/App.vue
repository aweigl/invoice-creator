<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type SubscriptionPlan = "none" | "1x_week" | "2x_week" | "3x_week" | "4x_week";

type CsvValidationError = {
  row_number: number;
  column: string | null;
  message: string;
};

type PricingRow = {
  invoice_number: string;
  invoice_date: string;
  due_date: string;
  customer_name: string;
  customer_address: string;
  dog_name: string;
  billing_month: string;
  subscription_plan: SubscriptionPlan;
  daily_count: string;
  daily_dates: string;
  daily_count_rebate: boolean;
  include_test_run: boolean;
  include_extended_km_surcharge: boolean;
  currency: string;
};

type EditablePricingRow = PricingRow & {
  uid: string;
  subscription_price_override: string;
  daily_price_override: string;
  test_run_price_override: string;
  extended_km_surcharge_amount: string;
};

type CsvValidationResult = {
  filename: string;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  errors: CsvValidationError[];
  validated_rows: Array<{
    invoice_number: string;
    invoice_date: string;
    due_date: string;
    customer_name: string;
    customer_address: string;
    dog_name: string;
    billing_month: string;
    subscription_plan: SubscriptionPlan;
    daily_count: number;
    daily_dates: string;
    daily_count_rebate: boolean;
    include_test_run: boolean;
    include_extended_km_surcharge: boolean;
    currency: string;
  }>;
  sample_row: PricingRow | null;
};

type PreviewLineItem = {
  label: string;
  detail: string;
  amount: number;
};

type CoordinatePoint = {
  latitude: number;
  longitude: number;
};

type AddressDistanceResult = {
  address: string;
  resolved_address: string;
  origin: CoordinatePoint;
  destination: CoordinatePoint;
  route_distance_meters: number;
  route_distance_km: number;
  included_radius_km: number;
  should_apply_extended_km_surcharge: boolean;
};

const MAX_CSV_BYTES = 2 * 1024 * 1024;
const REQUIRED_COLUMNS = [
  "invoice_number",
  "invoice_date",
  "due_date",
  "customer_name",
  "customer_address",
  "dog_name",
  "billing_month",
  "subscription_plan",
  "daily_count",
  "daily_dates",
  "daily_count_rebate",
  "include_test_run",
  "currency",
] as const;

const SUBSCRIPTION_PRICES: Record<SubscriptionPlan, number> = {
  none: 0,
  "1x_week": 120,
  "2x_week": 190,
  "3x_week": 290,
  "4x_week": 390,
};

const PLAN_LABELS: Record<SubscriptionPlan, string> = {
  none: "Kein Abo",
  "1x_week":
    "Abholung Gruppenspaziergang und Heimbringen {dog_name} von/zu Ihrem Haus in Köln (Abo 1x pro Woche)",
  "2x_week":
    "Abholung Gruppenspaziergang und Heimbringen {dog_name} von/zu Ihrem Haus in Köln (2x pro Woche)",
  "3x_week":
    "Abholung Gruppenspaziergang und Heimbringen {dog_name} von/zu Ihrem Haus in Köln (3x pro Woche)",
  "4x_week":
    "Abholung Gruppenspaziergang und Heimbringen {dog_name} von/zu Ihrem Haus in Köln (4x pro Woche)",
};

const DAILY_PRICE = 35;
const DAILY_PRICE_REBATED = 30;
const TEST_RUN_PRICE = 20;
const DEFAULT_EXTENDED_KM_SURCHARGE_AMOUNT = 5.0;
const SERVICE_AREA_RADIUS_KM = 17;
const CSV_DELIMITERS = [";", ","] as const;
const SAMPLE_CSV_DOWNLOAD_PATH = `${import.meta.env.BASE_URL}invoice-pricing-example.csv`;

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "";

const selectedFileName = ref("");
const csvContent = ref("");
const localHeaders = ref<string[]>([]);
const localRowCount = ref(0);
const editableRows = ref<EditablePricingRow[]>([]);
const validationResult = ref<CsvValidationResult | null>(null);
const fileError = ref("");
const serverError = ref("");
const isValidating = ref(false);
const isGenerating = ref(false);
const isPreviewLoading = ref(false);
const lastValidatedSnapshot = ref("");
const selectedRowUid = ref("");
const generatedRowUids = ref<string[]>([]);
const previewError = ref("");
const distanceLookupResults = ref<Record<string, AddressDistanceResult>>({});
const distanceLookupErrors = ref<Record<string, string>>({});
const resolvingDistanceRowUid = ref("");

const hasRows = computed(() => editableRows.value.length > 0);
const generatedRowUidSet = computed(() => new Set(generatedRowUids.value));
const selectedRowIndex = computed(() =>
  editableRows.value.findIndex((row) => row.uid === selectedRowUid.value),
);
const selectedRow = computed(
  () =>
    editableRows.value.find((row) => row.uid === selectedRowUid.value) ?? null,
);
const selectedRowAddressDistance = computed(() =>
  selectedRow.value
    ? distanceLookupResults.value[selectedRow.value.uid] ?? null
    : null,
);
const selectedRowAddressDistanceError = computed(() =>
  selectedRow.value ? distanceLookupErrors.value[selectedRow.value.uid] ?? "" : "",
);
const isResolvingSelectedRowDistance = computed(
  () =>
    selectedRow.value !== null &&
    resolvingDistanceRowUid.value === selectedRow.value.uid,
);

const currentRowsSnapshot = computed(() =>
  JSON.stringify({
    filename: selectedFileName.value || "bearbeitete-rechnungen.csv",
    rows: buildPayloadRows(),
  }),
);

const validationIsCurrent = computed(
  () =>
    validationResult.value !== null &&
    lastValidatedSnapshot.value.length > 0 &&
    lastValidatedSnapshot.value === currentRowsSnapshot.value,
);

const canGenerate = computed(
  () =>
    validationIsCurrent.value &&
    validationResult.value !== null &&
    validationResult.value.invalid_rows === 0 &&
    hasRows.value &&
    !isGenerating.value,
);

function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatEuro(amount: number): string {
  return new Intl.NumberFormat("de-DE", {
    style: "currency",
    currency: "EUR",
  }).format(amount);
}

function formatKilometers(value: number): string {
  return `${new Intl.NumberFormat("de-DE", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 2,
  }).format(value)} km`;
}

function formatCoordinate(value: number): string {
  return value.toFixed(6);
}

function formatGermanMonth(value: string): string {
  if (!value) {
    return "offen";
  }

  const date = new Date(`${value}-01T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("de-DE", {
    month: "2-digit",
    year: "numeric",
  }).format(date);
}

function formatGermanDate(value: string): string {
  if (!value) {
    return value;
  }

  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("de-DE").format(date);
}

function parseDailyDates(value: string): string[] {
  const normalized = value.trim();
  if (!normalized) {
    return [];
  }

  const parts = normalized.split(",").map((part) => part.trim());
  if (parts.some((part) => part.length === 0)) {
    return [];
  }

  return parts;
}

function formatGermanDateList(value: string): string {
  const parsedDates = parseDailyDates(value);
  if (parsedDates.length === 0) {
    return value.trim();
  }

  const formattedDates = parsedDates.map((entry) => formatGermanDate(entry));
  if (formattedDates.length === 1) {
    return formattedDates[0];
  }

  if (formattedDates.length === 2) {
    return `${formattedDates[0]} und ${formattedDates[1]}`;
  }

  return `${formattedDates.slice(0, -1).join(", ")} und ${formattedDates[formattedDates.length - 1]}`;
}

function detectCsvDelimiter(content: string): string {
  const firstNonEmptyLine = content
    .replace(/^\uFEFF/, "")
    .split(/\r?\n/)
    .find((line) => line.trim().length > 0);

  if (!firstNonEmptyLine) {
    return ";";
  }

  const delimiterCounts = CSV_DELIMITERS.map((delimiter) => ({
    delimiter,
    count: firstNonEmptyLine.split(delimiter).length - 1,
  }));
  const bestMatch = delimiterCounts.sort(
    (left, right) => right.count - left.count,
  )[0];

  return bestMatch && bestMatch.count > 0 ? bestMatch.delimiter : ";";
}

function parseCsvLine(line: string, delimiter: string): string[] {
  const values: string[] = [];
  let current = "";
  let inQuotes = false;

  for (let index = 0; index < line.length; index += 1) {
    const character = line[index];
    const nextCharacter = line[index + 1];

    if (character === '"') {
      if (inQuotes && nextCharacter === '"') {
        current += '"';
        index += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }

    if (character === delimiter && !inQuotes) {
      values.push(current.trim());
      current = "";
      continue;
    }

    current += character;
  }

  values.push(current.trim());
  return values;
}

function toBoolean(value: string): boolean {
  return ["true", "1", "ja", "yes"].includes(value.trim().toLowerCase());
}

function normalizeMoneyInput(value: string): string | null {
  const trimmed = value.trim().replace(/\s+/g, "").replace(/'/g, "");
  if (!trimmed) {
    return null;
  }

  const hasComma = trimmed.includes(",");
  const hasDot = trimmed.includes(".");

  if (hasComma && hasDot) {
    if (trimmed.lastIndexOf(",") > trimmed.lastIndexOf(".")) {
      return trimmed.replace(/\./g, "").replace(",", ".");
    }

    return trimmed.replace(/,/g, "");
  }

  if (hasComma) {
    return trimmed.replace(",", ".");
  }

  return trimmed;
}

function parseMoneyInput(value: string, fallback: number): number {
  const normalized = normalizeMoneyInput(value);
  if (!normalized) {
    return fallback;
  }

  const parsed = Number.parseFloat(normalized);
  return Number.isNaN(parsed) ? fallback : parsed;
}

function formatMoneyInput(value: string): string {
  const normalized = normalizeMoneyInput(value);
  if (!normalized) {
    return "";
  }

  const parsed = Number.parseFloat(normalized);
  if (Number.isNaN(parsed)) {
    return value.trim();
  }

  return parsed.toFixed(2);
}

function formatEditableMoneyField(
  row: EditablePricingRow,
  field:
    | "subscription_price_override"
    | "daily_price_override"
    | "test_run_price_override"
    | "extended_km_surcharge_amount",
) {
  row[field] = formatMoneyInput(row[field]);
  markRowDirty();
}

function isSubscriptionPlan(value: string): value is SubscriptionPlan {
  return value in SUBSCRIPTION_PRICES;
}

function subscriptionLabel(row: PricingRow): string {
  return PLAN_LABELS[row.subscription_plan].replace(
    "{dog_name}",
    row.dog_name || "Hund",
  );
}

function parseCsvContent(content: string): {
  headers: string[];
  rows: PricingRow[];
} {
  const normalized = content.replace(/^\uFEFF/, "");
  const delimiter = detectCsvDelimiter(normalized);
  const lines = normalized
    .split(/\r?\n/)
    .filter((line) => line.trim().length > 0);

  if (lines.length === 0) {
    return { headers: [], rows: [] };
  }

  const headers = parseCsvLine(lines[0], delimiter);
  const rows = lines.slice(1).map((line) => {
    const values = parseCsvLine(line, delimiter);
    const source = Object.fromEntries(
      headers.map((header, index) => [header, values[index] ?? ""]),
    );

    return {
      invoice_number: String(source.invoice_number ?? ""),
      invoice_date: String(source.invoice_date ?? ""),
      due_date: String(source.due_date ?? ""),
      customer_name: String(source.customer_name ?? ""),
      customer_address: String(source.customer_address ?? ""),
      dog_name: String(source.dog_name ?? ""),
      billing_month: String(source.billing_month ?? ""),
      subscription_plan: isSubscriptionPlan(
        String(source.subscription_plan ?? ""),
      )
        ? (String(source.subscription_plan) as SubscriptionPlan)
        : "none",
      daily_count: String(source.daily_count ?? "0"),
      daily_dates: String(source.daily_dates ?? ""),
      daily_count_rebate: toBoolean(
        String(source.daily_count_rebate ?? "false"),
      ),
      include_test_run: toBoolean(String(source.include_test_run ?? "false")),
      include_extended_km_surcharge: toBoolean(
        String(source.include_extended_km_surcharge ?? "false"),
      ),
      currency: String(source.currency ?? "EUR"),
    };
  });

  return { headers, rows };
}

function createRowUid(index: number): string {
  return `row-${Date.now()}-${index}-${Math.random().toString(36).slice(2, 8)}`;
}

function buildPayloadRows() {
  return editableRows.value.map((row) => ({
    invoice_number: row.invoice_number,
    invoice_date: row.invoice_date,
    due_date: row.due_date,
    customer_name: row.customer_name,
    customer_address: row.customer_address,
    dog_name: row.dog_name,
    billing_month: row.billing_month,
    subscription_plan: row.subscription_plan,
    daily_count: row.daily_count,
    daily_dates: row.daily_dates,
    daily_count_rebate: row.daily_count_rebate,
    include_test_run: row.include_test_run,
    include_extended_km_surcharge: row.include_extended_km_surcharge,
    subscription_price_override: normalizeMoneyInput(
      row.subscription_price_override,
    ),
    daily_price_override: normalizeMoneyInput(row.daily_price_override),
    test_run_price_override: normalizeMoneyInput(row.test_run_price_override),
    extended_km_surcharge_amount: normalizeMoneyInput(
      row.extended_km_surcharge_amount,
    ),
    currency: row.currency,
  }));
}

function validationErrorsForRow(rowIndex: number): CsvValidationError[] {
  const targetRowNumber = rowIndex + 2;
  return (
    validationResult.value?.errors.filter(
      (error) => error.row_number === targetRowNumber,
    ) ?? []
  );
}

function validationErrorsForField(rowIndex: number, field: string): string[] {
  return validationErrorsForRow(rowIndex)
    .filter((error) => error.column === field)
    .map((error) => error.message);
}

function rowHasErrors(rowIndex: number): boolean {
  return validationErrorsForRow(rowIndex).length > 0;
}

function effectiveSubscriptionPrice(row: EditablePricingRow): number {
  return parseMoneyInput(
    row.subscription_price_override,
    SUBSCRIPTION_PRICES[row.subscription_plan],
  );
}

function effectiveDailyPrice(row: EditablePricingRow): number {
  return parseMoneyInput(
    row.daily_price_override,
    row.daily_count_rebate ? DAILY_PRICE_REBATED : DAILY_PRICE,
  );
}

function effectiveTestRunPrice(row: EditablePricingRow): number {
  return parseMoneyInput(row.test_run_price_override, TEST_RUN_PRICE);
}

function effectiveExtendedKmSurchargeAmount(row: EditablePricingRow): number {
  return parseMoneyInput(
    row.extended_km_surcharge_amount,
    DEFAULT_EXTENDED_KM_SURCHARGE_AMOUNT,
  );
}

function previewLineItems(row: EditablePricingRow): PreviewLineItem[] {
  const items: PreviewLineItem[] = [];
  const dailyCount = Number.parseInt(row.daily_count || "0", 10);

  if (row.subscription_plan !== "none") {
    const subscriptionPrice = effectiveSubscriptionPrice(row);
    items.push({
      label: subscriptionLabel(row),
      detail: `Abrechnungsmonat ${formatGermanMonth(row.billing_month)}`,
      amount: subscriptionPrice,
    });
  }

  if (!Number.isNaN(dailyCount) && dailyCount > 0) {
    const formattedDates = formatGermanDateList(row.daily_dates);
    const dailyPrice = effectiveDailyPrice(row);
    items.push({
      label: "Zusaetzliche Tagesbetreuung",
      detail: `${dailyCount} Tag(e) x ${formatEuro(dailyPrice)}${row.daily_count_rebate ? " · Rabatt" : ""}${formattedDates ? ` · am ${formattedDates}` : ""}`,
      amount: dailyCount * dailyPrice,
    });
  }

  if (row.include_test_run) {
    const testRunPrice = effectiveTestRunPrice(row);
    items.push({
      label: "Probetag",
      detail: "Einmalige Kennenlernleistung",
      amount: testRunPrice,
    });
  }

  if (row.include_extended_km_surcharge) {
    items.push({
      label: "Erweiterter Kilometerbereich",
      detail: `Zuschlag fuer Anfahrt ausserhalb des Standardbereichs (${SERVICE_AREA_RADIUS_KM}km)`,
      amount: effectiveExtendedKmSurchargeAmount(row),
    });
  }

  return items;
}

function estimateTotal(row: EditablePricingRow): number {
  return previewLineItems(row).reduce((sum, item) => sum + item.amount, 0);
}

function markRowsDirty() {
  serverError.value = "";
  previewError.value = "";
}

function markRowDirty() {
  markRowsDirty();
}

function clearAddressDistanceStateForRow(uid: string) {
  const { [uid]: _result, ...remainingResults } = distanceLookupResults.value;
  const { [uid]: _error, ...remainingErrors } = distanceLookupErrors.value;

  distanceLookupResults.value = remainingResults;
  distanceLookupErrors.value = remainingErrors;

  if (resolvingDistanceRowUid.value === uid) {
    resolvingDistanceRowUid.value = "";
  }
}

function handleSelectedAddressInput() {
  markRowDirty();

  if (selectedRow.value) {
    clearAddressDistanceStateForRow(selectedRow.value.uid);
  }
}

function selectNextAvailableRow() {
  const nextRow = editableRows.value.find(
    (row) => !generatedRowUidSet.value.has(row.uid),
  );
  selectedRowUid.value = nextRow?.uid ?? "";
}

async function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];

  fileError.value = "";
  serverError.value = "";
  validationResult.value = null;
  lastValidatedSnapshot.value = "";
  selectedFileName.value = "";
  csvContent.value = "";
  localHeaders.value = [];
  localRowCount.value = 0;
  editableRows.value = [];
  selectedRowUid.value = "";
  generatedRowUids.value = [];
  previewError.value = "";
  distanceLookupResults.value = {};
  distanceLookupErrors.value = {};
  resolvingDistanceRowUid.value = "";

  if (!file) {
    return;
  }

  if (!file.name.toLowerCase().endsWith(".csv")) {
    fileError.value = "Bitte waehle eine CSV-Datei aus.";
    input.value = "";
    return;
  }

  if (file.size > MAX_CSV_BYTES) {
    fileError.value = `Die CSV-Datei ist zu gross. Bitte lade eine Datei unter ${formatBytes(MAX_CSV_BYTES)} hoch.`;
    input.value = "";
    return;
  }

  const content = await file.text();
  const parsed = parseCsvContent(content);

  selectedFileName.value = file.name;
  csvContent.value = content;
  localHeaders.value = parsed.headers;
  localRowCount.value = parsed.rows.length;
  editableRows.value = parsed.rows.map((row, index) => ({
    uid: createRowUid(index),
    ...row,
    subscription_price_override: "",
    daily_price_override: "",
    test_run_price_override: "",
    extended_km_surcharge_amount: "",
  }));
  selectedRowUid.value = editableRows.value[0]?.uid ?? "";
}

async function validateRows() {
  if (!hasRows.value) {
    fileError.value =
      "Bitte lade zuerst eine CSV-Datei mit Rechnungszeilen hoch.";
    return;
  }

  isValidating.value = true;
  serverError.value = "";

  try {
    const response = await fetch(`${apiBaseUrl}/api/invoices/validate-rows`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        filename: selectedFileName.value || "bearbeitete-rechnungen.csv",
        rows: buildPayloadRows(),
      }),
    });

    if (!response.ok) {
      const payload = (await response.json().catch(() => null)) as {
        detail?: string;
      } | null;
      throw new Error(
        payload?.detail ?? `Validierung fehlgeschlagen (${response.status})`,
      );
    }

    validationResult.value = (await response.json()) as CsvValidationResult;
    lastValidatedSnapshot.value = currentRowsSnapshot.value;
  } catch (error) {
    validationResult.value = null;
    lastValidatedSnapshot.value = "";
    serverError.value =
      error instanceof Error ? error.message : "Unbekannter Serverfehler.";
  } finally {
    isValidating.value = false;
  }
}

async function generateInvoices() {
  if (!canGenerate.value) {
    serverError.value =
      "Bitte validiere die aktuellen Zeilen erfolgreich, bevor du PDFs erzeugst.";
    return;
  }

  isGenerating.value = true;
  serverError.value = "";

  try {
    const response = await fetch(`${apiBaseUrl}/api/invoices/generate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        filename: selectedFileName.value || "bearbeitete-rechnungen.csv",
        rows: buildPayloadRows(),
      }),
    });

    if (!response.ok) {
      const payload = (await response.json().catch(() => null)) as {
        detail?: string;
      } | null;
      throw new Error(
        payload?.detail ?? `PDF-Erstellung fehlgeschlagen (${response.status})`,
      );
    }

    const blob = await response.blob();
    const downloadUrl = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = downloadUrl;
    anchor.download = "rechnungen.zip";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(downloadUrl);
  } catch (error) {
    serverError.value =
      error instanceof Error
        ? error.message
        : "Unbekannter Fehler bei der PDF-Erstellung.";
  } finally {
    isGenerating.value = false;
  }
}

function isRowGenerated(uid: string): boolean {
  return generatedRowUidSet.value.has(uid);
}

function buildSingleRowPayload(row: EditablePricingRow) {
  return {
    filename: `${row.invoice_number || "rechnung"}.csv`,
    rows: [
      {
        invoice_number: row.invoice_number,
        invoice_date: row.invoice_date,
        due_date: row.due_date,
        customer_name: row.customer_name,
        customer_address: row.customer_address,
        dog_name: row.dog_name,
        billing_month: row.billing_month,
        subscription_plan: row.subscription_plan,
        daily_count: row.daily_count,
        daily_dates: row.daily_dates,
        daily_count_rebate: row.daily_count_rebate,
        include_test_run: row.include_test_run,
        include_extended_km_surcharge: row.include_extended_km_surcharge,
        subscription_price_override: normalizeMoneyInput(
          row.subscription_price_override,
        ),
        daily_price_override: normalizeMoneyInput(row.daily_price_override),
        test_run_price_override: normalizeMoneyInput(
          row.test_run_price_override,
        ),
        extended_km_surcharge_amount: normalizeMoneyInput(
          row.extended_km_surcharge_amount,
        ),
        currency: row.currency,
      },
    ],
  };
}

async function resolveSelectedRowAddressDistance() {
  if (!selectedRow.value) {
    serverError.value = "Bitte waehle zuerst eine Rechnungszeile aus.";
    return;
  }

  const rowUid = selectedRow.value.uid;
  const address = selectedRow.value.customer_address.trim();
  clearAddressDistanceStateForRow(rowUid);

  if (!address) {
    distanceLookupErrors.value = {
      ...distanceLookupErrors.value,
      [rowUid]: "Bitte hinterlege zuerst eine Kundenadresse.",
    };
    return;
  }

  resolvingDistanceRowUid.value = rowUid;

  try {
    const response = await fetch(`${apiBaseUrl}/api/address/resolve-distance`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ address }),
    });

    if (!response.ok) {
      const payload = (await response.json().catch(() => null)) as {
        detail?: string;
      } | null;
      throw new Error(
        payload?.detail ?? `Distanzberechnung fehlgeschlagen (${response.status})`,
      );
    }

    const result = (await response.json()) as AddressDistanceResult;
    distanceLookupResults.value = {
      ...distanceLookupResults.value,
      [rowUid]: result,
    };

    const { [rowUid]: _error, ...remainingErrors } = distanceLookupErrors.value;
    distanceLookupErrors.value = remainingErrors;

    const targetRow = editableRows.value.find((row) => row.uid === rowUid);
    if (targetRow) {
      targetRow.include_extended_km_surcharge =
        result.should_apply_extended_km_surcharge;
    }

    markRowDirty();
  } catch (error) {
    clearAddressDistanceStateForRow(rowUid);
    distanceLookupErrors.value = {
      ...distanceLookupErrors.value,
      [rowUid]:
        error instanceof Error
          ? error.message
          : "Unbekannter Fehler bei der Distanzberechnung.",
    };
  } finally {
    if (resolvingDistanceRowUid.value === rowUid) {
      resolvingDistanceRowUid.value = "";
    }
  }
}

async function generateSelectedRowPdf() {
  if (!selectedRow.value) {
    serverError.value = "Bitte waehle zuerst eine Rechnungszeile aus.";
    return;
  }

  if (isRowGenerated(selectedRow.value.uid)) {
    serverError.value = "Fuer diese Zeile wurde das PDF bereits erstellt.";
    return;
  }

  if (!validationIsCurrent.value) {
    serverError.value =
      "Bitte validiere die aktuellen Daten erneut, bevor du ein PDF erzeugst.";
    return;
  }

  if (rowHasErrors(selectedRowIndex.value)) {
    serverError.value =
      "Die ausgewaehlte Zeile enthaelt noch Validierungsfehler.";
    return;
  }

  isGenerating.value = true;
  serverError.value = "";

  try {
    const response = await fetch(`${apiBaseUrl}/api/invoices/generate-single`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(buildSingleRowPayload(selectedRow.value)),
    });

    if (!response.ok) {
      const payload = (await response.json().catch(() => null)) as {
        detail?: string;
      } | null;
      throw new Error(
        payload?.detail ?? `PDF-Erstellung fehlgeschlagen (${response.status})`,
      );
    }

    const blob = await response.blob();
    const downloadUrl = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = downloadUrl;
    anchor.download = `${selectedRow.value.invoice_number || "rechnung"}.pdf`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(downloadUrl);

    generatedRowUids.value = [...generatedRowUids.value, selectedRow.value.uid];
    selectNextAvailableRow();
  } catch (error) {
    serverError.value =
      error instanceof Error
        ? error.message
        : "Unbekannter Fehler bei der PDF-Erstellung.";
  } finally {
    isGenerating.value = false;
  }
}

async function loadSelectedRowPreview() {
  previewError.value = "";

  if (!selectedRow.value) {
    previewError.value =
      "Bitte waehle zuerst eine Rechnungszeile fuer die PDF-Vorschau aus.";
    return;
  }

  if (!validationIsCurrent.value) {
    previewError.value =
      "Bitte validiere die aktuellen Daten erneut, bevor du die PDF-Vorschau laedst.";
    return;
  }

  if (rowHasErrors(selectedRowIndex.value)) {
    previewError.value =
      "Die ausgewaehlte Zeile enthaelt noch Validierungsfehler.";
    return;
  }

  const previewWindow = window.open("", "_blank");
  if (!previewWindow) {
    previewError.value =
      "Bitte erlaube Pop-ups, damit die PDF-Vorschau in einem neuen Tab geoeffnet werden kann.";
    return;
  }

  previewWindow.opener = null;
  previewWindow.document.write(`
    <!doctype html>
    <html lang="de">
      <head>
        <meta charset="utf-8">
        <title>PDF-Vorschau</title>
      </head>
      <body style="font-family: sans-serif; padding: 24px;">
        PDF-Vorschau wird geladen...
      </body>
    </html>
  `);
  previewWindow.document.close();

  isPreviewLoading.value = true;

  try {
    const response = await fetch(`${apiBaseUrl}/api/invoices/generate-single`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(buildSingleRowPayload(selectedRow.value)),
    });

    if (!response.ok) {
      const payload = (await response.json().catch(() => null)) as {
        detail?: string;
      } | null;
      throw new Error(
        payload?.detail ?? `PDF-Vorschau fehlgeschlagen (${response.status})`,
      );
    }

    const blob = await response.blob();
    const previewUrl = URL.createObjectURL(blob);

    previewWindow.location.href = previewUrl;
    window.setTimeout(() => {
      URL.revokeObjectURL(previewUrl);
    }, 60_000);
  } catch (error) {
    previewWindow.close();
    previewError.value =
      error instanceof Error
        ? error.message
        : "Unbekannter Fehler bei der PDF-Vorschau.";
  } finally {
    isPreviewLoading.value = false;
  }
}

watch(selectedRowUid, () => {
  previewError.value = "";
});
</script>

<template>
  <main
    class="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(255,214,153,0.28),transparent_28%),linear-gradient(135deg,#fffdf8_0%,#f6f8fb_52%,#eef6ef_100%)]"
  >
    <div
      class="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 md:px-8 md:py-10"
    >
      <section>
        <Card class="border-white/60 bg-white/88 shadow-lg backdrop-blur">
          <CardHeader>
            <Badge variant="outline" class="mb-3 w-fit bg-white/80">
              Validieren, bearbeiten, erzeugen
            </Badge>
            <CardTitle class="text-3xl tracking-tight md:text-5xl">
              CSV hochladen, Zeilen pruefen und erst dann Rechnungs-PDFs
              erstellen.
            </CardTitle>
            <CardDescription class="max-w-2xl text-base text-slate-600">
              Nach dem Upload kannst du jede Rechnungszeile bearbeiten. Erst
              wenn die aktuelle Version fehlerfrei validiert ist, wird die
              ZIP-Datei mit allen PDF-Rechnungen erzeugt.
            </CardDescription>
          </CardHeader>
        </Card>
      </section>

      <section class="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <Card class="border-white/60 bg-white/88 shadow-lg backdrop-blur">
          <CardHeader>
            <CardTitle>CSV-Datei laden</CardTitle>
            <CardDescription>
              Das aktuelle Preismodell erwartet genau diese Spalten.
            </CardDescription>
          </CardHeader>
          <CardContent class="space-y-6">
            <div class="space-y-2">
              <Label for="csv-upload">CSV-Datei</Label>
              <Input
                id="csv-upload"
                type="file"
                accept=".csv,text/csv"
                class="bg-white"
                @change="handleFileChange"
              />
            </div>

            <div class="flex flex-wrap gap-3">
              <Button
                as="a"
                :href="SAMPLE_CSV_DOWNLOAD_PATH"
                download="invoice-pricing-example.csv"
                variant="outline"
              >
                Beispiel-CSV herunterladen
              </Button>
              <p class="self-center text-sm text-slate-500">
                Enthält auch die optionale Spalte
                <code>include_extended_km_surcharge</code>.
              </p>
            </div>

            <div class="flex flex-wrap gap-2">
              <Badge
                v-for="column in REQUIRED_COLUMNS"
                :key="column"
                variant="secondary"
                class="bg-slate-100 text-slate-700"
              >
                {{ column }}
              </Badge>
            </div>

            <Alert v-if="fileError" variant="destructive">
              <AlertTitle>Dateifehler</AlertTitle>
              <AlertDescription>{{ fileError }}</AlertDescription>
            </Alert>

            <Alert v-if="serverError" variant="destructive">
              <AlertTitle>Serverfehler</AlertTitle>
              <AlertDescription>{{ serverError }}</AlertDescription>
            </Alert>

            <div
              v-if="hasRows"
              class="grid gap-4 rounded-xl border border-slate-200 bg-slate-50 p-4 md:grid-cols-3"
            >
              <div>
                <p
                  class="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500"
                >
                  Datei
                </p>
                <p class="mt-1 text-sm font-medium text-slate-900">
                  {{ selectedFileName }}
                </p>
              </div>
              <div>
                <p
                  class="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500"
                >
                  Zeilen
                </p>
                <p class="mt-1 text-sm font-medium text-slate-900">
                  {{ localRowCount }}
                </p>
              </div>
              <div>
                <p
                  class="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500"
                >
                  Spalten
                </p>
                <p class="mt-1 text-sm font-medium text-slate-900">
                  {{ localHeaders.length }}
                </p>
              </div>
            </div>

            <div class="flex flex-wrap gap-3">
              <Button
                :disabled="!hasRows || isValidating"
                @click="validateRows"
              >
                {{
                  isValidating
                    ? "Zeilen werden validiert..."
                    : "Aktuelle Zeilen validieren"
                }}
              </Button>
              <Button
                variant="outline"
                :disabled="!canGenerate"
                @click="generateInvoices"
              >
                {{
                  isGenerating
                    ? "PDFs werden erzeugt..."
                    : "PDF-Rechnungen als ZIP erzeugen"
                }}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card class="border-white/60 bg-white/88 shadow-lg backdrop-blur">
          <CardHeader>
            <CardTitle>Validierungsstatus</CardTitle>
            <CardDescription>
              Bearbeitete Daten muessen erneut geprueft werden, bevor die
              PDF-Erstellung aktiv ist.
            </CardDescription>
          </CardHeader>
          <CardContent class="space-y-4">
            <div
              v-if="!validationResult"
              class="rounded-xl border border-dashed border-slate-300 p-6 text-sm text-slate-500"
            >
              Noch keine Validierung ausgefuehrt.
            </div>

            <template v-else>
              <div class="grid gap-4 md:grid-cols-3">
                <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <p
                    class="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500"
                  >
                    Gesamt
                  </p>
                  <p class="mt-2 text-2xl font-semibold text-slate-900">
                    {{ validationResult.total_rows }}
                  </p>
                </div>
                <div
                  class="rounded-xl border border-emerald-200 bg-emerald-50 p-4"
                >
                  <p
                    class="text-xs font-semibold uppercase tracking-[0.16em] text-emerald-700"
                  >
                    Gueltig
                  </p>
                  <p class="mt-2 text-2xl font-semibold text-emerald-900">
                    {{ validationResult.valid_rows }}
                  </p>
                </div>
                <div class="rounded-xl border border-rose-200 bg-rose-50 p-4">
                  <p
                    class="text-xs font-semibold uppercase tracking-[0.16em] text-rose-700"
                  >
                    Fehlerhaft
                  </p>
                  <p class="mt-2 text-2xl font-semibold text-rose-900">
                    {{ validationResult.invalid_rows }}
                  </p>
                </div>
              </div>

              <Alert
                :variant="
                  validationResult.invalid_rows > 0 ? 'destructive' : 'default'
                "
                :class="
                  validationResult.invalid_rows === 0
                    ? 'border-emerald-200 bg-emerald-50 text-emerald-950'
                    : ''
                "
              >
                <AlertTitle>
                  {{
                    validationIsCurrent
                      ? validationResult.invalid_rows === 0
                        ? "Aktuelle Zeilen sind gueltig"
                        : "Aktuelle Zeilen enthalten Fehler"
                      : "Validierung ist veraltet"
                  }}
                </AlertTitle>
                <AlertDescription>
                  {{
                    validationIsCurrent
                      ? validationResult.invalid_rows === 0
                        ? "Du kannst jetzt einzelne PDFs oder die gesamte ZIP-Datei erzeugen."
                        : "Bitte korrigiere die markierten Felder und validiere erneut."
                      : "Seit der letzten Validierung wurden Werte geaendert. Bitte erneut pruefen."
                  }}
                </AlertDescription>
              </Alert>

              <div
                v-if="validationResult.errors.length > 0"
                class="overflow-hidden rounded-xl border border-slate-200"
              >
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead class="w-24">Zeile</TableHead>
                      <TableHead class="w-40">Spalte</TableHead>
                      <TableHead>Fehler</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow
                      v-for="error in validationResult.errors"
                      :key="`${error.row_number}-${error.column}-${error.message}`"
                    >
                      <TableCell>{{ error.row_number }}</TableCell>
                      <TableCell>{{ error.column ?? "Allgemein" }}</TableCell>
                      <TableCell>{{ error.message }}</TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </div>
            </template>
          </CardContent>
        </Card>
      </section>

      <section v-if="hasRows" class="space-y-4">
        <div class="flex items-center justify-between gap-4">
          <div>
            <h2 class="text-2xl font-semibold tracking-tight text-slate-950">
              Einzelne Rechnungszeile bearbeiten
            </h2>
            <p class="text-sm text-slate-600">
              Waehle eine Zeile aus. Bereits erzeugte PDFs werden im Auswahlfeld
              deaktiviert.
            </p>
          </div>
          <Badge variant="outline" class="bg-white/80">
            {{ editableRows.length }} Zeile(n) ·
            {{ generatedRowUids.length }} PDF(s) erzeugt
          </Badge>
        </div>

        <Card class="border-white/60 bg-white/88 shadow-lg backdrop-blur">
          <CardHeader>
            <div class="grid gap-3 md:grid-cols-[1fr_auto_auto] md:items-end">
              <div class="space-y-2">
                <Label for="row-select">Rechnungszeile auswaehlen</Label>
                <select
                  id="row-select"
                  v-model="selectedRowUid"
                  class="border-input bg-background flex h-10 w-full rounded-md border px-3 py-2 text-sm shadow-xs"
                >
                  <option
                    v-for="(row, index) in editableRows"
                    :key="row.uid"
                    :value="row.uid"
                    :disabled="isRowGenerated(row.uid)"
                  >
                    Zeile {{ index + 2 }} ·
                    {{ row.invoice_number || "Ohne Rechnungsnummer" }} ·
                    {{ row.customer_name || "Ohne Kundenname"
                    }}{{ isRowGenerated(row.uid) ? " · PDF erstellt" : "" }}
                  </option>
                </select>
              </div>
              <Button
                variant="secondary"
                :disabled="!selectedRow || isPreviewLoading"
                @click="loadSelectedRowPreview"
              >
                {{
                  isPreviewLoading
                    ? "Vorschau wird geladen..."
                    : "PDF-Vorschau laden"
                }}
              </Button>
              <Button
                variant="outline"
                :disabled="
                  !selectedRow ||
                  isGenerating ||
                  (selectedRow ? isRowGenerated(selectedRow.uid) : true)
                "
                @click="generateSelectedRowPdf"
              >
                {{
                  isGenerating
                    ? "PDF wird erzeugt..."
                    : selectedRow && isRowGenerated(selectedRow.uid)
                      ? "PDF bereits erstellt"
                      : "PDF fuer diese Zeile erzeugen"
                }}
              </Button>
            </div>
          </CardHeader>
        </Card>

        <Alert v-if="previewError" variant="destructive">
          <AlertTitle>Vorschau nicht verfuegbar</AlertTitle>
          <AlertDescription>{{ previewError }}</AlertDescription>
        </Alert>

        <div v-if="selectedRow" :key="selectedRow.uid" class="grid gap-5">
          <Card class="border-white/60 bg-white/88 shadow-lg backdrop-blur">
            <CardHeader
              class="gap-4 md:flex-row md:items-start md:justify-between"
            >
              <div>
                <CardTitle class="text-xl">
                  Zeile {{ selectedRowIndex + 2 }} ·
                  {{ selectedRow.invoice_number || "Ohne Rechnungsnummer" }}
                </CardTitle>
                <CardDescription>
                  {{ selectedRow.customer_name || "Ohne Kundenname" }} ·
                  {{ selectedRow.dog_name || "Ohne Hundename" }}
                </CardDescription>
              </div>
              <Badge
                :variant="
                  isRowGenerated(selectedRow.uid)
                    ? 'secondary'
                    : rowHasErrors(selectedRowIndex)
                      ? 'destructive'
                      : 'secondary'
                "
              >
                {{
                  isRowGenerated(selectedRow.uid)
                    ? "PDF bereits erstellt"
                    : rowHasErrors(selectedRowIndex)
                      ? "Fehler vorhanden"
                      : "Ohne Fehlerhinweis"
                }}
              </Badge>
            </CardHeader>
            <CardContent class="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
              <div class="grid gap-4 md:grid-cols-2">
                <div class="space-y-2">
                  <Label for="invoice-number-selected">Rechnungsnummer</Label>
                  <Input
                    id="invoice-number-selected"
                    v-model="selectedRow.invoice_number"
                    @update:model-value="markRowDirty"
                  />
                  <p
                    v-for="message in validationErrorsForField(
                      selectedRowIndex,
                      'invoice_number',
                    )"
                    :key="message"
                    class="text-xs text-rose-600"
                  >
                    {{ message }}
                  </p>
                </div>

                <div class="space-y-2">
                  <Label for="billing-month-selected">Abrechnungsmonat</Label>
                  <Input
                    id="billing-month-selected"
                    v-model="selectedRow.billing_month"
                    type="month"
                    @update:model-value="markRowDirty"
                  />
                  <p
                    v-for="message in validationErrorsForField(
                      selectedRowIndex,
                      'billing_month',
                    )"
                    :key="message"
                    class="text-xs text-rose-600"
                  >
                    {{ message }}
                  </p>
                </div>

                <div class="space-y-2">
                  <Label for="invoice-date-selected">Rechnungsdatum</Label>
                  <Input
                    id="invoice-date-selected"
                    v-model="selectedRow.invoice_date"
                    type="date"
                    @update:model-value="markRowDirty"
                  />
                  <p
                    v-for="message in validationErrorsForField(
                      selectedRowIndex,
                      'invoice_date',
                    )"
                    :key="message"
                    class="text-xs text-rose-600"
                  >
                    {{ message }}
                  </p>
                </div>

                <div class="space-y-2">
                  <Label for="due-date-selected">Faelligkeitsdatum</Label>
                  <Input
                    id="due-date-selected"
                    v-model="selectedRow.due_date"
                    type="date"
                    @update:model-value="markRowDirty"
                  />
                  <p
                    v-for="message in validationErrorsForField(
                      selectedRowIndex,
                      'due_date',
                    )"
                    :key="message"
                    class="text-xs text-rose-600"
                  >
                    {{ message }}
                  </p>
                </div>

                <div class="space-y-2">
                  <Label for="customer-name-selected">Kundenname</Label>
                  <Input
                    id="customer-name-selected"
                    v-model="selectedRow.customer_name"
                    @update:model-value="markRowDirty"
                  />
                  <p
                    v-for="message in validationErrorsForField(
                      selectedRowIndex,
                      'customer_name',
                    )"
                    :key="message"
                    class="text-xs text-rose-600"
                  >
                    {{ message }}
                  </p>
                </div>

                <div class="space-y-2">
                  <Label for="dog-name-selected">Hundename</Label>
                  <Input
                    id="dog-name-selected"
                    v-model="selectedRow.dog_name"
                    @update:model-value="markRowDirty"
                  />
                  <p
                    v-for="message in validationErrorsForField(
                      selectedRowIndex,
                      'dog_name',
                    )"
                    :key="message"
                    class="text-xs text-rose-600"
                  >
                    {{ message }}
                  </p>
                </div>

                <div class="space-y-2">
                  <Label for="subscription-plan-selected">Abo-Modell</Label>
                  <select
                    id="subscription-plan-selected"
                    v-model="selectedRow.subscription_plan"
                    class="border-input bg-background flex h-9 w-full rounded-md border px-3 py-1 text-sm shadow-xs"
                    @change="markRowDirty"
                  >
                    <option value="none">Kein Abo</option>
                    <option value="1x_week">1x pro Woche</option>
                    <option value="2x_week">2x pro Woche</option>
                    <option value="3x_week">3x pro Woche</option>
                    <option value="4x_week">4x pro Woche</option>
                  </select>
                  <p
                    v-for="message in validationErrorsForField(
                      selectedRowIndex,
                      'subscription_plan',
                    )"
                    :key="message"
                    class="text-xs text-rose-600"
                  >
                    {{ message }}
                  </p>
                  <p class="text-xs text-slate-500">
                    Standardpreis:
                    {{
                      formatEuro(
                        SUBSCRIPTION_PRICES[selectedRow.subscription_plan],
                      )
                    }}
                  </p>
                  <div
                    class="space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-3"
                  >
                    <Label for="subscription-price-override-selected"
                      >Abo-Preis manuell anpassen</Label
                    >
                    <Input
                      id="subscription-price-override-selected"
                      v-model="selectedRow.subscription_price_override"
                      type="text"
                      inputmode="decimal"
                      :placeholder="
                        SUBSCRIPTION_PRICES[
                          selectedRow.subscription_plan
                        ].toFixed(2)
                      "
                      :disabled="selectedRow.subscription_plan === 'none'"
                      @update:model-value="markRowDirty"
                      @blur="
                        formatEditableMoneyField(
                          selectedRow,
                          'subscription_price_override',
                        )
                      "
                    />
                    <p class="text-xs text-slate-500">
                      Leer = Standardtarif, Wert = nur fuer diese Zeile
                      ueberschreiben.
                    </p>
                    <p
                      v-for="message in validationErrorsForField(
                        selectedRowIndex,
                        'subscription_price_override',
                      )"
                      :key="message"
                      class="text-xs text-rose-600"
                    >
                      {{ message }}
                    </p>
                  </div>
                </div>

                <div class="space-y-2">
                  <Label for="daily-count-selected"
                    >Zusaetzliche Tagesbetreuung</Label
                  >
                  <Input
                    id="daily-count-selected"
                    v-model="selectedRow.daily_count"
                    type="number"
                    min="0"
                    @update:model-value="markRowDirty"
                  />
                  <p
                    v-for="message in validationErrorsForField(
                      selectedRowIndex,
                      'daily_count',
                    )"
                    :key="message"
                    class="text-xs text-rose-600"
                  >
                    {{ message }}
                  </p>
                  <p class="text-xs text-slate-500">
                    Standardpreis pro Tag:
                    {{
                      formatEuro(
                        selectedRow.daily_count_rebate
                          ? DAILY_PRICE_REBATED
                          : DAILY_PRICE,
                      )
                    }}
                  </p>
                  <div
                    class="space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-3"
                  >
                    <Label for="daily-price-override-selected"
                      >Tagespreis manuell anpassen</Label
                    >
                    <Input
                      id="daily-price-override-selected"
                      v-model="selectedRow.daily_price_override"
                      type="text"
                      inputmode="decimal"
                      :placeholder="
                        (selectedRow.daily_count_rebate
                          ? DAILY_PRICE_REBATED
                          : DAILY_PRICE
                        ).toFixed(2)
                      "
                      @update:model-value="markRowDirty"
                      @blur="
                        formatEditableMoneyField(
                          selectedRow,
                          'daily_price_override',
                        )
                      "
                    />
                    <p class="text-xs text-slate-500">
                      Gilt pro Termin und nur fuer diese Zeile.
                    </p>
                    <p
                      v-for="message in validationErrorsForField(
                        selectedRowIndex,
                        'daily_price_override',
                      )"
                      :key="message"
                      class="text-xs text-rose-600"
                    >
                      {{ message }}
                    </p>
                  </div>
                </div>

                <div
                  class="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 md:col-span-2"
                >
                  <input
                    id="daily-count-rebate-selected"
                    v-model="selectedRow.daily_count_rebate"
                    type="checkbox"
                    class="h-4 w-4 rounded border-slate-300"
                    @change="markRowDirty"
                  />
                  <Label for="daily-count-rebate-selected"
                    >Tagesbetreuung-Rabatt fuer alle Termine (30 statt
                    35)</Label
                  >
                </div>

                <div class="space-y-2 md:col-span-2">
                  <Label for="daily-dates-selected"
                    >Tagesbetreuung Termine</Label
                  >
                  <Input
                    id="daily-dates-selected"
                    v-model="selectedRow.daily_dates"
                    placeholder="2026-03-03,2026-03-10,2026-03-17"
                    @update:model-value="markRowDirty"
                  />
                  <p class="text-xs text-slate-500">
                    Kommagetrennte ISO-Daten, z. B. 2026-03-03,2026-03-10
                  </p>
                  <p
                    v-for="message in validationErrorsForField(
                      selectedRowIndex,
                      'daily_dates',
                    )"
                    :key="message"
                    class="text-xs text-rose-600"
                  >
                    {{ message }}
                  </p>
                </div>

                <div
                  class="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 md:col-span-2"
                >
                  <input
                    id="test-run-selected"
                    v-model="selectedRow.include_test_run"
                    type="checkbox"
                    class="h-4 w-4 rounded border-slate-300"
                    @change="markRowDirty"
                  />
                  <Label for="test-run-selected">Probetag berechnen</Label>
                </div>

                <div class="space-y-2 md:col-span-2">
                  <Label for="test-run-price-override-selected"
                    >Probetag-Preis manuell anpassen</Label
                  >
                  <Input
                    :key="`${selectedRow.uid}-test-run-price-${selectedRow.include_test_run}`"
                    id="test-run-price-override-selected"
                    v-model="selectedRow.test_run_price_override"
                    type="text"
                    inputmode="decimal"
                    :placeholder="TEST_RUN_PRICE.toFixed(2)"
                    :disabled="!selectedRow.include_test_run"
                    @update:model-value="markRowDirty"
                    @blur="
                      formatEditableMoneyField(
                        selectedRow,
                        'test_run_price_override',
                      )
                    "
                  />
                  <p class="text-xs text-slate-500">
                    Standardpreis: {{ formatEuro(TEST_RUN_PRICE) }}
                  </p>
                  <p
                    v-for="message in validationErrorsForField(
                      selectedRowIndex,
                      'test_run_price_override',
                    )"
                    :key="message"
                    class="text-xs text-rose-600"
                  >
                    {{ message }}
                  </p>
                </div>

                <div
                  class="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 md:col-span-2"
                >
                  <input
                    id="extended-km-surcharge-selected"
                    v-model="selectedRow.include_extended_km_surcharge"
                    type="checkbox"
                    class="h-4 w-4 rounded border-slate-300"
                    @change="markRowDirty"
                  />
                  <Label for="extended-km-surcharge-selected"
                    >Zuschlag fuer erweiterten Kilometerbereich berechnen</Label
                  >
                </div>
                <div class="space-y-2 md:col-span-2">
                  <Label for="extended-km-surcharge-amount-selected"
                    >Kilometer-Zuschlag</Label
                  >
                  <Input
                    :key="`${selectedRow.uid}-extended-km-${selectedRow.include_extended_km_surcharge}`"
                    id="extended-km-surcharge-amount-selected"
                    v-model="selectedRow.extended_km_surcharge_amount"
                    type="text"
                    inputmode="decimal"
                    :placeholder="
                      DEFAULT_EXTENDED_KM_SURCHARGE_AMOUNT.toFixed(2)
                    "
                    :disabled="!selectedRow.include_extended_km_surcharge"
                    @update:model-value="markRowDirty"
                    @blur="
                      formatEditableMoneyField(
                        selectedRow,
                        'extended_km_surcharge_amount',
                      )
                    "
                  />
                  <p class="text-xs text-slate-500">
                    Standardwert:
                    {{ formatEuro(DEFAULT_EXTENDED_KM_SURCHARGE_AMOUNT) }}
                  </p>
                  <p
                    v-for="message in validationErrorsForField(
                      selectedRowIndex,
                      'extended_km_surcharge_amount',
                    )"
                    :key="message"
                    class="text-xs text-rose-600"
                  >
                    {{ message }}
                  </p>
                </div>

                <div class="space-y-2 md:col-span-2">
                  <Label for="customer-address-selected">Kundenadresse</Label>
                  <textarea
                    id="customer-address-selected"
                    v-model="selectedRow.customer_address"
                    class="border-input bg-background min-h-24 w-full rounded-md border px-3 py-2 text-sm shadow-xs"
                    @input="handleSelectedAddressInput"
                  />
                  <div class="flex flex-wrap items-center gap-3">
                    <Button
                      type="button"
                      variant="outline"
                      :disabled="isResolvingSelectedRowDistance"
                      @click="resolveSelectedRowAddressDistance"
                    >
                      {{
                        isResolvingSelectedRowDistance
                          ? "Adresse wird geprueft..."
                          : "Adresse ueber Nominatim + OSRM pruefen"
                      }}
                    </Button>
                    <p class="text-xs text-slate-500">
                      Loest die Adresse in Koordinaten auf und setzt den
                      Kilometer-Zuschlag passend zum
                      {{ SERVICE_AREA_RADIUS_KM }}-km-Standardbereich.
                    </p>
                  </div>
                  <p
                    v-for="message in validationErrorsForField(
                      selectedRowIndex,
                      'customer_address',
                    )"
                    :key="message"
                    class="text-xs text-rose-600"
                  >
                    {{ message }}
                  </p>
                  <Alert
                    v-if="selectedRowAddressDistanceError"
                    variant="destructive"
                  >
                    <AlertTitle>Distanz konnte nicht berechnet werden</AlertTitle>
                    <AlertDescription>
                      {{ selectedRowAddressDistanceError }}
                    </AlertDescription>
                  </Alert>
                  <div
                    v-if="selectedRowAddressDistance"
                    class="rounded-xl border border-slate-200 bg-slate-50 p-4"
                  >
                    <div
                      class="flex flex-wrap items-start justify-between gap-3"
                    >
                      <div>
                        <p
                          class="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500"
                        >
                          Distanz ab Basis
                        </p>
                        <p class="mt-1 text-2xl font-semibold text-slate-950">
                          {{
                            formatKilometers(
                              selectedRowAddressDistance.route_distance_km,
                            )
                          }}
                        </p>
                      </div>
                      <Badge
                        :variant="
                          selectedRowAddressDistance.should_apply_extended_km_surcharge
                            ? 'destructive'
                            : 'secondary'
                        "
                      >
                        {{
                          selectedRowAddressDistance.should_apply_extended_km_surcharge
                            ? 'Zuschlag aktiv'
                            : 'Im Standardbereich'
                        }}
                      </Badge>
                    </div>
                    <p class="mt-3 text-sm text-slate-700">
                      {{ selectedRowAddressDistance.resolved_address }}
                    </p>
                    <p class="mt-2 text-xs text-slate-500">
                      Start:
                      {{
                        formatCoordinate(
                          selectedRowAddressDistance.origin.latitude,
                        )
                      }},
                      {{
                        formatCoordinate(
                          selectedRowAddressDistance.origin.longitude,
                        )
                      }}
                      · Ziel:
                      {{
                        formatCoordinate(
                          selectedRowAddressDistance.destination.latitude,
                        )
                      }},
                      {{
                        formatCoordinate(
                          selectedRowAddressDistance.destination.longitude,
                        )
                      }}
                    </p>
                    <p class="mt-2 text-xs text-slate-500">
                      Standardbereich:
                      {{
                        formatKilometers(
                          selectedRowAddressDistance.included_radius_km,
                        )
                      }}.
                      Der Zuschlag-Schalter wurde automatisch
                      {{
                        selectedRowAddressDistance.should_apply_extended_km_surcharge
                          ? 'aktiviert'
                          : 'deaktiviert'
                      }}.
                    </p>
                  </div>
                </div>
              </div>

              <div class="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p
                  class="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500"
                >
                  Vorschau der Leistungspositionen
                </p>
                <div class="mt-4 space-y-3">
                  <div
                    v-for="item in previewLineItems(selectedRow)"
                    :key="`${item.label}-${item.detail}`"
                    class="rounded-xl border border-white bg-white p-3 shadow-sm"
                  >
                    <div class="flex items-start justify-between gap-3">
                      <div>
                        <p class="font-medium text-slate-950">
                          {{ item.label }}
                        </p>
                        <p class="text-sm text-slate-600">{{ item.detail }}</p>
                      </div>
                      <p class="font-semibold text-slate-950">
                        {{ formatEuro(item.amount) }}
                      </p>
                    </div>
                  </div>

                  <div
                    v-if="previewLineItems(selectedRow).length === 0"
                    class="rounded-xl border border-dashed border-slate-300 p-4 text-sm text-slate-500"
                  >
                    Noch keine abrechenbare Position vorhanden.
                  </div>
                </div>

                <div
                  class="mt-4 rounded-xl bg-slate-950 px-4 py-3 text-slate-50"
                >
                  <p class="text-xs uppercase tracking-[0.16em] text-slate-300">
                    Netto geschaetzt
                  </p>
                  <p class="mt-1 text-2xl font-semibold">
                    {{ formatEuro(estimateTotal(selectedRow)) }}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
        <div
          v-else
          class="rounded-2xl border border-dashed border-slate-300 bg-white/70 p-8 text-center text-sm text-slate-600"
        >
          Alle aktuell ausgewaehlten Zeilen wurden bereits als PDF erzeugt.
        </div>
      </section>
    </div>
  </main>
</template>
