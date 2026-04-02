<script setup lang="ts">
import { CheckCircle2, FileUp, ShieldCheck, Sparkles } from "lucide-vue-next";

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

defineProps<{
  sampleCsvDownloadPath: string;
  requiredColumns: readonly string[];
  hasRows: boolean;
  selectedFileName: string;
  localRowCount: number;
  localHeadersCount: number;
  validationMessage: string;
  isValidating: boolean;
  fileError: string;
  serverError: string;
  onFileChange: (event: Event) => void | Promise<void>;
  onContinue: () => void;
}>();
</script>

<template>
  <section class="grid gap-6 xl:grid-cols-[1.08fr_0.92fr]">
    <Card
      class="border-white/70 bg-white/92 shadow-[0_30px_80px_rgba(69,73,58,0.12)]"
    >
      <CardHeader class="space-y-4">
        <Badge
          variant="secondary"
          class="w-fit rounded-full bg-[#eef2e8] px-3 py-1 text-[#4d6145]"
        >
          Schritt 1
        </Badge>
        <div class="space-y-3">
          <CardTitle class="max-w-2xl text-2xl leading-tight">
            Lade einfach deine CSV hoch. Den ersten Check übernimmt die App.
          </CardTitle>
        </div>
      </CardHeader>

      <CardContent class="space-y-6">
        <div
          class="rounded-[1.75rem] border border-dashed border-[#d8cfbf] bg-[#fbf6ef] p-5 md:p-7"
        >
          <div class="flex items-start gap-4">
            <div class="rounded-2xl bg-white p-3 text-[#5d7253] shadow-sm">
              <FileUp class="size-6" />
            </div>
            <div class="flex-1 space-y-4">
              <div>
                <p class="text-lg font-semibold text-slate-950">
                  CSV-Datei waehlen
                </p>
                <p class="mt-1 text-sm leading-6 text-slate-600">
                  Bitte eine `.csv` Datei mit den bekannten Rechnungsdaten
                  verwenden.
                </p>
              </div>

              <input
                accept=".csv,text/csv"
                class="block w-full rounded-2xl border border-[#ddd4c6] bg-white px-4 py-4 text-sm text-slate-700 shadow-sm file:mr-4 file:rounded-xl file:border-0 file:bg-[#5d7253] file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-[#4f6348]"
                type="file"
                @change="onFileChange"
              />

              <div class="flex flex-wrap gap-3">
                <Button
                  as="a"
                  :href="sampleCsvDownloadPath"
                  download="invoice-pricing-example.csv"
                  variant="outline"
                  class="rounded-full border-[#d8e2d3] bg-white px-5"
                >
                  Beispiel-CSV herunterladen
                </Button>
                <span class="self-center text-sm text-slate-500">
                  Gut zum Vergleichen oder als Vorlage.
                </span>
              </div>
            </div>
          </div>
        </div>

        <Alert
          v-if="hasRows && !fileError && !serverError"
          class="border-[#dbe4d4] bg-[#f7fbf4] text-slate-900"
        >
          <CheckCircle2 class="mt-0.5 size-4 text-[#5d7253]" />
          <AlertTitle>Upload abgeschlossen</AlertTitle>
          <AlertDescription class="leading-6 text-slate-600">
            {{ validationMessage }}
          </AlertDescription>
        </Alert>

        <Alert v-if="fileError" variant="destructive">
          <AlertTitle>Datei konnte nicht verwendet werden</AlertTitle>
          <AlertDescription>{{ fileError }}</AlertDescription>
        </Alert>

        <Alert v-if="serverError" variant="destructive">
          <AlertTitle>Pruefung fehlgeschlagen</AlertTitle>
          <AlertDescription>{{ serverError }}</AlertDescription>
        </Alert>

        <div class="flex flex-wrap items-center justify-between gap-4">
          <div class="flex items-center gap-3 text-sm text-slate-500">
            <Sparkles class="size-4 text-[#8a6e54]" />
            <span>
              {{
                isValidating
                  ? "Datei wird gerade geprueft..."
                  : "Nach dem Upload geht es direkt weiter zur Pruefung."
              }}
            </span>
          </div>
          <Button
            :disabled="!hasRows || isValidating"
            class="rounded-full bg-[#5d7253] px-6 hover:bg-[#4f6348]"
            size="lg"
            @click="onContinue"
          >
            Zur Rechnungspruefung
          </Button>
        </div>
      </CardContent>
    </Card>

    <Card
      class="border-white/70 bg-white/78 shadow-[0_20px_60px_rgba(69,73,58,0.08)]"
    >
      <CardHeader class="space-y-4">
        <div class="rounded-2xl bg-[#f1e4d4] p-3 text-[#7c634b]">
          <ShieldCheck class="size-6" />
        </div>
        <div>
          <CardTitle class="text-2xl">So bleibt es unkompliziert</CardTitle>
          <CardDescription class="mt-2 text-sm leading-6 text-slate-600">
            Die App ist jetzt auf den einfachen Standardfall ausgelegt. Erst
            hochladen, dann kurz pruefen, dann gesammelt herunterladen.
          </CardDescription>
        </div>
      </CardHeader>
      <CardContent class="space-y-4">
        <div class="rounded-2xl bg-[#fbf8f2] p-4">
          <p class="text-sm font-semibold text-slate-900">
            1. Datei vorbereiten
          </p>
          <p class="mt-1 text-sm leading-6 text-slate-600">
            Nutze die bestehende CSV oder die Beispiel-Datei als Vorlage.
          </p>
        </div>
        <div class="rounded-2xl bg-[#f6faf5] p-4">
          <p class="text-sm font-semibold text-slate-900">
            2. Hinweise korrigieren
          </p>
          <p class="mt-1 text-sm leading-6 text-slate-600">
            Nur die aktuelle Rechnung anschauen und eventuelle Fehler direkt
            daneben beheben.
          </p>
        </div>
        <div class="rounded-2xl bg-[#f5f8fb] p-4">
          <p class="text-sm font-semibold text-slate-900">
            3. Alles zusammen herunterladen
          </p>
          <p class="mt-1 text-sm leading-6 text-slate-600">
            Wenn alles gruen ist, gibt es die PDF-Rechnungen gesammelt als ZIP.
          </p>
        </div>
      </CardContent>
    </Card>
  </section>
</template>
