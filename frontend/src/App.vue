<template>
  <div class="app-container">
    <el-container>
      <el-header class="header">
        <div class="header-content">
          <div class="header-title">
            <el-icon class="header-icon"><DataAnalysis /></el-icon>
            <h1>设备运行数据分析</h1>
          </div>
          <div class="header-actions">
            <el-select
              v-model="useLocalModel"
              @change="handleModelChange"
              placeholder="选择AI模型"
              size="small"
              style="width: 140px"
            >
              <el-option :value="false" label="DeepSeek 云端" />
              <el-option :value="true" label="Ollama 本地" />
            </el-select>
          </div>
        </div>
      </el-header>

      <el-main class="main-content">
        <div class="loading-overlay" v-if="analyzing">
          <div class="loading-spinner">
            <el-icon class="is-loading" :size="48"><Loading /></el-icon>
            <div class="loading-text">{{ analyzingText }}</div>
            <div class="loading-subtext">{{ analyzingType === 'table' ? '预计 1-2 分钟' : '预计 30秒-1 分钟' }}</div>
          </div>
        </div>
        <div class="content-wrapper">
          <div class="left-panel">
            <el-card class="left-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span><el-icon><UploadFilled /></el-icon> 上传数据</span>
                </div>
              </template>
              <el-upload
                class="upload-area"
                drag
                :action="uploadUrl"
                :auto-upload="false"
                :on-change="handleFileChange"
                :on-success="handleUploadSuccess"
                :on-error="handleUploadError"
                :limit="1"
                :accept="acceptTypes"
              >
                <el-icon class="upload-icon"><upload-filled /></el-icon>
                <div class="upload-text">
                  拖拽或<em>点击上传</em>
                </div>
                <template #tip>
                  <div class="upload-tip">支持 MDB、ACCDB、SQL</div>
                </template>
              </el-upload>
              <el-button
                type="primary"
                :loading="uploading"
                :disabled="!selectedFile"
                @click="handleUpload"
                class="upload-btn"
              >
                {{ uploading ? '解析中...' : '开始解析' }}
              </el-button>
            </el-card>

            <el-card class="records-card" shadow="hover" v-if="records.length > 0">
              <template #header>
                <div class="card-header">
                  <span><el-icon><Document /></el-icon> 历史记录</span>
                  <el-button text @click="loadRecords">
                    <el-icon><Refresh /></el-icon>
                  </el-button>
                </div>
              </template>
              <div class="records-list">
                <div
                  v-for="record in records"
                  :key="record.id"
                  class="record-item"
                  :class="{ active: selectedRecord?.id === record.id }"
                  @click="selectRecord(record)"
                >
                  <div class="record-name">
                    <el-icon><Document /></el-icon>
                    {{ record.table_name || record.file_name }}
                  </div>
                  <div class="record-info">
                    <el-tag size="small" :type="getStatusType(record.status)" effect="dark">
                      {{ getStatusText(record.status) }}
                    </el-tag>
                    <span class="record-time">{{ formatTime(record.created_at) }}</span>
                  </div>
                </div>
              </div>
            </el-card>
          </div>

          <div class="right-panel" v-if="selectedRecord">
            <el-card class="right-card" shadow="hover">
              <template #header>
                <div class="card-header card-header-responsive">
                  <span class="file-name">
                    <el-icon><Folder /></el-icon> 
                    {{ selectedRecord.table_name || selectedRecord.file_name }}
                  </span>
                  <div class="header-btns">
                    <el-button
                      type="primary"
                      size="small"
                      :disabled="analyzing || (selectedRecord.status !== 'completed' && selectedRecord.status !== 'analyzed')"
                      @click="handleAnalyze"
                    >
                      {{ analyzeButtonText }}
                    </el-button>
                    <el-button type="danger" size="small" text @click="handleDelete">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </div>
                </div>
              </template>

              <div class="file-info">
                <el-descriptions :column="2" border size="small">
                  <el-descriptions-item label="大小">{{ formatSize(selectedRecord.file_size) }}</el-descriptions-item>
                  <el-descriptions-item label="类型">
                    <el-tag size="small">{{ selectedRecord.file_type?.toUpperCase() }}</el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="表数">
                    <el-tag type="info" size="small">{{ selectedRecord.table_count }}</el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="记录">
                    <el-tag type="success" size="small">{{ selectedRecord.record_count }}</el-tag>
                  </el-descriptions-item>
                </el-descriptions>
              </div>

              <el-tabs v-model="activeTab" class="data-tabs">
                <el-tab-pane v-if="!selectedRecord?.table_name" label="数据表" name="tables">
                  <div class="tables-list">
                    <el-table :data="tables" stripe size="small">
                      <el-table-column prop="table_name" label="表名" min-width="120">
                        <template #default="{ row }">
                          <el-icon><Grid /></el-icon> {{ row.table_name }}
                        </template>
                      </el-table-column>
                      <el-table-column prop="columns" label="字段" width="70">
                        <template #default="{ row }">
                          {{ row.columns?.length || 0 }}
                        </template>
                      </el-table-column>
                      <el-table-column prop="row_count" label="记录" width="80" />
                      <el-table-column label="操作" width="140">
                        <template #default="{ row }">
                          <el-button type="primary" link size="small" @click.stop="viewTableData(row)">查看</el-button>
                          <el-button type="success" link size="small" @click.stop="handleAnalyzeTable(row)">数据分析</el-button>
                        </template>
                      </el-table-column>
                    </el-table>
                  </div>
                </el-tab-pane>

                <el-tab-pane v-if="selectedRecord?.table_name" label="数据集" name="data">
                  <div class="dataset-header">
                    <el-button type="primary" size="small" @click="handleDownloadData">
                      <el-icon><Download /></el-icon> 导出Excel
                    </el-button>
                    <span class="dataset-count">共 {{ tableDataForView.length }} 条数据</span>
                  </div>
                  <div class="tables-list">
                    <el-table :data="tableDataForView" stripe size="small" max-height="500">
                      <el-table-column v-for="col in tableColumnsForView" :key="col" :prop="col" :label="col" min-width="120" show-overflow-tooltip />
                    </el-table>
                    <el-empty v-if="tableDataForView.length === 0" description="暂无数据" />
                  </div>
                </el-tab-pane>

                <el-tab-pane label="分析结果" name="analysis">
                  <div class="analysis-info" v-if="selectedRecord.analysis_result?.content">
                    <el-tag :type="selectedRecord.analysis_result?.data_mode === '全量' ? 'success' : 'warning'" effect="dark" size="small">
                      {{ selectedRecord.analysis_result?.data_mode === '全量' ? '全量分析' : '采样分析 (1000条)' }}
                    </el-tag>
                    <el-tag type="info" size="small" v-if="selectedRecord.analysis_result?.table_name">
                      表: {{ selectedRecord.analysis_result.table_name }}
                    </el-tag>
                  </div>
                  <div class="analysis-result" v-if="selectedRecord.analysis_result?.content" v-html="renderMarkdown(selectedRecord.analysis_result.content)">
                  </div>
                  <el-empty v-else description="暂无分析结果" />
                </el-tab-pane>

                <el-tab-pane label="运行模拟" name="simulation" v-if="selectedRecord?.table_name">
                  <div class="simulation-panel">
                    <div class="simulation-header">
                      <el-button 
                        :type="simulationRunning ? 'danger' : 'primary'" 
                        size="small"
                        @click="simulationRunning ? handleStopSimulation() : handleStartSimulation()"
                      >
                        {{ simulationRunning ? '停止模拟' : '启动模拟' }}
                      </el-button>
                      <el-checkbox v-model="useAnalysisFeatures" style="margin-left: 16px">
                        应用AI分析特征
                      </el-checkbox>
                      <span class="simulation-tip" v-if="useAnalysisFeatures">
                        模拟数据将体现AI分析发现的问题特征（缺失值、异常值等）
                      </span>
                    </div>
                    <div class="simulation-data">
                      <el-table :data="simulationData" stripe size="small" max-height="400" v-if="simulationData.length > 0">
                        <el-table-column v-for="col in simulationColumns" :key="col" :prop="col" :label="col" min-width="100" show-overflow-tooltip>
                          <template #default="{ row }">
                            <span :class="{'anomaly-value': isAnomalyValue(row[col])}">
                              {{ row[col] === null || row[col] === undefined ? '-' : row[col] }}
                            </span>
                          </template>
                        </el-table-column>
                      </el-table>
                      <el-empty v-else description="点击开关启动模拟" />
                    </div>
                  </div>
                </el-tab-pane>
              </el-tabs>
            </el-card>
          </div>

          <div v-else class="right-panel">
            <div class="empty-card">
              <el-empty description="请上传数据文件或选择历史记录">
                <template #image>
                  <el-icon :size="60" color="#dcdfe6"><DataLine /></el-icon>
                </template>
              </el-empty>
            </div>
          </div>
        </div>
      </el-main>
    </el-container>

    <el-dialog v-model="tableDialogVisible" :title="currentTable?.table_name" width="90%">
      <el-table :data="tableData" stripe size="small" max-height="50vh" v-if="tableData.length > 0">
        <el-table-column
          v-for="col in currentTableColumns"
          :key="col"
          :prop="col"
          :label="col"
          min-width="120"
          show-overflow-tooltip
        />
      </el-table>
      <el-pagination
        v-if="tablePagination.total > 0"
        v-model:current-page="tablePagination.page"
        v-model:page-size="tablePagination.pageSize"
        :total="tablePagination.total"
        layout="total, prev, pager, next"
        :page-sizes="[50, 100]"
        @current-change="loadTableData"
        small
      />
      <el-empty v-else description="暂无数据" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  UploadFilled, 
  DataAnalysis, 
  Document, 
  Refresh, 
  Delete, 
  Grid, 
  Folder,
  DataLine,
  Loading,
  Download
} from '@element-plus/icons-vue'
import { equipmentApi, type AnalysisRecord, type TableInfo } from './api/equipment'

