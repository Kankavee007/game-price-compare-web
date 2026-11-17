<script setup lang="ts">
// setPriceAlert, ApiError (utils/) are auto-imported by Nuxt
import type { Currency } from '~/types'

const props = defineProps<{
  gameId: string
  currency: Currency
  /** Today's cheapest price in `currency` */
  currentPrice: number
}>()

const open = ref(false)
const email = ref('')
const priceText = ref<string | number>('')
const sending = ref(false)
const done = ref<string | null>(null) // success message
const serverError = ref<string | null>(null)
const submitted = ref(false) // show field errors only after the first submit

// Same simple check as the backend; the real check is CheapShark delivering the email
const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/

const price = computed(() => {
  // v-model on type="number" stores a number once the user types (Vue casts it), '' when empty
  const raw = String(priceText.value).trim()
  const n = Number(raw)
  return raw !== '' && Number.isFinite(n) ? n : null
})
const emailError = computed(() =>
  EMAIL_RE.test(email.value.trim()) ? null : 'Enter a valid email address',
)
const priceError = computed(() =>
  price.value !== null && price.value > 0 ? null : 'Enter a target price above 0',
)
const aboveCurrent = computed(() => price.value !== null && price.value >= props.currentPrice)

// Prefill a bit (10%) under today's price, so the alert means "cheaper than now"
function prefill() {
  priceText.value = (Math.floor(props.currentPrice * 0.9 * 100) / 100).toFixed(2)
}

function start() {
  open.value = true
  done.value = null
  serverError.value = null
  submitted.value = false
  prefill()
}

// Another currency: the old number means something else now
watch(
  () => props.currency,
  () => {
    if (open.value) prefill()
    done.value = null
  },
)

let controller: AbortController | undefined
onBeforeUnmount(() => controller?.abort())

async function submit() {
  submitted.value = true
  serverError.value = null
  if (emailError.value || priceError.value || price.value === null) return // nothing sent

  controller?.abort()
  controller = new AbortController()
  sending.value = true
  const target = price.value
  const currency = props.currency
  try {
    await setPriceAlert(
      { email: email.value.trim(), gameID: props.gameId, price: target, currency },
      controller.signal,
    )
    done.value = `Alert set. CheapShark will email you when the price drops below ${target.toFixed(2)} ${currency}.`
    open.value = false
  } catch (err) {
    if (controller.signal.aborted) return
    // Keep what the user typed so they can retry
    serverError.value =
      err instanceof Error ? err.message : 'Could not create alert, try again later'
  }
  sending.value = false
}

const ids = { email: useId(), price: useId(), note: useId() }
</script>

<template>
  <section aria-label="Price alert" class="space-y-3">
    <p v-if="done" class="text-success" role="status">
      🔔 {{ done }}
      <NuxtLink to="/alerts" class="text-accent hover:underline">Manage your alerts</NuxtLink>
    </p>

    <button
      v-if="!open"
      type="button"
      class="px-4 py-2 rounded-lg border border-accent text-accent-2 hover:bg-accent/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
      @click="start"
    >
      🔔 {{ done ? 'Set another alert' : 'Alert me when cheaper' }}
    </button>

    <form
      v-else
      class="panel space-y-3 p-4"
      novalidate
      :aria-describedby="ids.note"
      @submit.prevent="submit"
    >
      <div class="flex flex-wrap items-start gap-4">
        <div class="flex flex-col gap-1 flex-1 min-w-48">
          <label :for="ids.email" class="text-sm text-muted">Email</label>
          <input
            :id="ids.email"
            v-model="email"
            type="email"
            autocomplete="email"
            placeholder="you@example.com"
            class="field p-2"
            :aria-invalid="submitted && !!emailError"
            :aria-describedby="submitted && emailError ? `${ids.email}-error` : undefined"
          />
          <p v-if="submitted && emailError" :id="`${ids.email}-error`" class="text-sm text-danger">
            {{ emailError }}
          </p>
        </div>

        <div class="flex flex-col gap-1">
          <label :for="ids.price" class="text-sm text-muted">Alert below ({{ currency }})</label>
          <input
            :id="ids.price"
            v-model="priceText"
            type="number"
            inputmode="decimal"
            min="0"
            step="any"
            class="field w-32 p-2"
            :aria-invalid="submitted && !!priceError"
            :aria-describedby="submitted && priceError ? `${ids.price}-error` : undefined"
          />
          <p v-if="submitted && priceError" :id="`${ids.price}-error`" class="text-sm text-danger">
            {{ priceError }}
          </p>
        </div>
      </div>

      <p v-if="aboveCurrent" class="text-sm text-warn">
        This is not below today's price ({{ currentPrice.toFixed(2) }} {{ currency }}), so the alert
        may be sent right away.
      </p>

      <p :id="ids.note" class="text-xs text-muted">
        Your email is sent to CheapShark, which sends the alert and lets you manage or stop it. We
        do not store it.
        <NuxtLink to="/alerts" class="text-accent hover:underline">Manage your alerts</NuxtLink>.
        <template v-if="currency !== 'USD'">
          CheapShark checks prices in USD, so your target is converted at today's exchange rate.
        </template>
      </p>

      <div class="flex flex-wrap items-center gap-3">
        <button type="submit" :disabled="sending" class="btn-primary">
          {{ sending ? 'Setting alert…' : 'Set alert' }}
        </button>
        <button
          type="button"
          class="btn-ghost border-transparent bg-transparent"
          @click="open = false"
        >
          Cancel
        </button>
      </div>

      <p v-if="serverError" class="text-danger" role="alert">⚠️ {{ serverError }}</p>
    </form>
  </section>
</template>
