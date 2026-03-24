<script setup>
  import { ref, watch } from "vue"

  const query = ref("")
  const currency = ref("USD")
  const games = ref([])
  const loading = ref(false)
  const stores = {
      "1": "Steam",
      "2": "GamersGate",
      "3": "GreenManGaming",
      "7": "GOG",
      "8": "Origin",
      "11": "Humble"
    }

  let timeout = null

  const searchGame = async () => {
    if (!query.value) {
      games.value = []
      return
    }

    loading.value = true

    try {
      const res =
        await fetch(`http://localhost:5000/api/search?query=${query.value}&currency=${currency.value}`)
      const data = await res.json()
      games.value = data
    } catch (err) {
      console.error(err)
    }

    loading.value = false
  }

  const openDeal = (url) => {
    if (!url) return
    window.open(url, "_blank")
  }

  const getStoreName = (id) => {

    return stores[id] || "Store"
  }

  watch(query, (newVal) => {
    clearTimeout(timeout)

    timeout = setTimeout(() => {
      searchGame()
    }, 500) // รอ 500ms
  })

  watch(currency, (newVal) => {
    clearTimeout(timeout)

    timeout = setTimeout(() => {
      searchGame()
    }, 500) // รอ 500ms
  })

  watch(query, (newVal) => {
    if (!newVal) {
      document.title = "Game Price Compare"
    } else {
      document.title = `${newVal} - Game Price Compare`
    }
  })
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-white p-6">
    
    <div class="max-w-6xl mx-auto">
      
      <!-- Title -->
      <h1 class="text-3xl font-bold text-center">
        🎮 Game Price Compare
      </h1>

      <!-- Currency selector -->
      <div class="flex justify-center mt-4">
        <select
          v-model="currency"
          class="bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="USD">USD 💵</option>
          <option value="THB">THB 🇹🇭</option>
          <option value="EUR">EUR 💶</option>
        </select>
      </div>

      <!-- Divider -->
      <hr class="my-6 border-gray-700" />

      <!-- Search -->
      <input
        v-model="query"
        placeholder="Search game..."
        class="w-full p-3 rounded-xl bg-gray-800 border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 mb-8"
      />

      <!-- Grid -->
      <div class="grid gap-6 grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
        
        <!-- card  -->
        <div
          v-for="game in games"
          :key="game.name"
          @click="openDeal(game.dealUrl)"
          class="group relative bg-gray-800 rounded-2xl overflow-hidden shadow-lg hover:scale-105 hover:shadow-blue-500/20 transition duration-300 cursor-pointer"
        >
          
          <!-- image -->
          <img :src="game.thumb" class="w-full h-60 object-cover" />
          
          <!-- tag store -->
          <div class="absolute top-2 left-2 bg-black/70 text-xs px-2 py-1 rounded">
            🏷️ {{ getStoreName(game.storeID) }}
          </div>

          <!-- hover overlay -->
          <div class="absolute inset-0 bg-gradient-to-t from-black via-black/70 to-transparent backdrop-blur-sm opacity-0 group-hover:opacity-100 transition duration-300 flex flex-col justify-end p-3">
            
            <h3 class="text-sm font-semibold">
              {{ game.name }}
            </h3>

            <p class="text-green-400 font-bold text-lg">
              💰 {{ game.price }} {{ game.currency }}
            </p>

          </div>

        </div>

      </div>
    </div>

  </div>
</template>