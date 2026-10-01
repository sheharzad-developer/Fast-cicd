import logging
import os
from uuid import UUID

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.models import HealthResponse, Task, TaskCreate, TaskUpdate
from app.storage import TaskNotFoundError, TaskRepository

APP_VERSION = os.getenv("APP_VERSION", "dev")

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("task-api")

app = FastAPI(
    title="Task Management API - Version 2",
    version=APP_VERSION,
    description="Simple task API deployed via GitHub Actions to AWS ECS Fargate.",
)

repo = TaskRepository()


@app.exception_handler(TaskNotFoundError)
async def task_not_found_handler(request: Request, exc: TaskNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"error": "not_found", "detail": str(exc)},
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    errors = [
        {"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "validation_error", "detail": errors},
    )


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "internal_error", "detail": "Something went wrong"},
    )


# ---------- Routes ----------


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", version=APP_VERSION)


@app.get("/tasks", response_model=list[Task], tags=["tasks"])
def list_tasks(completed: bool | None = None) -> list[Task]:  # query param
    return repo.list(completed=completed)


@app.post(
    "/tasks",
    response_model=Task,
    status_code=status.HTTP_201_CREATED,
    tags=["tasks"],
)
def create_task(payload: TaskCreate) -> Task:
    task = repo.create(payload)
    logger.info("Created task %s", task.id)
    return task


@app.get("/tasks/{task_id}", response_model=Task, tags=["tasks"])
def get_task(task_id: UUID) -> Task:
    return repo.get(task_id)


@app.put("/tasks/{task_id}", response_model=Task, tags=["tasks"])
def update_task(task_id: UUID, payload: TaskUpdate) -> Task:
    return repo.update(task_id, payload)


@app.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["tasks"],
)
def delete_task(task_id: UUID) -> None:
    repo.delete(task_id)
