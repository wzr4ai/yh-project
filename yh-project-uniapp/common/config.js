// 环境配置：优先取构建时注入的环境变量，其次退回本地默认
// 在 HBuilderX 中可通过 manifest -> vue3 环境变量 或 CLI 构建时注入 UNI_APP_API_BASE_URL / VITE_API_BASE_URL
const runtimeEnv =
  (typeof process !== 'undefined' && process.env) ||
  (typeof import.meta !== 'undefined' && import.meta.env) ||
  {}

export const API_BASE_URL =
  runtimeEnv.UNI_APP_API_BASE_URL ||
  runtimeEnv.VITE_API_BASE_URL ||
  'http://localhost:8000'
