import { createRouter, createWebHistory } from 'vue-router'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import { useWizardStore } from '@/stores/wizard'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { title: 'Вход', public: true },
    },
    {
      path: '/',
      component: DefaultLayout,
      children: [
        {
          path: '',
          name: 'home',
          component: () => import('@/views/HomeView.vue'),
          meta: { title: 'Главная' },
        },
        {
          path: 'wizard',
          name: 'wizard',
          component: () => import('@/views/wizard/WizardWrapper.vue'),
          redirect: '/wizard/equipment',
          meta: { title: 'Мастер регистрации' },
          children: [
            {
              path: 'equipment',
              name: 'wizard-equipment',
              component: () => import('@/views/wizard/Step1Equipment.vue'),
              meta: { title: 'Оборудование' },
            },
            {
              path: 'reserve/:equipmentId',
              name: 'wizard-reserve',
              component: () => import('@/views/wizard/Step2Reserve.vue'),
              meta: { title: 'Резерв' },
              props: true,
              beforeEnter: (to, from) => {
                const wizardStore = useWizardStore()
                const equipmentIdFromUrl = Number(to.params.equipmentId)

                if (wizardStore.selectedEquipmentId === equipmentIdFromUrl) {
                  return true
                }

                if (!from.path.startsWith('/wizard')) {
                  console.log('Direct navigation to Step 2, restoring state from URL...')
                  wizardStore.setEquipment(equipmentIdFromUrl)
                  return true
                }

                console.warn('Blocked navigation to Step 2: no equipment selected.')
                return { name: 'wizard-equipment' }
              },
            },
            {
              path: 'assign/:sessionId',
              name: 'wizard-assign',
              component: () => import('@/views/wizard/Step3Assign.vue'),
              meta: { title: 'Назначение' },
              props: true,
              beforeEnter: (to, from) => {
                const wizardStore = useWizardStore()
                const sessionIdFromUrl = String(to.params.sessionId)

                if (wizardStore.currentSessionId === sessionIdFromUrl) {
                  return true
                }

                if (!from.path.startsWith('/wizard')) {
                  console.warn(
                    'Direct navigation to Step 3 is not fully supported, redirecting to Step 1.',
                  )
                  wizardStore.reset()
                  return { name: 'wizard-equipment' }
                }

                console.warn('Blocked navigation to Step 3: no active session.')
                if (wizardStore.selectedEquipmentId) {
                  return {
                    name: 'wizard-reserve',
                    params: { equipmentId: wizardStore.selectedEquipmentId },
                  }
                }
                return { name: 'wizard-equipment' }
              },
            },
          ],
        },
        {
          path: 'reports',
          name: 'reports',
          component: () => import('@/views/ReportsView.vue'),
          meta: { title: 'Отчеты' },
        },
        {
          path: 'admin',
          name: 'admin',
          component: () => import('@/views/AdminView.vue'),
          meta: { title: 'Админка' },
        },
      ],
    },
  ],
})

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // 1. Проверка авторизации
  if (!to.meta.public && !authStore.isAuthenticated) {
    return next({ name: 'login' })
  }

  // 2. Если пользователь нажал F5, стейт сбросился, но токен в localStorage есть
  if (authStore.isAuthenticated && !authStore.user) {
    await authStore.fetchUser()
  }

  // 3. Если уже авторизован - не пускать на логин
  if (to.name === 'login' && authStore.isAuthenticated) {
    return next({ name: 'home' })
  }

  // 4. Очистка визарда при выходе
  if (from.path.startsWith('/wizard') && !to.path.startsWith('/wizard')) {
    const wizardStore = useWizardStore()
    if (wizardStore.hasSelectedEquipment || wizardStore.hasActiveSession) {
      wizardStore.reset()
    }
  }

  next()
})

router.afterEach((to) => {
  const baseTitle = 'Журнал УТЗ'
  const mostSpecificTitle = to.matched
    .slice()
    .reverse()
    .find((record) => record.meta.title)

  if (mostSpecificTitle && mostSpecificTitle.meta.title) {
    document.title = `${mostSpecificTitle.meta.title} | ${baseTitle}`
  } else {
    document.title = baseTitle
  }
})

export default router