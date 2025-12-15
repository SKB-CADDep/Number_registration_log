<template>
  <v-app>
    <router-view />
  </v-app>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useTheme } from 'vuetify'

const theme = useTheme()

onMounted(() => {
  const savedTheme = localStorage.getItem('utz-theme')
  if (savedTheme && (savedTheme === 'utzDarkTheme' || savedTheme === 'utzLightTheme')) {
    theme.global.name.value = savedTheme
  }
})
</script>