<script setup lang="ts">
// manageAlerts (utils/) is auto-imported by Nuxt
import type { ManageAlertsResult } from '~/types'

// Same simple check as the backend; the real check is CheapShark delivering the email
const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/

const email = ref('')
const submitted = ref(false) // show the field error only after the first submit
const sending = ref(false)
const result = ref<ManageAlertsResult['status'] | null>(null) // what CheapShark did
const serverError = ref<string | null>(null)

const emailError = computed(() =>
  EMAIL_RE.test(email.value.trim()) ? null : 'Enter a valid email address',
)

let controller: AbortController | undefined
onBeforeUnmount(() => controller?.abort())

async function submit() {
  submitted.value = true
  serverError.value = null
  if (emailError.value) return // nothing sent

  controller?.abort()
  controller = new AbortController()
  sending.value = true
  try {
    result.value = (await manageAlerts(email.value.trim(), controller.signal)).status
  } catch (err) {
    if (controller.signal.aborted) return
    // Keep the email so the user can retry
    serverError.value = err instanceof Error ? err.message : 'Could not send the email, try again later'
  }
  sending.value = false
}

function again() {
  result.value = null
  submitted.value = false
}

useHead({ title: 'Manage price alerts' })
</script>

<template>
  <div class="max-w-xl mx-auto space-y-6">
    <h1 class="text-3xl font-bold">🔔 Manage price alerts</h1>
    <p class="text-gray-300">
      Price alerts are kept by CheapShark, not by this site. Enter the email you used and
      CheapShark will email you a link where you can see, change or delete your alerts.
    </p>

    <div
      v-if="result"
      class="space-y-3 p-4 rounded-xl border"
      :class="
        result === 'sent' ? 'border-green-600/60 bg-green-500/5' : 'border-amber-500/50 bg-amber-500/5'
      "
      role="status"
    >
      <template v-if="result === 'sent'">
        <p class="text-green-400">
          Check your inbox: CheapShark has sent a link to manage your alerts.
        </p>
        <p class="text-sm text-gray-400">No email after a few minutes? Check your spam folder.</p>
      </template>

      <template v-else-if="result === 'alreadySent'">
        <p class="text-amber-300">
          CheapShark already sent a link to this email recently, so it did not send another one.
        </p>
        <p class="text-sm text-gray-400">
          Use the link in that email (check your spam folder too), or ask again later.
        </p>
      </template>

      <template v-else>
        <p class="text-amber-300">There are no price alerts for this email.</p>
        <p class="text-sm text-gray-400">
          Check the address for typos, or set an alert with 🔔 "Alert me when cheaper" on any game
          page.
        </p>
      </template>

      <button
        type="button"
        class="text-blue-400 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
        @click="again"
      >
        {{ result === 'noAlerts' ? 'Try another email' : 'Use another email' }}
      </button>
    </div>

    <form
      v-else
      class="space-y-3 p-4 rounded-xl bg-gray-800 border border-gray-700"
      novalidate
      aria-describedby="manage-note"
      @submit.prevent="submit"
    >
      <div class="flex flex-col gap-1">
        <label for="manage-email" class="text-sm text-gray-400">Email</label>
        <input
          id="manage-email"
          v-model="email"
          type="email"
          autocomplete="email"
          placeholder="you@example.com"
          class="p-2 rounded-lg bg-gray-900 border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          :aria-invalid="submitted && !!emailError"
          :aria-describedby="submitted && emailError ? 'manage-email-error' : undefined"
        />
        <p v-if="submitted && emailError" id="manage-email-error" class="text-sm text-red-400">
          {{ emailError }}
        </p>
      </div>

      <p id="manage-note" class="text-xs text-gray-400">
        Your email is sent to CheapShark, which sends the link. We do not store it.
      </p>

      <button
        type="submit"
        :disabled="sending"
        class="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 font-semibold disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-300"
      >
        {{ sending ? 'Sending…' : 'Email me my alerts' }}
      </button>

      <p v-if="serverError" class="text-red-400" role="alert">⚠️ {{ serverError }}</p>
    </form>
  </div>
</template>
