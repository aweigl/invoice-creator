<script setup lang="ts">
import { Archive, CheckCircle2, Download, Eye, FileWarning, RefreshCcw } from "lucide-vue-next";

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
import type { CsvValidationResult } from "@/lib/invoice-workflow";

defineProps<{
  rowsLength: number;
  generatedRowCount: number;
  validationResult: CsvValidationResult | null;
  validationIsCurrent: boolean;
  canGenerate: boolean;
  isGenerating: boolean;
  isPreviewLoading: boolean;
  serverError: string;
  selectedRowLabel: string;
  canPreviewSelected: boolean;
  canGenerateSelected: boolean;
  onGenerateAll: () => void;
  onPreviewSelected: () => void;
  onGenerateSelected: () => void;
  onGoReview: () => void;
}>();
</script>

<template>
  <section class="grid gap-6 xl:grid-cols-[1.04fr_0.96fr]">
    <Card class="border-white/70 bg-white/92 shadow-[0_30px_80px_rgba(69,73,58,0.12)]">
      <CardHeader class="space-y-4">
        <Badge
          variant="secondary"
          class="w-fit rounded-full bg-[#eef2e8] px-3 py-1 text-[#4d6145]"
        >
          Schritt 3
        </Badge>
        <div>
          <CardTitle class="text-3xl leading-tight md:text-4xl">
            PDFs gesammelt herunterladen.
          </CardTitle>
          <CardDescription class="mt-2 max-w-2xl text-base leading-7 text-slate-600">
            Hier siehst du auf einen Blick, ob alles bereit ist. Wenn ja, holst
            du dir die komplette ZIP-Datei mit einem Klick.
          </CardDescription>
        </div>
      </CardHeader>

      <CardContent class="space-y-6">
        <div class="grid gap-4 md:grid-cols-3">
          <div class="rounded-2xl bg-[#f5ede1] p-4">
            <p class="text-xs font-semibold uppercase tracking-[0.18em] text-[#7a654f]">
              Rechnungen
            </p>
            <p class="mt-2 text-2xl font-semibold text-slate-950">
              {{ rowsLength }}
            </p>
          </div>
          <div class="rounded-2xl bg-[#eef2e8] p-4">
            <p class="text-xs font-semibold uppercase tracking-[0.18em] text-[#5b6c54]">
              Gueltig
            </p>
            <p class="mt-2 text-2xl font-semibold text-slate-950">
              {{ validationResult?.valid_rows ?? 0 }}
            </p>
          </div>
          <div class="rounded-2xl bg-[#f7f1e7] p-4">
            <p class="text-xs font-semibold uppercase tracking-[0.18em] text-[#7c634b]">
              Bereits als PDF
            </p>
            <p class="mt-2 text-2xl font-semibold text-slate-950">
              {{ generatedRowCount }}
            </p>
          </div>
        </div>

        <Alert
          :variant="
            validationResult && validationIsCurrent && validationResult.invalid_rows > 0
              ? 'destructive'
              : 'default'
          "
          :class="
            canGenerate
              ? 'border-[#dbe4d4] bg-[#f7fbf4] text-slate-900'
              : 'border-[#f1e4c9] bg-[#fffaf1] text-slate-900'
          "
        >
          <component :is="canGenerate ? CheckCircle2 : FileWarning" class="mt-0.5 size-4" />
          <AlertTitle>
            {{
              canGenerate
                ? "Alles bereit fuer den Download."
                : !validationResult
                  ? "Bitte erst die Rechnungen pruefen."
                  : !validationIsCurrent
                    ? "Die letzte Aenderung wurde noch nicht geprueft."
                    : `${validationResult.invalid_rows} Rechnung(en) brauchen noch Aufmerksamkeit.`
            }}
          </AlertTitle>
          <AlertDescription class="leading-6">
            {{
              canGenerate
                ? "Die ZIP-Datei enthaelt alle aktuell gueltigen Rechnungs-PDFs."
                : "Wenn noch etwas fehlt, geh kurz in Schritt 2 zurueck und pruefe die markierten Stellen."
            }}
          </AlertDescription>
        </Alert>

        <Alert v-if="serverError" variant="destructive">
          <AlertTitle>Download fehlgeschlagen</AlertTitle>
          <AlertDescription>{{ serverError }}</AlertDescription>
        </Alert>

        <div class="flex flex-wrap items-center justify-between gap-4">
          <Button
            :disabled="!canGenerate"
            class="rounded-full bg-[#5d7253] px-7 hover:bg-[#4f6348]"
            size="lg"
            @click="onGenerateAll"
          >
            <Archive class="size-4" />
            {{ isGenerating ? "ZIP wird erstellt..." : "Alle PDFs als ZIP herunterladen" }}
          </Button>

          <Button
            variant="outline"
            class="rounded-full border-[#d8dfd3] bg-white px-5"
            @click="onGoReview"
          >
            <RefreshCcw class="size-4" />
            Zurueck zur Pruefung
          </Button>
        </div>
      </CardContent>
    </Card>

    <Card class="border-white/70 bg-white/86 shadow-[0_24px_60px_rgba(69,73,58,0.08)]">
      <CardHeader class="space-y-3">
        <div class="rounded-2xl bg-[#f1e7da] p-3 text-[#745e49]">
          <Download class="size-6" />
        </div>
        <div>
          <CardTitle class="text-2xl">Optional: aktuelle Rechnung einzeln</CardTitle>
          <CardDescription class="mt-2 text-sm leading-6 text-slate-600">
            Falls du vor dem Sammeldownload noch die gerade geoeffnete Rechnung
            anschauen oder einzeln speichern willst.
          </CardDescription>
        </div>
      </CardHeader>
      <CardContent class="space-y-4">
        <div class="rounded-2xl bg-[#f7f2ea] p-4">
          <p class="text-xs font-semibold uppercase tracking-[0.18em] text-[#7a654f]">
            Aktuelle Rechnung
          </p>
          <p class="mt-2 text-base font-semibold text-slate-950">
            {{ selectedRowLabel }}
          </p>
        </div>

        <div class="space-y-3">
          <Button
            variant="secondary"
            class="w-full rounded-full bg-[#f1e7da] px-5 text-[#6c5642] hover:bg-[#eadcc8]"
            :disabled="!canPreviewSelected || isPreviewLoading"
            @click="onPreviewSelected"
          >
            <Eye class="size-4" />
            {{ isPreviewLoading ? "Vorschau wird geladen..." : "PDF-Vorschau oeffnen" }}
          </Button>

          <Button
            variant="outline"
            class="w-full rounded-full border-[#d8dfd3] bg-white px-5"
            :disabled="!canGenerateSelected || isGenerating"
            @click="onGenerateSelected"
          >
            <Download class="size-4" />
            {{ isGenerating ? "PDF wird erstellt..." : "Nur diese Rechnung als PDF" }}
          </Button>
        </div>

        <p class="text-sm leading-6 text-slate-500">
          Diese Aktionen bleiben bewusst optional. Der Hauptweg ist der
          Sammeldownload links.
        </p>
      </CardContent>
    </Card>
  </section>
</template>
