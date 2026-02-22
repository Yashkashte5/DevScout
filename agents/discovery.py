import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from google.adk.models.lite_llm import LiteLlm
from tools.github_tool import search_github_repos
from tools.librariesio_tool import search_libraries, get_pypi_metadata


async def github_search(query: str, max_results: int = 5) -> dict:
    """Search GitHub for Python repositories matching the query."""
    return await search_github_repos(query, max_results)


async def libraries_search(query: str, max_results: int = 5) -> dict:
    """Search libraries.io for Python packages matching the query."""
    return await search_libraries(query, max_results)


async def pypi_metadata(package_name: str) -> dict:
    """Fetch detailed metadata from PyPI for a specific package name."""
    return await get_pypi_metadata(package_name)


github_tool = FunctionTool(func=github_search)
libraries_tool = FunctionTool(func=libraries_search)
pypi_tool = FunctionTool(func=pypi_metadata)


discovery_agent = Agent(
    name="discovery_agent",
    model=LiteLlm(model="groq/llama-3.3-70b-versatile"),
    description="Fetches relevant GitHub repositories and PyPI packages based on a search query.",
    instruction="""
You are a data collection agent. Your only job is to fetch data — no opinions, no ranking.

When given a search query:
1. Call github_search with the query to find relevant repositories
2. Call libraries_search with the query to find relevant packages
3. For the top 3 packages found, call pypi_metadata to enrich their data
4. If github_search returns a rate limit error, note it and continue with libraries data only
5. If libraries_search returns a rate limit error, note it and continue with GitHub data only
6. Return ALL collected data — do not filter or rank anything

Always return your findings in this exact JSON structure:
{
  "repos": [...],
  "packages": [...],
  "errors": []
}

If a source had an error, add it to the errors list but still return whatever data you have.
Do not make up data. Only return what the tools give you.
Return valid JSON only. No markdown, no backticks, no explanation.
""",
    tools=[github_tool, libraries_tool, pypi_tool]
)