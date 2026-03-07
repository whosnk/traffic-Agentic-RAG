// src/api/request.ts

import axios from 'axios';
import { ElMessage } from 'element-plus';
// 删除这一行：import router from '../router';  <-- 它是导致报错的罪魁祸首
import { API_BASE_URL } from './config';

const service = axios.create({
  baseURL: API_BASE_URL, 
  timeout: 60000
});

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

service.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const status = error.response.status;
      const detail = error.response.data?.detail;

      if (status === 401 || (status === 404 && detail === "用户不存在")) {
        ElMessage.error(detail || '身份验证失效，请重新登录');
        localStorage.removeItem('access_token');
        
        // --- 核心修复 ---
        // 使用原生跳转代替 router.push，打破循环引用依赖
        // 虽然会导致页面刷新，但能保证系统绝对稳定
        window.location.href = '/login'; 
        
      } else {
        ElMessage.error(detail || '系统繁忙，请稍后再试');
      }
    } else {
      // 处理网络断网等情况
      ElMessage.error('网络连接异常，请检查网络');
    }
    return Promise.reject(error);
  }
);

export default service;