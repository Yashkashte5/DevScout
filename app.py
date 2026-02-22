import streamlit as st
import httpx
import json
import re

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="DevScout",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;400;600;700&display=swap');

:root {
    --bg-primary: #020408;
    --bg-secondary: #050d14;
    --bg-card: #060f18;
    --accent-primary: #00f5a0;
    --accent-secondary: #00c8ff;
    --accent-warn: #ff6b35;
    --accent-danger: #ff2d55;
    --text-primary: #e2f4ff;
    --text-secondary: #7ab8d4;
    --text-muted: #2d5a72;
    --border: #0d2d40;
    --glow-green: 0 0 10px #00f5a040, 0 0 30px #00f5a015;
    --glow-blue: 0 0 10px #00c8ff40, 0 0 30px #00c8ff15;
}

* { box-sizing: border-box; }

html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    font-family: 'Rajdhani', sans-serif !important;
}

[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(ellipse at 20% 20%, #001a2e 0%, transparent 50%),
        radial-gradient(ellipse at 80% 80%, #001420 0%, transparent 50%),
        repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,245,160,0.012) 2px, rgba(0,245,160,0.012) 4px),
        var(--bg-primary) !important;
}

[data-testid="stHeader"] { display: none !important; }
[data-testid="stSidebar"] { display: none !important; }
section[data-testid="stMain"] > div { padding: 0 !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }

::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: var(--bg-primary); }
::-webkit-scrollbar-thumb { background: var(--accent-primary); border-radius: 2px; }

.header-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 32px;
    background: rgba(0,245,160,0.03);
    border-bottom: 1px solid rgba(0,245,160,0.15);
    backdrop-filter: blur(10px);
}

.header-logo {
    font-family: 'Orbitron', monospace;
    font-weight: 900;
    font-size: 1.4rem;
    color: var(--accent-primary);
    text-shadow: var(--glow-green);
    letter-spacing: 4px;
    display: flex;
    align-items: center;
    gap: 12px;
}

.header-sub {
    font-size: 0.55rem;
    color: var(--text-muted);
    letter-spacing: 2px;
    font-family: 'Share Tech Mono', monospace;
    line-height: 1.6;
}

.header-status { display: flex; gap: 28px; align-items: center; }

.status-dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    background: var(--accent-primary);
    box-shadow: var(--glow-green);
    animation: blink 2s infinite;
    display: inline-block;
    margin-right: 6px;
}

@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }

.stat-block { text-align: right; }
.stat-label { font-family:'Share Tech Mono',monospace; font-size:0.55rem; color:var(--text-muted); letter-spacing:2px; text-transform:uppercase; }
.stat-val { font-family:'Share Tech Mono',monospace; font-size:0.8rem; color:var(--accent-secondary); }

.search-label {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.62rem;
    color: var(--accent-primary);
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-bottom: 10px;
}
.search-label::before { content: '// '; color: var(--text-muted); }

.result-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent-primary);
    padding: 22px;
    margin-bottom: 14px;
    position: relative;
    transition: all 0.2s ease;
    clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 10px 100%, 0 calc(100% - 10px));
}

.result-card:hover {
    border-color: rgba(0,200,255,0.5);
    border-left-color: var(--accent-secondary);
    background: rgba(0,200,255,0.03);
}

.result-card::after {
    content:'';
    position:absolute;
    top:0; right:0;
    width:10px; height:10px;
    background: var(--accent-primary);
    clip-path: polygon(0 0,100% 0,100% 100%);
    opacity:0.3;
}

.result-id { font-family:'Share Tech Mono',monospace; font-size:0.55rem; color:var(--text-muted); letter-spacing:2px; margin-bottom:6px; }

.result-chips { display:flex; gap:8px; margin-bottom:10px; flex-wrap:wrap; }

.chip-score {
    font-family:'Share Tech Mono',monospace; font-size:0.68rem;
    background:rgba(0,245,160,0.08); color:var(--accent-primary);
    border:1px solid rgba(0,245,160,0.25); padding:2px 10px;
}
.chip-type {
    font-family:'Share Tech Mono',monospace; font-size:0.65rem;
    background:rgba(0,200,255,0.06); color:var(--accent-secondary);
    border:1px solid rgba(0,200,255,0.18); padding:2px 10px;
}

.result-name {
    font-family:'Orbitron',monospace; font-size:0.95rem; font-weight:700;
    color:var(--text-primary); text-decoration:none; letter-spacing:1px;
    display:block; margin-bottom:10px; transition:color 0.2s;
}
.result-name:hover { color:var(--accent-primary); }

