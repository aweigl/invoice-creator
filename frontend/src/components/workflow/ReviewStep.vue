<script setup lang="ts">
import {
  AlertCircle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  CirclePlus,
  Eye,
  PenLine,
  Trash2,
  Settings2,
} from "lucide-vue-next";

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
import { Label } from "@/components/ui/label";
import {
  DAILY_PRICE,
  DAILY_PRICE_REBATED,
  DEFAULT_EXTENDED_KM_SURCHARGE_AMOUNT,
  SERVICE_AREA_RADIUS_KM,
  SUBSCRIPTION_PRICES,
  TEST_RUN_PRICE,
} from "@/lib/invoice-workflow";
import type {
  AddressAutocompleteSuggestion,
  AddressDistanceResult,
  CsvValidationResult,
  EditablePricingRow,
  PreviewLineItem,
  WorkflowStep,
} from "@/lib/invoice-workflow";
import Input from "../ui/input/Input.vue";

const props = defineProps<{
  rows: EditablePricingRow[];
  selectedRow: EditablePricingRow | null;
  selectedRowIndex: number;
  generatedRowCount: number;
  validationResult: CsvValidationResult | null;
  validationIsCurrent: boolean;
  serverError: string;
  previewError: string;
  isPreviewLoading: boolean;
  isGenerating: boolean;
  isValidating: boolean;
  advancedOpen: boolean;
  addressAutocompleteSuggestions: AddressAutocompleteSuggestion[];
  addressAutocompleteError: string;
  isAddressAutocompleteOpen: boolean;
  isAddressAutocompleteLoading: boolean;
  highlightedAddressSuggestionIndex: number;
  selectedRowAddressDistance: AddressDistanceResult | null;
  selectedRowAddressDistanceError: string;
  isResolvingSelectedRowDistance: boolean;
  previewItems: PreviewLineItem[];
  estimateTotal: number;
  pendingDailyDate: string;
  dailyDateInputError: string;
  selectedDailyDates: string[];
  needsAddressCheck: boolean;
  onSelectRowAt: (index: number) => void;
  onPrevious: () => void;
  onNext: () => void;
  onToggleAdvanced: () => void;
  onValidate: (nextStepOnSuccess?: WorkflowStep | null) => Promise<boolean>;
  onPreview: () => void;
  onGenerateSingle: () => void;
  onOpenDownload: () => void;
  onPendingDailyDateChange: (value: string | number) => void;
  onAddDailyDate: () => void;
  onAddressFocus: () => void;
  onAddressBlur: () => void;
  onSelectedAddressKeydown: (event: KeyboardEvent) => void;
  onSelectAddressSuggestion: (
    suggestion: AddressAutocompleteSuggestion,
  ) => void;
  onHighlightAddressSuggestion: (index: number) => void;
  onRemoveDailyDate: (date: string) => void;
  onClearDailyDates: () => void;
  markRowDirty: () => void;
  handleSelectedAddressInput: () => void;
  formatEditableMoneyField: (
    row: EditablePricingRow,
    field:
      | "subscription_price_override"
      | "daily_price_override"
      | "test_run_price_override"
      | "extended_km_surcharge_amount",
  ) => void;
  validationErrorsForField: (rowIndex: number, field: string) => string[];
  rowHasErrors: (rowIndex: number) => boolean;
  isRowGenerated: (uid: string) => boolean;
  formatEuro: (amount: number) => string;
  formatKilometers: (value: number) => string;
  formatCoordinate: (value: number) => string;
}>();

const handleFormValidation = async () => {
  const isValid = await props.onValidate();

  if (!isValid) {
    const element = document.getElementById("error_card");
    element
      ? element.scrollIntoView({ behavior: "smooth", block: "start" })
      : window.scrollTo({ top: 350, behavior: "smooth" });
    return;
  }

  props.onOpenDownload();
};
</script>

