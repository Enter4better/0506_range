import { createRouter, createWebHistory } from "vue-router";
import {
  House,
  Aim,
  Umbrella,
  Connection,
  Document,
  Setting,
  MagicStick,
  DataAnalysis,
} from "@element-plus/icons-vue";

const routes = [
  {
    path: "/",
    name: "Dashboard",
    component: () => import("../views/Dashboard.vue"),
  },
  {
    path: "/attack",
    name: "Attack",
    component: () => import("../views/AttackPanel.vue"),
  },
  {
    path: "/defense",
    name: "Defense",
    component: () => import("../views/DefensePanel.vue"),
  },
  {
    path: "/topology",
    name: "Topology",
    component: () => import("../views/Topology.vue"),
  },
  { path: "/logs", name: "Logs", component: () => import("../views/Logs.vue") },
  {
    path: "/env",
    name: "EnvManage",
    component: () => import("../views/EnvManage.vue"),
  },
  {
    path: "/ai-range",
    name: "AIRangeGen",
    component: () => import("../views/AIRangeGen.vue"),
  },
  {
    path: "/report",
    name: "Report",
    component: () => import("../views/ReportView.vue"),
  },
  {
    path: "/login",
    name: "Login",
    component: () => import("../views/Login.vue"),
  },
];

// 导航链接（图标用组件对象，不用字符串）
// 靶场放在控制台后面第一个
export const navLinks = [
  { name: "控制台", path: "/", icon: House },
  { name: "AI靶场", path: "/ai-range", icon: MagicStick },
  { name: "靶场", path: "/env", icon: Setting },
  { name: "攻击", path: "/attack", icon: Aim },
  { name: "防御", path: "/defense", icon: Umbrella },
  { name: "拓扑", path: "/topology", icon: Connection },
  { name: "日志", path: "/logs", icon: Document },
  { name: "报告", path: "/report", icon: DataAnalysis },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// 登录拦截（跳过 /login）
router.beforeEach((to) => {
  const user = localStorage.getItem("cyber_user");
  if (to.path !== "/login" && !user) {
    return "/login";
  }
});

export default router;
