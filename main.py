from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query
from contextlib import asynccontextmanager
from typing import Optional
import os
import uuid

from celery.result import AsyncResult
from tasks_worker import analyze_document_task
from celery_app import celery
from db import (
    init_db,
    create_user,
    get_user,
    get_user_by_username,
    list_users,
    create_analysis,
    get_analysis,
    get_analysis_by_task_id,
    update_analysis_status,
    list_analyses,
    get_analysis_stats,
    delete_analysis,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    init_db()
    yield


app = FastAPI(title="Financial Document Analyzer", lifespan=lifespan)


# ── Health Check ───────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Financial Document Analyzer API is running"}


# ── Document Analysis ─────────────────────────────────────────────────────────

@app.post("/analyze")
async def analyze_document_endpoint(
    file: UploadFile = File(...),
    query: str = Form(default="Analyze this financial document for investment insights"),
    user_id: Optional[int] = Form(default=None),
):
    """Submit a financial document for analysis. Returns a task_id to poll for results."""

    # Validate user_id if provided
    if user_id is not None:
        user = get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User with id {user_id} not found")

    file_id = str(uuid.uuid4())
    file_path = f"data/financial_document_{file_id}.pdf"

    try:
        os.makedirs("data", exist_ok=True)

        content = await file.read()
        file_size = len(content)

        with open(file_path, "wb") as f:
            f.write(content)

        if not query or query.strip() == "":
            query = "Analyze this financial document for investment insights"

        # Dispatch to Celery worker instead of blocking
        task = analyze_document_task.delay(query=query.strip(), file_path=file_path)

        # Record in database
        db_record = create_analysis(
            task_id=task.id,
            filename=file.filename or "unknown.pdf",
            file_size=file_size,
            query=query.strip(),
            user_id=user_id,
        )

        return {
            "status": "queued",
            "task_id": task.id,
            "analysis_id": db_record["id"],
            "message": "Document submitted for analysis. Poll /status/{task_id} for results.",
        }

    except HTTPException:
        raise
    except Exception as e:
        # Clean up file if queuing fails
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
        raise HTTPException(status_code=500, detail=f"Error submitting document: {str(e)}")


@app.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """Check the status of a submitted analysis task. Also syncs status to DB."""
    result = AsyncResult(task_id, app=celery)

    if result.state == "PENDING":
        return {"task_id": task_id, "status": "pending", "message": "Task is waiting in queue."}

    elif result.state == "PROCESSING":
        update_analysis_status(task_id, "processing")
        return {"task_id": task_id, "status": "processing", "message": result.info.get("status", "Running...")}

    elif result.state == "RETRYING":
        update_analysis_status(task_id, "retrying")
        return {"task_id": task_id, "status": "retrying", "message": result.info.get("status", "Retrying...")}

    elif result.state == "SUCCESS":
        analysis_text = result.result.get("analysis")
        update_analysis_status(task_id, "success", analysis=analysis_text)
        return {
            "task_id": task_id,
            "status": "success",
            "query": result.result.get("query"),
            "analysis": analysis_text,
        }

    elif result.state == "FAILURE":
        error_text = str(result.result)
        update_analysis_status(task_id, "failed", error=error_text)
        return {
            "task_id": task_id,
            "status": "failed",
            "error": error_text,
        }

    else:
        return {"task_id": task_id, "status": result.state}


# ── Analysis History ───────────────────────────────────────────────────────────

@app.get("/analyses")
async def list_analyses_endpoint(
    user_id: Optional[int] = Query(default=None, description="Filter by user ID"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List past analyses with optional filtering and pagination."""
    results = list_analyses(user_id=user_id, status=status, limit=limit, offset=offset)
    return {"count": len(results), "analyses": results}


@app.get("/analyses/stats")
async def analyses_stats_endpoint(
    user_id: Optional[int] = Query(default=None, description="Filter stats by user ID"),
):
    """Get aggregate analysis statistics."""
    return get_analysis_stats(user_id=user_id)


@app.get("/analyses/{task_id}")
async def get_analysis_endpoint(task_id: str):
    """Get a specific analysis record by task_id."""
    record = get_analysis_by_task_id(task_id)
    if not record:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return record


@app.delete("/analyses/{task_id}")
async def delete_analysis_endpoint(task_id: str):
    """Delete a specific analysis record."""
    if not delete_analysis(task_id):
        raise HTTPException(status_code=404, detail="Analysis not found")
    return {"message": "Analysis deleted", "task_id": task_id}


# ── User Management ───────────────────────────────────────────────────────────

@app.post("/users")
async def create_user_endpoint(
    username: str = Form(...),
    email: Optional[str] = Form(default=None),
):
    """Create a new user."""
    existing = get_user_by_username(username)
    if existing:
        raise HTTPException(status_code=409, detail=f"Username '{username}' already exists")
    try:
        user = create_user(username=username, email=email)
        return user
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/users")
async def list_users_endpoint(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List all users."""
    users = list_users(limit=limit, offset=offset)
    return {"count": len(users), "users": users}


@app.get("/users/{user_id}")
async def get_user_endpoint(user_id: int):
    """Get user details and their analysis history."""
    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_analyses = list_analyses(user_id=user_id, limit=10)
    stats = get_analysis_stats(user_id=user_id)

    return {
        **user,
        "analyses": user_analyses,
        "stats": stats,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)