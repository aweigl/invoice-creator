<script setup lang="ts">
import { computed, reactive, ref } from 'vue'

type InvoiceItem = {
  description: string
  quantity: number
  unitPrice: number
}

const form = reactive({
  customerName: 'Acme GmbH',
  invoiceNumber: 'INV-2026-001',
  items: [
    {
      description: 'Design work',
      quantity: 8,
      unitPrice: 75
    }
  ] as InvoiceItem[]
})

const currency = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'EUR'
})

const apiMessage = ref('Backend not queried yet.')
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? ''

const total = computed(() =>
  form.items.reduce((sum, item) => sum + item.quantity * item.unitPrice, 0)
)

function addItem() {
  form.items.push({
    description: '',
    quantity: 1,
    unitPrice: 0
  })
}

async function previewInvoice() {
  try {
    const response = await fetch(`${apiBaseUrl}/api/invoices/preview`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(form)
    })

    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`)
    }

    const data = (await response.json()) as { summary: string }
    apiMessage.value = data.summary
  } catch (error) {
    apiMessage.value =
      error instanceof Error ? error.message : 'Unknown backend error'
  }
}
</script>

<template>
  <main class="page-shell">
    <section class="hero-card">
      <div>
        <p class="eyebrow">Invoice workflow</p>
        <h1>Build invoices fast with Vue and FastAPI.</h1>
        <p class="lede">
          This starter app lets you draft invoice data in the frontend and send
          it to a Python API for validation and preview generation.
        </p>
      </div>

      <div class="stat-block">
        <span>Total preview</span>
        <strong>{{ currency.format(total) }}</strong>
      </div>
    </section>

    <section class="content-grid">
      <form class="panel" @submit.prevent="previewInvoice">
        <h2>Invoice Form</h2>

        <label>
          <span>Customer name</span>
          <input v-model="form.customerName" type="text" />
        </label>

        <label>
          <span>Invoice number</span>
          <input v-model="form.invoiceNumber" type="text" />
        </label>

        <div class="items-header">
          <h3>Items</h3>
          <button class="secondary-button" type="button" @click="addItem">
            Add item
          </button>
        </div>

        <div
          v-for="(item, index) in form.items"
          :key="index"
          class="item-row"
        >
          <input v-model="item.description" type="text" placeholder="Description" />
          <input v-model.number="item.quantity" type="number" min="1" placeholder="Qty" />
          <input
            v-model.number="item.unitPrice"
            type="number"
            min="0"
            step="0.01"
            placeholder="Unit price"
          />
        </div>

        <button class="primary-button" type="submit">Generate preview</button>
      </form>

      <aside class="panel panel-accent">
        <h2>Backend Response</h2>
        <p>{{ apiMessage }}</p>

        <div class="summary-box">
          <span>Invoice total</span>
          <strong>{{ currency.format(total) }}</strong>
        </div>
      </aside>
    </section>
  </main>
</template>