.result-summary { font-size:0.88rem; color:var(--text-secondary); line-height:1.6; margin-bottom:14px; font-weight:300; }

.traits-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:12px; }
.trait-heading { font-family:'Share Tech Mono',monospace; font-size:0.58rem; letter-spacing:2px; text-transform:uppercase; margin-bottom:5px; }
.trait-item { font-size:0.78rem; color:var(--text-secondary); padding:2px 0 2px 12px; position:relative; font-weight:300; }
.trait-item::before { content:'›'; position:absolute; left:0; font-weight:700; }
.trait-item.s::before { color:var(--accent-primary); }
.trait-item.w::before { color:var(--accent-warn); }

.best-for {
    font-family:'Share Tech Mono',monospace; font-size:0.62rem; color:var(--text-muted);
    padding:6px 12px; border-left:2px solid var(--accent-primary);
    background:rgba(0,245,160,0.03); margin-bottom:12px; letter-spacing:1px;
}
.best-for em { color:var(--accent-primary); font-style:normal; }

.insight-bar {
    background:rgba(0,245,160,0.04); border:1px solid rgba(0,245,160,0.12);
    border-left:3px solid var(--accent-primary); padding:12px 18px;
    margin-bottom:20px; display:flex; gap:12px; align-items:flex-start;
}
.insight-text { font-size:0.85rem; color:var(--text-secondary); line-height:1.5; font-weight:300; }

.panel-title {
    font-family:'Orbitron',monospace; font-size:0.58rem; color:var(--accent-primary);
    letter-spacing:3px; text-transform:uppercase; margin-bottom:14px;
    display:flex; align-items:center; gap:8px;
}
.panel-title::after { content:''; flex:1; height:1px; background:rgba(0,245,160,0.15); }

.trace-step { display:flex; gap:10px; margin-bottom:12px; position:relative; }
.trace-step:not(:last-child)::before {
    content:''; position:absolute; left:9px; top:20px; bottom:-12px;
    width:1px; background:linear-gradient(to bottom,rgba(0,245,160,0.3),transparent);
}
.trace-dot {
    width:18px; height:18px; border:1px solid var(--accent-primary); border-radius:50%;
    display:flex; align-items:center; justify-content:center; font-size:0.55rem;
    flex-shrink:0; margin-top:2px; background:rgba(0,245,160,0.05); color:var(--accent-primary);
}
.trace-agent { font-family:'Share Tech Mono',monospace; font-size:0.68rem; color:var(--accent-primary); letter-spacing:1px; margin-bottom:2px; }
.trace-action { font-size:0.7rem; color:var(--text-muted); line-height:1.4; font-weight:300; }

.sess-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
.sess-card { background:rgba(0,200,255,0.04); border:1px solid rgba(0,200,255,0.1); padding:10px; }
.sess-label { font-family:'Share Tech Mono',monospace; font-size:0.52rem; color:var(--text-muted); letter-spacing:2px; text-transform:uppercase; margin-bottom:4px; }
.sess-val { font-family:'Orbitron',monospace; font-size:0.85rem; color:var(--accent-secondary); }

.empty-state {
    padding:70px 28px; text-align:center;
}
.empty-title { font-family:'Orbitron',monospace; font-size:2.5rem; color:rgba(0,245,160,0.05); letter-spacing:10px; margin-bottom:20px; }
.empty-lines { font-family:'Share Tech Mono',monospace; font-size:0.68rem; color:var(--text-muted); letter-spacing:3px; line-height:2.2; }

.stTextInput > div > div {
    background:var(--bg-card) !important; border:1px solid var(--border) !important;
    border-radius:0 !important; color:var(--text-primary) !important;
    font-family:'Share Tech Mono',monospace !important; font-size:0.85rem !important;
    transition:border-color 0.2s !important;
}
.stTextInput > div > div:focus-within { border-color:var(--accent-primary) !important; box-shadow:var(--glow-green) !important; }
.stTextInput input { color:var(--accent-primary) !important; font-family:'Share Tech Mono',monospace !important; caret-color:var(--accent-primary) !important; }
.stTextInput input::placeholder { color:var(--text-muted) !important; }

div[data-testid="stButton"] > button {
    background:transparent !important; border:1px solid var(--accent-primary) !important;
    color:var(--accent-primary) !important; font-family:'Orbitron',monospace !important;
    font-size:0.6rem !important; letter-spacing:3px !important; text-transform:uppercase !important;
    border-radius:0 !important; padding:10px 20px !important; transition:all 0.2s !important;
    clip-path:polygon(0 0,calc(100% - 7px) 0,100% 7px,100% 100%,7px 100%,0 calc(100% - 7px)) !important;
    width:100% !important;
}
div[data-testid="stButton"] > button:hover { background:rgba(0,245,160,0.08) !important; box-shadow:var(--glow-green) !important; }
div[data-testid="stButton"] > button[kind="primary"] { background:rgba(0,245,160,0.06) !important; }

