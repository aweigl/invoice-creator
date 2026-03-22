<script setup lang="ts">
import { computed, ref } from 'vue'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table'

type CsvValidationError = {
  row_number: number
  column: string | null
  message: string
}

type CsvSampleRow = {
  invoice_number: string
  invoice_date: string
  due_date: string
  customer_name: string
  customer_address: string
  dog_name: string
  billing_month: string
  subscription_plan: 'none' | '1x_week' | '2x_week' | '3x_week' | '4x_week'
  daily_count: number
  include_test_run: boolean
  currency: string
}

type CsvValidationResult = {
  filename: string
  total_rows: number
  valid_rows: number
  invalid_rows: number
  errors: CsvValidationError[]
  sample_row: CsvSampleRow | null
}

const MAX_CSV_BYTES = 2 * 1024 * 1024
const REQUIRED_COLUMNS = [
  'invoice_number',
  'invoice_date',
  'due_date',
  'customer_name',
  'customer_address',
  'dog_name',
  'billing_month',
  'subscription_plan',
  'daily_count',
  'include_test_run',
  'currency'
]

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? ''

const selectedFileName = ref('')
const csvContent = ref('')
const localHeaders = ref<string[]>([])
const localRowCount = ref(0)
const fileError = ref('')
const serverError = ref('')
const validationResult = ref<CsvValidationResult | null>(null)
const isUploading = ref(false)

const hasFileInMemory = computed(() => csvContent.value.length > 0)

function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`
  }

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`
  }

  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function parseCsvLine(line: string): string[] {
  const values: string[] = []
  let current = ''
  let inQuotes = false

  for (let index = 0; index < line.length; index += 1) {
    const character = line[index]
    const nextCharacter = line[index + 1]

    if (character === '"') {
      if (inQuotes && nextCharacter === '"') {
        current += '"'
        index += 1
      } else {
        inQuotes = !inQuotes
      }
      continue
    }

    if (character === ',' && !inQuotes) {
      values.push(current.trim())
      current = ''
      continue
    }

    current += character
  }

  values.push(current.trim())
  return values
}

function summarizeCsv(content: string) {
  const normalized = content.replace(/^\uFEFF/, '')
  const rows = normalized
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0)

  if (rows.length === 0) {
    return {
      headers: [],
      rowCount: 0
    }
  }

  return {
    headers: parseCsvLine(rows[0]),
    rowCount: Math.max(rows.length - 1, 0)
  }
}

async function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]

  fileError.value = ''
  serverError.value = ''
  validationResult.value = null
  selectedFileName.value = ''
  csvContent.value = ''
  localHeaders.value = []
  localRowCount.value = 0

  if (!file) {
    return
  }

  if (!file.name.toLowerCase().endsWith('.csv')) {
    fileError.value = 'Bitte waehle eine CSV-Datei aus.'
    input.value = ''
    return
  }

  if (file.size > MAX_CSV_BYTES) {
    fileError.value = `Die CSV-Datei ist zu gross. Bitte lade eine Datei unter ${formatBytes(MAX_CSV_BYTES)} hoch.`
    input.value = ''
    return
  }

  const content = await file.text()
  const summary = summarizeCsv(content)

  selectedFileName.value = file.name
  csvContent.value = content
  localHeaders.value = summary.headers
  localRowCount.value = summary.rowCount
}

async function validateCsv() {
  if (!hasFileInMemory.value || !selectedFileName.value) {
    fileError.value = 'Bitte waehle zuerst eine CSV-Datei aus.'
    return
  }

  isUploading.value = true
  serverError.value = ''
  validationResult.value = null

  try {
    const formData = new FormData()
    const file = new File([csvContent.value], selectedFileName.value, { type: 'text/csv' })
    formData.append('file', file)

    const response = await fetch(`${apiBaseUrl}/api/csv/validate`, {
      method: 'POST',
      body: formData
    })

    if (!response.ok) {
      const payload = (await response.json().catch(() => null)) as { detail?: string } | null
      throw new Error(payload?.detail ?? `Validierung fehlgeschlagen (${response.status})`)
    }

    validationResult.value = (await response.json()) as CsvValidationResult
  } catch (error) {
    serverError.value =
      error instanceof Error ? error.message : 'Unbekannter Serverfehler.'
  } finally {
    isUploading.value = false
  }
}
</script>

