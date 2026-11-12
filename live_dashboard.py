from pathlib import Path
from datetime import datetime
import html
import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from PIL import Image, UnidentifiedImageError
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="VISIONTRACK | Operations", layout="wide", initial_sidebar_state="expanded")
BASE = Path(__file__).resolve().parent
CSV_FILE = BASE / "events.csv"
FRAME_FILE = BASE / "latest_frame.jpg"
REFRESH_MS = 2000
st_autorefresh(interval=REFRESH_MS, key="vt_refresh")

BG = "#0A0F16"
PANEL = "#121B26"
LINE = "#253344"
TEXT = "#E8EFF6"
MUTED = "#91A4B8"
CYAN = "#43C6DC"
GREEN = "#42C7A2"
AMBER = "#E7AD62"

st.markdown("""
<style>
:root { color-scheme: dark; }
.stApp {background:#0A0F16;color:#E8EFF6;font-family:'Segoe UI',Arial,sans-serif;}
[data-testid="stHeader"] {background:transparent;}
[data-testid="stSidebar"] {background:#101823;border-right:1px solid #253344;}
[data-testid="stSidebar"] .block-container {padding-top:1.4rem;}
.block-container {max-width:1480px;padding-top:1.35rem;padding-bottom:2rem;}
#MainMenu,footer {visibility:hidden;}
h1,h2,h3 {letter-spacing:-.035em!important;color:#E8EFF6!important;}
h1 {font-size:1.7rem!important;font-weight:650!important;}
h2 {font-size:1.05rem!important;font-weight:600!important;}
h3 {font-size:.95rem!important;}
[data-testid="stVerticalBlock"] {gap:.65rem;}
[data-testid="stMetric"] {background:#121B26;border:1px solid #253344;border-radius:9px;padding:15px;}
[data-testid="stMetricLabel"] {color:#91A4B8;}
[data-testid="stMetricValue"] {color:#E8EFF6;}
[data-testid="stImage"] img {border-radius:7px;}
[data-testid="stDataFrame"] {border:1px solid #253344;border-radius:8px;}
.stButton button,.stDownloadButton button {background:#162636;border:1px solid #315066;color:#DDEBF2;border-radius:7px;}
.stButton button:hover,.stDownloadButton button:hover {border-color:#43C6DC;color:#43C6DC;}
[data-baseweb="select"]>div {background:#121B26;border-color:#253344;}
hr {border-color:#253344!important;}
.vt-brand {font-size:22px;font-weight:750;letter-spacing:.11em;color:#E8EFF6;}
.vt-kicker {font-size:10px;letter-spacing:.15em;text-transform:uppercase;color:#91A4B8;font-weight:650;}
.vt-muted {font-size:12px;color:#91A4B8;}
.vt-section {font-size:14px;font-weight:650;color:#E8EFF6;margin:0 0 8px;}
.vt-card {background:#121B26;border:1px solid #253344;border-radius:9px;padding:18px 20px;min-height:111px;}
.vt-card .label {font-size:10px;letter-spacing:.11em;color:#91A4B8;font-weight:650;}
.vt-card .value {font-size:30px;line-height:1.4;font-weight:650;font-variant-numeric:tabular-nums;color:#E8EFF6;}
.vt-card .note {font-size:11px;color:#91A4B8;}
.vt-panel-head {background:#121B26;border:1px solid #253344;border-bottom:0;border-radius:9px 9px 0 0;padding:12px 16px;display:flex;justify-content:space-between;align-items:center;}
.vt-panel-title {font-size:12px;font-weight:650;color:#E8EFF6;}
.vt-pill {font-size:10px;letter-spacing:.06em;border:1px solid #315066;background:#152A35;color:#43C6DC;padding:5px 9px;border-radius:5px;white-space:nowrap;}
.vt-pill.off {border-color:#5D4736;background:#30231B;color:#E7AD62;}
.vt-note {color:#91A4B8;font-size:11px;padding:8px 0;}
.vt-rule {height:1px;background:#253344;margin:10px 0 17px;}
.vt-status-row {padding:10px 0;border-bottom:1px solid #253344;display:flex;justify-content:space-between;font-size:12px;color:#91A4B8;gap:10px;}
.vt-status-row strong {color:#E8EFF6;font-weight:550;text-align:right;}
.vt-logo-line {width:27px;height:3px;background:#43C6DC;margin-bottom:13px;border-radius:3px;}
.vt-topline {display:flex;justify-content:space-between;align-items:center;gap:12px;}
.vt-table-title {font-size:13px;font-weight:650;color:#E8EFF6;}
@media(max-width:800px){.vt-card {padding:12px;min-height:96px;}.vt-card .value{font-size:23px;}}
</style>
""", unsafe_allow_html=True)

