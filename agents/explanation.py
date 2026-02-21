import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from google.adk.agents import Agent
from google.adk.tools import FunctionTool


async def format_for_explanation(ranked_json: str, intent_json: str) -> dict:
    """
    Prepare ranked results for explanation generation.
    
    Args:
        ranked_json: JSON string of ranked results from ranking agent
        intent_json: JSON string of user intent from coordinator
    
    Returns:
        Structured data ready for explanation
    """
    try:
        ranked = json.loads(ranked_json)
        intent = json.loads(intent_json)
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {str(e)}"}

    top_results = ranked.get("ranked", [])[:3]
    
    prepared = []
    for i, result in enumerate(top_results):
        data = result.get("data", {})
        prepared.append({
            "rank": i + 1,
            "type": result.get("type"),
            "name": data.get("name"),
            "score": result.get("score"),
            "stars": data.get("stars"),
            "description": data.get("description"),
            "last_commit_days": data.get("last_commit_days"),
            "release_days": data.get("release_days"),
            "url": data.get("url") or data.get("package_url"),
            "topics": data.get("topics", []),
            "forks": data.get("forks"),
            "latest_version": data.get("latest_version")
        })

    return {
        "top_results": prepared,
        "user_intent": intent,
        "query": intent.get("original_query", "")
    }


async def format_comparison(item_one: str, item_two: str) -> dict:
    """
    Prepare two items for head-to-head comparison.
    
    Args:
        item_one: JSON string of first item
        item_two: JSON string of second item
    
    Returns:
        Structured comparison data
    """
    try:
        one = json.loads(item_one)
        two = json.loads(item_two)
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {str(e)}"}

    return {
        "item_one": one,
        "item_two": two,
        "comparison_signals": {
            "stars": {
                "item_one": one.get("data", {}).get("stars", 0),
                "item_two": two.get("data", {}).get("stars", 0)
            },
            "commit_recency_days": {
                "item_one": one.get("data", {}).get("last_commit_days"),
                "item_two": two.get("data", {}).get("last_commit_days")
            },
            "score": {
                "item_one": one.get("score"),
                "item_two": two.get("score")
            }
        }
    }


format_tool = FunctionTool(func=format_for_explanation)
comparison_tool = FunctionTool(func=format_comparison)


explanation_agent = Agent(
    name="explanation_agent",
    model="gemini-2.0-flash",
    description="Converts ranked results into clear, human-readable recommendations with tradeoff analysis.",
    instruction="""
You are an expert developer advisor. Your job is to explain recommendations clearly and honestly.

For standard recommendations:
1. Call format_for_explanation with the ranked data and intent
2. Write a concise recommendation for each of the top 3 results
3. Explain WHY it ranked where it did — cite actual data (stars, commit recency, etc.)
4. Highlight tradeoffs honestly — mention weaknesses, not just strengths
5. End with a "Best for" summary for each result

For comparison requests:
1. Call format_comparison with the two items
2. Compare them across: maturity, activity, complexity, community size
3. Give a clear recommendation based on the user's stated need
4. Never be vague — always say which one wins for which use case

Output format for recommendations:
{
  "recommendations": [
    {
      "rank": 1,
      "name": "...",
      "type": "repo or package",
      "url": "...",
      "summary": "2-3 sentence explanation",
      "strengths": ["...", "..."],
      "weaknesses": ["...", "..."],
      "best_for": "...",
      "score": 0.0
    }
  ],
  "overall_insight": "1-2 sentence summary of the landscape",
  "mode": "recommendations"
}

Output format for comparisons:
{
  "comparison": {
    "item_one": { "name": "...", "verdict": "..." },
    "item_two": { "name": "...", "verdict": "..." },
    "winner_for": {
      "beginners": "...",
      "production": "...",
      "simplicity": "..."
    },
    "final_recommendation": "..."
  },
  "mode": "comparison"
}

Always be specific. Never say "it depends" without explaining what it depends on.
""",
    tools=[format_tool, comparison_tool]
)