<template>
  <main class="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(255,214,153,0.28),transparent_28%),linear-gradient(135deg,#fffdf8_0%,#f6f8fb_52%,#eef6ef_100%)]">
    <div class="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 md:px-8 md:py-10">
      <section class="grid gap-4 lg:grid-cols-[1.5fr_0.8fr]">
        <Card class="border-white/60 bg-white/85 shadow-lg backdrop-blur">
          <CardHeader>
            <Badge variant="outline" class="mb-3 w-fit bg-white/80">
              CSV Upload
            </Badge>
            <CardTitle class="text-3xl tracking-tight md:text-5xl">
              Rechnungsdaten hochladen und vor dem Generieren pruefen.
            </CardTitle>
            <CardDescription class="max-w-2xl text-base text-slate-600">
              Diese Ansicht liest die CSV zuerst im Browser ein, prueft die Dateigroesse
              und schickt sie dann an FastAPI zur strukturierten Validierung.
            </CardDescription>
          </CardHeader>
        </Card>

        <Card class="border-amber-200/70 bg-slate-950 text-slate-50 shadow-lg">
          <CardHeader>
            <CardDescription class="text-slate-300">
              Aktuelle Grenze
            </CardDescription>
            <CardTitle class="text-4xl">
              {{ formatBytes(MAX_CSV_BYTES) }}
            </CardTitle>
          </CardHeader>
          <CardContent class="text-sm text-slate-300">
            Die Datei wird fuer das MVP im Speicher gehalten. Dateien ueber diesem
            Limit werden direkt vor dem Upload abgelehnt.
          </CardContent>
        </Card>
      </section>

      <section class="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <Card class="border-white/60 bg-white/88 shadow-lg backdrop-blur">
          <CardHeader>
            <CardTitle>CSV-Datei auswaehlen</CardTitle>
            <CardDescription>
              Erwartet wird das aktuelle Preismodell mit genau diesen Spalten.
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
              <AlertTitle>Validierung fehlgeschlagen</AlertTitle>
              <AlertDescription>{{ serverError }}</AlertDescription>
            </Alert>

            <div
              v-if="hasFileInMemory"
              class="grid gap-4 rounded-xl border border-slate-200 bg-slate-50 p-4 md:grid-cols-3"
            >
              <div>
                <p class="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                  Datei
                </p>
                <p class="mt-1 text-sm font-medium text-slate-900">
                  {{ selectedFileName }}
                </p>
              </div>
              <div>
                <p class="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                  Gefundene Datenzeilen
                </p>
                <p class="mt-1 text-sm font-medium text-slate-900">
                  {{ localRowCount }}
                </p>
              </div>
              <div>
                <p class="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                  Erkannte Spalten
                </p>
                <p class="mt-1 text-sm font-medium text-slate-900">
                  {{ localHeaders.length }}
                </p>
              </div>
            </div>

            <div class="flex flex-wrap gap-3">
              <Button :disabled="!hasFileInMemory || isUploading" @click="validateCsv">
                {{ isUploading ? 'CSV wird validiert...' : 'CSV validieren' }}
              </Button>
              <Button
                variant="outline"
                :disabled="!hasFileInMemory"
                @click="validationResult = null"
              >
                Ergebnis ausblenden
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card class="border-white/60 bg-white/88 shadow-lg backdrop-blur">
          <CardHeader>
            <CardTitle>Lokale Schnellansicht</CardTitle>
            <CardDescription>
              Diese Werte werden direkt aus der Datei im Browser gelesen, noch bevor der
              Server die eigentliche Validierung uebernimmt.
            </CardDescription>
          </CardHeader>
          <CardContent class="space-y-4">
            <div v-if="!hasFileInMemory" class="rounded-xl border border-dashed border-slate-300 p-6 text-sm text-slate-500">
              Noch keine CSV geladen.
            </div>

            <template v-else>
              <div>
                <p class="mb-2 text-sm font-semibold text-slate-900">Spaltenkopf</p>
                <div class="flex flex-wrap gap-2">
                  <Badge
                    v-for="header in localHeaders"
                    :key="header"
                    variant="outline"
                  >
                    {{ header }}
                  </Badge>
                </div>
              </div>

              <div class="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                Die Datei wird im Speicher gehalten, damit wir die Groesse sofort pruefen
                und den Upload nur bei sinnvollen CSV-Dateien starten.
              </div>
            </template>
          </CardContent>
        </Card>
      </section>

      <section v-if="validationResult" class="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <Card class="border-white/60 bg-white/88 shadow-lg backdrop-blur">
          <CardHeader>
            <CardTitle>Validierungsergebnis</CardTitle>
            <CardDescription>
              Rueckmeldung vom FastAPI-Endpunkt fuer {{ validationResult.filename }}
            </CardDescription>
          </CardHeader>
          <CardContent class="space-y-4">
            <div class="grid gap-4 md:grid-cols-3">
              <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <p class="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                  Gesamtzeilen
                </p>
                <p class="mt-2 text-2xl font-semibold text-slate-900">
                  {{ validationResult.total_rows }}
                </p>
              </div>
              <div class="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
                <p class="text-xs font-semibold uppercase tracking-[0.16em] text-emerald-700">
                  Gueltig
                </p>
                <p class="mt-2 text-2xl font-semibold text-emerald-900">
                  {{ validationResult.valid_rows }}
                </p>
              </div>
              <div class="rounded-xl border border-rose-200 bg-rose-50 p-4">
                <p class="text-xs font-semibold uppercase tracking-[0.16em] text-rose-700">
                  Ungueltig
                </p>
                <p class="mt-2 text-2xl font-semibold text-rose-900">
                  {{ validationResult.invalid_rows }}
                </p>
              </div>
            </div>

            <Alert
              :variant="validationResult.invalid_rows > 0 ? 'destructive' : 'default'"
              :class="validationResult.invalid_rows === 0 ? 'border-emerald-200 bg-emerald-50 text-emerald-950' : ''"
            >
              <AlertTitle>
                {{ validationResult.invalid_rows === 0 ? 'CSV ist valide' : 'CSV enthaelt Fehler' }}
              </AlertTitle>
              <AlertDescription>
                {{
                  validationResult.invalid_rows === 0
                    ? 'Die Datei passt zum aktuellen Preismodell und kann als naechstes fuer Rechnungen verwendet werden.'
                    : 'Bitte korrigiere die markierten Zeilen oder Spalten, bevor wir Rechnungen erzeugen.'
                }}
              </AlertDescription>
            </Alert>

            <div v-if="validationResult.sample_row" class="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p class="mb-3 text-sm font-semibold text-slate-900">Erste gueltige Beispielzeile</p>
              <div class="grid gap-3 text-sm md:grid-cols-2">
                <div><span class="font-medium">Rechnungsnummer:</span> {{ validationResult.sample_row.invoice_number }}</div>
                <div><span class="font-medium">Hund:</span> {{ validationResult.sample_row.dog_name }}</div>
                <div><span class="font-medium">Abo:</span> {{ validationResult.sample_row.subscription_plan }}</div>
                <div><span class="font-medium">Tagesbetreuung:</span> {{ validationResult.sample_row.daily_count }}</div>
                <div><span class="font-medium">Probetag:</span> {{ validationResult.sample_row.include_test_run ? 'Ja' : 'Nein' }}</div>
                <div><span class="font-medium">Monat:</span> {{ validationResult.sample_row.billing_month }}</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card class="border-white/60 bg-white/88 shadow-lg backdrop-blur">
          <CardHeader>
            <CardTitle>Fehlerliste</CardTitle>
            <CardDescription>
              Zeilenbezogene Fehler aus der Backend-Validierung.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div class="overflow-hidden rounded-xl border border-slate-200">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead class="w-28">Zeile</TableHead>
                    <TableHead class="w-40">Spalte</TableHead>
                    <TableHead>Fehlermeldung</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow v-if="validationResult.errors.length === 0">
                    <TableCell colspan="3" class="py-8 text-center text-slate-500">
                      Keine Fehler gefunden.
                    </TableCell>
                  </TableRow>
                  <TableRow
                    v-for="error in validationResult.errors"
                    :key="`${error.row_number}-${error.column}-${error.message}`"
                  >
                    <TableCell>{{ error.row_number }}</TableCell>
                    <TableCell>{{ error.column ?? 'Allgemein' }}</TableCell>
                    <TableCell>{{ error.message }}</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  </main>
</template>