COLUMNS = ["timestamp", "label", "event_type"]

@st.cache_data(ttl=1, show_spinner=False)
def load_events(path, modified_ns):
    try:
        df = pd.read_csv(path)
        if not set(COLUMNS).issubset(df.columns):
            return pd.DataFrame(columns=COLUMNS), "CSV headers do not match expected format"
        df = df[COLUMNS].copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df["label"] = df["label"].fillna("Unknown").astype(str).str.strip()
        df["event_type"] = df["event_type"].fillna("").astype(str).str.strip().str.upper()
        df = df.dropna(subset=["timestamp"])
        df = df[df["event_type"].isin(["ENTRY", "EXIT"])]
        return df, None
    except (OSError, UnicodeError, pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
        return pd.DataFrame(columns=COLUMNS), str(exc)

if CSV_FILE.exists():
    events, csv_error = load_events(str(CSV_FILE), CSV_FILE.stat().st_mtime_ns)
else:
    events, csv_error = pd.DataFrame(columns=COLUMNS), "events.csv not found"

entries = int((events["event_type"] == "ENTRY").sum())
exits = int((events["event_type"] == "EXIT").sum())
occupancy = max(0, entries - exits)
total_events = len(events)
frame_exists = FRAME_FILE.exists()
frame_age = max(0, time.time() - FRAME_FILE.stat().st_mtime) if frame_exists else None
camera_online = frame_age is not None and frame_age < 10
last_event = events["timestamp"].max() if not events.empty else None


def metric_card(label, value, note):
    st.markdown(
        f'<div class="vt-card"><div class="label">{html.escape(label)}</div>'
        f'<div class="value">{value:,}</div><div class="note">{html.escape(note)}</div></div>',
        unsafe_allow_html=True,
    )


def section_title(title, subtitle=None):
    st.markdown(f'<div class="vt-section">{html.escape(title)}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="vt-muted">{html.escape(subtitle)}</div>', unsafe_allow_html=True)


def chart_style(fig, height=275):
    fig.update_layout(
        template="plotly_dark", height=height,
        paper_bgcolor=PANEL, plot_bgcolor=PANEL,
        font=dict(family="Segoe UI, Arial", color=MUTED, size=11),
        margin=dict(l=18, r=18, t=25, b=20),
        legend=dict(orientation="h", y=1.15, x=0, title=None),
        xaxis=dict(showgrid=False, zeroline=False, linecolor=LINE),
        yaxis=dict(gridcolor=LINE, zeroline=False),
        hoverlabel=dict(bgcolor="#1B2A38"),
    )
    return fig


def show_events(df, height=310):
    if df.empty:
        st.info("No matching events recorded.")
        return
    view = df.sort_values("timestamp", ascending=False).copy()
    view["timestamp"] = view["timestamp"].dt.strftime("%d %b %Y  |  %H:%M:%S")
    view = view.rename(columns={"timestamp":"Timestamp", "label":"Object class", "event_type":"Event"})
    st.dataframe(view, hide_index=True, use_container_width=True, height=height)


with st.sidebar:
    st.markdown('<div class="vt-logo-line"></div><div class="vt-brand">VISIONTRACK</div>', unsafe_allow_html=True)
    st.markdown('<div class="vt-kicker" style="margin-top:6px">Object intelligence platform</div>', unsafe_allow_html=True)
    st.markdown('<div class="vt-rule" style="margin-top:25px"></div>', unsafe_allow_html=True)
    st.markdown('<div class="vt-kicker">Workspace</div>', unsafe_allow_html=True)
    page = st.radio("Workspace", ["Overview", "Analytics", "Event history", "System health"], label_visibility="collapsed")
    st.markdown('<div class="vt-rule"></div><div class="vt-kicker">System status</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="vt-status-row"><span>Camera source</span><strong style="color:{GREEN if camera_online else AMBER}">{"ACTIVE" if camera_online else "INACTIVE"}</strong></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="vt-status-row"><span>Event storage</span><strong>{"AVAILABLE" if csv_error is None else "CHECK FILE"}</strong></div>', unsafe_allow_html=True)
    st.markdown('<div class="vt-status-row"><span>Detection engine</span><strong>YOLO11 / ByteTrack</strong></div>', unsafe_allow_html=True)
    st.markdown('<div class="vt-muted" style="margin-top:35px">VISIONTRACK  /  MONITORING CONSOLE<br>Local deployment  ·  Version 2.0</div>', unsafe_allow_html=True)

st.markdown('<div class="vt-kicker">Operations / '+html.escape(page)+'</div>', unsafe_allow_html=True)
st.markdown('<div class="vt-topline"><div><h1 style="margin:6px 0 2px">'+html.escape({"Overview":"Monitoring overview", "Analytics":"Traffic analytics", "Event history":"Event history", "System health":"System health"}[page])+'</h1><div class="vt-muted">Real-time object monitoring and recorded crossing intelligence</div></div><span class="vt-pill '+('' if camera_online else 'off')+'">'+('LIVE SOURCE' if camera_online else 'SOURCE INACTIVE')+'</span></div>', unsafe_allow_html=True)
st.markdown('<div class="vt-rule" style="margin-top:20px"></div>', unsafe_allow_html=True)

if csv_error:
    st.warning(f"Event data: {csv_error}")

if page == "Overview":
    cols = st.columns(4, gap="small")
    for col, args in zip(cols, [
        ("TOTAL ENTRIES", entries, "Recorded crossing events"),
        ("TOTAL EXITS", exits, "Recorded crossing events"),
        ("EST. OCCUPANCY", occupancy, "Entries minus exits"),
        ("TOTAL EVENTS", total_events, "All valid CSV records"),
    ]):
        with col:
            metric_card(*args)
    st.write("")
    camera_col, activity_col = st.columns([1.65, 1], gap="medium")
    with camera_col:
        st.markdown('<div class="vt-panel-head"><span class="vt-panel-title">Camera 01  /  Detection viewport</span><span class="vt-pill '+('' if camera_online else 'off')+'">'+('STREAM ACTIVE' if camera_online else 'LAST CAPTURE')+'</span></div>', unsafe_allow_html=True)
        if frame_exists:
            try:
                with Image.open(FRAME_FILE) as im:
                    frame = im.convert("RGB").copy()
                st.image(frame, use_container_width=True)
            except (OSError, ValueError, UnidentifiedImageError):
                st.info("Frame is being written. Waiting for next refresh.")
        else:
            st.info("No frame available. Run python main.py to begin monitoring.")
        age_text = f"{int(frame_age)} seconds ago" if frame_age is not None else "Not available"
        st.markdown(f'<div class="vt-note">Frame update: {html.escape(age_text)}  |  Source: latest_frame.jpg  |  Refresh: 2 seconds</div>', unsafe_allow_html=True)
    with activity_col:
        st.markdown('<div class="vt-panel-head"><span class="vt-panel-title">Crossing distribution</span><span class="vt-pill">HISTORICAL</span></div>', unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=[entries, exits], y=["Entry", "Exit"], orientation="h", marker_color=[GREEN, CYAN], text=[entries, exits], textposition="outside", cliponaxis=False))
        chart_style(fig, 230)
        fig.update_layout(showlegend=False, xaxis_title=None, yaxis_title=None, xaxis=dict(showgrid=True, gridcolor=LINE), yaxis=dict(showgrid=False, autorange="reversed"))
        fig.update_xaxes(range=[0, max(entries, exits, 1) * 1.25])
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
        share = f"{entries / total_events * 100:.1f}%" if total_events else "0.0%"
        st.markdown(f'<div class="vt-status-row"><span>Recorded entry share</span><strong>{share}</strong></div>', unsafe_allow_html=True)
        last_text = last_event.strftime("%d %b %Y, %H:%M:%S") if last_event is not None else "No recorded events"
        st.markdown(f'<div class="vt-status-row"><span>Latest recorded event</span><strong>{html.escape(last_text)}</strong></div>', unsafe_allow_html=True)
        st.markdown('<div class="vt-note">Totals are accumulated from events.csv, not the current camera session.</div>', unsafe_allow_html=True)
    st.write("")
    section_title("Recent crossings", "Most recent recorded entry and exit events")
    show_events(events.head(0) if events.empty else events.sort_values("timestamp", ascending=False).head(8), 300)

