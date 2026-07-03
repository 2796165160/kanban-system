import os
import uuid
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from database import SessionLocal
from models import Item, Task, Project, Platform
from datetime import date


class ExportManager:
    def __init__(self, max_workers=2):
        self._tasks = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def start_export(self, td_path, output_dir, platform_id, item_ids):
        export_id = uuid.uuid4().hex[:12]
        export_info = {
            "id": export_id,
            "tdPath": td_path,
            "outputDir": output_dir,
            "platformId": platform_id,
            "status": "running",
            "total": len(item_ids),
            "done": 0,
            "failed": 0,
            "items": [],
        }
        db = SessionLocal()
        try:
            platform = db.query(Platform).filter(Platform.id == platform_id).first()
            access_key = platform.access_key if platform else ""
            host = platform.base_url if platform else ""

            item_records = []
            for iid in item_ids:
                item = db.query(Item).filter(Item.id == iid).first()
                if not item:
                    export_info["items"].append({
                        "itemId": iid, "taskName": "", "taskKey": "",
                        "questionId": "", "clipName": "",
                        "status": "failed", "error": "题不存在",
                    })
                    export_info["failed"] += 1
                    continue
                task = db.query(Task).filter(Task.id == item.task_id).first()
                tn = task.name if task else ""
                tk = task.task_key if task else ""
                item_records.append({
                    "itemId": item.id,
                    "taskName": tn,
                    "taskKey": tk,
                    "questionId": item.question_id,
                    "clipName": item.clip_name,
                    "status": "pending",
                    "error": "",
                })
                export_info["items"].append(item_records[-1])

            export_info["total"] = len(item_records)
            export_info["accessKey"] = access_key
            export_info["host"] = host
        finally:
            db.close()

        with self._lock:
            self._tasks[export_id] = export_info

        self._executor.submit(self._run_export, export_id)
        return export_id

    def _run_export(self, export_id):
        with self._lock:
            info = self._tasks.get(export_id)
            if not info:
                return
            td_path = info["tdPath"]
            output_dir = info["outputDir"]
            access_key = info["accessKey"]
            host = info["host"]
            items = info["items"]

        for item in items:
            if item["status"] == "failed":
                continue
            task_key = item["taskKey"]
            question_id = item["questionId"]
            task_name = item["taskName"]

            task_dir = os.path.join(output_dir, task_name)
            os.makedirs(task_dir, exist_ok=True)

            cmd = [
                td_path,
                "export",
                access_key,
                task_key,
                task_dir,
                "-p", str(question_id),
                "-d", "original_and_label",
                "-w", "4",
                "--host", host,
            ]

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600,
                )
                if result.returncode == 0:
                    item["status"] = "completed"
                else:
                    item["status"] = "failed"
                    item["error"] = result.stderr.strip() or result.stdout.strip()
            except subprocess.TimeoutExpired:
                item["status"] = "failed"
                item["error"] = "超时"
            except Exception as e:
                item["status"] = "failed"
                item["error"] = str(e)

            with self._lock:
                if info["status"] != "running":
                    break
                if item["status"] == "completed":
                    info["done"] += 1
                else:
                    info["failed"] += 1

        with self._lock:
            info["status"] = "completed" if info["failed"] == 0 else "completed_with_errors"

        db = SessionLocal()
        try:
            today = str(date.today())
            for item in items:
                if item["status"] == "completed":
                    db.query(Item).filter(Item.id == item["itemId"]).update({
                        "export_status": "已导出",
                        "export_date": today,
                        "return_status": "已回传",
                        "return_date": today,
                    })
            db.commit()
        finally:
            db.close()

    def get_status(self, export_id):
        with self._lock:
            info = self._tasks.get(export_id)
            if not info:
                return None
            return {
                "id": info["id"],
                "status": info["status"],
                "total": info["total"],
                "done": info["done"],
                "failed": info["failed"],
                "items": [
                    {"taskName": i["taskName"], "questionId": i["questionId"],
                     "clipName": i["clipName"], "status": i["status"],
                     "error": i.get("error", "")}
                    for i in info["items"]
                ],
            }


export_manager = ExportManager(max_workers=2)
