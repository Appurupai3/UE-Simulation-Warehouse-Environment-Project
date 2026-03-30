import { ref } from 'vue'

export function useCodeEditor() {
  const templates = ref([])
  const loading = ref(false)
  const error = ref(null)

  const API_BASE = 'http://localhost:8000/api'

  /**
   * 載入所有模板列表
   */
  const loadTemplates = async () => {
    loading.value = true
    error.value = null
    
    try {
      const response = await fetch(`${API_BASE}/algorithms/templates`)
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      templates.value = await response.json()
      return templates.value
    } catch (err) {
      error.value = `載入模板失敗: ${err.message}`
      console.error('載入模板失敗:', err)
      return []
    } finally {
      loading.value = false
    }
  }

  /**
   * 載入特定模板
   * @param {string} name - 模板名稱
   */
  const loadTemplate = async (name) => {
    loading.value = true
    error.value = null
    
    try {
      const response = await fetch(`${API_BASE}/algorithms/templates/${name}`)
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const template = await response.json()
      return template
    } catch (err) {
      error.value = `載入模板失敗: ${err.message}`
      console.error('載入模板失敗:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * 驗證程式碼
   * @param {string} code - 程式碼字串
   */
  const validateCode = async (code) => {
    loading.value = true
    error.value = null
    
    try {
      const response = await fetch(`${API_BASE}/algorithms/validate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code }),
      })
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const result = await response.json()
      return result
    } catch (err) {
      error.value = `驗證失敗: ${err.message}`
      console.error('驗證失敗:', err)
      return {
        valid: false,
        errors: [err.message],
        warnings: [],
        forbidden_operations: []
      }
    } finally {
      loading.value = false
    }
  }

  /**
   * 執行程式碼
   * @param {string} code - 程式碼字串
   * @param {Object} order - 訂單物件 { items: [75, 12, 43] }
   * @param {number} timeout - 超時時間（秒）
   */
  const executeCode = async (code, order, timeout = 5) => {
    loading.value = true
    error.value = null
    
    try {
      const response = await fetch(`${API_BASE}/algorithms/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          code,
          order,
          timeout
        }),
      })
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const result = await response.json()
      return result
    } catch (err) {
      error.value = `執行失敗: ${err.message}`
      console.error('執行失敗:', err)
      return {
        success: false,
        error_message: err.message,
        error_type: 'NetworkError'
      }
    } finally {
      loading.value = false
    }
  }

  return {
    templates,
    loading,
    error,
    loadTemplates,
    loadTemplate,
    validateCode,
    executeCode
  }
}