<template>
  <section class="space-y-6">
    <Card
      class="border-white/70 bg-white/92 shadow-[0_30px_80px_rgba(69,73,58,0.12)]"
    >
      <CardHeader class="gap-4 md:flex-row md:items-end md:justify-between">
        <div class="space-y-3">
          <Badge
            variant="secondary"
            class="w-fit rounded-full bg-[#eef2e8] px-3 py-1 text-[#4d6145]"
          >
            Schritt 2
          </Badge>
          <CardTitle class="text-3xl leading-tight md:text-4xl" id="error_card">
            Eine Rechnung nach der anderen in Ruhe prüfen.
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent class="space-y-5">
        <div v-if="!!validationResult?.invalid_rows">
          <Alert
            :variant="
              !!validationResult?.invalid_rows ? 'destructive' : 'default'
            "
            :class="
              !!validationResult?.invalid_rows
                ? 'border-[#dbe4d4] bg-[#f7fbf4] text-slate-900'
                : 'border-[#f1e4c9] bg-[#fffaf1] text-slate-900'
            "
          >
            <component
              :is="
                !!validationResult?.invalid_rows ? CheckCircle2 : AlertCircle
              "
              class="mt-0.5 size-4"
            />
            <AlertTitle>
              {{
                !!validationResult?.invalid_rows
                  ? "Es gibt noch Fehler in den Rechnungen."
                  : "Alles ist aktuell geprüft."
              }}
            </AlertTitle>
            <AlertDescription class="leading-6">
              {{
                !!validationResult?.invalid_rows
                  ? "Die markierten Felder brauchen noch Aufmerksamkeit."
                  : "Du kannst jetzt direkt in den Download-Schritt wechseln."
              }}
            </AlertDescription>
          </Alert>
        </div>

        <div
          class="flex flex-col gap-4 rounded-[1.75rem] border border-[#ddd3c3] bg-[#faf5ed] p-5 lg:flex-row lg:items-center lg:justify-between"
        >
          <div class="space-y-3">
            <div class="flex items-center gap-2">
              <Button
                variant="outline"
                class="rounded-full border-[#ddd3c3] bg-white px-3"
                :disabled="selectedRowIndex <= 0"
                @click="onPrevious"
              >
                <ChevronLeft class="size-4" />
                Vorherige
              </Button>
              <Button
                variant="outline"
                class="rounded-full border-[#ddd3c3] bg-white px-3"
                :disabled="selectedRowIndex >= rows.length - 1"
                @click="onNext"
              >
                Nächste
                <ChevronRight class="size-4" />
              </Button>
            </div>
            <div>
              <p class="text-sm font-semibold text-slate-900">
                Rechnung {{ selectedRowIndex + 1 }} von {{ rows.length }}
              </p>
              <p class="text-sm text-slate-600">
                {{ selectedRow?.customer_name || "Ohne Kundenname" }}
                <span class="text-slate-400">·</span>
                {{ selectedRow?.invoice_number || "Ohne Rechnungsnummer" }}
              </p>
            </div>
          </div>

          <div class="flex flex-wrap gap-2">
            <button
              v-for="(row, index) in rows"
              :key="row.uid"
              type="button"
              class="flex size-10 items-center justify-center rounded-full border text-sm font-semibold transition hover:-translate-y-0.5"
              :class="
                index === selectedRowIndex
                  ? 'border-[#5d7253] bg-[#5d7253] text-white shadow-sm'
                  : isRowGenerated(row.uid)
                    ? 'border-[#dbe4d4] bg-[#f6faf3] text-[#5d7253]'
                    : validationIsCurrent && rowHasErrors(index)
                      ? 'border-[#f0c5c5] bg-[#fff4f4] text-[#b34242]'
                      : validationIsCurrent
                        ? 'border-[#ddd3c3] bg-white text-slate-700'
                        : 'border-[#ddd3c3] bg-white text-slate-500'
              "
              :title="`Rechnung ${index + 1}`"
              @click="onSelectRowAt(index)"
            >
              {{ index + 1 }}
            </button>
          </div>
        </div>
      </CardContent>
    </Card>

    <Alert v-if="serverError" variant="destructive">
      <AlertTitle>Prüfung fehlgeschlagen</AlertTitle>
      <AlertDescription>{{ serverError }}</AlertDescription>
    </Alert>

    <Alert v-if="previewError" variant="destructive">
      <AlertTitle>Vorschau nicht verfügbar</AlertTitle>
      <AlertDescription>{{ previewError }}</AlertDescription>
    </Alert>

    <div v-if="selectedRow" class="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
      <Card
        class="border-white/70 bg-white/92 shadow-[0_24px_60px_rgba(69,73,58,0.1)]"
      >
        <CardHeader class="space-y-3">
          <div class="flex items-center gap-3">
            <div class="rounded-2xl bg-[#f1e4d4] p-3 text-[#7c634b]">
              <PenLine class="size-5" />
            </div>
            <div>
              <CardTitle class="text-2xl">Wichtige Angaben</CardTitle>
            </div>
          </div>
        </CardHeader>

        <CardContent class="space-y-6">
          <div class="grid gap-4 md:grid-cols-2">
            <div class="space-y-2">
              <Label for="invoice-number-selected">Rechnungsnummer</Label>
              <Input
                id="invoice-number-selected"
                v-model="selectedRow.invoice_number"
                class="h-11 rounded-2xl border-[#d8dfd3] bg-[#fcfdfb]"
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
                class="h-11 rounded-2xl border-[#d8dfd3] bg-[#fcfdfb]"
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
                class="h-11 rounded-2xl border-[#d8dfd3] bg-[#fcfdfb]"
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
              <Label for="due-date-selected">Fälligkeitsdatum</Label>
              <Input
                id="due-date-selected"
                v-model="selectedRow.due_date"
                type="date"
                class="h-11 rounded-2xl border-[#d8dfd3] bg-[#fcfdfb]"
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
                class="h-11 rounded-2xl border-[#d8dfd3] bg-[#fcfdfb]"
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
                class="h-11 rounded-2xl border-[#d8dfd3] bg-[#fcfdfb]"
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
              <Label for="subscription-plan-selected">Abo</Label>
              <select
                id="subscription-plan-selected"
                v-model="selectedRow.subscription_plan"
                class="flex h-11 w-full rounded-2xl border border-[#d8dfd3] bg-[#fcfdfb] px-4 text-sm text-slate-700 shadow-xs"
                @change="markRowDirty"
              >
                <option value="none">Kein Abo</option>
                <option value="1x_week">1x pro Woche</option>
                <option value="2x_week">2x pro Woche</option>
                <option value="3x_week">3x pro Woche</option>
                <option value="4x_week">4x pro Woche</option>
              </select>
              <p class="text-xs text-slate-500">
                Standard:
                {{
                  formatEuro(SUBSCRIPTION_PRICES[selectedRow.subscription_plan])
                }}
              </p>
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
            </div>

            <div class="space-y-2">
              <Label for="daily-count-selected"
                >Zusätzliche Betreuungstage</Label
              >
              <div
                id="daily-count-selected"
                class="flex h-11 items-center rounded-2xl border border-[#d8dfd3] bg-[#f6f8f2] px-4 text-base font-semibold text-slate-900"
              >
                {{ selectedDailyDates.length }}
              </div>
              <p class="text-xs text-slate-500">
                Wird automatisch aus den ausgewählten Terminen berechnet.
                Standard pro Tag:
                {{
                  formatEuro(
                    selectedRow.daily_count_rebate
                      ? DAILY_PRICE_REBATED
                      : DAILY_PRICE,
                  )
                }}
              </p>
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
            </div>

            <div
              class="flex items-center gap-3 rounded-2xl border border-[#dfe6db] bg-[#f7faf5] px-4 py-3 md:col-span-2"
            >
              <input
                id="daily-count-rebate-selected"
                v-model="selectedRow.daily_count_rebate"
                type="checkbox"
                class="size-4 rounded border-slate-300"
                @change="markRowDirty"
              />
              <Label for="daily-count-rebate-selected" class="leading-6">
                Rabatt für Betreuungstage verwenden
              </Label>
            </div>

            <div class="space-y-2 md:col-span-2">
              <div class="flex flex-wrap items-center justify-between gap-3">
                <Label for="daily-dates-selected"
                  >Termine für Betreuungstage</Label
                >
                <Button
                  v-if="selectedDailyDates.length > 0"
                  variant="ghost"
                  class="h-auto rounded-full px-2 py-1 text-xs text-slate-500 hover:text-slate-900"
                  @click="onClearDailyDates"
                >
                  Alle Termine entfernen
                </Button>
              </div>
              <div
                class="rounded-[1.5rem] border border-[#ddd3c3] bg-[#faf5ed] p-4"
              >
                <div class="flex flex-col gap-3 sm:flex-row">
                  <Input
                    id="daily-dates-selected"
                    :model-value="pendingDailyDate"
                    type="date"
                    class="h-11 rounded-2xl border-[#d8dfd3] bg-white"
                    @update:model-value="onPendingDailyDateChange"
                  />
                  <Button
                    class="rounded-full bg-[#5d7253] px-5 hover:bg-[#4f6348]"
                    @click="onAddDailyDate"
                  >
                    <CirclePlus class="size-4" />
                    Termin hinzufügen
                  </Button>
                </div>
                <p class="mt-3 text-xs text-slate-500">
                  Füge Betreuungstage einzeln hinzu. Die Anzahl wird automatisch
                  passend gesetzt.
                </p>
                <p
                  v-if="dailyDateInputError"
                  class="mt-2 text-xs text-rose-600"
                >
                  {{ dailyDateInputError }}
                </p>

                <div
                  v-if="selectedDailyDates.length > 0"
                  class="mt-4 flex flex-wrap gap-2"
                >
                  <div
                    v-for="dateValue in selectedDailyDates"
                    :key="dateValue"
                    class="flex items-center gap-2 rounded-full border border-[#d8dfd3] bg-white px-3 py-2 text-sm text-slate-700 shadow-sm"
                  >
                    <span>{{ dateValue }}</span>
                    <button
                      type="button"
                      class="rounded-full p-1 text-slate-400 transition hover:bg-[#f5ede1] hover:text-slate-700"
                      :aria-label="`Termin ${dateValue} entfernen`"
                      @click="onRemoveDailyDate(dateValue)"
                    >
                      <Trash2 class="size-3.5" />
                    </button>
                  </div>
                </div>

                <div
                  v-else
                  class="mt-4 rounded-2xl border border-dashed border-[#d8dfd3] bg-white/70 p-4 text-sm text-slate-500"
                >
                  Noch keine Termine hinzugefügt.
                </div>
              </div>
              <p class="text-xs text-slate-500">
                Die Termine werden intern weiterhin als Liste für die Rechnung
                gespeichert.
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

            <div class="space-y-2 md:col-span-2">
              <Label for="customer-address-selected">Kundenadresse</Label>
              <Input
                id="customer-address-selected"
                v-model="selectedRow.customer_address"
                class="w-full rounded-3xl border border-[#d8dfd3] bg-[#fcfdfb] px-4 py-3 text-sm text-slate-700 shadow-xs"
                @input="handleSelectedAddressInput"
                @focus="onAddressFocus"
                @blur="onAddressBlur"
                @keydown="onSelectedAddressKeydown"
              />
              <div
                v-if="isAddressAutocompleteOpen"
                class="overflow-hidden rounded-3xl border border-[#d8dfd3] bg-white shadow-[0_18px_40px_rgba(69,73,58,0.12)]"
              >
                <p
                  v-if="isAddressAutocompleteLoading"
                  class="px-4 py-3 text-sm text-slate-500"
                >
                  Adressvorschläge werden geladen...
                </p>
                <p
                  v-else-if="addressAutocompleteError"
                  class="px-4 py-3 text-sm text-rose-600"
                >
                  {{ addressAutocompleteError }}
                </p>
                <p
                  v-else-if="
                    selectedRow.customer_address.trim().length >= 3 &&
                    addressAutocompleteSuggestions.length === 0
                  "
                  class="px-4 py-3 text-sm text-slate-500"
                >
                  Keine Vorschläge gefunden. Du kannst die Adresse weiter
                  manuell eingeben.
                </p>
                <div v-else class="py-2">
                  <button
                    v-for="(
                      suggestion, index
                    ) in addressAutocompleteSuggestions"
                    :key="`${suggestion.value}-${index}`"
                    type="button"
                    class="block w-full px-4 py-3 text-left text-sm transition"
                    :class="
                      index === highlightedAddressSuggestionIndex
                        ? 'bg-[#f6f2ea] text-slate-900'
                        : 'text-slate-700 hover:bg-[#f8f4ed]'
                    "
                    @mouseenter="onHighlightAddressSuggestion(index)"
                    @mousedown.prevent="onSelectAddressSuggestion(suggestion)"
                  >
                    {{ suggestion.label }}
                  </button>
                </div>
              </div>
              <p
                v-if="isResolvingSelectedRowDistance"
                class="text-xs text-slate-500"
              >
                Adresse wird geprüft...
              </p>
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
            </div>
          </div>

          <div
            v-if="selectedRowAddressDistance"
            class="rounded-2xl bg-white p-4"
          >
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p class="text-sm font-semibold text-slate-900">
                  Adressprüfung erfolgreich
                </p>
                <p class="mt-1 text-sm leading-6 text-slate-600">
                  Die Strecke wurde berechnet und der Zuschlag passend zum
                  {{ SERVICE_AREA_RADIUS_KM }}-km-Bereich gesetzt.
                </p>
              </div>
              <Badge
                :variant="
                  selectedRowAddressDistance.should_apply_extended_km_surcharge
                    ? 'destructive'
                    : 'secondary'
                "
                class="rounded-full px-3 py-1"
              >
                {{
                  selectedRowAddressDistance.should_apply_extended_km_surcharge
                    ? "Zuschlag aktiv"
                    : "Im Standardbereich"
                }}
              </Badge>
            </div>

            <div class="mt-4 rounded-2xl bg-[#f6f2ea] p-4">
              <p
                class="text-xs font-semibold uppercase tracking-[0.18em] text-[#7a654f]"
              >
                Distanz
              </p>
              <p class="mt-2 text-2xl font-semibold text-slate-950">
                {{
                  formatKilometers(selectedRowAddressDistance.route_distance_km)
                }}
              </p>
              <p class="mt-3 text-sm leading-6 text-slate-700">
                {{ selectedRowAddressDistance.resolved_address }}
              </p>
              <p class="mt-2 text-xs leading-5 text-slate-500">
                Start:
                <span class="font-bold">Zu Hause bei deinen Liebsten 🧡 </span>
                <br />
                Ziel:
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
            </div>
          </div>

          <div
            class="rounded-[1.5rem] border border-[#e3d5c2] bg-[#fcf7ef] p-4"
          >
            <div class="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p class="text-sm font-semibold text-slate-900">
                  Erweiterte Optionen
                </p>
                <p class="mt-1 text-sm leading-6 text-slate-600">
                  Nur öffnen, wenn du Sonderfälle, Einzel-PDFs oder die
                  Adressprüfung brauchst.
                </p>
              </div>
              <Button
                variant="outline"
                class="rounded-full border-[#dcccb4] bg-white px-4"
                @click="onToggleAdvanced"
              >
                <Settings2 class="size-4" />
                {{
                  advancedOpen ? "Weniger zeigen" : "Erweiterte Optionen zeigen"
                }}
              </Button>
            </div>

            <div v-if="advancedOpen" class="mt-5 space-y-6">
              <div class="grid gap-4 md:grid-cols-2">
                <div class="space-y-2 rounded-2xl bg-white p-4">
                  <Label for="subscription-price-override-selected">
                    Abo-Preis manuell anpassen
                  </Label>
                  <Input
                    id="subscription-price-override-selected"
                    v-model="selectedRow.subscription_price_override"
                    type="text"
                    inputmode="decimal"
                    :disabled="selectedRow.subscription_plan === 'none'"
                    :placeholder="
                      SUBSCRIPTION_PRICES[
                        selectedRow.subscription_plan
                      ].toFixed(2)
                    "
                    class="h-11 rounded-2xl border-[#e0ddd5]"
                    @update:model-value="markRowDirty"
                    @blur="
                      formatEditableMoneyField(
                        selectedRow,
                        'subscription_price_override',
                      )
                    "
                  />
                  <p class="text-xs text-slate-500">
                    Leer lassen für den Standardpreis.
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

                <div class="space-y-2 rounded-2xl bg-white p-4">
                  <Label for="daily-price-override-selected">
                    Preis pro Betreuungstag anpassen
                  </Label>
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
                    class="h-11 rounded-2xl border-[#e0ddd5]"
                    @update:model-value="markRowDirty"
                    @blur="
                      formatEditableMoneyField(
                        selectedRow,
                        'daily_price_override',
                      )
                    "
                  />
                  <p class="text-xs text-slate-500">
                    Gilt nur für diese eine Rechnung.
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

                <div
                  class="flex items-center gap-3 rounded-2xl border border-[#eadfc9] bg-white px-4 py-3 md:col-span-2"
                >
                  <input
                    id="test-run-selected"
                    v-model="selectedRow.include_test_run"
                    type="checkbox"
                    class="size-4 rounded border-slate-300"
                    @change="markRowDirty"
                  />
                  <Label for="test-run-selected">Probetag berechnen</Label>
                </div>

                <div class="space-y-2 rounded-2xl bg-white p-4">
                  <Label for="test-run-price-override-selected">
                    Probetag-Preis anpassen
                  </Label>
                  <Input
                    :key="`${selectedRow.uid}-test-run-price-${selectedRow.include_test_run}`"
                    id="test-run-price-override-selected"
                    v-model="selectedRow.test_run_price_override"
                    type="text"
                    inputmode="decimal"
                    :disabled="!selectedRow.include_test_run"
                    :placeholder="TEST_RUN_PRICE.toFixed(2)"
                    class="h-11 rounded-2xl border-[#e0ddd5]"
                    @update:model-value="markRowDirty"
                    @blur="
                      formatEditableMoneyField(
                        selectedRow,
                        'test_run_price_override',
                      )
                    "
                  />
                  <p class="text-xs text-slate-500">
                    Standard: {{ formatEuro(TEST_RUN_PRICE) }}
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
                  class="flex items-center gap-3 rounded-2xl border border-[#eadfc9] bg-white px-4 py-3 md:col-span-2"
                >
                  <input
                    id="extended-km-surcharge-selected"
                    v-model="selectedRow.include_extended_km_surcharge"
                    type="checkbox"
                    class="size-4 rounded border-slate-300"
                    @change="markRowDirty"
                  />
                  <Label for="extended-km-surcharge-selected">
                    Kilometer-Zuschlag berechnen
                  </Label>
                </div>

                <div class="space-y-2 rounded-2xl bg-white p-4">
                  <Label for="extended-km-surcharge-amount-selected">
                    Kilometer-Zuschlag
                  </Label>
                  <Input
                    :key="`${selectedRow.uid}-extended-km-${selectedRow.include_extended_km_surcharge}`"
                    id="extended-km-surcharge-amount-selected"
                    v-model="selectedRow.extended_km_surcharge_amount"
                    type="text"
                    inputmode="decimal"
                    :disabled="!selectedRow.include_extended_km_surcharge"
                    :placeholder="
                      DEFAULT_EXTENDED_KM_SURCHARGE_AMOUNT.toFixed(2)
                    "
                    class="h-11 rounded-2xl border-[#e0ddd5]"
                    @update:model-value="markRowDirty"
                    @blur="
                      formatEditableMoneyField(
                        selectedRow,
                        'extended_km_surcharge_amount',
                      )
                    "
                  />
                  <p class="text-xs text-slate-500">
                    Standard:
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
              </div>

              <div class="w-full flex items-end justify-end">
                <Button
                  variant="secondary"
                  class="rounded-full bg-[#f1e7da] px-5 text-[#6c5642] hover:bg-[#eadcc8]"
                  :disabled="!selectedRow || isPreviewLoading"
                  @click="onPreview"
                >
                  <Eye class="size-4" />
                  {{
                    isPreviewLoading
                      ? "Vorschau wird geladen..."
                      : "Einzelne PDF-Vorschau"
                  }}
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card
        class="border-white/70 bg-white/86 shadow-[0_24px_60px_rgba(69,73,58,0.08)]"
      >
        <CardHeader class="space-y-3">
          <div class="flex items-center gap-3">
            <div class="rounded-2xl bg-[#eef2e8] p-3 text-[#5d7253]">
              <CheckCircle2 class="size-5" />
            </div>
            <div>
              <CardTitle class="text-2xl">Schnelle Vorschau</CardTitle>
              <CardDescription class="mt-1 text-sm leading-6 text-slate-600">
                So sieht die aktuelle Rechnung inhaltlich ungefähr aus.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent class="space-y-4">
          <div class="rounded-2xl bg-[#f7f9f6] p-4">
            <p class="text-sm font-semibold text-slate-900">
              {{ selectedRow.customer_name || "Ohne Kundenname" }}
            </p>
            <p class="mt-1 text-sm text-slate-600">
              {{ selectedRow.invoice_number || "Ohne Rechnungsnummer" }}
            </p>
          </div>

          <div class="space-y-3">
            <div
              v-for="item in previewItems"
              :key="`${item.label}-${item.detail}`"
              class="rounded-2xl border border-[#e3e7df] bg-white p-4"
            >
              <div class="flex items-start justify-between gap-3">
                <div>
                  <p class="font-medium text-slate-950">{{ item.label }}</p>
                  <p class="mt-1 text-sm leading-6 text-slate-600">
                    {{ item.detail }}
                  </p>
                </div>
                <p class="font-semibold text-slate-950">
                  {{ formatEuro(item.amount) }}
                </p>
              </div>
            </div>

            <div
              v-if="previewItems.length === 0"
              class="rounded-2xl border border-dashed border-[#d6ddd2] bg-[#fbfcfa] p-4 text-sm leading-6 text-slate-500"
            >
              Noch keine abrechenbare Position vorhanden.
            </div>
          </div>

          <div class="rounded-[1.5rem] bg-[#334235] px-5 py-4 text-white">
            <p class="text-xs uppercase tracking-[0.18em] text-white/70">
              Geschätzter Netto-Betrag
            </p>
            <p class="mt-2 text-3xl font-semibold">
              {{ formatEuro(estimateTotal) }}
            </p>
          </div>

          <Button
            variant="outline"
            class="w-full rounded-full border-[#d8dfd3] bg-white px-6"
            @click="handleFormValidation"
          >
            Weiter zum Download-Schritt
          </Button>
        </CardContent>
      </Card>
    </div>

    <Card
      v-else
      class="border-white/70 bg-white/86 shadow-[0_24px_60px_rgba(69,73,58,0.08)]"
    >
      <CardContent class="p-8 text-center">
        <p class="text-lg font-semibold text-slate-900">
          Alle Rechnungen wurden bereits einzeln als PDF erstellt.
        </p>
        <p class="mt-2 text-sm leading-6 text-slate-600">
          Du kannst jetzt direkt in den Download-Schritt wechseln oder oben eine
          andere Rechnung auswählen, falls neue Daten dazukommen.
        </p>
        <Button
          variant="outline"
          class="mt-5 rounded-full border-[#d8dfd3] bg-white px-6"
          @click="onOpenDownload"
        >
          Weiter zum Download-Schritt
        </Button>
      </CardContent>
    </Card>
  </section>
</template>