const uploadUrl = '/api/v1/upload'
const acceptTypes = '.mdb,.accdb,.sql,.bak,.mysql'

const selectedFile = ref<File | null>(null)
const uploading = ref(false)
const analyzing = ref(false)
const analyzingType = ref<'file' | 'table'>('file')

const analyzingText = computed(() => {
  if (analyzingType.value === 'table') {
    return 'AI 正在分析数据表中，请稍候...'
  }
  return 'AI 正在分析文件中，请稍候...'
})

const analyzeButtonText = computed(() => {
  if (analyzing.value) return '分析中'
  return selectedRecord.value?.table_name ? '数据分析' : '文件分析'
})

const useLocalModel = ref(false)
const records = ref<AnalysisRecord[]>([])
const selectedRecord = ref<AnalysisRecord | null>(null)
const tables = ref<TableInfo[]>([])
const tableDataForView = ref<any[]>([])
const tableColumnsForView = ref<string[]>([])
const simulationId = ref('')
const simulationRunning = ref(false)
const simulationData = ref<any[]>([])
const simulationColumns = ref<string[]>([])
const useAnalysisFeatures = ref(true)
const activeTab = ref('tables')

const tableDialogVisible = ref(false)
const currentTable = ref<TableInfo | null>(null)
const tableData = ref<any[]>([])
const currentTableColumns = ref<string[]>([])
const tablePagination = ref({
  page: 1,
  pageSize: 100,
  total: 0
})

