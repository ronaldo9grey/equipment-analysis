import axios from 'axios'

const API_BASE_URL = '/api/v1'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000,
  headers: {
    'Content-Type': 'application/json'
  }
})

apiClient.interceptors.response.use(
  response => response,
  error => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export interface TableInfo {
  table_name: string
  columns: string[]
  row_count: number
  preview?: Record<string, any>[]
}

export interface AnalysisRecord {
  id: string
  file_name: string
  file_size: number
  file_type: string
  table_count: number
  record_count: number
  status: string
  analysis_result?: any
  error_message?: string
  created_at: string
  completed_at?: string
}

export const equipmentApi = {
  uploadFile: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await apiClient.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return response.data
  },

  getRecords: async (skip = 0, limit = 20) => {
    const response = await apiClient.get('/records', {
      params: { skip, limit }
    })
    return response.data
  },

  getRecord: async (id: string) => {
    const response = await apiClient.get(`/records/${id}`)
    return response.data
  },

  getRecordTables: async (id: string) => {
    const response = await apiClient.get(`/records/${id}/tables`)
    return response.data
  },

  getTableData: async (recordId: string, tableName: string, page = 1, pageSize = 100) => {
    const response = await apiClient.get(`/records/${recordId}/tables/${tableName}`, {
      params: { page, page_size: pageSize }
    })
    return response.data
  },

  analyzeData: async (recordId: string, query?: string, useLocalModel = false) => {
    const response = await apiClient.post('/analyze', {
      record_id: recordId,
      query,
      use_local_model: useLocalModel
    })
    return response.data
  },

  deleteRecord: async (id: string) => {
    const response = await apiClient.delete(`/records/${id}`)
    return response.data
  },

  healthCheck: async () => {
    const response = await apiClient.get('/health')
    return response.data
  }
}

export default apiClient
