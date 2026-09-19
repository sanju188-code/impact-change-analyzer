from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal, Optional, Union
import uvicorn
from contextlib import asynccontextmanager

from data import load_sample_data, INCIDENTS
from agent import analyze_change, chat_followup
from db import get_recent_analyses, init_db, save_analysis

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

# Application State
class AppState:
    graph = None
    incidents = None
    current_analysis = None

state = AppState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load data on startup
    print("Loading graph data and incidents...")
    init_db()
    state.graph = load_sample_data()
    state.incidents = INCIDENTS
    yield
    # Cleanup on shutdown
    state.graph = None
    state.incidents = None
    state.current_analysis = None

app = FastAPI(title="Change Impact Analyzer API", lifespan=lifespan)

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

@app.get("/")
def root():
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "message": "Change Impact Analyzer API is running.",
        "endpoints": [
            "/health",
            "/analyze-change",
            "/chat",
            "/history",
        ],
    }

# CORS middleware — allow all origins for production (frontend is served from same origin on Render)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    change_description: str

class AffectedComponent(BaseModel):
    node_id: str
    path: str
    evidence_strength: Literal["confirmed", "inferred"]
    hop_distance: int
    risk_level: Literal["Low", "Medium", "High", "Critical"]
    explanation: str
    related_incidents: list[str] = Field(default_factory=list)
    llm_risk_level: Optional[str] = None

class Mitigation(BaseModel):
    node_id: str
    suggestion: str
    mitigation_type: Literal[
        "staged_rollout",
        "monitoring",
        "code_change",
        "config_adjustment",
        "testing",
    ]

class AnalyzeResponse(BaseModel):
    targeted_node: str
    affected_components: list[AffectedComponent]
    mitigations: list[Mitigation] = Field(default_factory=list)
    overall_recommendation: str = ""

class UnclearResponse(BaseModel):
    status: Literal["unclear"]
    message: str
    valid_components: list[str]

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    message: str
    chat_history: list[ChatMessage] = Field(default_factory=list)
    current_analysis: Optional[dict] = None

class ChatResponse(BaseModel):
    response: str

class HistoryItem(BaseModel):
    id: int
    timestamp: str
    change_description: str
    target_node: str
    result: dict

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/analyze-change", response_model=Union[AnalyzeResponse, UnclearResponse])
def handle_analyze_change(request: AnalyzeRequest):
    if not state.graph or not state.incidents:
        raise HTTPException(status_code=500, detail="Graph data not initialized.")
    
    try:
        result = analyze_change(request.change_description, state.graph, state.incidents)
        if result.get("status") == "unclear":
            state.current_analysis = None
            return {
                "status": result["status"],
                "message": result["message"],
                "valid_components": list(state.graph.nodes),
            }
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        state.current_analysis = result
        save_analysis(request.change_description, result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat", response_model=ChatResponse)
def handle_chat(request: ChatRequest):
    if state.graph is None or state.incidents is None:
        raise HTTPException(status_code=500, detail="Graph data not initialized.")

    current_analysis = (
        request.current_analysis
        if request.current_analysis is not None
        else state.current_analysis
    )
    if current_analysis is None:
        raise HTTPException(status_code=400, detail="Run a change analysis before asking follow-up questions.")

    try:
        response = chat_followup(
            request.message,
            [message.model_dump() for message in request.chat_history],
            current_analysis,
            state.graph,
            state.incidents,
        )
        return {"response": response}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))

@app.get("/history", response_model=list[HistoryItem])
def get_history():
    return get_recent_analyses()

if __name__ == "__main__":
    # Instructions: run this file directly via `python main.py` 
    # or via CLI using `uvicorn main:app --reload --port 8000`
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
