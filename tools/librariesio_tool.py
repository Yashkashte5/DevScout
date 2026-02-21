import httpx
import os
from dotenv import load_dotenv

load_dotenv()

LIBRARIES_IO_KEY = os.getenv("LIBRARIES_IO_KEY")
BASE_URL = "https://libraries.io/api"


async def search_libraries(query: str, max_results: int = 5) -> dict:
    """Search libraries.io for Python packages."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/search",
                params={
                    "q": query,
                    "platforms": "Pypi",
                    "languages": "Python",
                    "per_page": max_results,
                    "api_key": LIBRARIES_IO_KEY
                },
                timeout=10.0
            )

            if response.status_code == 429:
                return {"error": "librariesio_rate_limited", "packages": []}

            if response.status_code != 200:
                return {"error": f"librariesio_error_{response.status_code}", "packages": []}

            data = response.json()
            packages = []

            for item in data:
                from datetime import datetime, timezone
                latest_release = item.get("latest_release_published_at", "")
                release_days = None
                if latest_release:
                    release_date = datetime.fromisoformat(latest_release.replace("Z", "+00:00"))
                    release_days = (datetime.now(timezone.utc) - release_date).days

                packages.append({
                    "name": item.get("name"),
                    "description": item.get("description", "No description"),
                    "latest_version": item.get("latest_release_number", "Unknown"),
                    "release_days": release_days,
                    "stars": item.get("stars", 0),
                    "forks": item.get("forks", 0),
                    "url": item.get("repository_url", ""),
                    "package_url": f"https://pypi.org/project/{item.get('name')}",
                    "dependent_repos": item.get("dependent_repos_count", 0)
                })

            return {"packages": packages, "error": None}

    except httpx.TimeoutException:
        return {"error": "librariesio_timeout", "packages": []}
    except Exception as e:
        return {"error": str(e), "packages": []}


async def get_pypi_metadata(package_name: str) -> dict:
    """Fetch additional metadata directly from PyPI for a known package."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://pypi.org/pypi/{package_name}/json",
                timeout=10.0
            )

            if response.status_code != 200:
                return {}

            data = response.json()
            info = data.get("info", {})

            return {
                "name": info.get("name"),
                "version": info.get("version"),
                "summary": info.get("summary"),
                "home_page": info.get("home_page"),
                "license": info.get("license"),
                "requires_python": info.get("requires_python")
            }

    except Exception:
        return {}