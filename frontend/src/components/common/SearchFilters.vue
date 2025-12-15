<template>
  <v-card flat class="border mb-6">
    <v-card-title class="d-flex align-center">
      <v-icon start icon="mdi-filter-variant"></v-icon>
      Фильтры
      <v-spacer></v-spacer>
      <v-btn size="small" variant="text" prepend-icon="mdi-close" @click="reset"> Сбросить </v-btn>
    </v-card-title>
    <v-divider></v-divider>
    <v-card-text>
      <v-row>
        <!-- 1. Станция/Объект -->
        <v-col cols="12" sm="6" md="3">
          <v-text-field
            v-model="modelValue.station_object"
            label="Станция/Объект"
            clearable
            hide-details="auto"
          ></v-text-field>
        </v-col>

        <!-- 2. Станционный номер -->
        <v-col cols="12" sm="6" md="3">
          <v-text-field
            v-model="modelValue.station_no"
            label="№ станционный"
            clearable
            hide-details="auto"
            :rules="[rules.stationNo]"
          >
            <template #append-inner>
              <v-tooltip text="Фильтрует по объекту, но не отображается в таблице" location="top">
                <template #activator="{ props }">
                  <v-icon v-bind="props" icon="mdi-information-outline" size="small"></v-icon>
                </template>
              </v-tooltip>
            </template>
          </v-text-field>
        </v-col>

        <!-- 3. Заводской номер -->
        <v-col cols="12" sm="6" md="3">
          <v-text-field
            v-model="modelValue.factory_no"
            label="№ заводской"
            clearable
            hide-details="auto"
            :rules="[rules.factoryNo]"
          >
            <template #append-inner>
              <v-tooltip text="Фильтрует по объекту, но не отображается в таблице" location="top">
                <template #activator="{ props }">
                  <v-icon v-bind="props" icon="mdi-information-outline" size="small"></v-icon>
                </template>
              </v-tooltip>
            </template>
          </v-text-field>
        </v-col>

        <!-- 4. Номер заказа -->
        <v-col cols="12" sm="6" md="3">
          <v-text-field
            v-model="modelValue.order_no"
            label="№ заказа"
            clearable
            hide-details="auto"
          ></v-text-field>
        </v-col>

        <!-- 5. Маркировка -->
        <v-col cols="12" sm="6" md="3">
          <v-text-field v-model="modelValue.label" label="Маркировка" clearable hide-details="auto">
            <template #append-inner>
              <v-tooltip text="Фильтрует по объекту, но не отображается в таблице" location="top">
                <template #activator="{ props }">
                  <v-icon v-bind="props" icon="mdi-information-outline" size="small"></v-icon>
                </template>
              </v-tooltip>
            </template>
          </v-text-field>
        </v-col>

        <!-- 6. Имя документа -->
        <v-col cols="12" sm="6" md="3">
          <v-text-field
            v-model="modelValue.doc_name"
            label="Имя документа"
            clearable
            hide-details="auto"
          ></v-text-field>
        </v-col>

        <!-- 7. Тип оборудования -->
        <v-col cols="12" sm="6" md="3">
          <v-text-field
            v-model="modelValue.eq_type"
            label="Тип оборудования"
            clearable
            hide-details="auto"
          >
            <template #append-inner>
              <v-tooltip text="Фильтрует по объекту, но не отображается в таблице" location="top">
                <template #activator="{ props }">
                  <v-icon v-bind="props" icon="mdi-information-outline" size="small"></v-icon>
                </template>
              </v-tooltip>
            </template>
          </v-text-field>
        </v-col>
        
        <!-- 8. Отдел (Новое поле) -->
        <v-col cols="12" sm="6" md="3">
          <v-select
            v-model="modelValue.department"
            :items="departments"
            :loading="loadingDepartments"
            label="Отдел"
            clearable
            hide-details="auto"
            placeholder="Все отделы"
            no-data-text="Нет отделов"
          ></v-select>
        </v-col>

        <!-- 9. Пользователь -->
        <v-col cols="12" sm="6" md="3">
          <v-text-field
            v-model="modelValue.username"
            label="Автор (Login/ФИО)"
            clearable
            hide-details="auto"
            prepend-inner-icon="mdi-account-outline"
          ></v-text-field>
        </v-col>

        <!-- 10. Дата от -->
        <v-col cols="12" sm="6" md="3">
          <v-text-field
            v-model="modelValue.date_from"
            label="Дата от"
            type="date"
            clearable
            hide-details="auto"
          ></v-text-field>
        </v-col>

        <!-- 11. Дата до -->
        <v-col cols="12" sm="6" md="3">
          <v-text-field
            v-model="modelValue.date_to"
            label="Дата до"
            type="date"
            clearable
            hide-details="auto"
          ></v-text-field>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import type { SearchParams } from '@/types/api'

// Принимаем модель фильтров
const modelValue = defineModel<Partial<SearchParams>>({ required: true })

// Принимаем данные для селекта
defineProps<{
  departments?: string[]
  loadingDepartments?: boolean
}>()

const emit = defineEmits(['reset'])

const rules = {
  factoryNo: (v: string) => !v || /^\d{1,5}$/.test(v) || 'Не более 5 цифр',
  stationNo: (v: string) => !v || /^\d{1,2}$/.test(v) || 'Не более 2 цифр',
  orderNo: (v: string) => !v || /^\d{5}-\d{2}-\d{5}$/.test(v) || 'Формат XXXXX-XX-XXXXX',
}

function reset() {
  emit('reset')
}
</script>