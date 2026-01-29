
import { ref, type Ref } from 'vue'
import httpInstance from '@/utils/http'

interface UseAsyncTaskOptions {
  initialData?: any;
  pollInterval?: number;
  useFormData?: boolean;
}

interface UseAsyncTaskReturn {
  data: Ref<any>;
  loading: Ref<boolean>;
  error: Ref<string | null>;
  execute: (payload?: any) => Promise<string | null>;
  poll: (taskId: string, pollParams?: Record<string, any>) => Promise<void>;
}

interface ApiResponse {
  status: string;
  task_id?: string;
  result?: any;
  error?: string;
}

/**
 * A composable for handling long-running asynchronous tasks with polling.
 * @param startEndpoint - The API endpoint to start the task.
 * @param resultEndpoint - The API endpoint to poll for results, with `:taskId` placeholder.
 * @param options - Configuration options.
 */
export function useAsyncTask(startEndpoint: string, resultEndpoint: string, options: UseAsyncTaskOptions = {}): UseAsyncTaskReturn {
  const { initialData = null, pollInterval = 5000, useFormData = false } = options

  const data = ref<any>(initialData)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const poll = async (taskId: string, pollParams?: Record<string, any>) => {
    loading.value = true
    error.value = null

    try {
      const url = resultEndpoint.replace(':taskId', taskId)
      const response = await httpInstance.get(url, { params: pollParams })
      
      // 处理响应数据 - 检查是否已经通过拦截器处理
      const responseData = response as unknown as ApiResponse

      if (responseData.status === 'SUCCESS') {
        // Handle both stringified JSON and direct JSON objects
        if (typeof responseData.result === 'string') {
          try {
            data.value = JSON.parse(responseData.result)
          } catch (e) {
            throw new Error('Failed to parse result JSON string.')
          }
        } else {
          data.value = responseData.result
        }
        loading.value = false
      } else if (responseData.status === 'PENDING') {
        setTimeout(() => poll(taskId, pollParams), pollInterval)
      } else {
        throw new Error(responseData.error || `Task failed with status: ${responseData.status}`)
      }
    } catch (err: any) {
      error.value = `Failed to fetch results: ${err.message}`
      loading.value = false
      console.error(err)
    }
  }

  const execute = async (payload: any) => {
    loading.value = true
    error.value = null
    data.value = initialData

    try {
      let response
      if (useFormData) {
        const formData = new FormData()
        for (const key in payload) {
          if (Object.prototype.hasOwnProperty.call(payload, key)) {
            const value = payload[key]
            if (Array.isArray(value)) {
              value.forEach(item => formData.append(key, item))
            } else {
              formData.append(key, value)
            }
          }
        }
        response = await httpInstance.post(startEndpoint, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        })
      } else {
        response = await httpInstance.post(startEndpoint, payload)
      }

      // 处理响应数据 - 检查是否已经通过拦截器处理
      const responseData = response as unknown as ApiResponse

      if (responseData.status === 'success' && responseData.task_id) {
        return responseData.task_id
      } else {
        throw new Error(responseData.error || 'Failed to start the task.')
      }
    } catch (err: any) {
      error.value = `Failed to execute task: ${err.message}`
      loading.value = false // Stop loading on execution failure
      console.error(err)
      return null
    }
  }

  return {
    data,
    loading,
    error,
    execute,
    poll,
  } as UseAsyncTaskReturn
}
