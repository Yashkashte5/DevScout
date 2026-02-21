import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from utils.scoring import score_repo, score_package, get_weights_from_context


async def rank_results(raw_data_json: str, intent_json: str) -> dict:
    """
    Rank repos and packages based on scoring logic and intent context.
    
    Args:
        raw_data_json: JSON string with repos and packages from discovery agent
        intent_json: JSON string with coordinator intent including prioritize signal
    
    Returns:
        Ranked and scored results
    """
    try:
        raw_data = json.loads(raw_data_json)
        intent = json.loads(intent_json)
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON input: {str(e)}", "ranked": []}

    weights = get_weights_from_context(intent)
    ranked = []

    # Score repos
    for repo in raw_data.get("repos", []):
        s = score_repo(repo, weights)
        ranked.append({
            "type": "repo",
            "score": s,
            "data": repo
        })

    # Score packages
    for pkg in raw_data.get("packages", []):
        s = score_package(pkg, weights)
        ranked.append({
            "type": "package",
            "score": s,
            "data": pkg
        })

    # Sort by score descending
    ranked.sort(key=lambda x: x["score"], reverse=True)

    return {
        "ranked": ranked[:6],  # top 6 across repos and packages
        "weights_used": weights,
        "errors": raw_data.get("errors", [])
    }


ranking_tool = FunctionTool(func=rank_results)

ranking_agent = Agent(
    name="ranking_agent",
    model="gemini-2.0-flash",
    description="Ranks repositories and packages using deterministic scoring with LLM interpretation.",
    instruction="""
You are a ranking agent. Your job is to score and sort developer resources objectively.

When given raw discovery data and user intent:
1. Call rank_results with the raw data and intent as JSON strings
2. Review the ranked output
3. If any result seems clearly misranked based on the query context, you may adjust its position
   but you MUST explain why in a "ranking_notes" field
4. Return the final ranked list with scores visible

Do not invent data. Only work with what rank_results returns.
Always preserve the score values in your output so the UI can display them.

Return format:
{
  "ranked": [...],
  "ranking_notes": "optional explanation if you adjusted anything",
  "weights_used": {...}
}
""",
    tools=[ranking_tool]
)