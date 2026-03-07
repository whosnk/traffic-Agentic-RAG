// src/api/config.ts

// import.meta.env.DEV 是 Vite 提供的环境变量
// 运行 npm run dev 时为 true，npm run build 时为 false

// 1. API 请求的基础路径
export const API_BASE_URL = import.meta.env.DEV 
  ? '/api' // 开发环境：继续走 vite.config.ts 的代理
  : 'https://ragqa.asmi1e.us.ci/api'; // 打包环境：直接写死你的公网域名 (如果你只想用局域网，可以写 http://192.168.1.6:8000/api)

// 2. 静态资源（头像）的基础路径
export const STATIC_BASE_URL = import.meta.env.DEV 
  ? window.location.origin // 开发环境：用当前浏览器地址
  : 'https://ragqa.asmi1e.us.ci'; // 打包环境：直接用后端公网地址