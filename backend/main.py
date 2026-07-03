import os
import csv
import io
from datetime import date, datetime
from fastapi import FastAPI, UploadFile, File, Depends, Query, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from urllib.parse import quote
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session, contains_eager
from sqlalchemy import desc, or_

from database import engine, Base, get_db, run_migrations, enable_wal
from models import User, Platform, Project, Task, Item, Snapshot, SnapshotTask, StatusLog
from platform_client import PlatformClient
from scheduler import scheduler, schedule_platform, unschedule_platform
from utils import hash_password, verify_password, create_token, decode_token

app = FastAPI(title="工序进度看板 API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

enable_wal()
Base.metadata.create_all(bind=engine)
run_migrations()

STATUS_ORDER = ["未开始", "待处理", "进行中", "已通过", "已驳回"]
PROCESS_FIELDS = {
    "labelStatus": "label_status",
    "reviewStatus": "review_status",
    "qualityStatus": "quality_status",
    "acceptanceStatus": "acceptance_status",
}


# ── Status log helper ──
FIELD_MAP = {
    "labelStatus": "标注", "reviewStatus": "审核",
    "qualityStatus": "质检", "acceptanceStatus": "验收",
    "exportStatus": "导出", "returnStatus": "回传",
}

def _log_status_change(db, item, field, old_value, new_value, username=""):
    db.add(StatusLog(
        item_id=item.id,
        project_id=item.task.project_id,
        field=FIELD_MAP.get(field, field),
        old_value=old_value,
        new_value=new_value,
        changed_by=username,
    ))


# ── Shared fetch helpers ──
def _snapshot_task_stats(db, snapshot_id, task, items):
    db.add(SnapshotTask(
        snapshot_id=snapshot_id, task_name=task.name,
        total=len(items),
        label_passed=sum(1 for i in items if i.label_status == "已通过"),
        review_passed=sum(1 for i in items if i.review_status == "已通过"),
        quality_passed=sum(1 for i in items if i.quality_status == "已通过"),
        acceptance_passed=sum(1 for i in items if i.acceptance_status == "已通过"),
    ))


def _determine_process_statuses(pkg):
    """从 package 的 work_type/status 推导四工序状态。
    work_type: 1=标注 2=审核 3=质检 4=验收 99=全部完成
    status: 0=待处理 1=进行中 2=已驳回"""
    wt = pkg.get("work_type", 0)
    st = pkg.get("status", 0)

    if wt == 99:
        return "已通过", "已通过", "已通过", "已通过"
    if wt == 0:
        return "未开始", "未开始", "未开始", "未开始"

    sm = {0: "待处理", 1: "进行中", 2: "已驳回"}
    label_s   = "已通过" if wt > 1 else (sm.get(st, "待处理") if wt == 1 else "未开始")
    review_s  = "已通过" if wt > 2 else (sm.get(st, "待处理") if wt == 2 else "未开始")
    quality_s = "已通过" if wt > 3 else (sm.get(st, "待处理") if wt == 3 else "未开始")
    accept_s  = sm.get(st, "待处理") if wt == 4 else "未开始"

    return label_s, review_s, quality_s, accept_s


def _fetch_and_update_task(client, db, task):
    """拉取单 task 数据，按 question_id / clip_name 匹配每道题，更新工序状态"""
    items = db.query(Item).filter(Item.task_id == task.id).all()
    if not items:
        return {"status": "ok", "msg": "无 items"}

    by_qid = {}
    by_clip = {}
    for item in items:
        if item.question_id:
            by_qid[item.question_id] = item
        if item.clip_name:
            by_clip[item.clip_name] = item

    try:
        packages = client.get_packages(task.task_key)
    except Exception as e:
        return {"status": "error", "error": f"获取 packages 失败: {e}"}

    matched = 0
    for pkg in packages:
        pkg_id = str(pkg.get("package_id", ""))
        clip = pkg.get("clip_name", "")
        if not pkg_id:
            continue

        item = by_qid.get(pkg_id)
        if not item:
            item = by_clip.get(clip)
        if not item:
            continue

        label_s, review_s, quality_s, accept_s = _determine_process_statuses(pkg)
        item.label_status = label_s
        item.review_status = review_s
        item.quality_status = quality_s
        item.acceptance_status = accept_s
        matched += 1

    return {"status": "ok", "matched": matched}


# ── Seed default admin ──
def seed_admin():
    from database import SessionLocal
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "admin").first():
            db.add(User(username="admin", password_hash=hash_password("admin123"), role="admin"))
            db.commit()
    finally:
        db.close()


