<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Archive, CheckCircle2, FileUp, PenLine } from "lucide-vue-next";

import DownloadStep from "@/components/workflow/DownloadStep.vue";
import ReviewStep from "@/components/workflow/ReviewStep.vue";
import UploadStep from "@/components/workflow/UploadStep.vue";
import { Badge } from "@/components/ui/badge";
import {
  PLAN_LABELS,
  CSV_DELIMITERS,
  DAILY_PRICE,
  DAILY_PRICE_REBATED,
  DEFAULT_EXTENDED_KM_SURCHARGE_AMOUNT,
  MAX_CSV_BYTES,
  REQUIRED_COLUMNS,
  SAMPLE_CSV_DOWNLOAD_PATH,
  SERVICE_AREA_RADIUS_KM,
  SUBSCRIPTION_PRICES,
  TEST_RUN_PRICE,
} from "@/lib/invoice-workflow";
import type {
  AddressDistanceResult,
  CsvValidationError,
  CsvValidationResult,
  EditablePricingRow,
  PreviewLineItem,
  PricingRow,
  SubscriptionPlan,
  WorkflowStep,
} from "@/lib/invoice-workflow";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "";

const selectedFileName = ref("");
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
const lastCheckedAddressByRow = ref<Record<string, string>>({});
const attemptedAddressLookupByRow = ref<Record<string, boolean>>({});
const resolvingDistanceRowUid = ref("");
const currentStep = ref<WorkflowStep>("upload");
const advancedOptionsOpen = ref(false);
const pendingDailyDateByRow = ref<Record<string, string>>({});
const dailyDateInputErrorByRow = ref<Record<string, string>>({});

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
    ? (distanceLookupResults.value[selectedRow.value.uid] ?? null)
    : null,
);
const selectedRowAddressDistanceError = computed(() =>
  selectedRow.value
    ? (distanceLookupErrors.value[selectedRow.value.uid] ?? "")
    : "",
);
const selectedRowNeedsAddressCheck = computed(() => {
  if (!selectedRow.value) {
    return false;
  }

  const address = selectedRow.value.customer_address.trim();
  if (!address) {
    return false;
  }

  return lastCheckedAddressByRow.value[selectedRow.value.uid] !== address;
});
const selectedDailyDates = computed(() =>
  selectedRow.value ? parseDailyDates(selectedRow.value.daily_dates) : [],
);
const selectedPendingDailyDate = computed(() =>
  selectedRow.value ? (pendingDailyDateByRow.value[selectedRow.value.uid] ?? "") : "",
);
const selectedDailyDateInputError = computed(() =>
  selectedRow.value ? (dailyDateInputErrorByRow.value[selectedRow.value.uid] ?? "") : "",
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

const canAccessReview = computed(() => hasRows.value);
const canAccessDownload = computed(() => hasRows.value);

const uploadValidationMessage = computed(() => {
  if (isValidating.value) {
    return "Datei wird automatisch geprueft.";
  }

  if (fileError.value) {
    return "Bitte eine passende CSV hochladen.";
  }

  if (serverError.value && currentStep.value === "upload") {
    return "Pruefung konnte nicht abgeschlossen werden.";
  }

  if (!hasRows.value) {
    return "Bereit fuer deine CSV-Datei.";
  }

  if (!validationResult.value) {
    return "Datei eingelesen. Eine Pruefung steht noch aus.";
  }

  if (!validationIsCurrent.value) {
    return "Datei eingelesen. Aenderungen bitte erneut pruefen.";
  }

  if (validationResult.value.invalid_rows > 0) {
    return `${validationResult.value.invalid_rows} Rechnung(en) brauchen noch Aufmerksamkeit.`;
  }

  return "Datei erfolgreich geprueft. Du kannst weitermachen.";
});

const reviewReady = computed(
  () =>
    validationResult.value !== null &&
    validationIsCurrent.value &&
    validationResult.value.invalid_rows === 0,
);

const selectedRowLabel = computed(() =>
  selectedRow.value
    ? `${selectedRow.value.customer_name || "Ohne Kundenname"} · ${selectedRow.value.invoice_number || "Ohne Rechnungsnummer"}`
    : "Keine Rechnung ausgewaehlt",
);

const selectedRowPreviewItems = computed(() =>
  selectedRow.value ? previewLineItems(selectedRow.value) : [],
);
const selectedRowEstimateTotal = computed(() =>
  selectedRow.value ? estimateTotal(selectedRow.value) : 0,
);

const canPreviewSelectedRow = computed(
  () =>
    selectedRow.value !== null &&
    validationIsCurrent.value &&
    selectedRowIndex.value >= 0 &&
    !rowHasErrors(selectedRowIndex.value),
);

const canGenerateSelectedRow = computed(
  () =>
    selectedRow.value !== null &&
    canPreviewSelectedRow.value &&
    !isRowGenerated(selectedRow.value.uid),
);

const workflowSteps = computed<
  Array<{
    key: WorkflowStep;
    label: string;
    hint: string;
    icon: typeof FileUp;
  }>
>(() => [
  {
    key: "upload",
    label: "CSV hochladen",
    hint: hasRows.value ? "Datei bereit" : "Datei waehlen",
    icon: FileUp,
  },
  {
    key: "review",
    label: "Rechnungen pruefen",
    hint: reviewReady.value ? "Bereit" : "Bearbeiten",
    icon: PenLine,
  },
  {
    key: "download",
    label: "PDFs herunterladen",
    hint: canGenerate.value ? "ZIP bereit" : "Letzter Schritt",
    icon: Archive,
  },
]);

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

function serializeDailyDates(values: string[]): string {
  return values.join(",");
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

function syncDailyDatesForRow(row: EditablePricingRow, dates: string[]) {
  row.daily_dates = serializeDailyDates(dates);
  row.daily_count = String(dates.length);
  markRowDirty();
}

function clearDailyDateInputError(uid: string) {
  const { [uid]: _removed, ...remainingErrors } = dailyDateInputErrorByRow.value;
  dailyDateInputErrorByRow.value = remainingErrors;
}

function setPendingDailyDateForSelectedRow(value: string | number) {
  if (!selectedRow.value) {
    return;
  }

  pendingDailyDateByRow.value = {
    ...pendingDailyDateByRow.value,
    [selectedRow.value.uid]: String(value),
  };
  clearDailyDateInputError(selectedRow.value.uid);
}

function addDailyDateToSelectedRow() {
  if (!selectedRow.value) {
    return;
  }

  const rowUid = selectedRow.value.uid;
  const pendingValue = (pendingDailyDateByRow.value[rowUid] ?? "").trim();

  if (!pendingValue) {
    dailyDateInputErrorByRow.value = {
      ...dailyDateInputErrorByRow.value,
      [rowUid]: "Bitte zuerst einen Termin auswaehlen.",
    };
    return;
  }

  const currentDates = parseDailyDates(selectedRow.value.daily_dates);
  if (currentDates.includes(pendingValue)) {
    dailyDateInputErrorByRow.value = {
      ...dailyDateInputErrorByRow.value,
      [rowUid]: "Dieser Termin ist bereits vorhanden.",
    };
    return;
  }

  syncDailyDatesForRow(selectedRow.value, [...currentDates, pendingValue]);
  pendingDailyDateByRow.value = {
    ...pendingDailyDateByRow.value,
    [rowUid]: "",
  };
  clearDailyDateInputError(rowUid);
}

function removeDailyDateFromSelectedRow(dateValue: string) {
  if (!selectedRow.value) {
    return;
  }

  const nextDates = parseDailyDates(selectedRow.value.daily_dates).filter(
    (entry) => entry !== dateValue,
  );
  syncDailyDatesForRow(selectedRow.value, nextDates);
  clearDailyDateInputError(selectedRow.value.uid);
}

function clearDailyDatesForSelectedRow() {
  if (!selectedRow.value) {
    return;
  }

  syncDailyDatesForRow(selectedRow.value, []);
  clearDailyDateInputError(selectedRow.value.uid);
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
  if (rowIndex < 0) {
    return false;
  }

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
  if (!selectedRow.value) {
    markRowDirty();
    return;
  }

  markRowDirty();
  clearAddressDistanceStateForRow(selectedRow.value.uid);
}

function selectNextAvailableRow() {
  const nextRow = editableRows.value.find(
    (row) => !generatedRowUidSet.value.has(row.uid),
  );
  selectedRowUid.value = nextRow?.uid ?? editableRows.value[0]?.uid ?? "";
}

function resetWorkflowState() {
  validationResult.value = null;
  lastValidatedSnapshot.value = "";
  selectedFileName.value = "";
  localHeaders.value = [];
  localRowCount.value = 0;
  editableRows.value = [];
  selectedRowUid.value = "";
  generatedRowUids.value = [];
  previewError.value = "";
  distanceLookupResults.value = {};
  distanceLookupErrors.value = {};
  lastCheckedAddressByRow.value = {};
  attemptedAddressLookupByRow.value = {};
  resolvingDistanceRowUid.value = "";
  currentStep.value = "upload";
  advancedOptionsOpen.value = false;
  pendingDailyDateByRow.value = {};
  dailyDateInputErrorByRow.value = {};
}

async function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];

  fileError.value = "";
  serverError.value = "";
  resetWorkflowState();

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

  if (parsed.headers.length === 0 || parsed.rows.length === 0) {
    fileError.value =
      "Die CSV-Datei konnte nicht gelesen werden oder enthaelt keine Rechnungszeilen.";
    input.value = "";
    return;
  }

  selectedFileName.value = file.name;
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

  const validationSucceeded = await validateRows("review");
  if (!validationSucceeded) {
    currentStep.value = "upload";
  }
}

