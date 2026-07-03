# Windows Server 部署指南

## 环境要求

| 组件 | 版本 | 说明 |
|------|------|------|
| Python | 3.10+ | 后端运行环境 |
| Node.js | 18+ | 前端构建（仅首次需要） |
| nssm    | 2.24+ | 将 Python 进程注册为 Windows 服务 |

---

## 快速部署（一键脚本）

以 **管理员 PowerShell** 执行：

```powershell
# 1. 构建前端 + 安装 Python 依赖
.\deploy_windows.ps1

# 2. 安装为 Windows 服务（自动开机启动）
.\deploy_windows.ps1 -InstallService

# 3. 启动服务
.\deploy_windows.ps1 -StartService
```

浏览器访问 `http://服务器IP:8000` 即可。

---

## 手动部署步骤

### 1. 安装 Python 依赖

```powershell
cd D:\zjkj\看板系统\backend
python -m pip install -r requirements.txt
```

### 2. 构建前端

```powershell
cd D:\zjkj\看板系统\frontend
npm install
npm run build
```

构建产物在 `frontend/dist/` 目录。

### 3. 下载 nssm

从 https://nssm.cc/download 下载 `nssm.exe`，放入 `C:\Windows\System32\` 或任意 PATH 目录。

### 4. 注册为 Windows 服务

```powershell
nssm install KanbanSystem python "-m uvicorn main:app --host 0.0.0.0 --port 8000"
nssm set KanbanSystem AppDirectory D:\zjkj\看板系统\backend
nssm set KanbanSystem AppStdout D:\zjkj\看板系统\backend\access.log
nssm set KanbanSystem AppStderr D:\zjkj\看板系统\backend\error.log
nssm set KanbanSystem Start SERVICE_AUTO_START
nssm set KanbanSystem DisplayName "工序进度看板系统"

# 启动
nssm start KanbanSystem
```

### 5. 防火墙放行

```powershell
# 管理员 PowerShell
netsh advfirewall firewall add rule name="看板系统" dir=in action=allow protocol=TCP localport=8000
```

### 6. 验证

浏览器访问 `http://服务器IP:8000`，用 `admin / admin123` 登录。

---

## 运维命令

```powershell
# 查看服务状态
nssm status KanbanSystem

# 查看日志
Get-Content D:\zjkj\看板系统\backend\access.log -Tail 50
Get-Content D:\zjkj\看板系统\backend\error.log -Tail 50

# 重启服务
nssm restart KanbanSystem

# 卸载服务（先停止）
nssm stop KanbanSystem
nssm remove KanbanSystem confirm
```

---

## 如何更新代码

```powershell
# 1. 停止服务
nssm stop KanbanSystem

# 2. 替换代码文件（覆盖 backend/ frontend/ 目录）

# 3. 重新构建前端
cd D:\zjkj\看板系统\frontend
npm run build

# 4. 启动服务
nssm start KanbanSystem
```

---

## 数据库

- 默认使用 SQLite，数据库文件在 `backend/data.db`
- 如需切换 PostgreSQL，设置环境变量 `DB_TYPE=postgresql` 并配置连接信息
- 数据库自动迁移（新增字段无需手动删表）

---

## 开发模式（调试用）

同时开两个终端：

```powershell
# 终端1：启动后端
cd D:\zjkj\看板系统\backend
$env:DEV_MODE=1
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 终端2：启动前端（带热更新）
cd D:\zjkj\看板系统\frontend
npm run dev
```

开发模式需通过 `http://localhost:3000` 访问（前端 dev server 代理 API 到 8000 端口）。
