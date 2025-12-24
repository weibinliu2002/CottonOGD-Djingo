import httpInstance from '@/utils/http'
// 测试API
export const testAPI = () => {
  return httpInstance({
    url: '/test',
    method: 'get',
  })
}