const handleFileChange = (file: any) => {
  selectedFile.value = file.raw
}

const handleUpload = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }

  uploading.value = true
  try {
    const result = await equipmentApi.uploadFile(selectedFile.value)
    ElMessage.success('文件解析成功')
    selectedRecord.value = result
    await loadTables(result.id)
    await loadRecords()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '上传失败')
  } finally {
    uploading.value = false
  }
}

const handleUploadSuccess = () => ElMessage.success('上传成功')

const handleUploadError = (error: any) => ElMessage.error(error.message || '上传失败')

const loadRecords = async () => {
  try {
    records.value = await equipmentApi.getRecords(0, 20)
  } catch (error) {
    console.error('加载记录失败:', error)
  }
}

const selectRecord = async (record: AnalysisRecord) => {
  selectedRecord.value = record
  
  if (record.table_name) {
    activeTab.value = 'data'
    tableDataForView.value = []
    tableColumnsForView.value = []
    if (record.status === 'completed' || record.status === 'analyzed') {
      try {
        const result = await equipmentApi.getTableData(record.id, record.table_name, 1, 1000)
        tableDataForView.value = result.data || []
        tableColumnsForView.value = result.columns || []
      } catch (error) {
        console.error('加载表数据失败:', error)
      }
    }
  } else {
    activeTab.value = 'tables'
    if (record.status === 'completed' || record.status === 'analyzed') {
      await loadTables(record.id)
    }
  }
}

