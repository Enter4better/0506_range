import axios from "axios";
import router from "@/router";
import { ElMessage } from "element-plus";

const request = axios.create({
  baseURL: "/api",
  timeout: 60000,
  headers: { "Content-Type": "application/json" },
});

// 请求拦截器 - 只在有token时添加认证头
request.interceptors.request.use(
  (config) => {
    // 只添加有效的token
    const token = localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// 响应拦截器
request.interceptors.response.use(
  (response) => {
    // 如果是blob响应，直接返回原始response
    if (response.config.responseType === "blob") {
      return response;
    }
    return response.data;
  },
  (err) => {
    // 处理 401 认证失败 - token过期或无效
    if (err.response?.status === 401) {
      console.warn("认证失败，正在清除登录状态...");
      localStorage.removeItem('cyber_user');
      localStorage.removeItem('token');
      localStorage.removeItem('cyber_remember');
      ElMessage.warning("登录已过期，请重新登录");
      router.push('/login');
      return Promise.reject(err);
    }
    console.error("API Error:", err.message);
    return Promise.reject(err);
  },
);

export default request;
