import os
import json
from groq import Groq

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

EXPLANATION_MODEL = "llama-3.1-8b-instant"


def build_explanation_prompt(trimmed_results: list, intent: dict) -> str:
    """Build a compact prompt for explanation generation."""
    results_text = ""
    for item in trimmed_results:
        results_text += f"""
Rank {item.get('rank')}: {item.get('name')} ({item.get('type')})
- Score: {item.get('score')}
- Stars: {item.get('stars')} | Forks: {item.get('forks')}
- Last commit: {item.get('last_commit_days')} days ago
- Description: {item.get('description', '')[:100]}
- URL: {item.get('url')}
"""

    return f"""You are a developer advisor. Explain these ranked results for the query: "{intent.get('original_query')}".

Results:
{results_text}

Return ONLY valid JSON in this exact format:
{{
  "recommendations": [
    {{
      "rank": 1,
      "name": "...",
      "type": "repo or package",
      "url": "...",
      "summary": "2 sentence explanation citing actual data",
      "strengths": ["strength 1", "strength 2"],
      "weaknesses": ["weakness 1"],
      "best_for": "who should use this",
      "score": 0.0
    }}
  ],
  "overall_insight": "1 sentence landscape summary",
  "mode": "recommendations"
}}

Include all {len(trimmed_results)} results. No markdown, no backticks, valid JSON only."""


def build_comparison_prompt(item_one: dict, item_two: dict, query: str) -> str:
    """Build a compact prompt for comparison."""
    return f"""Compare these two developer resources for: "{query}"

Item 1: {item_one.get('name')}
- Stars: {item_one.get('stars')} | Last commit: {item_one.get('last_commit_days')} days ago
- Description: {item_one.get('description', '')[:80]}

Item 2: {item_two.get('name')}
- Stars: {item_two.get('stars')} | Last commit: {item_two.get('last_commit_days')} days ago
- Description: {item_two.get('description', '')[:80]}

Return ONLY valid JSON:
{{
  "comparison": {{
    "item_one": {{"name": "...", "verdict": "2 sentence verdict"}},
    "item_two": {{"name": "...", "verdict": "2 sentence verdict"}},
    "winner_for": {{
      "beginners": "name",
      "production": "name",
      "simplicity": "name"
    }},
    "final_recommendation": "1 sentence clear recommendation"
  }},
  "mode": "comparison"
}}

No markdown, no backticks, valid JSON only."""


async def explain_results(trimmed_results: list, intent: dict) -> dict:
    """Generate explanations via direct Groq call — no ADK, no tools."""
    import re

    prompt = build_explanation_prompt(trimmed_results, intent)

    response = groq_client.chat.completions.create(
        model=EXPLANATION_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a developer advisor. Always return valid JSON only. No markdown, no backticks."
            },
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        response_format={"type": "json_object"}
    )

    raw = response.choices[0].message.content.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', raw)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {"raw_text": raw}


async def explain_comparison(item_one: dict, item_two: dict, query: str) -> dict:
    """Generate comparison via direct Groq call."""
    import re

    prompt = build_comparison_prompt(item_one, item_two, query)

    response = groq_client.chat.completions.create(
        model=EXPLANATION_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a developer advisor. Always return valid JSON only. No markdown, no backticks."
            },
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        response_format={"type": "json_object"}
    )

    raw = response.choices[0].message.content.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', raw)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {"raw_text": raw}