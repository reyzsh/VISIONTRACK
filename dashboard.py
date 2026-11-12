"""VISIONTRACK — Streamlit dashboard.

Replace ``load_dashboard_data`` with an adapter to the project's detector and
counter outputs. This UI deliberately contains no detection or tracking logic.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(
    page_title="VISIONTRACK | Real Time Object Intelligence",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --- Demo data adapter -----------------------------------------------------
# Keep this return shape when wiring in real modules:
# {
#   "metrics": {"current_objects": int, "total_entered": int,
#               "total_exited": int, "total_tracked": int},
#   "timeline": DataFrame[time, entries, exits],
#   "events": DataFrame[time, direction, object, location, confidence],
#   "object_statistics": {class_name: current_count},
#   "occupancy_percent": int,
#   "camera_frame": optional image bytes / array,
#   "camera_status": str,
# }
def load_dashboard_data() -> dict[str, Any]:
    """Return deterministic sample data; replace this adapter with live data."""
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    times = pd.date_range(end=now, periods=24, freq="h")
    timeline = pd.DataFrame(
        {
            "time": times,
            "entries": [2, 4, 3, 1, 0, 2, 5, 8, 11, 9, 7, 10,
                        13, 12, 8, 6, 9, 14, 12, 10, 8, 6, 4, 7],
            "exits": [1, 2, 3, 2, 1, 1, 3, 5, 7, 10, 8, 6,
                      9, 11, 10, 8, 7, 10, 13, 12, 10, 8, 6, 5],
        }
    )
    events = pd.DataFrame(
        [
            (now - timedelta(minutes=2), "ENTRY", "Person", "North entrance", 98),
            (now - timedelta(minutes=5), "EXIT", "Vehicle", "Gate 02", 96),
            (now - timedelta(minutes=8), "ENTRY", "Person", "Lobby", 94),
            (now - timedelta(minutes=13), "EXIT", "Person", "South exit", 99),
            (now - timedelta(minutes=17), "ENTRY", "Bicycle", "North entrance", 91),
            (now - timedelta(minutes=22), "ENTRY", "Person", "Lobby", 97),
        ],
        columns=["time", "direction", "object", "location", "confidence"],
    )
    return {
        "metrics": {
            "current_objects": 37,
            "total_entered": 248,
            "total_exited": 211,
            "total_tracked": 286,
        },
        "object_statistics": {"Person": 21, "Vehicle": 9, "Bicycle": 4, "Other": 3},
        "occupancy_percent": 37,
        "timeline": timeline,
        "events": events,
        "camera_frame": None,
        "camera_status": "Demo feed",
    }


# --- Visual system ---------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
    :root { --bg:#080b10; --panel:#10151d; --line:#202936; --muted:#8390a2; --text:#edf2f8; --lime:#b8f36b; --cyan:#55d9d0; }
    html, body, [class*="css"] { font-family:'Manrope',sans-serif; }
    .stApp { background:radial-gradient(ellipse at 12% -15%,#172332 0%,transparent 43%),var(--bg); color:var(--text); }
    [data-testid="stHeader"] { background:transparent; }
    [data-testid="stSidebar"] { background:#0b0f15; border-right:1px solid var(--line); }
    [data-testid="stSidebar"] > div { padding-top:1.6rem; }
    .block-container { max-width:1600px; padding:2rem 2.7rem 3rem; }
    .brand { font-size:1.7rem; letter-spacing:.17em; font-weight:800; color:#f4f7fb; }
    .brand-dot { color:var(--lime); }
    .subtitle { color:#95a2b3; font-size:.82rem; letter-spacing:.08em; margin-top:.16rem; }
    .topline { border-bottom:1px solid var(--line); padding-bottom:1.35rem; margin-bottom:1.4rem; }
    .eyebrow { color:var(--lime); font:500 .68rem 'DM Mono',monospace; letter-spacing:.16em; text-transform:uppercase; }
    .section-title { color:#eaf0f7; font-weight:700; font-size:1.03rem; margin:0 0 .15rem; }
    .section-caption { color:var(--muted); font-size:.76rem; margin-bottom:.9rem; }
    .metric-card { background:linear-gradient(145deg,#121923,#0f141c); border:1px solid var(--line); border-radius:12px; padding:1rem 1.15rem .95rem; min-height:108px; position:relative; overflow:hidden; }
    .metric-card:after { content:''; position:absolute; width:76px; height:76px; border-radius:50%; right:-28px; top:-30px; background:rgba(184,243,107,.055); }
    .metric-label { color:#95a2b3; font-size:.72rem; letter-spacing:.04em; }
    .metric-value { color:#f2f6fb; font-size:1.8rem; line-height:1.35; font-weight:700; letter-spacing:-.04em; }
    .metric-foot { color:#718094; font: .63rem 'DM Mono',monospace; }
    .panel { background:#0e131a; border:1px solid var(--line); border-radius:14px; padding:1rem 1.1rem; }
    .feed { height:350px; border-radius:10px; overflow:hidden; position:relative; border:1px solid #2a3643; background:linear-gradient(180deg,rgba(7,12,18,.14),rgba(6,10,15,.45)),radial-gradient(ellipse at 52% 60%,#36434b 0%,#222e35 32%,#111a21 75%); }
    .feed:before { content:''; position:absolute; inset:0; opacity:.27; background:repeating-linear-gradient(0deg,transparent,transparent 3px,rgba(0,0,0,.2) 4px); }
    .feed-grid { position:absolute; inset:0; background:linear-gradient(90deg,transparent 49.8%,rgba(172,203,215,.18) 50%,transparent 50.2%),linear-gradient(0deg,transparent 49.8%,rgba(172,203,215,.14) 50%,transparent 50.2%); }
    .feed-floor { position:absolute; bottom:0; width:100%; height:36%; background:linear-gradient(180deg,transparent,#0c1318 85%); clip-path:polygon(22% 0,78% 0,100% 100%,0 100%); border-top:1px solid #74818a; }
    .feed-lane { position:absolute; left:49.7%; bottom:0; height:34%; width:1px; background:linear-gradient(transparent,#8b979b); transform:perspective(120px) rotateX(30deg); }
    .person { position:absolute; bottom:23%; width:17px; height:54px; border-radius:9px 9px 3px 3px; background:linear-gradient(90deg,#929c9b,#515d63); box-shadow:0 0 18px #9cb0b633; }
    .person:before { content:''; position:absolute; width:15px; height:15px; border-radius:50%; background:#adb6b1; top:-13px; left:1px; }
    .p1 { left:39%; transform:scale(.88); }.p2 { left:62%; bottom:19%; transform:scale(1.05); }
    .bbox { position:absolute; border:1px solid var(--lime); box-shadow:0 0 12px #b8f36b22; }
    .bbox span { position:absolute; top:-19px; left:-1px; background:var(--lime); color:#11170c; font:500 9px 'DM Mono',monospace; padding:2px 5px; white-space:nowrap; }
    .box1 { left:37%; bottom:19%; width:39px; height:91px; }.box2 { left:60%; bottom:16%; width:42px; height:99px; }
    .cam-label { position:absolute; z-index:2; top:13px; left:14px; color:#e7edf2; font:10px 'DM Mono',monospace; letter-spacing:.08em; }
    .live-pill { position:absolute; z-index:2; right:13px; top:12px; border:1px solid #f16e6e77; border-radius:20px; padding:4px 8px; background:#221414cc; color:#ff8585; font:9px 'DM Mono',monospace; }
    .live-pill i { display:inline-block; width:6px; height:6px; background:#ff6868; border-radius:50%; margin-right:5px; box-shadow:0 0 7px #ff6868; }
    .feed-footer { color:#8390a2; display:flex; justify-content:space-between; font:9px 'DM Mono',monospace; padding:.55rem .1rem 0; }
    .status-dot { color:var(--lime); }
    div[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:9px; overflow:hidden; }
    .sidebar-brand { font-size:1.35rem; letter-spacing:.15em; font-weight:800; }
    .sidebar-note { color:#728096; font-size:.73rem; line-height:1.6; }
    .stSelectbox label { color:#aeb8c6!important; font-size:.78rem!important; }
    .stButton button { border:1px solid #354251; background:#131a23; color:#dbe4ed; border-radius:8px; }
    .stButton button:hover { border-color:var(--lime); color:var(--lime); }
    @media(max-width:900px) { .block-container { padding:1.2rem 1rem 2rem; } .feed { height:280px; } }
    </style>
    """,
    unsafe_allow_html=True,
)