elif page == "Analytics":
    cols = st.columns(3)
    for col, args in zip(cols, [("ENTRY EVENTS", entries, "Cumulative"), ("EXIT EVENTS", exits, "Cumulative"), ("UNIQUE CLASSES", events["label"].nunique(), "In crossing log")]):
        with col:
            metric_card(*args)
    st.write("")
    left, right = st.columns(2, gap="medium")
    with left:
        section_title("Crossings by object class")
        if not events.empty:
            grouped = events.groupby(["label", "event_type"]).size().unstack(fill_value=0).sort_index()
            fig = go.Figure()
            for event, color in [("ENTRY", GREEN), ("EXIT", CYAN)]:
                fig.add_trace(go.Bar(name=event.title(), x=grouped.index.tolist(), y=grouped[event] if event in grouped else [0]*len(grouped), marker_color=color))
            chart_style(fig, 315)
            fig.update_layout(barmode="group", xaxis_title=None, yaxis_title="Events")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
        else:
            st.info("Waiting for event records.")
    with right:
        section_title("Hourly crossing volume")
        if not events.empty:
            hourly = events.assign(hour=events["timestamp"].dt.hour).groupby(["hour", "event_type"]).size().unstack(fill_value=0).reindex(range(24), fill_value=0)
            fig = go.Figure()
            for event, color in [("ENTRY", GREEN), ("EXIT", CYAN)]:
                fig.add_trace(go.Scatter(x=hourly.index, y=hourly[event] if event in hourly else [0]*24, mode="lines+markers", name=event.title(), line=dict(color=color, width=2), marker=dict(size=5)))
            chart_style(fig, 315)
            fig.update_layout(xaxis=dict(dtick=3, showgrid=False, title="Hour of day"), yaxis_title="Events")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
        else:
            st.info("Waiting for event records.")
    section_title("Daily activity", "Entry and exit counts grouped by date")
    if not events.empty:
        daily = events.assign(day=events["timestamp"].dt.strftime("%Y-%m-%d")).groupby(["day", "event_type"]).size().unstack(fill_value=0)
        fig = go.Figure()
        for event, color in [("ENTRY", GREEN), ("EXIT", CYAN)]:
            fig.add_trace(go.Bar(x=daily.index.tolist(), y=daily[event] if event in daily else [0]*len(daily), name=event.title(), marker_color=color))
        chart_style(fig, 265)
        fig.update_layout(barmode="group", xaxis_title=None, yaxis_title="Events")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
    else:
        st.info("No daily activity yet.")