const loadTables = async (recordId: string) => {
  try {
    const result = await equipmentApi.getRecordTables(recordId)
    tables.value = result.tables
  } catch (error) {
    console.error('加载表列表失败:', error)
  }
}

const viewTableData = async (table: TableInfo) => {
  currentTable.value = table
  tablePagination.value.page = 1
  await loadTableData()
  tableDialogVisible.value = true
}

const loadTableData = async () => {
  if (!selectedRecord.value || !currentTable.value) return

  try {
    const result = await equipmentApi.getTableData(
      selectedRecord.value.id,
      currentTable.value.table_name,
      tablePagination.value.page,
      tablePagination.value.pageSize
    )
    tableData.value = result.data
    currentTableColumns.value = result.columns
    tablePagination.value.total = result.row_count
  } catch (error) {
    console.error('加载表数据失败:', error)
  }
}

const handleAnalyze = async () => {
  if (!selectedRecord.value) return

  analyzingType.value = 'file'
  analyzing.value = true
  try {
    const result = await equipmentApi.analyzeData(
      selectedRecord.value.id,
      undefined,
      undefined,
      useLocalModel.value
    )
    selectedRecord.value.analysis_result = result.result
    ElMessage.success('分析完成')
    activeTab.value = 'analysis'
  } catch (error: any) {
    console.error('分析错误:', error)
    ElMessage.error(error.response?.data?.detail || '分析失败')
  } finally {
    analyzing.value = false
  }
}

const handleAnalyzeTable = async (table: TableInfo) => {
  if (!selectedRecord.value) return

  analyzingType.value = 'table'
  analyzing.value = true
  try {
    const result = await equipmentApi.analyzeData(
      selectedRecord.value.id,
      table.table_name,
      undefined,
      useLocalModel.value
    )
    
    ElMessage.success(`表 ${table.table_name} 分析完成`)
    activeTab.value = 'analysis'
    
    await loadRecords()
    
    const newRecord = records.value.find(r => r.id === result.record_id)
    if (newRecord) {
      selectedRecord.value = newRecord
    }
  } catch (error: any) {
    console.error('分析错误:', error)
    ElMessage.error(error.response?.data?.detail || '分析失败')
  } finally {
    analyzing.value = false
  }
}

const handleDelete = async () => {
  if (!selectedRecord.value) return

  try {
    await ElMessageBox.confirm('确定要删除这条记录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await equipmentApi.deleteRecord(selectedRecord.value.id)
    ElMessage.success('删除成功')
    selectedRecord.value = null
    tables.value = []
    await loadRecords()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handleDownloadData = async () => {
  if (!selectedRecord.value?.table_name) return
  
  try {
    await equipmentApi.downloadTableData(selectedRecord.value.id, selectedRecord.value.table_name)
    ElMessage.success('下载成功')
  } catch (error: any) {
    ElMessage.error('下载失败')
  }
}

const handleStartSimulation = async () => {
  if (!selectedRecord.value?.table_name) return
  
  simulationId.value = `${selectedRecord.value.id}_${selectedRecord.value.table_name}`
  
  try {
    await equipmentApi.startSimulation(
      selectedRecord.value.id,
      selectedRecord.value.table_name,
      5,
      useAnalysisFeatures.value
    )
    simulationRunning.value = true
    activeTab.value = 'simulation'
    ElMessage.success('模拟已启动')
    fetchSimulationData()
  } catch (error: any) {
    ElMessage.error('启动模拟失败')
  }
}

const handleStopSimulation = async () => {
  if (!simulationId.value) return
  
  try {
    await equipmentApi.stopSimulation(simulationId.value)
    simulationRunning.value = false
    ElMessage.success('模拟已停止')
  } catch (error: any) {
    ElMessage.error('停止模拟失败')
  }
}

let simulationTimer: number | null = null

const fetchSimulationData = async () => {
  if (!simulationRunning.value || !simulationId.value) return
  
  try {
    const result = await equipmentApi.getSimulationData(simulationId.value, 20)
    simulationData.value = result.data || []
    simulationColumns.value = result.columns || []
    
    if (simulationRunning.value) {
      simulationTimer = window.setTimeout(fetchSimulationData, 3000)
    }
  } catch (error: any) {
    console.error('获取模拟数据失败:', error)
    simulationRunning.value = false
  }
}

const handleModelChange = (value: boolean) => {
  ElMessage.info(value ? '已切换到本地模型' : '已切换到DeepSeek模型')
}

const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    pending: 'warning',
    completed: 'success',
    analyzed: 'success',
    failed: 'danger'
  }
  return map[status] || 'info'
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    pending: '处理中',
    completed: '已完成',
    analyzed: '已分析',
    failed: '失败'
  }
  return map[status] || status
}

