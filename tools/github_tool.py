import httpx
import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
BASE_URL = "https://api.github.com"

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}


async def search_github_repos(query: str, max_results: int = 5) -> dict:
    """Search GitHub repositories based on query."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/search/repositories",
                headers=HEADERS,
                params={
                    "q": query + " language:Python",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": max_results
                },
                timeout=10.0
            )

            if response.status_code == 403:
                return {"error": "github_rate_limited", "repos": []}

            if response.status_code != 200:
                return {"error": f"github_error_{response.status_code}", "repos": []}

            data = response.json()
            repos = []

            for item in data.get("items", []):
                # Calculate days since last commit
                from datetime import datetime, timezone
                last_push = item.get("pushed_at", "")
                days_since_commit = None
                if last_push:
                    pushed_date = datetime.fromisoformat(last_push.replace("Z", "+00:00"))
                    days_since_commit = (datetime.now(timezone.utc) - pushed_date).days

                repos.append({
                    "name": item.get("full_name"),
                    "description": item.get("description", "No description"),
                    "stars": item.get("stargazers_count", 0),
                    "language": item.get("language", "Unknown"),
                    "last_commit_days": days_since_commit,
                    "url": item.get("html_url"),
                    "topics": item.get("topics", []),
                    "open_issues": item.get("open_issues_count", 0),
                    "forks": item.get("forks_count", 0)
                })

            return {"repos": repos, "error": None}

    except httpx.TimeoutException:
        return {"error": "github_timeout", "repos": []}
    except Exception as e:
        return {"error": str(e), "repos": []}