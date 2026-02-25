from fastapi import FastAPI, File, UploadFile, Form, HTTPException
import os
import uuid

from celery.result import AsyncResult
from tasks_worker import analyze_document_task
from celery_app import celery

app = FastAPI(title="Financial Document Analyzer")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Financial Document Analyzer API is running"}


@app.post("/analyze")
async def analyze_document_endpoint(
    file: UploadFile = File(...),
    query: str = Form(default="Analyze this financial document for investment insights"),
):
    """Submit a financial document for analysis. Returns a task_id to poll for results."""

    file_id = str(uuid.uuid4())
    file_path = f"data/financial_document_{file_id}.pdf"

    try:
        os.makedirs("data", exist_ok=True)

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        if not query or query.strip() == "":
            query = "Analyze this financial document for investment insights"

        # Dispatch to Celery worker instead of blocking
        task = analyze_document_task.delay(query=query.strip(), file_path=file_path)

        return {
            "status": "queued",
            "task_id": task.id,
            "message": "Document submitted for analysis. Poll /status/{task_id} for results.",
        }

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
    """Check the status of a submitted analysis task."""
    result = AsyncResult(task_id, app=celery)

    if result.state == "PENDING":
        return {"task_id": task_id, "status": "pending", "message": "Task is waiting in queue."}

    elif result.state == "PROCESSING":
        return {"task_id": task_id, "status": "processing", "message": result.info.get("status", "Running...")}

    elif result.state == "RETRYING":
        return {"task_id": task_id, "status": "retrying", "message": result.info.get("status", "Retrying...")}

    elif result.state == "SUCCESS":
        return {
            "task_id": task_id,
            "status": "success",
            "query": result.result.get("query"),
            "analysis": result.result.get("analysis"),
        }

    elif result.state == "FAILURE":
        return {
            "task_id": task_id,
            "status": "failed",
            "error": str(result.result),
        }

    else:
        return {"task_id": task_id, "status": result.state}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)