data = load_dashboard_data()
metrics = data["metrics"]
timeline = data["timeline"].copy()
events = data["events"].copy()
object_statistics = data["object_statistics"]
occupancy_percent = data["occupancy_percent"]

with st.sidebar:
    st.markdown('<div class="sidebar-brand">VISION<span style="color:#b8f36b">TRACK</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-note">REAL TIME OBJECT INTELLIGENCE</div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown('<div class="eyebrow">MONITORING</div>', unsafe_allow_html=True)
    camera = st.selectbox("Camera source", ["North Entrance · CAM-01", "Lobby · CAM-02", "South Exit · CAM-03"])
    timeframe = st.selectbox("Analytics window", ["Last 24 hours", "Last 12 hours", "Last 6 hours"])
    st.markdown("---")
    st.markdown('<div class="eyebrow">SYSTEM STATUS</div>', unsafe_allow_html=True)
    st.markdown('<div style="margin-top:10px;color:#c9d2dd;font-size:.82rem"><span style="color:#b8f36b">●</span> &nbsp;All systems operational</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-note" style="margin-top:8px">Data source: demo adapter<br>Model pipeline: ready to connect</div>', unsafe_allow_html=True)
    st.markdown("---")
    if st.button("↻  Refresh dashboard", use_container_width=True):
        st.rerun()

# Header
header_left, header_right = st.columns([3, 1])
with header_left:
    st.markdown('<div class="topline"><div class="brand">VISION<span class="brand-dot">TRACK</span></div><div class="subtitle">Real Time Object Intelligence</div></div>', unsafe_allow_html=True)
with header_right:
    st.markdown(f'<div style="text-align:right;padding-top:13px"><div class="eyebrow">● &nbsp;SYSTEM ONLINE</div><div style="color:#778497;font:10px DM Mono,monospace;margin-top:7px">{datetime.now().strftime("%a, %d %b %Y · %H:%M:%S")}</div></div>', unsafe_allow_html=True)

# KPI row
kpis = [
    ("CURRENT OBJECTS", metrics["current_objects"], "Visible in monitored area", "◉"),
    ("TOTAL ENTERED", metrics["total_entered"], "Cumulative inbound count", "↘"),
    ("TOTAL EXITED", metrics["total_exited"], "Cumulative outbound count", "↗"),
    ("TOTAL TRACKED", metrics["total_tracked"], "Unique objects observed", "◎"),
]
cols = st.columns(4, gap="medium")
for col, (label, value, foot, icon) in zip(cols, kpis):
    with col:
        st.markdown(f'<div class="metric-card"><div class="metric-label">{label} <span style="float:right;color:#b8f36b">{icon}</span></div><div class="metric-value">{value:,}</div><div class="metric-foot">{foot}</div></div>', unsafe_allow_html=True)

st.markdown("<div style='height:1.4rem'></div>", unsafe_allow_html=True)

# Main: camera feed and object stats
left, right = st.columns([1.62, 1], gap="medium")
with left:
    st.markdown('<div class="section-title">Live camera feed</div><div class="section-caption">Object detections · monitored zone</div>', unsafe_allow_html=True)
    frame = data.get("camera_frame")
    if frame is not None:
        st.image(frame, use_container_width=True)
    else:
        st.markdown(
            f'<div class="feed"><div class="feed-grid"></div><div class="feed-floor"></div><div class="feed-lane"></div><div class="person p1"></div><div class="person p2"></div><div class="bbox box1"><span>PERSON · 98%</span></div><div class="bbox box2"><span>PERSON · 96%</span></div><div class="cam-label">{camera.upper()} &nbsp;·&nbsp; {data.get("camera_status", "DEMO FEED").upper()}</div><div class="live-pill"><i></i>DEMO</div></div><div class="feed-footer"><span><span class="status-dot">●</span> &nbsp;SIGNAL SIMULATED · CONNECT CAMERA SOURCE TO GO LIVE</span><span>1080P · 24 FPS</span></div>',
            unsafe_allow_html=True,
        )
with right:
    st.markdown('<div class="section-title">Object statistics</div><div class="section-caption">Live composition across this camera</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    object_colors = ["#b8f36b", "#55d9d0", "#f4b860", "#9a8dff"]
    object_total = sum(object_statistics.values()) or 1
    for index, (object_class, current_count) in enumerate(object_statistics.items()):
        share = round(current_count / object_total * 100)
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:10px;padding:12px 0;border-bottom:1px solid #202936"><div style="width:7px;height:7px;border-radius:50%;background:{object_colors[index % len(object_colors)]}"></div><div style="flex:1;color:#cbd4df;font-size:.82rem">{object_class}</div><div style="color:#f1f5fa;font:500 .85rem DM Mono,monospace">{current_count:02d}</div><div style="width:42px;text-align:right;color:#748195;font: .68rem DM Mono,monospace">{share}%</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown(f'<div style="padding-top:15px;display:flex;justify-content:space-between;color:#8a97a8;font-size:.76rem"><span>Objects in view</span><span style="color:#eaf0f7;font-family:DM Mono,monospace">{metrics["current_objects"]:02d}</span></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="panel" style="padding:.85rem 1rem"><div class="eyebrow">OCCUPANCY</div><div style="display:flex;align-items:baseline;gap:7px;margin-top:4px"><span style="font-size:1.55rem;font-weight:700;color:#edf2f8">{occupancy_percent}%</span><span style="font-size:.72rem;color:#8390a2">of monitored capacity</span></div><div style="height:5px;background:#232d38;border-radius:5px;margin-top:9px"><div style="width:{occupancy_percent}%;height:5px;background:linear-gradient(90deg,#72ce88,#b8f36b);border-radius:5px"></div></div></div>', unsafe_allow_html=True)

st.markdown("<div style='height:1.65rem'></div>", unsafe_allow_html=True)

# Lower section: event log and analytics chart
lower_left, lower_right = st.columns([1, 1.35], gap="medium")
with lower_left:
    st.markdown('<div class="section-title">Recent entry &amp; exit events</div><div class="section-caption">Latest object movements · newest first</div>', unsafe_allow_html=True)
    event_view = events.copy()
    event_view["time"] = pd.to_datetime(event_view["time"]).dt.strftime("%H:%M:%S")
    event_view["confidence"] = event_view["confidence"].astype(str) + "%"
    event_view.columns = ["Time", "Direction", "Object", "Location", "Confidence"]
    st.dataframe(event_view, hide_index=True, use_container_width=True, height=285)
with lower_right:
    st.markdown('<div class="section-title">Traffic analytics</div><div class="section-caption">Entries and exits over time</div>', unsafe_allow_html=True)
    hours = {"Last 24 hours": 24, "Last 12 hours": 12, "Last 6 hours": 6}[timeframe]
    chart_data = timeline.tail(hours)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=chart_data["time"], y=chart_data["entries"], name="Entries", mode="lines+markers", line={"color": "#b8f36b", "width": 2.5}, marker={"size": 5}, fill="tozeroy", fillcolor="rgba(184,243,107,.07)"))
    fig.add_trace(go.Scatter(x=chart_data["time"], y=chart_data["exits"], name="Exits", mode="lines+markers", line={"color": "#55d9d0", "width": 2.5}, marker={"size": 5}, fill="tozeroy", fillcolor="rgba(85,217,208,.045)"))
    fig.update_layout(
        height=285,
        margin={"l": 4, "r": 8, "t": 16, "b": 4},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "DM Mono, monospace", "size": 10, "color": "#8491a2"},
        legend={"orientation": "h", "y": 1.14, "x": 0.0, "font": {"size": 10}},
        xaxis={"showgrid": False, "tickformat": "%H:%M", "linecolor": "#293440", "tickfont": {"color": "#788698"}},
        yaxis={"showgrid": True, "gridcolor": "#202936", "zeroline": False, "title": None, "tickfont": {"color": "#788698"}},
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

st.markdown('<div style="text-align:center;color:#596779;font:9px DM Mono,monospace;padding-top:25px;letter-spacing:.08em">VISIONTRACK &nbsp;·&nbsp; OBJECT INTELLIGENCE PLATFORM &nbsp;·&nbsp; DEMO DATA</div>', unsafe_allow_html=True)
