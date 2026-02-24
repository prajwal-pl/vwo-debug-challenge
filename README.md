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

## Pending Bugs

### agents.py
- [ ] **Line 30** — `tool=[...]` should be `tools=[...]` (plural parameter name)
- [ ] **Lines 17–28** — Agent `goal` and `backstory` are intentionally unprofessional/harmful (tells agent to make up advice, ignore compliance, hallucinate facts)
- [ ] **Lines 32–33** — `max_iter=1` and `max_rpm=1` are too restrictive for meaningful agent work
- [ ] **Lines 42–54** — `verifier` agent goal/backstory tells it to approve everything without reading, ignore accuracy
- [ ] **Lines 63–77** — `investment_advisor` agent goal/backstory promotes selling sketchy products, fake credentials, ignoring SEC compliance
- [ ] **Lines 82–96** — `risk_assessor` agent goal/backstory promotes ignoring real risk factors, YOLO mentality

### main.py
- [ ] **Line 30** — `async def analyze_financial_document(...)` name collides with the imported task `analyze_financial_document` on line 8, shadowing it
- [ ] **Line 12** — `run_crew()` accepts `file_path` parameter but never uses it (uploaded file path is ignored)
- [ ] **Line 14** — `Crew` only includes `financial_analyst` in agents list, but project defines multiple agents that should participate

### task.py
- [ ] **Lines 8–25** — `analyze_financial_document` task description tells agent to make things up, use imagination, include fake URLs, contradict itself
- [ ] **Lines 28–47** — `investment_analysis` task description tells agent to ignore user query, recommend unnecessary products, make up research
- [ ] **Lines 50–69** — `risk_assessment` task description tells agent to ignore compliance, recommend dangerous strategies, use fake institutions
- [ ] **Lines 72–82** — `verification` task description tells agent to skip reading files, hallucinate, approve everything blindly
- [ ] **Line 24** — `tools=[FinancialDocumentTool.read_data_tool]` references a class that no longer exists; should be `tools=[read_data_tool]` with updated import