.stSelectbox > div > div {
    background:var(--bg-card) !important; border:1px solid var(--border) !important;
    border-radius:0 !important; color:var(--text-primary) !important;
    font-family:'Share Tech Mono',monospace !important; font-size:0.72rem !important;
}
.stSelectbox svg { color:var(--accent-primary) !important; }

.stAlert { border-radius:0 !important; font-family:'Share Tech Mono',monospace !important; font-size:0.75rem !important; }
#MainMenu, footer, header { visibility:hidden !important; }
</style>
""", unsafe_allow_html=True)


# ─── SESSION HELPER ──────────────────────────────────────────────────────

def get_session():
    try:
        return httpx.get(f"{API_URL}/session/state", timeout=3).json()
    except Exception:
        return {}


def parse_output(output) -> dict:
    if isinstance(output, dict):
        return output
    if isinstance(output, str):
        text = output.strip()
        if "```" in text:
            for part in text.split("```"):
                if part.startswith("json"):
                    text = part[4:].strip(); break
                elif part.strip().startswith("{"):
                    text = part.strip(); break
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        m = re.search(r'\{[\s\S]*\}', text)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
    return {"raw_text": str(output)}


# ─── HEADER ──────────────────────────────────────────────────────────────

sess = get_session()
last_q = sess.get("last_query") or "—"
result_count = sess.get("result_count", 0)
pref = sess.get("preferences", {}).get("prioritize", "balanced").upper()

st.markdown(f"""
<div class="header-bar">
    <div class="header-logo">
        🔭 DEVSCOUT
        <div class="header-sub">
            MULTI-AGENT RESOURCE ADVISOR<br>
            <span style="color:rgba(0,245,160,0.4)">GOOGLE ADK + GROQ + LITELLM</span>
        </div>
    </div>
    <div class="header-status">
        <div class="stat-block">
            <div class="stat-label"><span class="status-dot"></span>SYSTEM</div>
            <div class="stat-val">ONLINE</div>
        </div>
        <div class="stat-block">
            <div class="stat-label">LAST QUERY</div>
            <div class="stat-val" style="font-size:0.65rem;max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{last_q}</div>
        </div>
        <div class="stat-block">
            <div class="stat-label">RESULTS</div>
            <div class="stat-val">{result_count}</div>
        </div>
        <div class="stat-block">
            <div class="stat-label">MODE</div>
            <div class="stat-val">{pref}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ─── LAYOUT ──────────────────────────────────────────────────────────────

left, right = st.columns([3, 1], gap="small")

ICONS = {"coordinator":"◎","discovery_agent":"◈","ranking_agent":"▣","explanation_agent":"◉"}

