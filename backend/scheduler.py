from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
_fetch_jobs = {}  # platform_id -> job_id


from datetime import datetime, date as date_type
from database import SessionLocal
from models import Platform, Project, Task, Item, Snapshot, SnapshotTask, DailyPerformance
from platform_client import PlatformClient


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
    items = db.query(Item).filter(Item.task_id == task.id).all()
    if not items:
        return

    by_qid = {}
    by_clip = {}
    for item in items:
        if item.question_id:
            by_qid[item.question_id] = item
        if item.clip_name:
            by_clip[item.clip_name] = item

    try:
        packages = client.get_packages(task.task_key)
    except Exception:
        return

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


def run_fetch(platform_id: int):
    """Callback: run fetch for a platform. Called from scheduler."""

    db = SessionLocal()
    try:
        p = db.query(Platform).filter(Platform.id == platform_id).first()
        if not p or not p.base_url or not p.access_key:
            return
        client = PlatformClient(p.base_url, p.access_key)
        try:
            client.test_connection()
            projects = db.query(Project).filter(Project.platform_id == platform_id).all()
            for project in projects:
                if not project.project_key:
                    continue
                now = datetime.now()
                snapshot = Snapshot(platform_id=platform_id, project_id=project.id, snapshot_at=now)
                db.add(snapshot)
                db.flush()

                tasks = db.query(Task).filter(Task.project_id == project.id).all()
                for task in tasks:
                    if not task.task_key:
                        continue
                    items = db.query(Item).filter(Item.task_id == task.id).all()
                    db.add(SnapshotTask(
                        snapshot_id=snapshot.id, task_name=task.name,
                        total=len(items),
                        label_passed=sum(1 for i in items if i.label_status == "已通过"),
                        review_passed=sum(1 for i in items if i.review_status == "已通过"),
                        quality_passed=sum(1 for i in items if i.quality_status == "已通过"),
                        acceptance_passed=sum(1 for i in items if i.acceptance_status == "已通过"),
                    ))

                    _fetch_and_update_task(client, db, task)

                    db.commit()

            # ── Fetch daily performance for each project ──
            from datetime import timedelta
            yesterday = date_type.today() - timedelta(days=1)
            perf_date_str = yesterday.strftime("%Y-%m-%d")
            perf_md = yesterday.strftime("%m/%d")

            for project in projects:
                if not project.project_key:
                    continue
                try:
                    work_types = [
                        (1, "label_num"), (2, "review_num"),
                        (3, "quality_num"), (4, "acceptance_num"),
                    ]
                    user_map = {}
                    for wt, field_name in work_types:
                        items = client.get_performance(project.project_key, wt, 7)
                        for u in items:
                            uid = u.get("user_id")
                            if not uid:
                                continue
                            nald = u.get("new_add_list", {})
                            dates = nald.get("date", [])
                            nums = nald.get("new_add_num", [])
                            idx = -1
                            for i, d in enumerate(dates):
                                if d == perf_md:
                                    idx = i
                                    break
                            val = nums[idx] if idx >= 0 and idx < len(nums) else 0
                            if uid not in user_map:
                                user_map[uid] = {
                                    "user_id": uid,
                                    "user_name": u.get("user_name", ""),
                                    "nickname": u.get("nickname", ""),
                                    "label_num": 0, "review_num": 0,
                                    "quality_num": 0, "acceptance_num": 0,
                                }
                            user_map[uid][field_name] = val

                    for uid, data in user_map.items():
                        existing = db.query(DailyPerformance).filter(
                            DailyPerformance.project_key == project.project_key,
                            DailyPerformance.date == perf_date_str,
                            DailyPerformance.user_id == uid,
                        ).first()
                        if existing:
                            existing.label_num = data["label_num"]
                            existing.review_num = data["review_num"]
                            existing.quality_num = data["quality_num"]
                            existing.acceptance_num = data["acceptance_num"]
                        else:
                            db.add(DailyPerformance(
                                platform_id=p.id,
                                project_id=project.id,
                                project_key=project.project_key,
                                date=perf_date_str,
                                user_id=uid,
                                user_name=data["user_name"],
                                nickname=data["nickname"],
                                label_num=data["label_num"],
                                review_num=data["review_num"],
                                quality_num=data["quality_num"],
                                acceptance_num=data["acceptance_num"],
                            ))
                    db.commit()
                except Exception:
                    pass  # log and continue

        finally:
            client.close()
    finally:
        db.close()


def schedule_platform(platform_id: int, times_str: str):
    """Schedule fetch jobs for a platform at given comma-separated times."""
    unschedule_platform(platform_id)
    if not times_str:
        return
    times = [t.strip() for t in times_str.split(",") if t.strip()]
    for t in times:
        try:
            hour, minute = t.split(":")
            job = scheduler.add_job(
                run_fetch,
                trigger="cron",
                hour=int(hour),
                minute=int(minute),
                args=[platform_id],
                id=f"fetch_{platform_id}_{hour}_{minute}",
                replace_existing=True,
            )
            _fetch_jobs.setdefault(platform_id, []).append(job.id)
        except Exception:
            pass


def unschedule_platform(platform_id: int):
    """Remove all scheduled jobs for a platform."""
    for job_id in _fetch_jobs.pop(platform_id, []):
        try:
            scheduler.remove_job(job_id)
        except Exception:
            pass
