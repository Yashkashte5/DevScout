import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from utils.scoring import score_repo, score_package, get_weights_from_context


async def run_ranking(raw_data: dict, intent: dict) -> dict:
    """
    Pure deterministic ranking — no LLM needed here.
    Scores repos and packages based on intent-aware weights.
    """
    # Handle raw_text fallback from discovery agent
    if "raw_text" in raw_data and not raw_data.get("repos"):
        try:
            raw_data = json.loads(raw_data["raw_text"])
        except (json.JSONDecodeError, TypeError):
            pass

    weights = get_weights_from_context(intent)
    ranked = []

    for repo in raw_data.get("repos", []):
        s = score_repo(repo, weights)
        ranked.append({
            "type": "repo",
            "score": s,
            "data": repo
        })

    for pkg in raw_data.get("packages", []):
        s = score_package(pkg, weights)
        ranked.append({
            "type": "package",
            "score": s,
            "data": pkg
        })

    ranked.sort(key=lambda x: x["score"], reverse=True)

    return {
        "ranked": ranked[:6],
        "weights_used": weights,
        "errors": raw_data.get("errors", [])
    }