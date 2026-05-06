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
  (response) => response.data,
  (err) => {
    console.error("API Error:", err.message);
    return Promise.reject(err);
  },
);

export default request;
