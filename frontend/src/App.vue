<script setup lang="ts">
import { computed, reactive, ref } from 'vue'

type SubscriptionPlan = 'none' | '1x_week' | '2x_week' | '3x_week' | '4x_week'

type InvoiceDraft = {
  invoiceNumber: string
  invoiceDate: string
  dueDate: string
  customerName: string
  customerAddress: string
  dogName: string
  billingMonth: string
  subscriptionPlan: SubscriptionPlan
  dailyCount: number
  includeTestRun: boolean
  currency: string
}

type InvoiceLineItem = {
  label: string
  details: string
  amount: number
}

const PRICING = {
  testRun: 20,
  daily: 35,
  subscription: {
    none: 0,
    '1x_week': 120,
    '2x_week': 190,
    '3x_week': 290,
    '4x_week': 390
  }
} as const

const exampleInvoices: InvoiceDraft[] = [
  {
    invoiceNumber: 'INV-2026-03-001',
    invoiceDate: '2026-03-31',
    dueDate: '2026-04-07',
    customerName: 'Anna Becker',
    customerAddress: 'Musterweg 12, 50823 Koeln',
    dogName: 'Balu',
    billingMonth: '2026-03',
    subscriptionPlan: '1x_week',
    dailyCount: 0,
    includeTestRun: false,
    currency: 'EUR'
  },
  {
    invoiceNumber: 'INV-2026-03-002',
    invoiceDate: '2026-03-31',
    dueDate: '2026-04-07',
    customerName: 'Jonas Klein',
    customerAddress: 'Lindenstrasse 8, 50667 Koeln',
    dogName: 'Mila',
    billingMonth: '2026-03',
    subscriptionPlan: '2x_week',
    dailyCount: 2,
    includeTestRun: false,
    currency: 'EUR'
  },
  {
    invoiceNumber: 'INV-2026-03-003',
    invoiceDate: '2026-03-31',
    dueDate: '2026-04-07',
    customerName: 'Sarah Neumann',
    customerAddress: 'Aachener Strasse 101, 50931 Koeln',
    dogName: 'Lotte',
    billingMonth: '2026-03',
    subscriptionPlan: 'none',
    dailyCount: 3,
    includeTestRun: false,
    currency: 'EUR'
  },
  {
    invoiceNumber: 'INV-2026-03-004',
    invoiceDate: '2026-03-31',
    dueDate: '2026-04-07',
    customerName: 'David Schmitz',
    customerAddress: 'Venloer Strasse 42, 50825 Koeln',
    dogName: 'Bruno',
    billingMonth: '2026-03',
    subscriptionPlan: 'none',
    dailyCount: 0,
    includeTestRun: true,
    currency: 'EUR'
  },
  {
    invoiceNumber: 'INV-2026-03-005',
    invoiceDate: '2026-03-31',
    dueDate: '2026-04-07',
    customerName: 'Lea Hoffmann',
    customerAddress: 'Subbelrather Strasse 77, 50823 Koeln',
    dogName: 'Nala',
    billingMonth: '2026-03',
    subscriptionPlan: '4x_week',
    dailyCount: 1,
    includeTestRun: true,
    currency: 'EUR'
  }
]

const form = reactive<InvoiceDraft>({ ...exampleInvoices[1] })
const activeExample = ref(exampleInvoices[1].invoiceNumber)

const currencyFormatter = computed(
  () =>
    new Intl.NumberFormat('de-DE', {
      style: 'currency',
      currency: form.currency
    })
)

const planLabel = computed(() => {
  const labels: Record<SubscriptionPlan, string> = {
    none: 'Kein Abo',
    '1x_week': 'Abo 1x pro Woche',
    '2x_week': 'Abo 2x pro Woche',
    '3x_week': 'Abo 3x pro Woche',
    '4x_week': 'Abo 4x pro Woche'
  }

  return labels[form.subscriptionPlan]
})

const lineItems = computed<InvoiceLineItem[]>(() => {
  const items: InvoiceLineItem[] = []
  const subscriptionAmount = PRICING.subscription[form.subscriptionPlan]

  if (subscriptionAmount > 0) {
    items.push({
      label: planLabel.value,
      details: `Abrechnungsmonat ${form.billingMonth}`,
      amount: subscriptionAmount
    })
  }

  if (form.dailyCount > 0) {
    items.push({
      label: 'Tagesbetreuung',
      details: `${form.dailyCount} Tag(e) x ${currencyFormatter.value.format(PRICING.daily)}`,
      amount: form.dailyCount * PRICING.daily
    })
  }

  if (form.includeTestRun) {
    items.push({
      label: 'Probetag',
      details: 'Einmaliger Kennenlerntermin',
      amount: PRICING.testRun
    })
  }

  return items
})

const total = computed(() =>
  lineItems.value.reduce((sum, item) => sum + item.amount, 0)
)

const invoiceSummary = computed(() => {
  if (lineItems.value.length === 0) {
    return 'Diese Rechnung enthält noch keine abrechenbaren Leistungspositionen.'
  }

  return `Für ${form.customerName} werden ${lineItems.value.length} Leistungsposition(en) für ${form.dogName} im Monat ${form.billingMonth} abgerechnet.`
})

