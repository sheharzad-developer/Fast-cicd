from datetime import UTC, datetime
from threading import Lock
from uuid import UUID, uuid4

from app.models import Task, TaskCreate, TaskUpdate


class TaskNotFoundError(Exception):
    def __init__(self, task_id: UUID):
        self.task_id = task_id
        super().__init__(f"Task {task_id} not found")


class TaskRepository:
    """Thread-safe in-memory store. Replace with DynamoDB/RDS later."""

    def __init__(self) -> None:
        self._tasks: dict[UUID, Task] = {}
        self._lock = Lock()

    def list(self, completed: bool | None = None) -> list[Task]:
        tasks = list(self._tasks.values())
        if completed is not None:
            tasks = [t for t in tasks if t.completed == completed]
        return sorted(tasks, key=lambda t: t.created_at)

    def get(self, task_id: UUID) -> Task:
        task = self._tasks.get(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)
        return task

    def create(self, data: TaskCreate) -> Task:
        now = datetime.now(UTC)
        task = Task(id=uuid4(), created_at=now, updated_at=now, **data.model_dump())
        with self._lock:
            self._tasks[task.id] = task
        return task

    def update(self, task_id: UUID, data: TaskUpdate) -> Task:
        with self._lock:
            current = self.get(task_id)
            changes = data.model_dump(exclude_unset=True)
            updated = current.model_copy(
                update={**changes, "updated_at": datetime.now(UTC)}
            )
            self._tasks[task_id] = updated
            return updated

    def delete(self, task_id: UUID) -> None:
        with self._lock:
            self.get(task_id)
            del self._tasks[task_id]

    def clear(self) -> None:
        with self._lock:
            self._tasks.clear()