with right:
    st.markdown('<div style="padding:18px 16px 0">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">⬡ AGENT TRACE</div>', unsafe_allow_html=True)
    trace_ph = st.empty()
    st.markdown('<div style="height:1px;background:var(--border);margin:16px 0"></div>', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">◈ SESSION</div>', unsafe_allow_html=True)
    sess_ph = st.empty()
    st.markdown('<div style="height:1px;background:var(--border);margin:16px 0"></div>', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">▣ PRIORITY</div>', unsafe_allow_html=True)
    prioritize = st.selectbox("Priority", ["balanced","recency","popularity","stability"], label_visibility="collapsed")
    if st.button("CLEAR SESSION", key="clr"):
        try:
            httpx.post(f"{API_URL}/session/clear")
            st.rerun()
        except Exception:
            pass
    st.markdown('</div>', unsafe_allow_html=True)


def render_trace(trace):
    if not trace:
        trace_ph.markdown('<div style="font-family:\'Share Tech Mono\',monospace;font-size:0.65rem;color:var(--text-muted);">// AWAITING QUERY</div>', unsafe_allow_html=True)
        return
    html = ""
    for s in trace:
        agent = s.get("agent","")
        action = s.get("action","")
        icon = ICONS.get(agent,"○")
        html += f'<div class="trace-step"><div class="trace-dot">{icon}</div><div><div class="trace-agent">{agent}</div><div class="trace-action">{action[:80]}</div></div></div>'
    trace_ph.markdown(html, unsafe_allow_html=True)


def render_session(s):
    rc = s.get("result_count",0)
    fb = s.get("feedback_count",0)
    pr = s.get("preferences",{}).get("prioritize","balanced").upper()
    sess_ph.markdown(f"""
    <div class="sess-grid">
        <div class="sess-card"><div class="sess-label">Results</div><div class="sess-val">{rc}</div></div>
        <div class="sess-card"><div class="sess-label">Feedback</div><div class="sess-val">{fb}</div></div>
        <div class="sess-card" style="grid-column:1/-1"><div class="sess-label">Priority Mode</div><div class="sess-val" style="font-size:0.7rem">{pr}</div></div>
    </div>""", unsafe_allow_html=True)


with left:
    st.markdown('<div style="padding:24px 24px 16px">', unsafe_allow_html=True)
    st.markdown('<div class="search-label">QUERY INPUT — NATURAL LANGUAGE SEARCH</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([5,1], gap="small")
    with c1:
        query = st.text_input("q", placeholder="› find production-ready FastAPI auth libraries with Redis...", label_visibility="collapsed")
    with c2:
        search = st.button("SCAN ›", type="primary", key="scan")
    st.markdown('<div style="height:1px;background:var(--border);margin:18px 0 0"></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    results_ph = st.empty()


def render_recommendations(data):
    recs = data.get("recommendations",[])
    insight = data.get("overall_insight","")

    if not recs:
        results_ph.markdown('<div style="padding:20px 24px;font-family:\'Share Tech Mono\',monospace;font-size:0.75rem;color:var(--text-muted);">// NO RESULTS — TRY A DIFFERENT QUERY</div>', unsafe_allow_html=True)
        return

    with results_ph.container():
        if insight:
            st.markdown(f'<div style="padding:0 24px 14px"><div class="insight-bar"><div style="font-size:1rem;flex-shrink:0">◈</div><div class="insight-text">{insight}</div></div></div>', unsafe_allow_html=True)

        for rec in recs:
            rank = rec.get("rank","")
            name = rec.get("name","Unknown")
            rtype = rec.get("type","")
            url = rec.get("url","#")
            summary = rec.get("summary","")
            strengths = rec.get("strengths",[])
            weaknesses = rec.get("weaknesses",[])
            best_for = rec.get("best_for","")
            score = rec.get("score",0)

            s_html = "".join([f'<div class="trait-item s">{x}</div>' for x in strengths])
            w_html = "".join([f'<div class="trait-item w">{x}</div>' for x in weaknesses])
            bf_html = f'<div class="best-for">OPTIMAL FOR › <em>{best_for}</em></div>' if best_for else ""

            st.markdown(f"""
            <div style="padding:0 24px 2px">
            <div class="result-card">
                <div class="result-id">TARGET_{rank:02d} // REPOSITORY MATCH</div>
                <div class="result-chips">
                    <span class="chip-score">SCORE {score}</span>
                    <span class="chip-type">{rtype.upper()}</span>
                </div>
                <a href="{url}" target="_blank" class="result-name">{name}</a>
                <div class="result-summary">{summary}</div>
                <div class="traits-grid">
                    <div>
                        <div class="trait-heading" style="color:var(--accent-primary)">// STRENGTHS</div>
                        {s_html}
                    </div>
                    <div>
                        <div class="trait-heading" style="color:var(--accent-warn)">// WEAKNESSES</div>
                        {w_html}
                    </div>
                </div>
                {bf_html}
            </div>
            </div>""", unsafe_allow_html=True)

            fb1, fb2, _ = st.columns([1,1,10], gap="small")
            with fb1:
                if st.button("[ + ]", key=f"u_{rank}_{name[:10]}"):
                    try:
                        httpx.post(f"{API_URL}/feedback", json={"item_name":name,"feedback":"up"})
                        st.toast("Signal recorded ✓")
                    except Exception:
                        pass
            with fb2:
                if st.button("[ - ]", key=f"d_{rank}_{name[:10]}"):
                    try:
                        httpx.post(f"{API_URL}/feedback", json={"item_name":name,"feedback":"down"})
                        st.toast("Preference updated ✓")
                    except Exception:
                        pass


def render_comparison(data):
    comp = data.get("comparison",{})
    one = comp.get("item_one",{})
    two = comp.get("item_two",{})
    winners = comp.get("winner_for",{})
    final = comp.get("final_recommendation","")

    with results_ph.container():
        st.markdown('<div style="padding:0 24px 16px"><div style="font-family:\'Orbitron\',monospace;font-size:0.65rem;color:var(--accent-secondary);letter-spacing:3px;border-bottom:1px solid var(--border);padding-bottom:10px">⬡ HEAD-TO-HEAD ANALYSIS</div></div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2, gap="small")
        for col, item, label in [(c1,one,"ALPHA"),(c2,two,"BETA")]:
            with col:
                st.markdown(f"""
                <div style="padding:0 12px 12px">
                <div class="result-card">
                    <div class="result-id">CANDIDATE_{label}</div>
                    <div class="result-name" style="font-size:0.85rem">{item.get("name","—")}</div>
                    <div class="result-summary">{item.get("verdict","")}</div>
                </div></div>""", unsafe_allow_html=True)

        if winners:
            rows = "".join([
                f'<div style="display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid var(--border)">'
                f'<span style="font-family:\'Share Tech Mono\',monospace;font-size:0.65rem;color:var(--text-muted);letter-spacing:1px">{k.replace("_"," ").upper()}</span>'
                f'<span style="font-family:\'Share Tech Mono\',monospace;font-size:0.72rem;color:var(--accent-primary)">{v}</span></div>'
                for k,v in winners.items()
            ])
            st.markdown(f'<div style="padding:0 24px 14px"><div style="font-family:\'Orbitron\',monospace;font-size:0.55rem;color:var(--text-muted);letter-spacing:2px;margin-bottom:10px">WINNER BY USE CASE</div>{rows}</div>', unsafe_allow_html=True)

        if final:
            st.markdown(f'<div style="padding:0 24px"><div class="insight-bar"><div>◉</div><div class="insight-text">{final}</div></div></div>', unsafe_allow_html=True)


def render_output(output, mode):
    data = parse_output(output)
    if "raw_text" in data and not data.get("recommendations") and not data.get("comparison"):
        results_ph.markdown(f'<div style="padding:20px 24px;font-family:\'Share Tech Mono\',monospace;font-size:0.78rem;color:var(--text-secondary)">{data["raw_text"]}</div>', unsafe_allow_html=True)
        return
    if mode == "comparison" or data.get("mode") == "comparison":
        render_comparison(data)
    else:
        render_recommendations(data)


# ─── SEARCH EXECUTION ────────────────────────────────────────────────────

if search and query.strip():
    results_ph.markdown("""
    <div style="padding:60px 24px;text-align:center">
        <div style="font-family:'Orbitron',monospace;font-size:0.68rem;color:var(--accent-primary);letter-spacing:4px;animation:blink 1s infinite">◈ SCANNING REPOSITORIES...</div>
        <div style="font-family:'Share Tech Mono',monospace;font-size:0.62rem;color:var(--text-muted);margin-top:10px;letter-spacing:2px">AGENTS ACTIVE — PLEASE WAIT 20-40s</div>
    </div>""", unsafe_allow_html=True)

    try:
        response = httpx.post(f"{API_URL}/recommend", json={"query": query}, timeout=180.0)
        result = response.json()

        if "error" in result:
            results_ph.markdown(f'<div style="padding:20px 24px"><div style="font-family:\'Share Tech Mono\',monospace;font-size:0.78rem;color:var(--accent-danger);border-left:3px solid var(--accent-danger);padding-left:12px">// ERROR: {result["error"]}</div></div>', unsafe_allow_html=True)
        else:
            render_trace(result.get("agent_trace",[]))
            render_output(result.get("output"), result.get("mode","recommendations"))
            render_session(get_session())

    except httpx.TimeoutException:
        results_ph.markdown('<div style="padding:20px 24px"><div style="font-family:\'Share Tech Mono\',monospace;font-size:0.78rem;color:var(--accent-warn);border-left:3px solid var(--accent-warn);padding-left:12px">// TIMEOUT — RETRY IN 30s</div></div>', unsafe_allow_html=True)
    except Exception as e:
        results_ph.markdown(f'<div style="padding:20px 24px"><div style="font-family:\'Share Tech Mono\',monospace;font-size:0.78rem;color:var(--accent-danger);border-left:3px solid var(--accent-danger);padding-left:12px">// CONNECTION ERROR: {str(e)}</div></div>', unsafe_allow_html=True)

elif search:
    results_ph.markdown('<div style="padding:20px 24px;font-family:\'Share Tech Mono\',monospace;font-size:0.72rem;color:var(--text-muted);">// INPUT REQUIRED</div>', unsafe_allow_html=True)

else:
    results_ph.markdown("""
    <div class="empty-state">
        <div class="empty-title">DEVSCOUT</div>
        <div class="empty-lines">
            // MULTI-AGENT DEVELOPER RESOURCE DISCOVERY<br>
            // ENTER QUERY TO INITIALIZE SCAN<br>
            // SUPPORTS NATURAL LANGUAGE SEARCH<br>
            // TRY: "production-ready FastAPI auth with Redis"
        </div>
    </div>""", unsafe_allow_html=True)

render_session(sess)
render_trace([])