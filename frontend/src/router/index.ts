import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/resumes',
    },
    {
      path: '/resumes',
      name: 'ResumeList',
      component: () => import('@/pages/ResumeListPage.vue'),
      meta: { title: '简历管理' },
    },
    {
      path: '/resumes/:id',
      name: 'ResumeDetail',
      component: () => import('@/pages/ResumeDetailPage.vue'),
      meta: { title: '简历详情' },
      props: (route) => ({ id: Number(route.params.id) }),
    },
    {
      path: '/jobs',
      name: 'JobList',
      component: () => import('@/pages/JobListPage.vue'),
      meta: { title: '岗位管理' },
    },
    {
      path: '/jobs/create',
      name: 'JobCreate',
      component: () => import('@/pages/JobCreatePage.vue'),
      meta: { title: '新增岗位' },
    },
    {
      path: '/jobs/:id',
      name: 'JobDetail',
      component: () => import('@/pages/JobDetailPage.vue'),
      meta: { title: '岗位详情' },
      props: (route) => ({ id: Number(route.params.id) }),
    },
    {
      path: '/jobs/:id/edit',
      name: 'JobEdit',
      component: () => import('@/pages/JobEditPage.vue'),
      meta: { title: '编辑岗位' },
      props: (route) => ({ id: Number(route.params.id) }),
    },
    {
      path: '/jobs/:id/match',
      name: 'MatchResults',
      component: () => import('@/pages/MatchResultsPage.vue'),
      meta: { title: '匹配结果' },
      props: (route) => ({ jobId: Number(route.params.id) }),
    },
  ],
})

export default router
