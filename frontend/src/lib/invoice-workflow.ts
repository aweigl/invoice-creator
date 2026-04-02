export type WorkflowStep = "upload" | "review" | "download";

export type SubscriptionPlan =
  | "none"
  | "1x_week"
  | "2x_week"
  | "3x_week"
  | "4x_week";

export type CsvValidationError = {
  row_number: number;
  column: string | null;
  message: string;
};

export type PricingRow = {
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

export type EditablePricingRow = PricingRow & {
  uid: string;
  subscription_price_override: string;
  daily_price_override: string;
  test_run_price_override: string;
  extended_km_surcharge_amount: string;
};

export type CsvValidationResult = {
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

export type PreviewLineItem = {
  label: string;
  detail: string;
  amount: number;
};

export type CoordinatePoint = {
  latitude: number;
  longitude: number;
};

export type AddressDistanceResult = {
  address: string;
  resolved_address: string;
  origin: CoordinatePoint;
  destination: CoordinatePoint;
  route_distance_meters: number;
  route_distance_km: number;
  included_radius_km: number;
  should_apply_extended_km_surcharge: boolean;
};

export const MAX_CSV_BYTES = 2 * 1024 * 1024;

export const REQUIRED_COLUMNS = [
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

export const SUBSCRIPTION_PRICES: Record<SubscriptionPlan, number> = {
  none: 0,
  "1x_week": 120,
  "2x_week": 190,
  "3x_week": 290,
  "4x_week": 390,
};

export const PLAN_LABELS: Record<SubscriptionPlan, string> = {
  none: "Kein Abo",
  "1x_week":
    "Abholung Gruppenspaziergang und Heimbringen {dog_name} von/zu Ihrem Haus in Köln (1x pro Woche)",
  "2x_week":
    "Abholung Gruppenspaziergang und Heimbringen {dog_name} von/zu Ihrem Haus in Köln (2x pro Woche)",
  "3x_week":
    "Abholung Gruppenspaziergang und Heimbringen {dog_name} von/zu Ihrem Haus in Köln (3x pro Woche)",
  "4x_week":
    "Abholung Gruppenspaziergang und Heimbringen {dog_name} von/zu Ihrem Haus in Köln (4x pro Woche)",
};

export const DAILY_PRICE = 35;
export const DAILY_PRICE_REBATED = 30;
export const TEST_RUN_PRICE = 20;
export const DEFAULT_EXTENDED_KM_SURCHARGE_AMOUNT = 2.5;
export const SERVICE_AREA_RADIUS_KM = 10;
export const CSV_DELIMITERS = [";", ","] as const;
export const SAMPLE_CSV_DOWNLOAD_PATH = `${import.meta.env.BASE_URL}invoice-pricing-example.csv`;
