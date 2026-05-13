# 长期记忆

## 用户偏好

- **文件默认输出目录**：`D:\软件安装\`（用户于2026-05-12指定）

## 项目背景

- 用户正在开发「AI攻防靶场管理系统」毕业设计
- 技术栈：Flask + Docker SDK + JWT
- 后端路径：`D:/0503/AI_range/`
- 论文文档路径：`D:/毕设/`

## 小红书MCP（2026-05-12接入）

- MCP 程序位置：`D:/软件安装/xiaohongshu-mcp-windows-amd64/`
- 关键发现：服务器使用 `Mcp-Session-Id` HTTP 头进行会话管理（每次 initialize 后从响应头获取，后续所有请求必须带上）
- Skill 位置：`C:/Users/王山而/.workbuddy/skills/xiaohongshu-mcp/`
- MCP URL：`http://localhost:18060/mcp`