@app.on_event("startup")
def startup():
    seed_admin()
    # Start scheduler and load existing schedules
    try:
        scheduler.start()
        from database import SessionLocal
        db = SessionLocal()
        try:
            platforms = db.query(Platform).filter(Platform.schedule_times != "").all()
            for p in platforms:
                schedule_platform(p.id, p.schedule_times)
        finally:
            db.close()
    except Exception:
        pass


# ── Auth dependency ──
def get_current_user(authorization: str = Header(None), token: str = Query(None), db: Session = Depends(get_db)):
    token_str = None
    if authorization and authorization.startswith("Bearer "):
        token_str = authorization[7:]
    elif token:
        token_str = token
    if not token_str:
        raise HTTPException(401, "未提供有效的令牌")
    payload = decode_token(token_str)
    if not payload:
        raise HTTPException(401, "令牌无效或已过期")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(401, "用户不存在")
    return user


def require_admin(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(403, "仅管理员可执行此操作")
    return user


def require_editor(user: User = Depends(get_current_user)):
    if user.role == "inspector":
        raise HTTPException(403, "验收员无权修改数据")
    return user


# ── Auth APIs ──
@app.post("/api/auth/login")
def login(body: dict, db: Session = Depends(get_db)):
    username = body.get("username", "").strip()
    password = body.get("password", "")
    if not username or not password:
        raise HTTPException(400, "用户名和密码不能为空")
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    token = create_token(user.id, user.username, user.role)
    return {"token": token, "user": user.to_dict()}


@app.get("/api/auth/me")
def auth_me(user: User = Depends(get_current_user)):
    return user.to_dict()


@app.get("/api/users")
def list_users(_=Depends(require_admin), db: Session = Depends(get_db)):
    return [u.to_dict() for u in db.query(User).order_by(User.id).all()]


@app.post("/api/users")
def create_user(body: dict, _=Depends(require_admin), db: Session = Depends(get_db)):
    username = body.get("username", "").strip()
    password = body.get("password", "")
    role = body.get("role", "user")
    if role not in ("admin", "user", "inspector"):
        raise HTTPException(400, "角色无效")
    if not username or len(username) < 2:
        raise HTTPException(400, "用户名至少2个字符")
    if not password or len(password) < 4:
        raise HTTPException(400, "密码至少4个字符")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(400, "用户名已存在")
    user = User(username=username, password_hash=hash_password(password), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user.to_dict()


@app.delete("/api/users/{user_id}")
def delete_user(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if user_id == admin.id:
        raise HTTPException(400, "不能删除自己")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    if user.role == "admin":
        admin_count = db.query(User).filter(User.role == "admin").count()
        if admin_count <= 1:
            raise HTTPException(400, "不能删除最后一个管理员")
    db.delete(user)
    db.commit()
    return {"message": "已删除"}


# ── CSV Parser ──
def parse_csv(text: str):
    lines = text.replace("\ufeff", "").splitlines()
    if len(lines) < 2:
        return []
    headers = [h.strip().strip('"') for h in lines[0].split(",")]
    idx = {
        "taskName": next((i for i, h in enumerate(headers) if "任务名称" in h), -1),
        "questionId": next((i for i, h in enumerate(headers) if "题ID" in h), -1),
        "clipName": next((i for i, h in enumerate(headers) if "序列名称" in h), -1),
        "labelStatus": next((i for i, h in enumerate(headers) if "标注" in h), -1),
        "reviewStatus": next((i for i, h in enumerate(headers) if "审核" in h), -1),
        "qualityStatus": next((i for i, h in enumerate(headers) if "质检" in h), -1),
        "acceptanceStatus": next((i for i, h in enumerate(headers) if "验收" in h), -1),
    }
    if idx["taskName"] == -1 or idx["questionId"] == -1:
        return []
    rows = []
    for i in range(1, len(lines)):
        cols = [c.strip().strip('"') for c in lines[i].split(",")]
        tn = cols[idx["taskName"]] if idx["taskName"] < len(cols) else ""
        qi = cols[idx["questionId"]] if idx["questionId"] < len(cols) else ""
        if not tn or not qi:
            continue
        rows.append({
            "taskName": tn,
            "questionId": qi,
            "clipName": cols[idx["clipName"]] if idx["clipName"] != -1 and idx["clipName"] < len(cols) else "",
            "labelStatus": cols[idx["labelStatus"]] if idx["labelStatus"] != -1 and idx["labelStatus"] < len(cols) else "未开始",
            "reviewStatus": cols[idx["reviewStatus"]] if idx["reviewStatus"] != -1 and idx["reviewStatus"] < len(cols) else "未开始",
            "qualityStatus": cols[idx["qualityStatus"]] if idx["qualityStatus"] != -1 and idx["qualityStatus"] < len(cols) else "未开始",
            "acceptanceStatus": cols[idx["acceptanceStatus"]] if idx["acceptanceStatus"] != -1 and idx["acceptanceStatus"] < len(cols) else "未开始",
        })
    return rows


# ── Platforms ──
@app.get("/api/platforms")
def list_platforms(_=Depends(get_current_user), db: Session = Depends(get_db)):
    return [p.to_dict() for p in db.query(Platform).order_by(Platform.id).all()]


@app.post("/api/platforms")
def create_platform(body: dict, _=Depends(get_current_user), db: Session = Depends(get_db)):
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(400, "名称不能为空")
    exists = db.query(Platform).filter(Platform.name == name).first()
    if exists:
        raise HTTPException(400, "该平台名称已存在")
    p = Platform(name=name)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p.to_dict()


@app.delete("/api/platforms/{platform_id}")
def delete_platform(platform_id: int, _=Depends(require_admin), db: Session = Depends(get_db)):
    p = db.query(Platform).filter(Platform.id == platform_id).first()
    if not p:
        raise HTTPException(404, "平台不存在")
    db.delete(p)
    db.commit()
    return {"message": "已删除"}


# ── Platform Connection ──
@app.put("/api/platforms/{platform_id}/connection")
def update_platform_connection(platform_id: int, body: dict, _=Depends(require_admin), db: Session = Depends(get_db)):
    p = db.query(Platform).filter(Platform.id == platform_id).first()
    if not p:
        raise HTTPException(404, "平台不存在")
    p.base_url = body.get("baseUrl", "").strip().rstrip("/")
    p.access_key = body.get("accessKey", "").strip()
    db.commit()
    db.refresh(p)
    return p.to_dict()


@app.get("/api/platforms/{platform_id}/connection")
def get_platform_connection(platform_id: int, _=Depends(require_admin), db: Session = Depends(get_db)):
    p = db.query(Platform).filter(Platform.id == platform_id).first()
    if not p:
        raise HTTPException(404, "平台不存在")
    return {"baseUrl": p.base_url, "configured": bool(p.base_url and p.access_key)}


@app.post("/api/platforms/{platform_id}/test-connection")
def test_platform_connection(platform_id: int, _=Depends(require_admin), db: Session = Depends(get_db)):
    p = db.query(Platform).filter(Platform.id == platform_id).first()
    if not p:
        raise HTTPException(404, "平台不存在")
    if not p.base_url or not p.access_key:
        raise HTTPException(400, "请先配置平台连接信息")
    client = PlatformClient(p.base_url, p.access_key)
    try:
        info = client.test_connection()
        nickname = info.get("data", {}).get("nickname", "未知")
        return {"message": f"连接成功: {nickname}", "data": info.get("data")}
    except Exception as e:
        raise HTTPException(400, f"连接失败: {e}")
    finally:
        client.close()


@app.post("/api/platforms/{platform_id}/fetch")
def fetch_platform_data(platform_id: int, _=Depends(require_admin), db: Session = Depends(get_db)):
    p = db.query(Platform).filter(Platform.id == platform_id).first()
    if not p:
        raise HTTPException(404, "平台不存在")
    if not p.base_url or not p.access_key:
        raise HTTPException(400, "请先配置平台连接信息")

    client = PlatformClient(p.base_url, p.access_key)
    results = []
    try:
        client.test_connection()
        projects = db.query(Project).filter(Project.platform_id == platform_id).all()
        if not projects:
            raise HTTPException(400, "该平台下没有项目")

        for project in projects:
            if not project.project_key:
                results.append({"task": f"[{project.name}] 未配置 project_key", "status": "error", "error": "project_key 为空"})
                continue

            now = datetime.now()
            snapshot = Snapshot(platform_id=platform_id, project_id=project.id, snapshot_at=now)
            db.add(snapshot)
            db.flush()

            tasks = db.query(Task).filter(Task.project_id == project.id).all()
            for task in tasks:
                if not task.task_key:
                    results.append({"task": f"[{project.name}]{task.name} 未配置 task_key", "status": "error", "error": "task_key 为空"})
                    continue

                items = db.query(Item).filter(Item.task_id == task.id).all()
                _snapshot_task_stats(db, snapshot.id, task, items)

                r = _fetch_and_update_task(client, db, task)
                r["task"] = f"[{project.name}]{task.name}"
                results.append(r)

                db.commit()
        return {"message": f"拉取完成，共处理 {len(results)} 个任务", "results": results}
    except Exception as e:
        raise HTTPException(400, f"拉取失败: {e}")
    finally:
        client.close()


# ── Per-Project Fetch ──
@app.post("/api/platforms/{platform_id}/projects/{project_id}/fetch")
def fetch_project_data(platform_id: int, project_id: int, _=Depends(require_admin), db: Session = Depends(get_db)):
    p = db.query(Platform).filter(Platform.id == platform_id).first()
    if not p or not p.base_url or not p.access_key:
        raise HTTPException(400, "请先配置平台连接信息")
    project = db.query(Project).filter(Project.id == project_id, Project.platform_id == platform_id).first()
    if not project:
        raise HTTPException(404, "项目不存在")
    if not project.project_key:
        raise HTTPException(400, "该项目未配置 project_key")
    client = PlatformClient(p.base_url, p.access_key)
    results = []
    try:
        client.test_connection()
        tasks = db.query(Task).filter(Task.project_id == project.id).all()
        now = datetime.now()
        snapshot = Snapshot(platform_id=platform_id, project_id=project.id, snapshot_at=now)
        db.add(snapshot)
        db.flush()
        for task in tasks:
            if not task.task_key:
                results.append({"task": f"{task.name} 未配置 task_key", "status": "error", "error": "task_key 为空"})
                continue

            items = db.query(Item).filter(Item.task_id == task.id).all()
            _snapshot_task_stats(db, snapshot.id, task, items)

            r = _fetch_and_update_task(client, db, task)
            r["task"] = task.name
            results.append(r)

            db.commit()
        return {"message": f"项目「{project.name}」拉取完成", "results": results}
    except Exception as e:
        raise HTTPException(400, f"拉取失败: {e}")
    finally:
        client.close()


# ── Schedule ──
@app.get("/api/platforms/{platform_id}/schedule")
def get_schedule(platform_id: int, _=Depends(get_current_user), db: Session = Depends(get_db)):
    p = db.query(Platform).filter(Platform.id == platform_id).first()
    if not p:
        raise HTTPException(404, "平台不存在")
    return {"scheduleTimes": p.schedule_times}


@app.put("/api/platforms/{platform_id}/schedule")
def update_schedule(platform_id: int, body: dict, _=Depends(require_admin), db: Session = Depends(get_db)):
    p = db.query(Platform).filter(Platform.id == platform_id).first()
    if not p:
        raise HTTPException(404, "平台不存在")
    times = body.get("scheduleTimes", "").strip()
    p.schedule_times = times
    db.commit()
    schedule_platform(platform_id, times)
    return {"scheduleTimes": times}


# ── Snapshots ──
@app.get("/api/projects/{project_id}/snapshots")
def list_snapshots(project_id: int, _=Depends(get_current_user), db: Session = Depends(get_db)):
    snapshots = (
        db.query(Snapshot)
        .filter(Snapshot.project_id == project_id)
        .order_by(desc(Snapshot.snapshot_at))
        .all()
    )
    return [s.to_dict() for s in snapshots]


@app.get("/api/snapshots/{snapshot_id}/tasks")
def get_snapshot_tasks(snapshot_id: int, _=Depends(get_current_user), db: Session = Depends(get_db)):
    tasks = db.query(SnapshotTask).filter(SnapshotTask.snapshot_id == snapshot_id).order_by(SnapshotTask.task_name).all()
    return [t.to_dict() for t in tasks]


# ── Projects ──
@app.get("/api/projects")
def list_projects(platform_id: int = Query(...), _=Depends(get_current_user), db: Session = Depends(get_db)):
    return [p.to_dict() for p in db.query(Project).filter(Project.platform_id == platform_id).order_by(Project.id).all()]


@app.post("/api/projects")
def create_project(body: dict, _=Depends(get_current_user), db: Session = Depends(get_db)):
    name = body.get("name", "").strip()
    platform_id = body.get("platformId")
    if not name:
        raise HTTPException(400, "名称不能为空")
    if not platform_id:
        raise HTTPException(400, "platformId 不能为空")
    p = Project(name=name, platform_id=platform_id, project_key=body.get("projectKey", "").strip())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p.to_dict()


@app.put("/api/projects/{project_id}")
def update_project(project_id: int, body: dict, _=Depends(require_editor), db: Session = Depends(get_db)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(404, "项目不存在")
    if "name" in body:
        p.name = body["name"].strip()
    if "projectKey" in body:
        p.project_key = body["projectKey"].strip()
    db.commit()
    db.refresh(p)
    return p.to_dict()


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: int, _=Depends(require_admin), db: Session = Depends(get_db)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(404, "项目不存在")
    db.delete(p)
    db.commit()
    return {"message": "已删除"}


# ── Tasks ──
@app.get("/api/tasks")
def list_tasks(project_id: int = Query(...), _=Depends(get_current_user), db: Session = Depends(get_db)):
    return [t.to_dict() for t in db.query(Task).filter(Task.project_id == project_id).order_by(Task.id).all()]


@app.post("/api/tasks")
def create_task(body: dict, _=Depends(get_current_user), db: Session = Depends(get_db)):
    name = body.get("name", "").strip()
    project_id = body.get("projectId")
    if not name:
        raise HTTPException(400, "名称不能为空")
    if not project_id:
        raise HTTPException(400, "projectId 不能为空")
    t = Task(name=name, project_id=project_id, task_key=body.get("taskKey", "").strip())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t.to_dict()


@app.put("/api/tasks/{task_id}")
def update_task(task_id: int, body: dict, _=Depends(require_editor), db: Session = Depends(get_db)):
    t = db.query(Task).filter(Task.id == task_id).first()
    if not t:
        raise HTTPException(404, "任务不存在")
    if "taskKey" in body:
        t.task_key = body["taskKey"].strip()
    if "name" in body:
        t.name = body["name"].strip()
    db.commit()
    db.refresh(t)
    return t.to_dict()


@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int, _=Depends(require_admin), db: Session = Depends(get_db)):
    t = db.query(Task).filter(Task.id == task_id).first()
    if not t:
        raise HTTPException(404, "任务不存在")
    db.delete(t)
    db.commit()
    return {"message": "已删除"}


# ── Upload CSV ──
@app.post("/api/upload-csv")
def upload_csv(project_id: int = Query(...), file: UploadFile = File(...), _=Depends(require_editor), db: Session = Depends(get_db)):
    content = file.file.read().decode("utf-8", errors="replace")
    rows = parse_csv(content)
    if not rows:
        raise HTTPException(400, "CSV 解析失败，请检查列名是否正确")

    task_cache = {}
    for row in rows:
        tn = row["taskName"]
        if tn not in task_cache:
            task = db.query(Task).filter(
                Task.project_id == project_id,
                Task.name == tn,
            ).first()
            if not task:
                task = Task(name=tn, project_id=project_id)
                db.add(task)
                db.flush()
            task_cache[tn] = task
        task = task_cache[tn]

        item = db.query(Item).filter(
            Item.task_id == task.id,
            Item.question_id == row["questionId"],
        ).first()
        if item:
            item.label_status = row["labelStatus"]
            item.review_status = row["reviewStatus"]
            item.quality_status = row["qualityStatus"]
            item.acceptance_status = row["acceptanceStatus"]
        else:
            item = Item(
                task_id=task.id,
                question_id=row["questionId"],
                clip_name=row["clipName"],
                label_status=row["labelStatus"],
                review_status=row["reviewStatus"],
                quality_status=row["qualityStatus"],
                acceptance_status=row["acceptanceStatus"],
            )
            db.add(item)
    db.commit()
    total = db.query(Item).count()
    return {"message": f"导入完成，共 {len(rows)} 条", "total": total}


# ── Import Export CSV ──
@app.post("/api/import-export-csv")
def import_export_csv(file: UploadFile = File(...), _=Depends(require_editor), db: Session = Depends(get_db)):
    content = file.file.read().decode("utf-8", errors="replace")
    lines = content.replace("\ufeff", "").splitlines()
    if len(lines) < 2:
        raise HTTPException(400, "CSV 为空或格式错误")

    headers = [h.strip().strip('"') for h in lines[0].split(",")]
    clip_idx = next((i for i, h in enumerate(headers) if "序列名称" in h), -1)
    if clip_idx == -1:
        raise HTTPException(400, "CSV 列名不匹配，需要「序列名称」列")

    today = str(date.today())
    matched = 0
    errors = []
    for i in range(1, len(lines)):
        cols = [c.strip().strip('"') for c in lines[i].split(",")]
        if len(cols) <= clip_idx:
            continue
        cn = cols[clip_idx]
        if not cn:
            continue

        items = db.query(Item).filter(Item.clip_name == cn).all()
        if items:
            for item in items:
                item.export_status = "已导出"
                item.export_date = today
                item.return_status = "已回传"
                item.return_date = today
            matched += 1
        else:
            errors.append(f"第{i+1}行: {cn} 未匹配")

    db.commit()
    return {"message": f"匹配成功 {matched} 条，失败 {len(errors)} 条", "matched": matched, "errors": errors}


# ── Items (Kanban grouped by task) ──
@app.get("/api/items")
def get_items(
    project_id: int = Query(...),
    search: str = "",
    process: str = "",
    status: str = "",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Item).join(Task).filter(Task.project_id == project_id)
    if search:
        q = q.filter(Task.name.like(f"%{search}%"))
    items = q.order_by(Task.name, Item.id).all()

    if user.role == "inspector":
        VISIBLE_STATUSES = ["进行中", "已通过", "已驳回"]
        items = [i for i in items if i.quality_status in VISIBLE_STATUSES or i.acceptance_status in VISIBLE_STATUSES]

    groups = {}
    for item in items:
        d = item.to_dict()
        if user.role == "inspector":
            d.pop("labelStatus", None)
            d.pop("reviewStatus", None)
        tn = item.task.name
        if tn not in groups:
            groups[tn] = {
                "taskName": tn,
                "taskId": item.task_id,
                "taskKey": item.task.task_key,
                "details": [],
                "labelPassed": 0, "reviewPassed": 0, "qualityPassed": 0, "acceptancePassed": 0,
                "allPassedCount": 0, "exportedCount": 0, "returnedCount": 0,
            }
        g = groups[tn]
        if d.get("labelStatus", "") == "已通过": g["labelPassed"] += 1
        if d.get("reviewStatus", "") == "已通过": g["reviewPassed"] += 1
        if d["qualityStatus"] == "已通过": g["qualityPassed"] += 1
        if d["acceptanceStatus"] == "已通过": g["acceptancePassed"] += 1
        if d["allPassed"]:
            g["allPassedCount"] += 1
            if d["exportStatus"] == "已导出":
                g["exportedCount"] += 1
            if d["returnStatus"] == "已回传":
                g["returnedCount"] += 1
        g["details"].append(d)

    result = sorted(groups.values(), key=lambda x: x["taskName"])

    if process and status:
        col = PROCESS_FIELDS.get(process)
        if col:
            result = [t for t in result if any(d[process] == status for d in t["details"])]

    return result


# ── Batch Update Status ──
@app.post("/api/items/batch-status")
def batch_update_status(body: dict, _=Depends(require_editor), db: Session = Depends(get_db)):
    ids = body.get("ids", [])
    field = body.get("field")
    value = body.get("value")
    if not ids or not field:
        raise HTTPException(400, "参数不全")
    items = db.query(Item).filter(Item.id.in_(ids)).all()
    today = str(date.today())
    for item in items:
        if field in PROCESS_FIELDS:
            if value not in STATUS_ORDER:
                raise HTTPException(400, f"无效状态: {value}")
            setattr(item, PROCESS_FIELDS[field], value)
        elif field == "exportStatus":
            if value == "已导出":
                item.export_status = "已导出"
                item.export_date = body.get("date") or today
            else:
                item.export_status = ""
                item.export_date = ""
        elif field == "returnStatus":
            if value == "已回传":
                item.return_status = "已回传"
                item.return_date = body.get("date") or today
            else:
                item.return_status = ""
                item.return_date = ""
        else:
            raise HTTPException(400, f"无效字段: {field}")
    db.commit()
    return {"message": f"已更新 {len(items)} 条", "count": len(items)}


# ── Update Item Status ──
@app.put("/api/items/{item_id}/status")
def update_item_status(item_id: int, body: dict, _=Depends(require_editor), db: Session = Depends(get_db)):
    field = body.get("field")
    value = body.get("value")
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(404, "未找到该数据")

    if field in PROCESS_FIELDS:
        if value not in STATUS_ORDER:
            raise HTTPException(400, f"无效状态: {value}")
        setattr(item, PROCESS_FIELDS[field], value)

    elif field == "exportStatus":
        if value == "已导出":
            item.export_status = "已导出"
            item.export_date = body.get("date") or str(date.today())
        else:
            item.export_status = ""
            item.export_date = ""

    elif field == "returnStatus":
        if value == "已回传":
            item.return_status = "已回传"
            item.return_date = body.get("date") or str(date.today())
        else:
            item.return_status = ""
            item.return_date = ""

    else:
        raise HTTPException(400, f"无效字段: {field}")

    db.commit()
    db.refresh(item)
    return item.to_dict()


# ── Batch Export ──
@app.post("/api/items/export")
def mark_export(body: dict, _=Depends(require_editor), db: Session = Depends(get_db)):
    ids = body.get("ids", [])
    today = str(date.today())
    items = db.query(Item).filter(Item.id.in_(ids)).all()
    for item in items:
        item.export_status = "已导出"
        item.export_date = today
    db.commit()
    return {"message": f"已导出 {len(items)} 条", "count": len(items)}


# ── Batch Return ──
@app.post("/api/items/return")
def mark_return(body: dict, _=Depends(require_editor), db: Session = Depends(get_db)):
    ids = body.get("ids", [])
    today = str(date.today())
    items = db.query(Item).filter(Item.id.in_(ids)).all()
    for item in items:
        item.return_status = "已回传"
        item.return_date = today
    db.commit()
    return {"message": f"已回传 {len(items)} 条", "count": len(items)}


# ── Update Item Date ──
@app.put("/api/items/{item_id}/date")
def update_item_date(item_id: int, body: dict, _=Depends(require_editor), db: Session = Depends(get_db)):
    field = body.get("field")
    value = body.get("value", "")
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(404, "未找到该数据")
    if field == "exportDate":
        item.export_date = value
    elif field == "returnDate":
        item.return_date = value
    else:
        raise HTTPException(400, f"无效字段: {field}")
    db.commit()
    db.refresh(item)
    return item.to_dict()


# ── Stats ──
@app.get("/api/stats")
def get_stats(project_id: int = Query(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from sqlalchemy import func
    q = db.query(Item).join(Task).filter(Task.project_id == project_id)

    if user.role == "inspector":
        VISIBLE_STATUSES = ["进行中", "已通过", "已驳回"]
        q = q.filter(
            or_(
                Item.quality_status.in_(VISIBLE_STATUSES),
                Item.acceptance_status.in_(VISIBLE_STATUSES),
            )
        )

    total = q.count()
    task_count = db.query(Task).filter(Task.project_id == project_id).count()
    all_passed = q.filter(
        Item.label_status == "已通过",
        Item.review_status == "已通过",
        Item.quality_status == "已通过",
        Item.acceptance_status == "已通过",
    ).count()
    exported = q.filter(Item.export_status == "已导出").count()
    returned = q.filter(Item.return_status == "已回传").count()

    def _status_counts(col, full=True):
        counts = dict(
            db.query(col, func.count(Item.id))
            .join(Task).filter(Task.project_id == project_id)
            .group_by(col).all()
        )
        if full:
            return {s: counts.get(s, 0) for s in STATUS_ORDER}
        return {s: counts.get(s, 0) for s in STATUS_ORDER if s in VISIBLE_STATUSES}

    VISIBLE_STATUSES = ["进行中", "已通过", "已驳回"]

    if user.role == "inspector":
        return {
            "taskCount": task_count,
            "totalItems": total,
            "labelStats": {},
            "reviewStats": {},
            "qualityStats": _status_counts(Item.quality_status, full=False),
            "acceptanceStats": _status_counts(Item.acceptance_status, full=False),
            "allPassed": all_passed,
            "pendingExport": max(0, all_passed - exported),
            "exported": exported,
            "returned": returned,
        }

    return {
        "taskCount": task_count,
        "totalItems": total,
        "labelStats": _status_counts(Item.label_status),
        "reviewStats": _status_counts(Item.review_status),
        "qualityStats": _status_counts(Item.quality_status),
        "acceptanceStats": _status_counts(Item.acceptance_status),
        "allPassed": all_passed,
        "pendingExport": max(0, all_passed - exported),
        "exported": exported,
        "returned": returned,
    }


# ── Export CSV ──
@app.get("/api/export-csv")
def export_csv(project_id: int = Query(...), _=Depends(get_current_user), db: Session = Depends(get_db)):
    items = (
        db.query(Item)
        .join(Item.task)
        .options(contains_eager(Item.task))
        .filter(Task.project_id == project_id)
        .order_by(Task.name, Item.id)
        .all()
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["任务名称", "题ID", "序列名称", "标注工序", "审核工序", "质检工序", "验收工序",
                      "是否全通过", "导出状态", "导出日期", "回传状态", "回传日期"])
    for item in items:
        writer.writerow([
            item.task.name, item.question_id, item.clip_name,
            item.label_status, item.review_status, item.quality_status, item.acceptance_status,
            "是" if item.all_passed else "否",
            item.export_status, item.export_date,
            item.return_status, item.return_date,
        ])
    output.seek(0)
    return StreamingResponse(
        iter(["\ufeff" + output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(f'工序进度导出_{date.today()}.csv')}"}
    )


# ── Export Files (td.exe) ──
from export_manager import export_manager


@app.post("/api/export-files")
def start_export(body: dict, _=Depends(require_editor), db: Session = Depends(get_db)):
    td_path = body.get("tdPath", "").strip()
    output_dir = body.get("outputDir", "").strip()
    platform_id = body.get("platformId")
    item_ids = body.get("itemIds", [])

    if not td_path or not os.path.isfile(td_path):
        raise HTTPException(400, "td.exe 路径无效")
    if not output_dir:
        raise HTTPException(400, "导出目录不能为空")
    if not platform_id:
        raise HTTPException(400, "platformId 不能为空")
    if not item_ids:
        raise HTTPException(400, "未选中任何题")

    platform = db.query(Platform).filter(Platform.id == platform_id).first()
    if not platform or not platform.access_key:
        raise HTTPException(400, "平台 access_key 未配置")

    os.makedirs(output_dir, exist_ok=True)

    export_id = export_manager.start_export(td_path, output_dir, platform_id, item_ids)
    return {"exportId": export_id, "total": len(item_ids)}


@app.get("/api/export-files/{export_id}/status")
def get_export_status(export_id: str, _=Depends(get_current_user)):
    status = export_manager.get_status(export_id)
    if not status:
        raise HTTPException(404, "导出任务不存在")
    return status


# ── Serve built frontend (production) ──
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        file_path = os.path.join(FRONTEND_DIST, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
elif not os.environ.get("DEV_MODE"):
    print(f"[WARN] Frontend dist not found at: {FRONTEND_DIST}")
    print("[WARN] Run 'npm run build' in frontend/, or set DEV_MODE=1 for dev proxy")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
