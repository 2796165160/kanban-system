from sqlalchemy import Column, Integer, String, Text, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="user")  # "admin" or "user"
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {"id": self.id, "username": self.username, "role": self.role, "createdAt": self.created_at.isoformat() if self.created_at else ""}


class Platform(Base):
    __tablename__ = "platforms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    base_url = Column(String(500), default="")
    access_key = Column(String(255), default="")
    schedule_times = Column(String(200), default="")  # comma-separated, e.g. "12:00,18:00"
    projects = relationship("Project", back_populates="platform", cascade="all, delete-orphan")

    def to_dict(self):
        return {"id": self.id, "name": self.name, "baseUrl": self.base_url, "scheduleTimes": self.schedule_times}


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    platform_id = Column(Integer, ForeignKey("platforms.id"), nullable=False)
    project_key = Column(String(255), default="")
    platform = relationship("Platform", back_populates="projects")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")

    def to_dict(self):
        return {"id": self.id, "name": self.name, "platformId": self.platform_id, "projectKey": self.project_key}


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    task_key = Column(String(255), default="")
    project = relationship("Project", back_populates="tasks")
    items = relationship("Item", back_populates="task", cascade="all, delete-orphan")

    def to_dict(self):
        return {"id": self.id, "name": self.name, "projectId": self.project_id, "taskKey": self.task_key}


class Snapshot(Base):
    __tablename__ = "snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform_id = Column(Integer, ForeignKey("platforms.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    snapshot_at = Column(DateTime, nullable=False)  # when this snapshot was taken
    created_at = Column(DateTime, server_default=func.now())
    platform = relationship("Platform")
    project = relationship("Project")

    def to_dict(self):
        return {
            "id": self.id,
            "platformId": self.platform_id,
            "projectId": self.project_id,
            "snapshotAt": self.snapshot_at.isoformat() if self.snapshot_at else "",
        }


class SnapshotTask(Base):
    __tablename__ = "snapshot_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"), nullable=False)
    task_name = Column(String(255), nullable=False)
    total = Column(Integer, default=0)
    label_passed = Column(Integer, default=0)
    review_passed = Column(Integer, default=0)
    quality_passed = Column(Integer, default=0)
    acceptance_passed = Column(Integer, default=0)

    def to_dict(self):
        return {
            "id": self.id,
            "snapshotId": self.snapshot_id,
            "taskName": self.task_name,
            "total": self.total,
            "labelPassed": self.label_passed,
            "reviewPassed": self.review_passed,
            "qualityPassed": self.quality_passed,
            "acceptancePassed": self.acceptance_passed,
        }


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    task = relationship("Task", back_populates="items")
    question_id = Column(String(100), nullable=False)
    clip_name = Column(String(500), default="")
    label_status = Column(String(50), default="未开始")
    review_status = Column(String(50), default="未开始")
    quality_status = Column(String(50), default="未开始")
    acceptance_status = Column(String(50), default="未开始")
    export_status = Column(String(50), default="")
    export_date = Column(String(20), default="")
    return_status = Column(String(50), default="")
    return_date = Column(String(20), default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    @property
    def all_passed(self):
        return all(s == "已通过" for s in [
            self.label_status, self.review_status,
            self.quality_status, self.acceptance_status
        ])

    def to_dict(self):
        return {
            "id": self.id,
            "taskId": self.task_id,
            "questionId": self.question_id,
            "clipName": self.clip_name,
            "labelStatus": self.label_status,
            "reviewStatus": self.review_status,
            "qualityStatus": self.quality_status,
            "acceptanceStatus": self.acceptance_status,
            "allPassed": self.all_passed,
            "exportStatus": self.export_status,
            "exportDate": self.export_date,
            "returnStatus": self.return_status,
            "returnDate": self.return_date,
        }


class StatusLog(Base):
    __tablename__ = "status_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    field = Column(String(50), nullable=False)
    old_value = Column(String(50), default="")
    new_value = Column(String(50), default="")
    changed_by = Column(String(100), default="")
    changed_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "itemId": self.item_id,
            "projectId": self.project_id,
            "field": self.field,
            "oldValue": self.old_value,
            "newValue": self.new_value,
            "changedBy": self.changed_by,
            "changedAt": self.changed_at.isoformat() if self.changed_at else "",
        }