function loadExample(invoiceNumber: string) {
  const match = exampleInvoices.find((entry) => entry.invoiceNumber === invoiceNumber)

  if (!match) {
    return
  }

  Object.assign(form, match)
  activeExample.value = invoiceNumber
}
</script>

<template>
  <main class="page-shell">
    <section class="hero-card">
      <div>
        <p class="eyebrow">Rechnungsworkflow</p>
        <h1>Feste Preise für die Hundebetreuung zuerst sauber modellieren.</h1>
        <p class="lede">
          Diese Testansicht bildet das Beispiel-CSV nach und erweitert eine
          einzelne Rechnungszeile zu den Leistungspositionen, die später vom
          Backend erzeugt werden.
        </p>
      </div>

      <div class="stat-block">
        <span>Rechnungsbetrag</span>
        <strong>{{ currencyFormatter.format(total) }}</strong>
      </div>
    </section>

    <section class="content-grid">
      <form class="panel" @submit.prevent>
        <div class="section-heading">
          <div>
            <h2>Test-Rechnung</h2>
            <p>Starte mit einer Beispielzeile und passe die Preisbausteine an.</p>
          </div>

          <label class="compact-field">
            <span>Beispiel laden</span>
            <select :value="activeExample" @change="loadExample(($event.target as HTMLSelectElement).value)">
              <option
                v-for="invoice in exampleInvoices"
                :key="invoice.invoiceNumber"
                :value="invoice.invoiceNumber"
              >
                {{ invoice.invoiceNumber }} · {{ invoice.customerName }}
              </option>
            </select>
          </label>
        </div>

        <div class="field-grid">
          <label>
            <span>Rechnungsnummer</span>
            <input v-model="form.invoiceNumber" type="text" />
          </label>

          <label>
            <span>Abrechnungsmonat</span>
            <input v-model="form.billingMonth" type="month" />
          </label>

          <label>
            <span>Rechnungsdatum</span>
            <input v-model="form.invoiceDate" type="date" />
          </label>

          <label>
            <span>Fälligkeitsdatum</span>
            <input v-model="form.dueDate" type="date" />
          </label>
        </div>

        <div class="field-grid">
          <label>
            <span>Kundenname</span>
            <input v-model="form.customerName" type="text" />
          </label>

          <label>
            <span>Name des Hundes</span>
            <input v-model="form.dogName" type="text" />
          </label>
        </div>

        <label>
          <span>Kundenadresse</span>
          <textarea v-model="form.customerAddress" rows="3" />
        </label>

        <div class="pricing-panel">
          <div class="section-heading">
            <div>
              <h3>Preisbausteine</h3>
              <p>Diese Eingaben entsprechen exakt dem festen Preismodell.</p>
            </div>
          </div>

          <div class="field-grid">
            <label>
              <span>Abo-Modell</span>
              <select v-model="form.subscriptionPlan">
                <option value="none">Kein Abo</option>
                <option value="1x_week">1x pro Woche</option>
                <option value="2x_week">2x pro Woche</option>
                <option value="3x_week">3x pro Woche</option>
                <option value="4x_week">4x pro Woche</option>
              </select>
            </label>

            <label>
              <span>Zusätzliche Tagesbetreuung</span>
              <input v-model.number="form.dailyCount" type="number" min="0" />
            </label>

            <label>
              <span>Währung</span>
              <input v-model="form.currency" type="text" maxlength="3" />
            </label>
          </div>

          <label class="checkbox-row">
            <input v-model="form.includeTestRun" type="checkbox" />
            <span>Einmaligen Probetag hinzurechnen (20 €)</span>
          </label>
        </div>
      </form>

      <aside class="panel panel-accent">
        <h2>Rechnungsvorschau</h2>
        <p>{{ invoiceSummary }}</p>

        <div class="summary-box">
          <span>Gesamtbetrag</span>
          <strong>{{ currencyFormatter.format(total) }}</strong>
        </div>

        <div class="invoice-meta">
          <div>
            <span class="meta-label">Kunde</span>
            <strong>{{ form.customerName }}</strong>
            <p>{{ form.customerAddress }}</p>
          </div>

          <div>
            <span class="meta-label">Hund</span>
            <strong>{{ form.dogName }}</strong>
            <p>{{ form.invoiceNumber }} · fällig am {{ form.dueDate }}</p>
          </div>
        </div>

        <div class="line-items">
          <div class="line-items-header">
            <h3>Erzeugte Positionen</h3>
            <span>{{ lineItems.length }} Position(en)</span>
          </div>

          <p v-if="lineItems.length === 0" class="empty-state">
            Füge ein Abo, Tagesbetreuung oder einen Probetag hinzu, um Positionen zu erzeugen.
          </p>

          <div
            v-for="item in lineItems"
            :key="`${item.label}-${item.details}`"
            class="line-item-card"
          >
            <div>
              <strong>{{ item.label }}</strong>
              <p>{{ item.details }}</p>
            </div>
            <span>{{ currencyFormatter.format(item.amount) }}</span>
          </div>
        </div>
      </aside>
    </section>
  </main>
</template>