elif page == "Event history":
    section_title("Recorded crossing events", "Filter and export the local CSV event history")
    left, mid, right = st.columns([1, 1, 1.4])
    with left:
        event_filter = st.selectbox("Event type", ["All", "ENTRY", "EXIT"])
    with mid:
        object_filter = st.selectbox("Object class", ["All"] + sorted(events["label"].unique().tolist()))
    with right:
        query = st.text_input("Search object", placeholder="Search by object label")
    filtered = events.copy()
    if event_filter != "All":
        filtered = filtered[filtered["event_type"] == event_filter]
    if object_filter != "All":
        filtered = filtered[filtered["label"] == object_filter]
    if query.strip():
        filtered = filtered[filtered["label"].str.contains(query.strip(), case=False, regex=False, na=False)]
    st.markdown(f'<div class="vt-note">Showing {len(filtered):,} of {total_events:,} recorded events</div>', unsafe_allow_html=True)
    show_events(filtered, 530)
    st.download_button("Export filtered CSV", data=filtered.sort_values("timestamp", ascending=False).to_csv(index=False).encode("utf-8"), file_name="visiontrack_filtered_events.csv", mime="text/csv")

else:
    section_title("Deployment diagnostics", "Local files and data-source health")
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown('<div class="vt-panel-head"><span class="vt-panel-title">Runtime components</span></div>', unsafe_allow_html=True)
        for label, value in [("Application", "VISIONTRACK"), ("Detection model", "YOLO11 nano"), ("Tracking engine", "ByteTrack"), ("Dashboard", "Streamlit"), ("Refresh interval", "2 seconds")]:
            st.markdown(f'<div class="vt-status-row"><span>{html.escape(label)}</span><strong>{html.escape(value)}</strong></div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="vt-panel-head"><span class="vt-panel-title">Data sources</span></div>', unsafe_allow_html=True)
        for label, value in [("Camera snapshot", "Available" if frame_exists else "Missing"), ("Camera freshness", "Active" if camera_online else "Inactive"), ("Event CSV", "Available" if csv_error is None else "Unavailable"), ("CSV rows", str(total_events)), ("Latest frame age", f"{int(frame_age)} seconds" if frame_age is not None else "Unknown")]:
            st.markdown(f'<div class="vt-status-row"><span>{html.escape(label)}</span><strong>{html.escape(value)}</strong></div>', unsafe_allow_html=True)
    st.write("")
    st.info("Camera status indicates whether the snapshot file was updated within 10 seconds. It does not independently verify camera hardware connectivity.")
    st.info("Occupancy is an estimate from recorded crossing events. CSV totals persist across tracker restarts; the overlay on the camera frame may reset.")

st.markdown('<div class="vt-rule" style="margin-top:26px"></div><div class="vt-muted">VISIONTRACK  /  OBJECT INTELLIGENCE PLATFORM  ·  LOCAL OPERATIONS CONSOLE</div>', unsafe_allow_html=True)
