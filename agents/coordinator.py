import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import re
import asyncio
from groq import Groq
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.discovery import discovery_agent
from agents.ranking import run_ranking
from agents.explanation import explain_results, explain_comparison
from utils.session import session

# ADK session service
session_service = InMemorySessionService()

APP_NAME = "devscout"
USER_ID = "user_01"

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
INTENT_MODEL = "llama-3.1-8b-instant"


async def extract_intent(query: str) -> dict:
    """Extract structured intent from user query using Groq."""
    response = groq_client.chat.completions.create(
        model=INTENT_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are an intent extraction assistant. Always return valid JSON only. No explanation, no markdown, no backticks."
            },
            {
                "role": "user",
                "content": f"""Extract structured intent from this developer query.

Query: "{query}"

Return this exact structure:
{{
  "original_query": "{query}",
  "framework": "detected framework or null",
  "domain": "main topic area e.g. authentication, task queue, payments",
  "tech_requirements": ["list", "of", "technologies", "mentioned"],
  "quality_signals": ["production-ready", "lightweight", "actively-maintained"],
  "prioritize": "recency or popularity or stability or balanced",
  "search_keywords": "optimized search string for GitHub and libraries.io"
}}

prioritize rules:
- recency: user mentions actively maintained, recent, latest
- popularity: user mentions popular, widely used, community
- stability: user mentions production-ready, stable, mature
- balanced: no clear signal"""
            }
        ],
        temperature=0.1,
        response_format={"type": "json_object"}
    )

    raw = response.choices[0].message.content.strip()
    return json.loads(raw)


def trim_for_explanation(ranking_result: dict, intent: dict) -> tuple:
    """Trim ranked data to only what explanation needs."""
    top3 = ranking_result.get("ranked", [])[:3]

    trimmed = []
    for i, item in enumerate(top3):
        data = item.get("data", {}) if "data" in item else item
        trimmed.append({
            "rank": i + 1,
            "type": item.get("type", "repo"),
            "score": item.get("score", 0),
            "name": data.get("name") or item.get("name"),
            "description": (data.get("description") or item.get("description") or "")[:120],
            "stars": data.get("stars") or item.get("stars"),
            "forks": data.get("forks") or item.get("forks"),
            "last_commit_days": data.get("last_commit_days") or item.get("last_commit_days"),
            "release_days": data.get("release_days") or item.get("release_days"),
            "url": data.get("url") or data.get("package_url") or item.get("url"),
            "latest_version": data.get("latest_version") or item.get("latest_version"),
        })

    slim_intent = {
        "original_query": intent.get("original_query"),
        "domain": intent.get("domain"),
        "prioritize": intent.get("prioritize")
    }

    return trimmed, slim_intent


def extract_json_from_text(text: str) -> dict:
    """Robustly extract JSON from agent response text."""
    if not text:
        return {"raw_text": text}

    clean = text.strip()

    if "```" in clean:
        parts = clean.split("```")
        for part in parts:
            if part.startswith("json"):
                clean = part[4:].strip()
                break
            elif part.strip().startswith("{"):
                clean = part.strip()
                break

    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass

    match = re.search(r'\{[\s\S]*\}', clean)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return {"raw_text": text}


async def run_discovery_with_retry(session_id: str, message: str, max_retries: int = 3) -> dict:
    """Run discovery agent with automatic retry on rate limits."""
    for attempt in range(max_retries):
        try:
            return await run_discovery(session_id, message)
        except Exception as e:
            error_str = str(e)
            if "rate_limit_exceeded" in error_str or "RateLimitError" in error_str:
                wait_match = re.search(r'try again in (\d+(?:\.\d+)?)s', error_str)
                wait_time = float(wait_match.group(1)) if wait_match else 20.0
                wait_time = min(wait_time + 2, 60)
                print(f"Discovery rate limited. Waiting {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)
            else:
                raise e

    return {"repos": [], "packages": [], "errors": ["max retries exceeded"]}


async def run_discovery(session_id: str, message: str) -> dict:
    """Run the discovery ADK agent."""
    try:
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=session_id
        )
    except Exception:
        pass

    runner = Runner(
        agent=discovery_agent,
        app_name=APP_NAME,
        session_service=session_service
    )

    result_text = ""
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=message)]
        )
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if hasattr(part, "text"):
                    result_text += part.text

    return extract_json_from_text(result_text)


async def coordinate(query: str) -> dict:
    """Main coordination function."""

    # Step 1 — Comparison request check
    if session.is_comparison_request(query) and session.has_previous_results():
        intent = session.last_intent
        top_two = session.get_top_two()

        def trim_item(item):
            data = item.get("data", {}) if "data" in item else item
            return {
                "name": data.get("name") or item.get("name"),
                "score": item.get("score", 0),
                "stars": data.get("stars") or item.get("stars"),
                "last_commit_days": data.get("last_commit_days") or item.get("last_commit_days"),
                "description": (data.get("description") or item.get("description") or "")[:100],
                "url": data.get("url") or data.get("package_url") or item.get("url")
            }

        one = trim_item(top_two[0]) if len(top_two) > 0 else {}
        two = trim_item(top_two[1]) if len(top_two) > 1 else {}

        comparison_result = await explain_comparison(one, two, query)

        return {
            "mode": "comparison",
            "query": query,
            "agent_trace": [
                {"agent": "coordinator", "action": "detected comparison request from session memory"},
                {"agent": "explanation_agent", "action": "ran head-to-head comparison"}
            ],
            "output": comparison_result
        }

    # Step 2 — Extract intent
    try:
        intent = await extract_intent(query)
    except Exception as e:
        return {"error": f"Intent extraction failed: {str(e)}"}

    intent["prioritize"] = session.user_preferences.get(
        "prioritize", intent.get("prioritize", "balanced")
    )

    agent_trace = [
        {"agent": "coordinator", "action": f"extracted intent — domain: {intent.get('domain')}, prioritize: {intent.get('prioritize')}"}
    ]

    # Step 3 — Discovery Agent (ADK — only remaining ADK agent with real tool calling)
    discovery_result = await run_discovery_with_retry(
        f"{USER_ID}_discovery",
        f"Search for: {intent.get('search_keywords', query)}"
    )
    agent_trace.append({
        "agent": "discovery_agent",
        "action": "fetched GitHub repos and libraries.io packages"
    })

    # Step 4 — Ranking (pure Python, no LLM)
    ranking_result = await run_ranking(discovery_result, intent)
    agent_trace.append({
        "agent": "ranking_agent",
        "action": "scored and ranked all results by context-aware weights"
    })

    # Step 5 — Trim
    trimmed_results, slim_intent = trim_for_explanation(ranking_result, intent)

    # Step 6 — Explanation (direct Groq call — no ADK, no tool calling overhead)
    explanation_result = await explain_results(trimmed_results, slim_intent)
    agent_trace.append({
        "agent": "explanation_agent",
        "action": "generated human-readable recommendations with tradeoffs"
    })

    # Step 7 — Update session
    session.update_query(query, intent)
    session.update_results(ranking_result.get("ranked", []), ranking_result)

    return {
        "mode": "recommendations",
        "query": query,
        "intent": intent,
        "agent_trace": agent_trace,
        "output": explanation_result
    }