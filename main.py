import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agents.coordinator import coordinate
from utils.session import session

app = FastAPI(
    title="DevScout API",
    description="Multi-agent developer resource advisor powered by Google ADK",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


class QueryRequest(BaseModel):
    query: str


class FeedbackRequest(BaseModel):
    item_name: str
    feedback: str  # "up" or "down"


@app.get("/")
async def root():
    return {"status": "DevScout is running"}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "session_active": session.has_previous_results(),
        "last_query": session.last_query or "none"
    }


@app.post("/recommend")
async def recommend(request: QueryRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        result = await coordinate(request.query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feedback")
async def feedback(request: FeedbackRequest):
    if request.feedback not in ["up", "down"]:
        raise HTTPException(status_code=400, detail="Feedback must be 'up' or 'down'")

    session.add_feedback(request.item_name, request.feedback)
    return {
        "status": "recorded",
        "current_preference": session.user_preferences.get("prioritize")
    }


@app.post("/session/clear")
async def clear_session():
    session.clear()
    return {"status": "session cleared"}


@app.get("/session/state")
async def session_state():
    return {
        "last_query": session.last_query,
        "last_intent": session.last_intent,
        "result_count": len(session.last_results),
        "preferences": session.user_preferences,
        "feedback_count": len(session.feedback_history)
    }