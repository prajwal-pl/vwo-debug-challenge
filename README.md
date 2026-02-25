# Financial Document Analyzer - Bug Tracker

## Fixed Bugs

- [x] **requirements.txt** — `google-api-core==2.10.0` conflicted with `google-ai-generativelanguage` (excluded `2.10.*`)
- [x] **requirements.txt** — `opentelemetry-instrumentation==0.46b0` incompatible with `opentelemetry-api>=1.30.0` required by crewai
- [x] **requirements.txt** — `pydantic_core==2.8.0` mismatched with `pydantic==2.6.1` (needs `pydantic-core==2.16.2`)
- [x] **requirements.txt** — `openai==1.30.5` too old for `litellm 1.72.0` (needs `>=1.68.2`)
- [x] **requirements.txt** — `protobuf==4.25.3` conflicted between google packages (`<5.0`) and opentelemetry (`>=5.0`)
- [x] **requirements.txt** — `crewai-tools==0.76.0` incompatible with `crewai==0.130.0` (no `crewai.rag` module); restored to `0.47.1`
- [x] **requirements.txt** — `embedchain` missing, required at import time by `crewai-tools==0.47.1`
- [x] **agents.py line 7** — `from crewai.agents import Agent` wrong import path; should be `from crewai import Agent`
- [x] **tools.py line 7** — `from crewai_tools.tools.serper_dev_tool import SerperDevTool` wrong import path; fixed to `from crewai_tools import SerperDevTool`
- [x] **agents.py line 7** — Added `LLM` to import: `from crewai import Agent, LLM`
- [x] **agents.py line 11** — `llm = llm` self-reference replaced with `llm = LLM(model="gemini/gemini-2.5-flash", api_key=os.getenv("GEMINI_API_KEY"))`
- [x] **tools.py line 6** — `from crewai_tools import tools` invalid import removed
- [x] **tools.py** — `read_data_tool` was a plain class method, not a crewai tool; refactored to standalone function with `@tool("Read Financial Document")` decorator
- [x] **tools.py** — `read_data_tool` was missing `self` parameter as a class method; fixed by converting to standalone function
- [x] **tools.py** — `Pdf` (PyPDFLoader) import path fixed from `from langchain.document_loaders` to `from langchain_community.document_loaders`
- [x] **tools.py** — `read_data_tool` was `async` but crewai tools are synchronous; removed `async`
- [x] **tools.py** — Indentation error in `read_data_tool` function body (docstring at 8-space indent, body at 4-space); fixed to consistent 4-space indent
- [x] **agents.py line 8** — `from tools import FinancialDocumentTool` references deleted class; changed to `from tools import read_data_tool`
- [x] **agents.py line 27** — `tool=[FinancialDocumentTool.read_data_tool]` fixed to `tools=[read_data_tool]` (plural name + standalone function)
- [x] **task.py line 5** — `from tools import FinancialDocumentTool` changed to `from tools import read_data_tool`
- [x] **task.py lines 23,44,65,80** — `tools=[FinancialDocumentTool.read_data_tool]` changed to `tools=[read_data_tool]`
- [x] **main.py line 30** — `async def analyze_financial_document(...)` renamed to `analyze_document_endpoint` to avoid shadowing the imported task
- [x] **agents.py** — `financial_analyst` goal/backstory replaced with professional, data-driven analysis prompts
- [x] **agents.py** — `verifier` goal/backstory replaced with proper document verification and compliance-focused prompts
- [x] **agents.py** — `investment_advisor` goal/backstory replaced with balanced, SEC-compliant investment analysis prompts
- [x] **agents.py** — `risk_assessor` goal/backstory replaced with proper risk management framework prompts (VaR, stress testing, etc.)
- [x] **task.py** — `analyze_financial_document` description/expected_output rewritten to request data-driven financial analysis
- [x] **task.py** — `investment_analysis` description/expected_output rewritten to request balanced, data-backed recommendations
- [x] **task.py** — `risk_assessment` description/expected_output rewritten to request proper risk evaluation with mitigation strategies
- [x] **task.py** — `verification` description/expected_output rewritten to request proper document classification and validation

## Pending Bugs

### agents.py
- [ ] **Lines 30–31** — `max_iter=1` and `max_rpm=1` are too restrictive for meaningful agent work (applies to all 4 agents)

### main.py
- [ ] **Line 12** — `run_crew()` accepts `file_path` parameter but never passes it to the crew inputs (uploaded file path is ignored, tool defaults to `data/sample.pdf`)
- [ ] **Line 14** — `Crew` only includes `financial_analyst` in agents list, but project defines multiple agents that should participate
