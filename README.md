# 工序进度看板系统

前后端分离的看板系统，支持 CSV 上传展示工序状态、行内编辑、导出/回传标记。

## 技术栈

- **后端**: Python FastAPI + SQLite + SQLAlchemy
- **前端**: Vue 3 + Vite + Element Plus + Axios

---

## 快速启动（开发环境）

### 1. 启动后端

```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```

后端运行在 http://localhost:8000

### 2. 启动前端

```bash
cd frontend
npm install    # 首次运行需要
npm run dev
```

前端运行在 http://localhost:3000

> 前端开发服务器已配置代理，`/api` 请求自动转发到后端 8000 端口。

### 3. 使用

打开 http://localhost:3000 ，上传 CSV 文件即可。

**CSV 格式要求**（UTF-8 编码，含表头）：

| 任务名称 | 题ID | 序列名称 | 标注工序 | 审核工序 | 质检工序 | 验收工序 |
|---------|------|---------|---------|---------|---------|---------|

工序状态可选：未开始、待处理、进行中、已通过、已驳回（不填默认"未开始"）。

---

## 生产部署

### 方案一：前端构建 + 后端托管静态文件

```bash
# 1. 构建前端
cd frontend
npm run build

# 2. 将 dist 目录复制到后端
Copy-Item -Recurse dist ../backend/static

# 3. 修改后端 main.py，添加静态文件挂载：
#    from fastapi.staticfiles import StaticFiles
#    app.mount("/", StaticFiles(directory="static", html=True), name="static")

# 4. 启动后端（仅启动后端即可）
cd ../backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

访问 http://服务器IP:8000 即可。

### 方案二：前端构建 + Nginx 反向代理

```bash
# 1. 构建前端
cd frontend
npm run build

# 2. 将 dist 目录部署到 Nginx
# 将 dist 下所有文件复制到 Nginx 的 html 目录（如 /var/www/kanban）

# 3. Nginx 配置示例
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    root /var/www/kanban;
    index index.html;

    # 处理 SPA 路由
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# 4. 后台启动后端（使用 nohup 或系统服务）
nohup python -m uvicorn main:app --host 127.0.0.1 --port 8000 &
```

### 方案三：Docker 部署

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# 复制并安装后端依赖
COPY backend/requirements.txt .

# 安装 uvicorn
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY backend/ .

# 前端构建产物需提前放入 backend/static
COPY frontend/dist ./static

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# 构建并运行
docker build -t kanban .
docker run -d -p 8000:8000 kanban
```

---

## 常用命令

| 用途 | 命令 |
|------|------|
| 启动后端 | `python -m uvicorn main:app --reload --port 8000` |
| 启动前端 | `npm run dev` |
| 构建前端 | `npm run build` |
| 停止服务 | `Ctrl+C` |

---

## 项目结构

```
看板系统/
├── backend/
│   ├── main.py          # FastAPI 路由 + 业务逻辑
│   ├── models.py        # 数据库 ORM 模型
│   ├── database.py      # SQLite 连接配置
│   └── kanban.db        # SQLite 数据文件（自动生成）
├── frontend/
│   ├── src/
│   │   ├── App.vue
│   │   ├── api/index.js
│   │   └── components/
│   │       ├── StatsCards.vue
│   │       ├── FilterBar.vue
│   │       ├── TaskTable.vue
│   │       ├── EditableStatus.vue
│   │       ├── ExportDialog.vue
│   │       └── ReturnDialog.vue
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
└── README.md
```
