import os
from celery_app import celery
from crewai import Crew, Process
from agents import financial_analyst, verifier, investment_advisor, risk_assessor
from task import analyze_financial_document, investment_analysis, risk_assessment, verification


@celery.task(bind=True, name="analyze_document", max_retries=3)
def analyze_document_task(self, query: str, file_path: str):
    """Celery task that runs the CrewAI crew for financial document analysis."""
    try:
        self.update_state(state="PROCESSING", meta={"status": "Running AI agents..."})

        financial_crew = Crew(
            agents=[financial_analyst, verifier, investment_advisor, risk_assessor],
            tasks=[verification, analyze_financial_document, investment_analysis, risk_assessment],
            process=Process.sequential,
        )

        result = financial_crew.kickoff({"query": query, "file_path": file_path})

        return {
            "status": "success",
            "query": query,
            "analysis": str(result),
            "file_path": file_path,
        }

    except Exception as exc:
        error_msg = str(exc)

        # Retry on rate limit errors with exponential backoff
        if "RateLimitError" in error_msg or "429" in error_msg:
            countdown = 60 * (2 ** self.request.retries)  # 60s, 120s, 240s
            self.update_state(
                state="RETRYING",
                meta={"status": f"Rate limited. Retrying in {countdown}s..."},
            )
            raise self.retry(exc=exc, countdown=countdown)

        raise

    finally:
        # Clean up uploaded file after processing
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