async function validateRows(nextStepOnSuccess: WorkflowStep | null = null) {
  if (!hasRows.value) {
    fileError.value =
      "Bitte lade zuerst eine CSV-Datei mit Rechnungszeilen hoch.";
    return false;
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

    if (nextStepOnSuccess) {
      currentStep.value = nextStepOnSuccess;
    }

    return true;
  } catch (error) {
    validationResult.value = null;
    lastValidatedSnapshot.value = "";
    serverError.value =
      error instanceof Error ? error.message : "Unbekannter Serverfehler.";
    return false;
  } finally {
    isValidating.value = false;
  }
}

async function generateInvoices() {
  if (!canGenerate.value) {
    serverError.value =
      "Bitte pruefe die aktuellen Daten erfolgreich, bevor du die ZIP-Datei erstellst.";
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
  attemptedAddressLookupByRow.value = {
    ...attemptedAddressLookupByRow.value,
    [rowUid]: true,
  };

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
        payload?.detail ??
          `Distanzberechnung fehlgeschlagen (${response.status})`,
      );
    }

    const result = (await response.json()) as AddressDistanceResult;
    distanceLookupResults.value = {
      ...distanceLookupResults.value,
      [rowUid]: result,
    };
    lastCheckedAddressByRow.value = {
      ...lastCheckedAddressByRow.value,
      [rowUid]: address,
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
    lastCheckedAddressByRow.value = {
      ...lastCheckedAddressByRow.value,
      [rowUid]: address,
    };
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

function tryInitialSelectedRowAddressLookup() {
  if (!selectedRow.value) {
    return;
  }

  const rowUid = selectedRow.value.uid;
  const address = selectedRow.value.customer_address.trim();
  if (!address) {
    clearAddressDistanceStateForRow(rowUid);
    return;
  }

  if (
    lastCheckedAddressByRow.value[rowUid] === address &&
    attemptedAddressLookupByRow.value[rowUid]
  ) {
    return;
  }

  void resolveSelectedRowAddressDistance();
}

async function generateSelectedRowPdf() {
  if (!selectedRow.value) {
    serverError.value = "Bitte waehle zuerst eine Rechnungszeile aus.";
    return;
  }

  if (isRowGenerated(selectedRow.value.uid)) {
    serverError.value = "Fuer diese Rechnung wurde das PDF bereits erstellt.";
    return;
  }

  if (!validationIsCurrent.value) {
    serverError.value =
      "Bitte pruefe die aktuellen Daten erneut, bevor du ein PDF erzeugst.";
    return;
  }

  if (rowHasErrors(selectedRowIndex.value)) {
    serverError.value =
      "Die ausgewaehlte Rechnung enthaelt noch Validierungsfehler.";
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
      "Bitte pruefe die aktuellen Daten erneut, bevor du die PDF-Vorschau laedst.";
    return;
  }

  if (rowHasErrors(selectedRowIndex.value)) {
    previewError.value =
      "Die ausgewaehlte Rechnung enthaelt noch Validierungsfehler.";
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

function selectRowAt(index: number) {
  const row = editableRows.value[index];
  if (!row) {
    return;
  }

  selectedRowUid.value = row.uid;
}

function selectPreviousRow() {
  if (selectedRowIndex.value > 0) {
    selectRowAt(selectedRowIndex.value - 1);
  }
}

function selectNextRow() {
  if (
    selectedRowIndex.value >= 0 &&
    selectedRowIndex.value < editableRows.value.length - 1
  ) {
    selectRowAt(selectedRowIndex.value + 1);
  }
}

function toggleAdvancedOptions() {
  advancedOptionsOpen.value = !advancedOptionsOpen.value;
}

function goToStep(step: WorkflowStep) {
  if (step === "upload") {
    currentStep.value = step;
    return;
  }

  if (step === "review" && canAccessReview.value) {
    currentStep.value = step;
    return;
  }

  if (step === "download" && canAccessDownload.value) {
    currentStep.value = step;
  }
}

watch(selectedRowUid, () => {
  previewError.value = "";
  advancedOptionsOpen.value = false;
  tryInitialSelectedRowAddressLookup();
});

watch(
  hasRows,
  (value) => {
    if (!value) {
      currentStep.value = "upload";
    }
  },
  { immediate: true },
);

</script>

<template>
  <main
    class="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(222,198,166,0.42),transparent_28%),radial-gradient(circle_at_bottom_right,rgba(189,205,186,0.32),transparent_30%),linear-gradient(180deg,#fdf9f3_0%,#f8f1e5_48%,#f0f4ec_100%)]"
  >
    <div
      class="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-6 md:px-8 md:py-10"
    >
      <section
        class="rounded-[2rem] border border-white/70 bg-white/78 p-5 shadow-[0_30px_80px_rgba(69,73,58,0.1)] backdrop-blur md:p-8"
      >
        <div class="flex justify-between">
          <div>
            <img src="/logo.png" alt="Logo" class="h-30 w-auto" />
          </div>
          <div class="space-y-4">
            <Badge
              variant="secondary"
              class="w-fit rounded-full bg-[#f1e4d4] px-3 py-1 text-[#7c634b]"
            >
              <p class="max-w-3xl text-lg leading-7 font-bold text-slate-600">
                💜 Für Lisa von Aaron 🧡
              </p>
            </Badge>
            <div class="space-y-3"></div>
          </div>
        </div>

        <div class="mt-8 grid gap-3 md:grid-cols-3">
          <button
            v-for="(step, index) in workflowSteps"
            :key="step.key"
            type="button"
            class="group rounded-[1.5rem] border px-4 py-4 text-left transition md:px-5"
            :class="
              currentStep === step.key
                ? 'border-[#5d7253] bg-[#5d7253] text-white shadow-lg shadow-[#5d7253]/20'
                : (step.key === 'review' && !canAccessReview) ||
                    (step.key === 'download' && !canAccessDownload)
                  ? 'cursor-not-allowed border-white/60 bg-white/55 text-slate-400'
                  : 'border-white/70 bg-white/70 text-slate-800 hover:-translate-y-0.5 hover:bg-white'
            "
            :disabled="
              (step.key === 'review' && !canAccessReview) ||
              (step.key === 'download' && !canAccessDownload)
            "
            @click="goToStep(step.key)"
          >
            <div class="flex items-start justify-between gap-4">
              <div>
                <p
                  class="text-xs font-semibold uppercase tracking-[0.18em]"
                  :class="
                    currentStep === step.key
                      ? 'text-white/75'
                      : 'text-slate-500'
                  "
                >
                  Schritt {{ index + 1 }}
                </p>
                <p class="mt-2 text-lg font-semibold">
                  {{ step.label }}
                </p>
                <p
                  class="mt-1 text-sm leading-6"
                  :class="
                    currentStep === step.key
                      ? 'text-white/85'
                      : 'text-slate-500'
                  "
                >
                  {{ step.hint }}
                </p>
              </div>
              <component
                :is="step.icon"
                class="size-5"
                :class="
                  currentStep === step.key ? 'text-white' : 'text-slate-400'
                "
              />
            </div>
          </button>
        </div>
      </section>

      <UploadStep
        v-if="currentStep === 'upload'"
        :file-error="fileError"
        :has-rows="hasRows"
        :is-validating="isValidating"
        :local-headers-count="localHeaders.length"
        :local-row-count="localRowCount"
        :on-continue="() => goToStep('review')"
        :on-file-change="handleFileChange"
        :required-columns="REQUIRED_COLUMNS"
        :sample-csv-download-path="SAMPLE_CSV_DOWNLOAD_PATH"
        :selected-file-name="selectedFileName"
        :server-error="serverError"
        :validation-message="uploadValidationMessage"
      />

      <ReviewStep
        v-else-if="currentStep === 'review' && hasRows"
        :advanced-open="advancedOptionsOpen"
        :estimate-total="selectedRowEstimateTotal"
        :format-coordinate="formatCoordinate"
        :format-editable-money-field="formatEditableMoneyField"
        :format-euro="formatEuro"
        :format-kilometers="formatKilometers"
        :generated-row-count="generatedRowUids.length"
        :handle-selected-address-input="handleSelectedAddressInput"
        :is-generating="isGenerating"
        :is-preview-loading="isPreviewLoading"
        :is-resolving-selected-row-distance="isResolvingSelectedRowDistance"
        :is-row-generated="isRowGenerated"
        :is-validating="isValidating"
        :mark-row-dirty="markRowDirty"
        :needs-address-check="selectedRowNeedsAddressCheck"
        :daily-date-input-error="selectedDailyDateInputError"
        :on-generate-single="generateSelectedRowPdf"
        :on-next="selectNextRow"
        :on-open-download="() => goToStep('download')"
        :on-add-daily-date="addDailyDateToSelectedRow"
        :on-clear-daily-dates="clearDailyDatesForSelectedRow"
        :on-pending-daily-date-change="setPendingDailyDateForSelectedRow"
        :on-preview="loadSelectedRowPreview"
        :on-previous="selectPreviousRow"
        :on-remove-daily-date="removeDailyDateFromSelectedRow"
        :on-resolve-address="resolveSelectedRowAddressDistance"
        :on-select-row-at="selectRowAt"
        :on-toggle-advanced="toggleAdvancedOptions"
        :on-validate="() => validateRows()"
        :preview-error="previewError"
        :preview-items="selectedRowPreviewItems"
        :pending-daily-date="selectedPendingDailyDate"
        :row-has-errors="rowHasErrors"
        :rows="editableRows"
        :selected-daily-dates="selectedDailyDates"
        :selected-row="selectedRow"
        :selected-row-address-distance="selectedRowAddressDistance"
        :selected-row-address-distance-error="selectedRowAddressDistanceError"
        :selected-row-index="selectedRowIndex"
        :server-error="serverError"
        :validation-errors-for-field="validationErrorsForField"
        :validation-is-current="validationIsCurrent"
        :validation-result="validationResult"
      />

      <DownloadStep
        v-else-if="currentStep === 'download' && hasRows"
        :can-generate="canGenerate"
        :can-generate-selected="canGenerateSelectedRow"
        :can-preview-selected="canPreviewSelectedRow"
        :generated-row-count="generatedRowUids.length"
        :is-generating="isGenerating"
        :is-preview-loading="isPreviewLoading"
        :on-generate-all="generateInvoices"
        :on-generate-selected="generateSelectedRowPdf"
        :on-go-review="() => goToStep('review')"
        :on-preview-selected="loadSelectedRowPreview"
        :rows-length="editableRows.length"
        :selected-row-label="selectedRowLabel"
        :server-error="serverError"
        :validation-is-current="validationIsCurrent"
        :validation-result="validationResult"
      />

      <section
        v-else
        class="rounded-[2rem] border border-dashed border-[#d9e2d4] bg-white/70 p-8 text-center text-sm leading-7 text-slate-600"
      >
        Lade zuerst eine CSV hoch, damit die naechsten Schritte sichtbar werden.
      </section>
    </div>
  </main>
</template>
