import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.reload()
    }
    return Promise.reject(err)
  }
)

export function login(username, password) { return api.post('/auth/login', { username, password }) }
export function fetchMe() { return api.get('/auth/me') }

export function fetchUsers() { return api.get('/users') }
export function createUser(username, password, role) { return api.post('/users', { username, password, role }) }
export function deleteUser(id) { return api.delete(`/users/${id}`) }

export function fetchPlatforms() { return api.get('/platforms') }
export function createPlatform(name) { return api.post('/platforms', { name }) }
export function deletePlatform(id) { return api.delete(`/platforms/${id}`) }
export function updatePlatformConnection(id, baseUrl, accessKey) { return api.put(`/platforms/${id}/connection`, { baseUrl, accessKey }) }
export function getPlatformConnection(id) { return api.get(`/platforms/${id}/connection`) }
export function testPlatformConnection(id) { return api.post(`/platforms/${id}/test-connection`) }
export function fetchPlatformData(id) { return api.post(`/platforms/${id}/fetch`) }
export function fetchProjectData(platformId, projectId) { return api.post(`/platforms/${platformId}/projects/${projectId}/fetch`) }

export function fetchSnapshots(projectId) { return api.get(`/projects/${projectId}/snapshots`) }
export function fetchSnapshotTasks(snapshotId) { return api.get(`/snapshots/${snapshotId}/tasks`) }
export function getPlatformSchedule(id) { return api.get(`/platforms/${id}/schedule`) }
export function updatePlatformSchedule(id, scheduleTimes) { return api.put(`/platforms/${id}/schedule`, { scheduleTimes }) }

export function fetchProjects(platformId) { return api.get('/projects', { params: { platform_id: platformId } }) }
export function createProject(name, platformId, projectKey) { return api.post('/projects', { name, platformId, projectKey }) }
export function updateProject(id, data) { return api.put(`/projects/${id}`, data) }
export function deleteProject(id) { return api.delete(`/projects/${id}`) }

export function fetchTasks(projectId) { return api.get('/tasks', { params: { project_id: projectId } }) }
export function createTask(name, projectId) { return api.post('/tasks', { name, projectId }) }
export function updateTask(id, data) { return api.put(`/tasks/${id}`, data) }
export function deleteTask(id) { return api.delete(`/tasks/${id}`) }

export function uploadCsv(projectId, file) {
  const fd = new FormData()
  fd.append('file', file)
  return api.post('/upload-csv', fd, { params: { project_id: projectId } })
}

export function fetchItems(projectId, search, process, status) {
  return api.get('/items', { params: { project_id: projectId, search, process, status } })
}

export function batchUpdateStatus(ids, field, value) {
  return api.post('/items/batch-status', { ids, field, value })
}

export function updateItemStatus(itemId, field, value, date) {
  return api.put(`/items/${itemId}/status`, { field, value, date })
}

export function updateItemDate(itemId, field, value) {
  return api.put(`/items/${itemId}/date`, { field, value })
}

export function markExport(ids) { return api.post('/items/export', { ids }) }
export function markReturn(ids) { return api.post('/items/return', { ids }) }

export function fetchStats(projectId) {
  return api.get('/stats', { params: { project_id: projectId } })
}

export function importExportCsv(formData) {
  return api.post('/import-export-csv', formData)
}

export function startExport(data) {
  return api.post('/export-files', data)
}

export function getExportStatus(exportId) {
  return api.get(`/export-files/${exportId}/status`)
}

export function getExportCsvUrl(projectId) {
  const t = localStorage.getItem('token')
  return `/api/export-csv?project_id=${projectId}&token=${t}`
}

export function getPerformance(platformId, projectId, date) {
  return api.get('/performance', { params: { platform_id: platformId, project_id: projectId, date } })
}

export function fetchPerformance(data) {
  return api.post('/performance/fetch', data)
}
