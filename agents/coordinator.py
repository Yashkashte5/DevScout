import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.discovery import discovery_agent
from agents.ranking import ranking_agent
from agents.explanation import explanation_agent
from utils.session import session


# --- Session service for ADK ---
session_service = InMemorySessionService()

APP_NAME = "devscout"
USER_ID = "user_01"
SESSION_ID = "session_01"


async def extract_intent(query: str) -> dict:
    """
    Extract structured intent from user query using Gemini.
    Returns typed intent object before any agent runs.
    """
    from google import genai

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    prompt = f"""
Extract structured intent from this developer query. Return ONLY valid JSON, no explanation.

Query: "{query}"

Return this exact structure:
{{
  "original_query": "{query}",
  "framework": "detected framework or null",
  "domain": "main topic area e.g. authentication, task queue, payments",
  "tech_requirements": ["list", "of", "technologies", "mentioned"],
  "quality_signals": ["production-ready", "lightweight", "actively-maintained", etc based on query],
  "prioritize": "recency or popularity or stability or balanced",
  "search_keywords": "optimized search string for GitHub/libraries.io"
}}

prioritize should be:
- recency: if user mentions "actively maintained", "recent", "latest"
- popularity: if user mentions "popular", "widely used", "community"  
- stability: if user mentions "production-ready", "stable", "mature"
- balanced: if no clear signal
"""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )

    raw = response.text.strip()
    # Strip markdown code blocks if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)


async def run_discovery(search_keywords: str) -> dict:
    """Run the discovery agent with ADK runner."""
    adk_session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=f"{SESSION_ID}_discovery"
    )

    runner = Runner(
        agent=discovery_agent,
        app_name=APP_NAME,
        session_service=session_service
    )

    result_text = ""
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=f"{SESSION_ID}_discovery",
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=f"Search for: {search_keywords}")]
        )
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if hasattr(part, "text"):
                    result_text += part.text

    return {"raw_text": result_text}


async def run_ranking(raw_data: dict, intent: dict) -> dict:
    """Run the ranking agent with ADK runner."""
    runner = Runner(
        agent=ranking_agent,
        app_name=APP_NAME,
        session_service=session_service
    )

    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=f"{SESSION_ID}_ranking"
    )

    message = f"""
Rank these results:
raw_data: {json.dumps(raw_data)}
intent: {json.dumps(intent)}
"""

    result_text = ""
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=f"{SESSION_ID}_ranking",
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=message)]
        )
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if hasattr(part, "text"):
                    result_text += part.text

    return {"raw_text": result_text}


async def run_explanation(ranked_data: dict, intent: dict, mode: str = "recommend") -> dict:
    """Run the explanation agent with ADK runner."""
    runner = Runner(
        agent=explanation_agent,
        app_name=APP_NAME,
        session_service=session_service
    )

    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=f"{SESSION_ID}_explanation"
    )

    if mode == "compare":
        top_two = session.get_top_two()
        message = f"""
Compare these two items for the user.
Item one: {json.dumps(top_two[0]) if len(top_two) > 0 else "{}"}
Item two: {json.dumps(top_two[1]) if len(top_two) > 1 else "{}"}
User context: {json.dumps(intent)}
"""
    else:
        message = f"""
Explain these ranked results to the user.
ranked_data: {json.dumps(ranked_data)}
intent: {json.dumps(intent)}
"""

    result_text = ""
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=f"{SESSION_ID}_explanation",
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=message)]
        )
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if hasattr(part, "text"):
                    result_text += part.text

    return {"raw_text": result_text}


async def coordinate(query: str) -> dict:
    """
    Main coordination function. Orchestrates all agents in sequence.
    This is what FastAPI calls.
    """

    # Step 1 — Check if comparison request using session memory
    if session.is_comparison_request(query) and session.has_previous_results():
        intent = session.last_intent
        intent["original_query"] = query
        explanation = await run_explanation({}, intent, mode="compare")
        return {
            "mode": "comparison",
            "query": query,
            "agent_trace": [
                {"agent": "coordinator", "action": "detected comparison request"},
                {"agent": "explanation_agent", "action": "ran comparison"}
            ],
            "output": explanation["raw_text"]
        }

    # Step 2 — Extract intent
    try:
        intent = await extract_intent(query)
    except Exception as e:
        return {"error": f"Intent extraction failed: {str(e)}"}

    # Merge user session preferences
    intent["prioritize"] = session.user_preferences.get("prioritize", intent.get("prioritize", "balanced"))

    agent_trace = [
        {"agent": "coordinator", "action": f"extracted intent: {intent}"}
    ]

    # Step 3 — Discovery
    discovery_result = await run_discovery(intent.get("search_keywords", query))
    agent_trace.append({
        "agent": "discovery_agent",
        "action": "fetched GitHub repos and libraries.io packages"
    })

    # Step 4 — Ranking
    ranking_result = await run_ranking(discovery_result, intent)
    agent_trace.append({
        "agent": "ranking_agent",
        "action": "scored and ranked results"
    })

    # Step 5 — Explanation
    explanation_result = await run_explanation(ranking_result, intent, mode="recommend")
    agent_trace.append({
        "agent": "explanation_agent",
        "action": "generated human-readable recommendations"
    })

    # Step 6 — Update session memory
    session.update_query(query, intent)

    return {
        "mode": "recommendations",
        "query": query,
        "intent": intent,
        "agent_trace": agent_trace,
        "output": explanation_result["raw_text"]
    }