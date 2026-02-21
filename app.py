import streamlit as st
import httpx
import json

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="DevScout",
    page_icon="🔭",
    layout="wide"
)

# --- Styles ---
st.markdown("""
<style>
.result-card {
    background: #1e1e2e;
    border: 1px solid #313244;
    border-radius: 10px;
    padding: 1.2rem;
    margin-bottom: 1rem;
}
.score-badge {
    background: #a6e3a1;
    color: #1e1e2e;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: bold;
}
.rank-badge {
    background: #cba6f7;
    color: #1e1e2e;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: bold;
}
.tag {
    background: #313244;
    color: #cdd6f4;
    padding: 2px 8px;
    border-radius: 5px;
    font-size: 0.75rem;
    margin-right: 4px;
}
</style>
""", unsafe_allow_html=True)


# --- Header ---
st.title("🔭 DevScout")
st.caption("Context-aware developer resource advisor · Powered by Google ADK + Gemini")
st.divider()


# --- Layout ---
col_main, col_sidebar = st.columns([3, 1])


# --- Sidebar: Agent Trace + Session ---
with col_sidebar:
    st.subheader("🧠 Agent Trace")
    trace_placeholder = st.empty()

    st.divider()
    st.subheader("📋 Session")
    session_placeholder = st.empty()

    if st.button("🗑️ Clear Session", use_container_width=True):
        try:
            httpx.post(f"{API_URL}/session/clear")
            st.success("Session cleared")
            st.rerun()
        except Exception:
            st.error("Could not reach API")


# --- Main: Search + Results ---
with col_main:
    query = st.text_input(
        "What are you looking for?",
        placeholder="e.g. FastAPI authentication with Redis support",
        label_visibility="collapsed"
    )

    col_btn, col_pref = st.columns([2, 1])
    with col_btn:
        search_clicked = st.button("🔍 Search", use_container_width=True, type="primary")
    with col_pref:
        prioritize = st.selectbox(
            "Prioritize",
            ["balanced", "recency", "popularity", "stability"],
            label_visibility="collapsed"
        )

    st.divider()
    results_placeholder = st.empty()


# --- Search Logic ---
def render_trace(trace: list):
    with trace_placeholder.container():
        for step in trace:
            agent = step.get("agent", "")
            action = step.get("action", "")
            icon = {
                "coordinator": "🎯",
                "discovery_agent": "🔍",
                "ranking_agent": "📊",
                "explanation_agent": "💬"
            }.get(agent, "⚙️")
            st.markdown(f"**{icon} {agent}**")
            st.caption(action[:120])
            st.divider()


def render_session():
    try:
        resp = httpx.get(f"{API_URL}/session/state", timeout=5)
        state = resp.json()
        with session_placeholder.container():
            st.caption(f"Last query: {state.get('last_query') or 'none'}")
            st.caption(f"Results stored: {state.get('result_count', 0)}")
            st.caption(f"Preference: {state.get('preferences', {}).get('prioritize', 'balanced')}")
            st.caption(f"Feedback given: {state.get('feedback_count', 0)}")
    except Exception:
        session_placeholder.caption("Session unavailable")


def render_output(output_text: str, mode: str):
    with results_placeholder.container():
        try:
            # Try to parse JSON from output
            clean = output_text.strip()
            if "```" in clean:
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            clean = clean.strip()
            data = json.loads(clean)

            if mode == "comparison" or data.get("mode") == "comparison":
                render_comparison(data)
            else:
                render_recommendations(data)

        except json.JSONDecodeError:
            # Fallback: render as plain text
            st.markdown("### Results")
            st.markdown(output_text)


def render_recommendations(data: dict):
    recommendations = data.get("recommendations", [])
    overall = data.get("overall_insight", "")

    if overall:
        st.info(f"💡 {overall}")

    for rec in recommendations:
        rank = rec.get("rank", "")
        name = rec.get("name", "Unknown")
        rtype = rec.get("type", "")
        url = rec.get("url", "#")
        summary = rec.get("summary", "")
        strengths = rec.get("strengths", [])
        weaknesses = rec.get("weaknesses", [])
        best_for = rec.get("best_for", "")
        score = rec.get("score", 0)

        with st.container():
            st.markdown(
                f'<span class="rank-badge">#{rank}</span> '
                f'<span class="score-badge">Score: {score}</span> '
                f'<span class="tag">{rtype}</span>',
                unsafe_allow_html=True
            )
            st.markdown(f"### [{name}]({url})")
            st.markdown(summary)

            col_s, col_w = st.columns(2)
            with col_s:
                if strengths:
                    st.markdown("**✅ Strengths**")
                    for s in strengths:
                        st.markdown(f"- {s}")
            with col_w:
                if weaknesses:
                    st.markdown("**⚠️ Weaknesses**")
                    for w in weaknesses:
                        st.markdown(f"- {w}")

            if best_for:
                st.caption(f"🎯 Best for: {best_for}")

            # Feedback buttons
            fb_col1, fb_col2, _ = st.columns([1, 1, 6])
            with fb_col1:
                if st.button("👍", key=f"up_{name}"):
                    httpx.post(f"{API_URL}/feedback", json={
                        "item_name": name, "feedback": "up"
                    })
                    st.toast(f"Thanks for the feedback on {name}")
            with fb_col2:
                if st.button("👎", key=f"down_{name}"):
                    httpx.post(f"{API_URL}/feedback", json={
                        "item_name": name, "feedback": "down"
                    })
                    st.toast(f"Noted — we'll adjust rankings")

            st.divider()


def render_comparison(data: dict):
    comparison = data.get("comparison", {})
    item_one = comparison.get("item_one", {})
    item_two = comparison.get("item_two", {})
    winner_for = comparison.get("winner_for", {})
    final_rec = comparison.get("final_recommendation", "")

    st.markdown("## ⚖️ Comparison")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"### {item_one.get('name', 'Item 1')}")
        st.markdown(item_one.get("verdict", ""))
    with col2:
        st.markdown(f"### {item_two.get('name', 'Item 2')}")
        st.markdown(item_two.get("verdict", ""))

    st.divider()
    st.markdown("### 🏆 Winner by use case")
    for use_case, winner in winner_for.items():
        st.markdown(f"**{use_case.replace('_', ' ').title()}** → {winner}")

    if final_rec:
        st.success(f"**Final Recommendation:** {final_rec}")


# --- Run Search ---
if search_clicked and query.strip():
    with results_placeholder.container():
        with st.spinner("Agents are working..."):
            try:
                response = httpx.post(
                    f"{API_URL}/recommend",
                    json={"query": query},
                    timeout=60.0
                )
                result = response.json()

                if "error" in result:
                    st.error(f"Error: {result['error']}")
                else:
                    render_trace(result.get("agent_trace", []))
                    render_output(result.get("output", ""), result.get("mode", "recommendations"))
                    render_session()

            except httpx.TimeoutException:
                st.error("Request timed out. The agents took too long — try a simpler query.")
            except Exception as e:
                st.error(f"Could not reach API: {str(e)}")

elif search_clicked:
    with results_placeholder.container():
        st.warning("Please enter a query first.")

# Initial session render
render_session()