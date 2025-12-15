import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import type { SearchParams, ReportResponse, ReportItem } from '@/types/api'
import apiClient from '@/api'

// --- API Функции ---

const fetchReport = async (params: SearchParams): Promise<ReportResponse> => {
  const filteredParams = Object.fromEntries(
    Object.entries(params).filter(([, v]) => v != null && v !== ''),
  )
  const { data } = await apiClient.get<ReportItem[]>('/reports', { params: filteredParams })
  return { items: data, totalItems: data.length }
}

const fetchAllReportItemsForExport = async (
  params: Omit<SearchParams, 'page' | 'itemsPerPage' | 'sortBy'>,
): Promise<ReportItem[]> => {
  const filteredParams = Object.fromEntries(
    Object.entries(params).filter(([, v]) => v != null && v !== ''),
  )
  const { data } = await apiClient.get<ReportItem[]>('/reports', { params: filteredParams })
  return data
}

// Добавляем отсутствующую функцию
const fetchDepartments = async (): Promise<string[]> => {
  const { data } = await apiClient.get<string[]>('/reports/departments')
  return data
}

interface TableOptions {
  page: number
  itemsPerPage: number
  sortBy: { key: string; order: 'asc' | 'desc' }[]
}

// --- Composable ---

export function useReports(initialFilters: Partial<SearchParams> = {}) {
  const tableOptions = ref<TableOptions>({
    page: 1,
    itemsPerPage: 10,
    sortBy: [{ key: 'reg_date', order: 'desc' }],
  })

  // Инициализация фильтров
  const createDefaultFilters = (): Omit<SearchParams, 'page' | 'itemsPerPage' | 'sortBy'> => ({
    session_id: undefined,
    username: undefined,
    department: undefined, // Исправлено: undefined вместо null, чтобы совпадало с типом SearchParams
    station_object: '',
    factory_no: '',
    station_no: '',
    label: '',
    order_no: '',
    doc_name: '',
    date_from: '',
    date_to: '',
    eq_type: '',
    q: '',
  })

  // Состояние для списка отделов
  const departments = ref<string[]>([])
  const isLoadingDepartments = ref(false)

  // Реактивный объект фильтров
  const filters = reactive<Omit<SearchParams, 'page' | 'itemsPerPage' | 'sortBy'>>({
    ...createDefaultFilters(),
    ...initialFilters,
  })

  const apiQueryParams = computed<SearchParams>(() => ({
    ...filters,
  }))

  const { data, isLoading, isError, error } = useQuery<ReportResponse>({
    queryKey: ['reports', apiQueryParams],
    queryFn: () => fetchReport(apiQueryParams.value),
    staleTime: 1000 * 60 * 5,
    placeholderData: (previousData) => previousData,
  })

  watch(
    () => JSON.stringify(filters),
    (newVal, oldVal) => {
      if (newVal !== oldVal) {
        tableOptions.value.page = 1
      }
    },
  )

  const resetFilters = () => {
    // Сбрасываем значения, сохраняя реактивность
    const defaults = createDefaultFilters()
    Object.assign(filters, defaults, initialFilters)
    tableOptions.value.page = 1
  }

  // Загружаем отделы при инициализации
  onMounted(async () => {
    try {
      isLoadingDepartments.value = true
      departments.value = await fetchDepartments()
    } catch (e) {
      console.error('Failed to load departments', e)
    } finally {
      isLoadingDepartments.value = false
    }
  })

  return {
    report: data,
    departments,
    isLoadingDepartments, // Важно: возвращаем это состояние для UI
    isLoading,
    isError,
    error,
    tableOptions,
    filters,
    resetFiltersAndRefetch: resetFilters,
    fetchAllReportItemsForExport: () => fetchAllReportItemsForExport(filters),
  }
}