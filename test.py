import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

# ── Test 1: Gemini via ADK (agent orchestration only) ──────────────────────
async def test_adk_agent():
    print("\n[1] Testing ADK Agent with Gemini 2.5 Flash...")
    try:
        from google.adk.agents import Agent
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai import types

        async def dummy_tool(query: str) -> dict:
            """A simple dummy tool that returns fake data."""
            return {"result": f"dummy data for: {query}"}

        from google.adk.tools import FunctionTool
        tool = FunctionTool(func=dummy_tool)

        agent = Agent(
            name="test_agent",
            model="gemini-2.5-flash",
            description="Test agent",
            instruction="You are a test agent. When asked anything, call dummy_tool with the query and return the result.",
            tools=[tool]
        )

        session_service = InMemorySessionService()
        await session_service.create_session(
            app_name="test", user_id="u1", session_id="s1"
        )

        runner = Runner(agent=agent, app_name="test", session_service=session_service)

        result_text = ""
        async for event in runner.run_async(
            user_id="u1",
            session_id="s1",
            new_message=types.Content(
                role="user",
                parts=[types.Part(text="test query: fastapi auth")]
            )
        ):
            if event.is_final_response() and event.content:
                for part in event.content.parts:
                    if hasattr(part, "text"):
                        result_text += part.text

        print(f"   ✅ ADK Agent works — response: {result_text[:100]}")
        return True

    except Exception as e:
        print(f"   ❌ ADK Agent failed — {str(e)[:200]}")
        return False


# ── Test 2: Groq for text generation ──────────────────────────────────────
async def test_groq():
    print("\n[2] Testing Groq (intent extraction + explanation)...")
    try:
        from groq import Groq

        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "user",
                    "content": """Extract intent from this query and return ONLY valid JSON:
Query: "Find production-ready FastAPI auth repos with Redis"

Return:
{
  "framework": "...",
  "domain": "...",
  "prioritize": "recency or popularity or stability or balanced",
  "search_keywords": "..."
}"""
                }
            ],
            temperature=0.1
        )

        raw = response.choices[0].message.content.strip()
        print(f"   ✅ Groq works — response: {raw[:150]}")
        return True

    except Exception as e:
        print(f"   ❌ Groq failed — {str(e)[:200]}")
        return False


# ── Test 3: Groq JSON parsing ──────────────────────────────────────────────
async def test_groq_json():
    print("\n[3] Testing Groq JSON reliability...")
    try:
        import json
        from groq import Groq

        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "You are a JSON extraction assistant. Always return valid JSON only. No explanation, no markdown, no backticks."
                },
                {
                    "role": "user",
                    "content": 'Extract intent from: "Best Django payment libraries actively maintained"'
                }
            ],
            temperature=0.1,
            response_format={"type": "json_object"}  # forces JSON output
        )

        raw = response.choices[0].message.content.strip()
        parsed = json.loads(raw)
        print(f"   ✅ Groq JSON parsing works — keys: {list(parsed.keys())}")
        return True

    except Exception as e:
        print(f"   ❌ Groq JSON failed — {str(e)[:200]}")
        return False


# ── Main ───────────────────────────────────────────────────────────────────
async def main():
    print("=" * 50)
    print("DevScout — Hybrid Setup Test")
    print("=" * 50)

    adk_ok = await test_adk_agent()
    groq_ok = await test_groq()
    groq_json_ok = await test_groq_json()

    print("\n" + "=" * 50)
    print("Results:")
    print(f"  ADK + Gemini (orchestration) : {'✅ OK' if adk_ok else '❌ FAIL'}")
    print(f"  Groq (text generation)       : {'✅ OK' if groq_ok else '❌ FAIL'}")
    print(f"  Groq (JSON extraction)       : {'✅ OK' if groq_json_ok else '❌ FAIL'}")
    print("=" * 50)

    if adk_ok and groq_ok and groq_json_ok:
        print("\n✅ Hybrid setup is fully viable. Safe to proceed.")
    elif not adk_ok and groq_ok:
        print("\n⚠️  ADK is broken but Groq works. We can go full Groq and drop ADK.")
    elif adk_ok and not groq_ok:
        print("\n⚠️  Groq failed. Check your GROQ_API_KEY in .env")
    else:
        print("\n❌ Both failed. Check your API keys in .env")


asyncio.run(main())