import axios from 'axios';
import { ElMessage } from 'element-plus';
import router from '../router'; // 必须引入 router

const service = axios.create({
  baseURL: '/api',
  timeout: 60000
});

// 请求拦截器
service.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器：处理 Token 失效或用户被删的情况
service.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const status = error.response.status;
      const detail = error.response.data?.detail;

      // 如果返回 401(Token错误) 或 404(用户不存在)
      if (status === 401 || (status === 404 && detail === "用户不存在")) {
        ElMessage.error(detail || '身份验证失效，请重新登录');
        localStorage.removeItem('access_token'); // 清理脏数据
        router.push('/login'); // 强制回登录页
      } else {
        ElMessage.error(detail || '系统繁忙');
      }
    }
    return Promise.reject(error);
  }
);

export default service;