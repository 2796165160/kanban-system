# 数据库使用文档

## 当前配置

本系统默认使用 **SQLite** 数据库，文件位于 `backend/data.db`，无需额外安装配置。

---

## 切换到 PostgreSQL

### 1. 安装 PostgreSQL

- 从 https://www.postgresql.org/download/windows/ 下载并安装
- 安装时记住设置的 postgres 用户密码
- 默认端口为 5432

### 2. 创建数据库

打开 SQL Shell (psql) 或 pgAdmin，执行：

```sql
CREATE DATABASE kanban;
```

### 3. 配置环境变量

设置以下环境变量后重启后端即可切换：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DB_TYPE` | 数据库类型 | `sqlite`（设为 `postgresql` 切换） |
| `DB_HOST` | PostgreSQL 主机地址 | `localhost` |
| `DB_PORT` | 端口 | `5432` |
| `DB_NAME` | 数据库名 | `kanban` |
| `DB_USER` | 用户名 | `postgres` |
| `DB_PASS` | 密码 | `postgres` |

**Windows PowerShell 设置示例：**

```powershell
$env:DB_TYPE = "postgresql"
$env:DB_PASS = "你的密码"
```

或在启动后端时直接传入：

```powershell
$env:DB_TYPE="postgresql"; $env:DB_PASS="你的密码"; python -m uvicorn main:app --reload --port 8000
```

### 4. 验证切换

启动后端后访问任意 API，数据将存储在 PostgreSQL 中。SQLite 的 `data.db` 文件中的数据不会自动迁移。

---

## 数据模型

```
users (用户)
├── id          INTEGER (PK)
├── username    VARCHAR(100) 唯一
├── password    VARCHAR(255) 已哈希
├── role        VARCHAR(20)  admin / user
└── created_at  DATETIME

platforms (标注平台)
├── id          INTEGER (PK)
├── name        VARCHAR(255) 唯一
└── projects    关联项目列表

projects (项目)
├── id          INTEGER (PK)
├── name        VARCHAR(255)
├── platform_id INTEGER (FK → platforms.id)
└── tasks       关联任务列表

tasks (任务)
├── id          INTEGER (PK)
├── name        VARCHAR(255)
├── project_id  INTEGER (FK → projects.id)
└── items       关联题列表

items (题)
├── id                INTEGER (PK)
├── task_id           INTEGER (FK → tasks.id)
├── question_id       VARCHAR(100)
├── clip_name         VARCHAR(500)
├── label_status      VARCHAR(50)   标注工序状态
├── review_status     VARCHAR(50)   审核工序状态
├── quality_status    VARCHAR(50)   质检工序状态
├── acceptance_status VARCHAR(50)   验收工序状态
├── export_status     VARCHAR(50)   导出状态
├── export_date       VARCHAR(20)   导出日期
├── return_status     VARCHAR(50)   回传状态
├── return_date       VARCHAR(20)   回传日期
├── created_at        DATETIME
└── updated_at        DATETIME
```

### 工序状态取值

`label_status` / `review_status` / `quality_status` / `acceptance_status`：

- `未开始`（默认）
- `待处理`
- `进行中`
- `已通过`
- `已驳回`

### 导出/回传状态取值

- `export_status`：`""`（未导出） / `"已导出"`
- `return_status`：`""`（未回传） / `"已回传"`

---

## CSV 导入格式

文件需为 UTF-8 编码，含以下列（列名可含中文）：

| 任务名称 | 题ID | 序列名称 | 标注工序 | 审核工序 | 质检工序 | 验收工序 |
|---------|------|---------|---------|---------|---------|---------|

- `任务名称` 和 `题ID` 为必填
- `序列名称` 及四个工序状态可选填，不填默认为 `未开始`

---

## 数据备份

### SQLite
直接复制 `backend/data.db` 文件即可。

### PostgreSQL
```bash
pg_dump -U postgres kanban > kanban_backup.sql
```

## 数据恢复

### SQLite
停止后端，将备份的 `data.db` 覆盖 `backend/data.db`，重启后端。

### PostgreSQL
```bash
psql -U postgres -d kanban < kanban_backup.sql
```
