<template>
  <v-btn icon @click="toggleTheme">
    <v-icon
      :icon="
        theme.global.name.value === 'utzDarkTheme' ? 'mdi-white-balance-sunny' : 'mdi-weather-night'
      "
    ></v-icon>
    <v-tooltip activator="parent" location="bottom"> Переключить тему </v-tooltip>
  </v-btn>
</template>

<script setup lang="ts">
import { useTheme } from 'vuetify'

const theme = useTheme()

function toggleTheme() {
  const current = theme.global.name.value
  const next = current === 'utzDarkTheme' ? 'utzLightTheme' : 'utzDarkTheme'

  // 1. Применяем тему
  theme.global.name.value = next

  // 2. Сохраняем в LocalStorage
  localStorage.setItem('utz-theme', next)
  
  // Для проверки можно оставить лог, потом уберешь
  console.log('Theme saved:', next) 
}
</script>