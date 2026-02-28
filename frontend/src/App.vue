<template>
  <div class="app-container">
    <el-container>
      <el-header class="header">
        <div class="header-content">
          <div class="header-title">
            <el-icon class="header-icon"><DataAnalysis /></el-icon>
            <h1>设备运行数据分析系统</h1>
          </div>
          <div class="header-actions">
            <el-switch
              v-model="useLocalModel"
              active-text="本地模型"
              inactive-text="DeepSeek"
              @change="handleModelChange"
            />
          </div>
        </div>
      </el-header>

      <el-main class="main-content">
        <el-row :gutter="20" class="content-row">
          <el-col :span="8">
            <el-card class="left-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span><el-icon><UploadFilled /></el-icon> 上传数据文件</span>
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
                  拖拽文件到此处或<em>点击上传</em>
                </div>
                <template #tip>
                  <div class="upload-tip">
                    支持 MDB、ACCDB、SQL、BAK 文件
                  </div>
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
                    {{ record.file_name }}
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
          </el-col>

          <el-col :span="16">
            <el-card class="right-card" shadow="hover" v-if="selectedRecord">
              <template #header>
                <div class="card-header">
                  <span>
                    <el-icon><Folder /></el-icon> 
                    数据详情 - {{ selectedRecord.file_name }}
                  </span>
                  <div class="header-btns">
                    <el-button
                      type="primary"
                      :loading="analyzing"
                      :disabled="selectedRecord.status !== 'completed' && selectedRecord.status !== 'analyzed'"
                      @click="handleAnalyze"
                    >
                      <el-icon><MagicStick /></el-icon>
                      {{ analyzing ? '分析中...' : 'AI智能分析' }}
                    </el-button>
                    <el-button type="danger" text @click="handleDelete">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </div>
                </div>
              </template>

              <div class="file-info">
                <el-descriptions :column="4" border>
                  <el-descriptions-item label="文件大小">
                    <el-icon><Files /></el-icon> {{ formatSize(selectedRecord.file_size) }}
                  </el-descriptions-item>
                  <el-descriptions-item label="文件类型">
                    <el-tag size="small">{{ selectedRecord.file_type?.toUpperCase() }}</el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="数据表数">
                    <el-tag type="info">{{ selectedRecord.table_count }} 个</el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="总记录数">
                    <el-tag type="success">{{ selectedRecord.record_count }} 条</el-tag>
                  </el-descriptions-item>
                </el-descriptions>
              </div>

              <el-tabs v-model="activeTab" class="data-tabs">
                <el-tab-pane label="数据表" name="tables">
                  <div class="tables-list">
                    <el-table :data="tables" stripe height="100%">
                      <el-table-column prop="table_name" label="表名" min-width="150">
                        <template #default="{ row }">
                          <el-icon><Grid /></el-icon> {{ row.table_name }}
                        </template>
                      </el-table-column>
                      <el-table-column prop="columns" label="字段数" width="100">
                        <template #default="{ row }">
                          <el-tag size="small" type="info">{{ row.columns?.length || 0 }}</el-tag>
                        </template>
                      </el-table-column>
                      <el-table-column prop="row_count" label="记录数" width="100">
                        <template #default="{ row }">
                          <el-tag size="small" type="success">{{ row.row_count }}</el-tag>
                        </template>
                      </el-table-column>
                      <el-table-column label="操作" width="120">
                        <template #default="{ row }">
                          <el-button type="primary" link @click.stop="viewTableData(row)">
                            <el-icon><View /></el-icon> 查看
                          </el-button>
                        </template>
                      </el-table-column>
                    </el-table>
                  </div>
                </el-tab-pane>

                <el-tab-pane label="AI分析结果" name="analysis">
                  <div class="analysis-result" v-if="selectedRecord.analysis_result?.content" v-html="renderMarkdown(selectedRecord.analysis_result.content)">
                  </div>
                  <el-empty v-else description="暂无分析结果，请点击右上角按钮进行分析">
                    <template #image>
                      <el-icon :size="60" color="#909399"><MagicStick /></el-icon>
                    </template>
                  </el-empty>
                </el-tab-pane>
              </el-tabs>
            </el-card>

            <el-card v-else class="empty-card" shadow="hover">
              <el-empty description="请先上传数据文件或选择历史记录">
                <template #image>
                  <el-icon :size="100" color="#dcdfe6"><DataLine /></el-icon>
                </template>
              </el-empty>
            </el-card>
          </el-col>
        </el-row>
      </el-main>
    </el-container>

    <el-dialog v-model="tableDialogVisible" :title="currentTable?.table_name" width="90%" top="5vh">
      <el-table :data="tableData" stripe height="60vh" v-if="tableData.length > 0">
        <el-table-column
          v-for="col in currentTableColumns"
          :key="col"
          :prop="col"
          :label="col"
          min-width="150"
          show-overflow-tooltip
        />
      </el-table>
      <el-pagination
        v-if="tablePagination.total > 0"
        v-model:current-page="tablePagination.page"
        v-model:page-size="tablePagination.pageSize"
        :total="tablePagination.total"
        layout="total, sizes, prev, pager, next, jumper"
        :page-sizes="[50, 100, 200]"
        @current-change="loadTableData"
        @size-change="loadTableData"
      />
      <el-empty v-else description="暂无数据" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  UploadFilled, 
  DataAnalysis, 
  Document, 
  Refresh, 
  Delete, 
  MagicStick, 
  Files, 
  Grid, 
  View,
  Folder,
  DataLine
} from '@element-plus/icons-vue'
import { equipmentApi, type AnalysisRecord, type TableInfo } from './api/equipment'

