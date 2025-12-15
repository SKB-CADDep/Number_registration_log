<template>
  <v-container fluid>
    <v-row>
      <v-col>
        <h1 class="text-h4 font-weight-bold mb-4">Отчеты</h1>
        <p class="text-body-1 text-grey mb-6">
          Просмотр, фильтрация и экспорт всех зарегистрированных номеров.
        </p>
      </v-col>
    </v-row>

    <!-- Передаем departments и статус загрузки -->
    <search-filters 
      v-model="filters"
      :departments="departments"
      :loading-departments="isLoadingDepartments"
      @reset="resetFilters" 
    />

    <v-card flat class="border">
      <v-card-title class="d-flex align-center">
        Результаты
        <v-spacer></v-spacer>
        <v-btn
          color="primary"
          variant="tonal"
          prepend-icon="mdi-file-excel-outline"
          @click="exportToExcel"
          :loading="isExporting"
          :disabled="!report || report.items.length === 0"
        >
          Экспорт в Excel
        </v-btn>
      </v-card-title>
      <v-divider></v-divider>

      <v-data-table
        v-model:items-per-page="tableOptions.itemsPerPage"
        v-model:page="tableOptions.page"
        :headers="headers"
        :items="report?.items || []"
        :loading="isLoading"
        item-value="numeric"
        class="elevation-0"
        hover
        density="compact"
      >
        <template #no-data>
          <div class="text-center pa-6">
            <v-icon
              icon="mdi-database-off-outline"
              size="x-large"
              color="grey-lighten-1"
              class="mb-4"
            ></v-icon>
            <h3 class="text-h6 font-weight-medium">Нет данных для отображения</h3>
            <p class="text-medium-emphasis text-body-2 mt-2">
              Попробуйте изменить или сбросить фильтры.
            </p>
          </div>
        </template>
        <template #loading>
          <v-skeleton-loader type="table-row@10"></v-skeleton-loader>
        </template>
      </v-data-table>
    </v-card>
  </v-container>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useReports } from '@/composables/useReports'
import { useAuthStore } from '@/stores/auth'
import * as XLSX from 'xlsx'
import type { ReportItem, SearchParams } from '@/types/api'
import { useNotifier } from '@/composables/useNotifier'
import SearchFilters from '@/components/common/SearchFilters.vue'

const authStore = useAuthStore()
const notifier = useNotifier()

// Состояние по умолчанию для фильтров
const initialFilters: Partial<SearchParams> = authStore.user
  ? { username: authStore.user.username }
  : {}

const {
  report,
  departments,
  isLoadingDepartments, // Получаем статус загрузки отделов
  isLoading,
  tableOptions,
  filters,
  resetFiltersAndRefetch,
  fetchAllReportItemsForExport,
} = useReports(initialFilters)
const isExporting = ref(false)

const headers = [
  { title: '№ Документа', key: 'doc_no', sortable: true },
  { title: 'Дата регистрации', key: 'reg_date', sortable: true },
  { title: 'Наименование', key: 'doc_name', sortable: false },
  { title: 'Примечание', key: 'note', sortable: false },
  { title: 'Отдел', key: 'department', sortable: true },
  { title: 'Пользователь', key: 'username', sortable: true },
  { title: '№ заказа', key: 'order_no', sortable: false },
  { title: 'Станция/Объект', key: 'station_object', sortable: false },
  { title: 'Тип оборуд.', key: 'eq_type', sortable: false },
] as const

function resetFilters() {
  resetFiltersAndRefetch()
}

async function exportToExcel() {
  isExporting.value = true
  try {
    const allItems = await fetchAllReportItemsForExport()
    if (!allItems || allItems.length === 0) {
      notifier.warning('Нет данных для экспорта!')
      return
    }
    const dataToExport = allItems.map((item: ReportItem) => ({
      '№ Документа': item.doc_no,
      'Дата регистрации': item.reg_date,
      'Наименование документа': item.doc_name,
      'Примечание': item.note,
      'Отдел': item.department || '', // Добавили отдел в Excel
      'Пользователь': item.username,
      '№ заказа': item.order_no,
      'Станция/Объект': item.station_object,
      'Тип оборуд.': item.eq_type,
    }))
    const worksheet = XLSX.utils.json_to_sheet(dataToExport)
    const workbook = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Отчет')
    XLSX.writeFile(workbook, `Отчет_Регистрации_${new Date().toISOString().split('T')[0]}.xlsx`)
  } catch (error) {
    notifier.error(`Произошла ошибка при формировании отчета для экспорта: ${error}`)
  } finally {
    isExporting.value = false
  }
}
</script>