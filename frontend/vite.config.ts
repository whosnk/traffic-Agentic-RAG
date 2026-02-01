import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      // 凡是接口中包含 /api 的请求，都转发到 8000 端口
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        // 关键点：后端接口已经是 /api 开头的，所以这里不需要 rewrite 掉 /api
        // 如果后端接口没有 /api 前缀，才需要 rewrite
        // rewrite: (path) => path.replace(/^\/api/, '') 
      }
    }
  }
})