const uploadUrl = '/api/v1/upload'
const acceptTypes = '.mdb,.accdb,.sql,.bak,.mysql'

const selectedFile = ref<File | null>(null)
const uploading = ref(false)
const analyzing = ref(false)
const useLocalModel = ref(false)
const records = ref<AnalysisRecord[]>([])
const selectedRecord = ref<AnalysisRecord | null>(null)
const tables = ref<TableInfo[]>([])
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

const handleUploadSuccess = () => {
  ElMessage.success('上传成功')
}

const handleUploadError = (error: any) => {
  ElMessage.error(error.message || '上传失败')
}

const loadRecords = async () => {
  try {
    records.value = await equipmentApi.getRecords(0, 20)
  } catch (error) {
    console.error('加载记录失败:', error)
  }
}

const selectRecord = async (record: AnalysisRecord) => {
  selectedRecord.value = record
  if (record.status === 'completed' || record.status === 'analyzed') {
    await loadTables(record.id)
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

  console.log('分析按钮点击', selectedRecord.value.id, selectedRecord.value.status)
  analyzing.value = true
  try {
    const result = await equipmentApi.analyzeData(
      selectedRecord.value.id,
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
  return new Date(time).toLocaleString('zh-CN')
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
  html = html.replace(/^(\d+)\. (.*$)/gim, '<li class="md-li">$2</li>')
  
  html = html.replace(/`([^`]+)`/g, '<code class="md-code">$1</code>')
  
  html = html.replace(/\n\n/g, '</p><p class="md-p">')
  html = '<p class="md-p">' + html + '</p>'
  
  html = html.replace(/<p class="md-p"><\/p>/g, '')
  html = html.replace(/<p class="md-p"><h/g, '<h')
  html = html.replace(/<\/h\d><\/p>/g, '</h2>')
  html = html.replace(/<p class="md-p"><li/g, '<li')
  html = html.replace(/<\/li><\/p>/g, '</li>')
  
  return html
}

onMounted(() => {
  loadRecords()
})
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e7ed 100%);
}

.header {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  color: white;
  padding: 0 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
  max-width: 1600px;
  margin: 0 auto;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-icon {
  font-size: 28px;
  color: #409eff;
}

.header-title h1 {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
  background: linear-gradient(90deg, #fff 0%, #409eff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.header-actions {
  display: flex;
  align-items: center;
}

.main-content {
  padding: 20px;
  max-width: 1600px;
  margin: 0 auto;
}

.content-row {
  height: calc(100vh - 80px);
}

.left-card, .right-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.left-card :deep(.el-card__body),
.right-card :deep(.el-card__body) {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  color: #303133;
}

.card-header span {
  display: flex;
  align-items: center;
  gap: 8px;
}

.upload-area {
  flex: 0 0 auto;
  margin-bottom: 16px;
}

.upload-area :deep(.el-upload-dragger) {
  padding: 40px 20px;
  border-radius: 12px;
  border: 2px dashed #dcdfe6;
  background: #fafafa;
  transition: all 0.3s;
}

.upload-area :deep(.el-upload-dragger:hover) {
  border-color: #409eff;
  background: #ecf5ff;
}

.upload-icon {
  font-size: 48px;
  color: #409eff;
  margin-bottom: 12px;
}

.upload-text {
  color: #606266;
  font-size: 14px;
}

.upload-text em {
  color: #409eff;
  font-style: normal;
}

.upload-tip {
  color: #909399;
  font-size: 12px;
  margin-top: 8px;
}

.upload-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
  border-radius: 8px;
}

.records-card {
  flex: 1;
  margin-top: 16px;
  overflow: hidden;
}

.records-card :deep(.el-card__body) {
  padding: 0;
  max-height: calc(100% - 55px);
}

.records-list {
  max-height: 400px;
  overflow-y: auto;
}

.record-item {
  padding: 14px 16px;
  border-bottom: 1px solid #ebeef5;
  cursor: pointer;
  transition: all 0.3s;
}

.record-item:hover {
  background-color: #f5f7fa;
}

.record-item.active {
  background-color: #ecf5ff;
  border-left: 4px solid #409eff;
  padding-left: 12px;
}

.record-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #303133;
  margin-bottom: 8px;
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
  font-size: 12px;
  color: #909399;
}

.header-btns {
  display: flex;
  gap: 8px;
}

.file-info {
  margin-bottom: 16px;
}

.file-info :deep(.el-descriptions__label) {
  font-weight: 500;
  background: #fafafa;
}

.data-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.data-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow: hidden;
}

.data-tabs :deep(.el-tab-pane) {
  height: 100%;
  overflow: hidden;
}

.tables-list {
  height: 100%;
  overflow: auto;
}

.analysis-result {
  height: 100%;
  overflow-y: auto;
  padding: 20px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}

.analysis-result :deep(.md-h1) {
  font-size: 24px;
  color: #1a1a2e;
  margin: 20px 0 16px;
  padding-bottom: 8px;
  border-bottom: 2px solid #409eff;
}

.analysis-result :deep(.md-h2) {
  font-size: 20px;
  color: #303133;
  margin: 18px 0 14px;
  padding-left: 12px;
  border-left: 4px solid #67c23a;
}

.analysis-result :deep(.md-h3) {
  font-size: 16px;
  color: #409eff;
  margin: 14px 0 10px;
}

.analysis-result :deep(.md-p) {
  line-height: 1.8;
  color: #606266;
  margin: 8px 0;
}

.analysis-result :deep(.md-li) {
  line-height: 1.8;
  color: #606266;
  margin: 4px 0;
  padding-left: 8px;
}

.analysis-result :deep(strong) {
  color: #e6a23c;
  font-weight: 600;
}

.analysis-result :deep(.md-code) {
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 13px;
  color: #c7254e;
}

.empty-card {
  height: calc(100vh - 140px);
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border-radius: 12px;
}

:deep(.el-dialog) {
  border-radius: 12px;
}

:deep(.el-dialog__header) {
  border-bottom: 1px solid #ebeef5;
  padding: 16px 20px;
}

:deep(.el-dialog__body) {
  padding: 20px;
}
</style>