const formatTime = (time: string) => {
  const date = new Date(time)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const formatSize = (bytes: number) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const renderMarkdown = (text: string): string => {
  if (!text) return ''
  
  let html = text
  
  html = html.replace(/^### (.*$)/gim, '<h3 class="md-h3">$1</h3>')
  html = html.replace(/^## (.*$)/gim, '<h2 class="md-h2">$1</h2>')
  html = html.replace(/^# (.*$)/gim, '<h1 class="md-h1">$1</h1>')
  
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>')
  html = html.replace(/^- (.*$)/gim, '<li class="md-li">$1</li>')
  html = html.replace(/^(\*[^#][^*].*$)/gim, '<p class="md-li">$1</p>')
  html = html.replace(/^(\d+)\.\s+(.*$)/gim, '<li class="md-li md-ol" data-num="$1">$2</li>')
  html = html.replace(/`([^`]+)`/g, '<code class="md-code">$1</code>')
  
  html = html.replace(/\n\n/g, '</p><p class="md-p">')
  html = '<p class="md-p">' + html + '</p>'
  
  html = html.replace(/<p class="md-p"><\/p>/g, '')
  html = html.replace(/<p class="md-p"><h/g, '<h')
  html = html.replace(/<\/h\d><\/p>/g, '</h2>')
  html = html.replace(/<p class="md-p"><li/g, '<li')
  html = html.replace(/<\/li><\/p>/g, '</li>')
  html = html.replace(/<p class="md-p"><p class="md-li">/g, '<p class="md-li">')
  html = html.replace(/<\/p><\/p>/g, '</p>')
  
  return html
}

const isAnomalyValue = (value: any): boolean => {
  if (value === null || value === undefined) return true
  if (typeof value === 'number') {
    return value < 0 || value > 10000 || value === 9999
  }
  return false
}

onMounted(() => {
  loadRecords()
})

onUnmounted(() => {
  if (simulationTimer) {
    clearTimeout(simulationTimer)
  }
})
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  background: #f5f7fa;
  overflow: hidden;
}

.header {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  color: white;
  padding: 0 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-icon {
  font-size: 20px;
  color: #409eff;
}

.header-title h1 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  align-items: center;
}

:deep(.header-actions .el-select) {
  --el-select-input-focus-border-color: #409eff;
}

:deep(.header-actions .el-select .el-input__wrapper) {
  background-color: rgba(255, 255, 255, 0.1);
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.3) inset;
}

:deep(.header-actions .el-select .el-input__inner) {
  color: white;
}

:deep(.header-actions .el-select .el-input__placeholder) {
  color: rgba(255, 255, 255, 0.6);
}

:deep(.header-actions .el-select .el-select__caret) {
  color: rgba(255, 255, 255, 0.8);
}

.main-content {
  padding: 16px;
  height: calc(100vh - 60px);
  box-sizing: border-box;
  overflow: hidden;
}

.content-wrapper {
  display: flex;
  height: 100%;
  gap: 16px;
  overflow: hidden;
}

.left-panel {
  width: 400px;
  min-width: 400px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
}

.left-card {
  flex: 0 0 auto;
  min-height: 280px;
  max-height: 320px;
}

.records-card {
  flex: 1;
  overflow: hidden;
  min-height: 150px;
}

.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.right-panel .right-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.left-card, .right-card {
  border-radius: 8px;
  box-sizing: border-box;
}

.left-card :deep(.el-card__body),
.right-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  font-weight: 600;
}

.card-header span {
  display: flex;
  align-items: center;
  gap: 6px;
}

.card-header-responsive {
  flex-wrap: wrap;
  gap: 8px;
}

.file-name {
  flex: 1;
  min-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-btns {
  display: flex;
  gap: 4px;
}

.upload-area {
  flex: 0 0 auto;
  margin-bottom: 12px;
}

.upload-area :deep(.el-upload-dragger) {
  padding: 20px 10px;
  border-radius: 8px;
}

.upload-icon {
  font-size: 32px;
  color: #409eff;
  margin-bottom: 8px;
}

.upload-text {
  font-size: 13px;
}

.upload-text em {
  color: #409eff;
  font-style: normal;
}

.upload-tip {
  font-size: 11px;
  margin-top: 6px;
}

.upload-btn {
  width: 100%;
}

.records-card :deep(.el-card__body) {
  padding: 0;
  max-height: 100%;
  overflow: hidden;
}

.records-list {
  max-height: 100%;
  overflow-y: auto;
}

.record-item {
  padding: 10px 12px;
  border-bottom: 1px solid #ebeef5;
  cursor: pointer;
  transition: all 0.2s;
}

.record-item:hover {
  background-color: #f5f7fa;
}

.record-item.active {
  background-color: #ecf5ff;
  border-left: 3px solid #409eff;
  padding-left: 9px;
}

.record-name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  margin-bottom: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.record-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.record-time {
  font-size: 11px;
  color: #909399;
}

.file-info {
  margin-bottom: 12px;
}

.data-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  margin-top: 12px;
}

.data-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow: hidden;
}

.data-tabs :deep(.el-tab-pane) {
  height: 100%;
  overflow-y: auto;
}

.tables-list {
  height: 100%;
  overflow: auto;
}

.dataset-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 4px;
}

.dataset-count {
  color: #909399;
  font-size: 13px;
}

.simulation-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.simulation-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 4px;
}

.simulation-tip {
  color: #909399;
  font-size: 12px;
  margin-left: 8px;
}

.simulation-data {
  flex: 1;
  overflow: auto;
}

.anomaly-value {
  color: #f56c6c;
  font-weight: bold;
}

.analysis-result {
  flex: 1;
  height: auto;
  min-height: 200px;
  overflow-y: auto;
  padding: 16px;
  background: #fff;
  border-radius: 6px;
  font-size: 14px;
  text-align: left;
}

.analysis-info {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}

.analysis-result :deep(.md-h1) {
  font-size: 18px;
  margin: 16px 0 12px;
  padding-bottom: 8px;
  border-bottom: 2px solid #409eff;
  text-align: left;
}

.analysis-result :deep(.md-h2) {
  font-size: 16px;
  color: #303133;
  margin: 14px 0 10px;
  padding-left: 10px;
  border-left: 4px solid #67c23a;
  text-align: left;
}

.analysis-result :deep(.md-h3) {
  font-size: 15px;
  color: #409eff;
  margin: 12px 0 8px;
  text-align: left;
}

.analysis-result :deep(.md-p),
.analysis-result :deep(.md-li) {
  line-height: 1.8;
  color: #606266;
  margin: 8px 0;
  text-align: left;
}

.analysis-result :deep(strong) {
  color: #e6a23c;
}

.analysis-result :deep(.md-code) {
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 13px;
}

.analysis-result :deep(em) {
  color: #909399;
  font-style: italic;
}

.analysis-result :deep(.md-li.md-ol) {
  padding-left: 8px;
  margin-left: 0;
  list-style-type: none;
  position: relative;
  padding-left: 24px;
}

.analysis-result :deep(.md-li.md-ol)::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  width: 18px;
  height: 100%;
  background: linear-gradient(135deg, #409eff 0%, #67c23a 100%);
  border-radius: 3px;
  opacity: 0.15;
}

.analysis-result :deep(.md-li.md-ol)::after {
  content: attr(data-num);
  position: absolute;
  left: 6px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 12px;
  font-weight: 600;
  color: #409eff;
}

.empty-card {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

@media (max-width: 768px) {
  .header-title h1 {
    font-size: 14px;
  }
  
  .main-content {
    padding: 8px;
  }
  
  .file-name {
    font-size: 13px;
  }
}

.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  pointer-events: auto;
}

.loading-spinner {
  background: rgba(255, 255, 255, 0.95);
  padding: 32px 48px;
  border-radius: 16px;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.15);
  text-align: center;
  max-width: 360px;
}

.loading-spinner .el-icon {
  color: #409eff;
  animation: spin 1.5s linear infinite;
}

.loading-text {
  margin-top: 16px;
  font-size: 15px;
  color: #303133;
  font-weight: 500;
}

.loading-subtext {
  margin-top: 8px;
  font-size: 13px;
  color: #909399;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
