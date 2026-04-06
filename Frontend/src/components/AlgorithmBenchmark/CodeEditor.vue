<template>
  <div class="code-editor-container">
    <div class="editor-header">
      <select v-model="selectedTemplate" @change="onTemplateChange" class="template-select">
        <option value="">選擇模板...</option>
        <option v-for="template in templates" :key="template.name" :value="template.name">
          {{ template.display_name }}
        </option>
      </select>
      
      <button @click="handleValidate" :disabled="validating || !code.trim()" class="btn btn-validate">
        {{ validating ? '驗證中...' : '驗證' }}
      </button>
      
      <button @click="handleExecute" :disabled="executing || !code.trim()" class="btn btn-execute">
        {{ executing ? '執行中...' : '執行' }}
      </button>
    </div>
    
    <div class="editor-wrapper">
      <PathPreview2D
        v-if="hasPreviewData"
        class="inline-preview"
        :path="executionResult.path"
        :positions="executionResult.positions"
      />
      <textarea
        v-else
        v-model="code"
        class="code-textarea"
        placeholder="請選擇模板或開始編寫程式碼..."
        spellcheck="false"
      ></textarea>
    </div>
    
    <div v-if="validationResult" class="result-panel validation-result">
      <div v-if="validationResult.valid" class="success">
        <strong>✓ 程式碼驗證通過</strong>
        <div v-if="validationResult.warnings.length > 0" class="warnings">
          <div v-for="(warning, index) in validationResult.warnings" :key="index" class="warning-item">
            ⚠ {{ warning }}
          </div>
        </div>
      </div>
      <div v-else class="error">
        <strong>✗ 程式碼驗證失敗</strong>
        <div v-for="(err, index) in validationResult.errors" :key="index" class="error-item">
          {{ err }}
        </div>
        <div v-if="validationResult.forbidden_operations.length > 0" class="forbidden-ops">
          <div v-for="(op, index) in validationResult.forbidden_operations" :key="index" class="forbidden-item">
            🚫 {{ op }}
          </div>
        </div>
      </div>
    </div>
    
    <div v-if="executionResult" class="result-panel execution-result">
      <div v-if="executionResult.success" class="success">
        <h3>✓ 執行成功</h3>
        <div class="result-details">
          <p><strong>步數:</strong> {{ executionResult.step_count }}</p>
          <p><strong>路徑:</strong> {{ executionResult.path.join(' → ') }}</p>
          <p><strong>執行時間:</strong> {{ executionResult.execution_time_ms.toFixed(2) }} ms</p>
        </div>
      </div>
      <div v-else class="error">
        <h3>✗ 執行失敗</h3>
        <p><strong>{{ executionResult.error_type }}:</strong> {{ executionResult.error_message }}</p>
        <p v-if="executionResult.line_number">行號: {{ executionResult.line_number }}</p>
      </div>
    </div>
  </div>
</template>

<script>
import { computed, ref, onMounted } from 'vue'
import { useCodeEditor } from '../../composables/useCodeEditor'
import PathPreview2D from './PathPreview2D.vue'

export default {
  name: 'CodeEditor',
  components: {
    PathPreview2D
  },
  props: {
    testOrder: {
      type: Object,
      default: () => ({ items: [75, 12, 43] })
    }
  },
  emits: ['execution-success'],
  setup(props, { emit }) {
    const code = ref('')
    const selectedTemplate = ref('')
    const templates = ref([])
    const validating = ref(false)
    const executing = ref(false)
    const validationResult = ref(null)
    const executionResult = ref(null)
    const hasPreviewData = computed(() => {
      return Boolean(
        executionResult.value?.success &&
        executionResult.value?.path?.length > 0 &&
        executionResult.value?.positions?.length > 0
      )
    })
    
    const {
      loadTemplates,
      loadTemplate,
      validateCode,
      executeCode,
      loading,
      error
    } = useCodeEditor()
    
    onMounted(async () => {
      templates.value = await loadTemplates()
    })
    
    const onTemplateChange = async () => {
      if (!selectedTemplate.value) {
        code.value = ''
        return
      }
      
      const template = await loadTemplate(selectedTemplate.value)
      if (template) {
        code.value = template.code
        validationResult.value = null
        executionResult.value = null
      }
    }
    
    const handleValidate = async () => {
      validating.value = true
      validationResult.value = null
      executionResult.value = null
      
      try {
        const result = await validateCode(code.value)
        validationResult.value = result
      } finally {
        validating.value = false
      }
    }
    
    const handleExecute = async () => {
      executing.value = true
      executionResult.value = null
      
      try {
        const result = await executeCode(code.value, props.testOrder, 5)
        executionResult.value = result
        
        if (result.success) {
          emit('execution-success', result)
        }
      } finally {
        executing.value = false
      }
    }
    
    return {
      code,
      selectedTemplate,
      templates,
      validating,
      executing,
      validationResult,
      executionResult,
      hasPreviewData,
      onTemplateChange,
      handleValidate,
      handleExecute,
      loading,
      error
    }
  }
}
</script>

<style scoped>
.code-editor-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #1e1e1e;
  border-radius: 8px;
  overflow: hidden;
}

.editor-header {
  display: flex;
  gap: 10px;
  padding: 12px;
  background: #2d2d2d;
  border-bottom: 1px solid #3e3e3e;
}

.template-select {
  flex: 1;
  padding: 8px 12px;
  background: #3e3e3e;
  color: #d4d4d4;
  border: 1px solid #555;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
}

.template-select:focus {
  outline: none;
  border-color: #007acc;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-validate {
  background: #0e639c;
  color: white;
}

.btn-validate:hover:not(:disabled) {
  background: #1177bb;
}

.btn-execute {
  background: #16825d;
  color: white;
}

.btn-execute:hover:not(:disabled) {
  background: #1a9870;
}

.editor-wrapper {
  flex: 1;
  overflow: hidden;
}

.inline-preview {
  margin-top: 0;
  height: 100%;
  box-sizing: border-box;
}

.code-textarea {
  width: 100%;
  height: 100%;
  padding: 16px;
  background: #1e1e1e;
  color: #d4d4d4;
  border: none;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.6;
  resize: none;
  outline: none;
}

.result-panel {
  padding: 16px;
  margin: 12px;
  border-radius: 6px;
  font-size: 14px;
}

.validation-result.success {
  background: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.validation-result.error {
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.execution-result .success {
  background: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
  padding: 16px;
  border-radius: 6px;
}

.execution-result .error {
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
  padding: 16px;
  border-radius: 6px;
}

.result-details {
  margin-top: 12px;
}

.result-details p {
  margin: 6px 0;
}

.error-item,
.warning-item,
.forbidden-item {
  margin: 6px 0;
  padding: 4px 0;
}

.warnings {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #c3e6cb;
}

.forbidden-ops {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f5c6cb;
}

h3 {
  margin: 0 0 12px 0;
  font-size: 16px;
}
</style>
