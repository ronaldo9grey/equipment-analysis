<template>
  <div class="app-container">
    <el-container>
      <el-header class="header">
        <div class="header-content">
          <h1>设备运行数据分析系统</h1>
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

      <el-main>
        <div class="main-content">
          <el-row :gutter="20">
            <el-col :span="8">
              <el-card class="upload-card">
                <template #header>
                  <div class="card-header">
                    <span>上传数据文件</span>
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
                  <el-icon class="el-icon--upload"><upload-filled /></el-icon>
                  <div class="el-upload__text">
                    拖拽文件到此处或<em>点击上传</em>
                  </div>
                  <template #tip>
                    <div class="el-upload__tip">
                      支持 MDB、ACCDB、SQL、BAK 文件，最大 50MB
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

              <el-card class="records-card" v-if="records.length > 0">
                <template #header>
                  <div class="card-header">
                    <span>历史记录</span>
                    <el-button text @click="loadRecords">刷新</el-button>
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
                    <div class="record-name">{{ record.file_name }}</div>
                    <div class="record-info">
                      <el-tag size="small" :type="getStatusType(record.status)">
                        {{ getStatusText(record.status) }}
                      </el-tag>
                      <span class="record-time">{{ formatTime(record.created_at) }}</span>
                    </div>
                  </div>
                </div>
              </el-card>
            </el-col>

            <el-col :span="16">
              <el-card class="result-card" v-if="selectedRecord">
                <template #header>
                  <div class="card-header">
                    <span>数据详情 - {{ selectedRecord.file_name }}</span>
                    <div class="header-btns">
                      <el-button
                        type="primary"
                        :loading="analyzing"
                        :disabled="selectedRecord.status !== 'completed' && selectedRecord.status !== 'analyzed'"
                        @click="handleAnalyze"
                      >
                        {{ analyzing ? '分析中...' : 'AI智能分析' }}
                      </el-button>
                      <el-button
                        type="danger"
                        text
                        @click="handleDelete"
                      >
                        删除
                      </el-button>
                    </div>
                  </div>
                </template>

                <div class="file-info">
                  <el-descriptions :column="4" border>
                    <el-descriptions-item label="文件大小">{{ formatSize(selectedRecord.file_size) }}</el-descriptions-item>
                    <el-descriptions-item label="文件类型">{{ selectedRecord.file_type }}</el-descriptions-item>
                    <el-descriptions-item label="数据表数">{{ selectedRecord.table_count }}</el-descriptions-item>
                    <el-descriptions-item label="总记录数">{{ selectedRecord.record_count }}</el-descriptions-item>
                  </el-descriptions>
                </div>

                <el-tabs v-model="activeTab" class="data-tabs">
                  <el-tab-pane label="数据表" name="tables">
                    <div class="tables-list">
                      <el-table :data="tables" stripe>
                        <el-table-column prop="table_name" label="表名" />
                        <el-table-column prop="columns" label="字段数">
                          <template #default="{ row }">
                            {{ row.columns?.length || 0 }}
                          </template>
                        </el-table-column>
                        <el-table-column prop="row_count" label="记录数" />
                        <el-table-column label="操作">
                          <template #default="{ row }">
                            <el-button type="primary" link @click.stop="viewTableData(row)">
                              查看数据
                            </el-button>
                          </template>
                        </el-table-column>
                      </el-table>
                    </div>
                  </el-tab-pane>

                  <el-tab-pane label="AI分析结果" name="analysis">
                    <div class="analysis-result" v-if="selectedRecord.analysis_result?.content">
                      <pre>{{ selectedRecord.analysis_result.content }}</pre>
                    </div>
                    <el-empty v-else description="暂无分析结果，请点击右上角按钮进行分析" />
                  </el-tab-pane>
                </el-tabs>
              </el-card>

              <el-card v-else class="empty-card">
                <el-empty description="请先上传数据文件或选择历史记录">
                  <template #image>
                    <el-icon :size="80" color="#909399"><data-analysis /></el-icon>
                  </template>
                </el-empty>
              </el-card>
            </el-col>
          </el-row>
        </div>
      </el-main>
    </el-container>

    <el-dialog v-model="tableDialogVisible" :title="currentTable?.table_name" width="90%">
      <el-table :data="tableData" stripe max-height="500" v-if="tableData.length > 0">
        <el-table-column
          v-for="col in currentTableColumns"
          :key="col"
          :prop="col"
          :label="col"
          min-width="120"
        />
      </el-table>
      <el-pagination
        v-if="tablePagination.total > 0"
        v-model:current-page="tablePagination.page"
        v-model:page-size="tablePagination.pageSize"
        :total="tablePagination.total"
        layout="total, prev, pager, next"
        @current-change="loadTableData"
      />
      <el-empty v-else description="暂无数据" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled, DataAnalysis } from '@element-plus/icons-vue'
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

onMounted(() => {
  loadRecords()
})
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  background-color: #f5f7fa;
}

.header {
  background: linear-gradient(135deg, #409eff 0%, #67c23a 100%);
  color: white;
  padding: 0 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
}

.header-content h1 {
  margin: 0;
  font-size: 24px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 20px;
}

.main-content {
  padding: 20px;
}

.upload-card, .records-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.upload-area {
  margin-bottom: 20px;
}

.upload-btn {
  width: 100%;
}

.records-list {
  max-height: 400px;
  overflow-y: auto;
}

.record-item {
  padding: 12px;
  border-bottom: 1px solid #ebeef5;
  cursor: pointer;
  transition: all 0.3s;
}

.record-item:hover {
  background-color: #f5f7fa;
}

.record-item.active {
  background-color: #ecf5ff;
  border-left: 3px solid #409eff;
}

.record-name {
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

.result-card {
  min-height: 600px;
}

.header-btns {
  display: flex;
  gap: 10px;
}

.file-info {
  margin-bottom: 20px;
}

.data-tabs {
  margin-top: 20px;
}

.analysis-result {
  padding: 20px;
  background-color: #f5f7fa;
  border-radius: 4px;
  min-height: 300px;
  white-space: pre-wrap;
  line-height: 1.8;
}

.empty-card {
  min-height: 500px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.tables-list {
  max-height: 400px;
  overflow-y: auto;
}
</style>
