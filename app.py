"""
Retailerz - Retail Inventory & Stock Analytics Management System.
Production-grade business intelligence dashboard connected to MongoDB via PyMongo.
"""
import json
from datetime import datetime, timezone
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pymongo.errors import PyMongoError

import config
from database.connection import DatabaseConnectionError, get_database
from database.indexes import initialize_database
from services import analytics_service as an
from services import product_service as ps
from services import stock_service as ss
from services import supplier_service as sup
from services.errors import AppError

# -----------------------------------------------------------------------------
# Application Configuration & Restrained Design System
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Retailerz | Inventory Management",
    layout="wide",
    initial_sidebar_state="expanded"
)

CUR = config.CURRENCY_SYMBOL

# Restrained Minimalist Dark Theme CSS
CUSTOM_CSS = """
<style>
    /* Typography */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"], .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        background-color: #0B0F14 !important;
        color: #F3F6FC !important;
    }

    code, pre {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Fixed Top Navigation Bar - Compact, Crisp, Aligned */
    header[data-testid="stHeader"] {
        height: 3.25rem !important;
        background: #111720 !important;
        border-bottom: 1px solid #2A3545 !important;
        z-index: 999990 !important;
        display: flex !important;
        align-items: center !important;
    }

    header[data-testid="stHeader"]::before {
        content: "Retailerz | Inventory Management";
        position: absolute;
        left: 4.8rem;
        top: 50%;
        transform: translateY(-50%);
        font-family: 'Inter', sans-serif;
        font-size: 0.92rem;
        font-weight: 600;
        color: #F3F6FC;
        letter-spacing: -0.01em;
        pointer-events: none;
    }

    header[data-testid="stHeader"]::after {
        content: "● Connected";
        position: absolute;
        left: 21.2rem;
        top: 50%;
        transform: translateY(-50%);
        font-family: 'Inter', sans-serif;
        font-size: 0.72rem;
        font-weight: 500;
        color: #14B8A6;
        background: #171F2B;
        border: 1px solid #2A3545;
        border-radius: 4px;
        padding: 0.12rem 0.55rem;
        pointer-events: none;
    }

    @media (max-width: 900px) {
        header[data-testid="stHeader"]::after {
            display: none !important;
        }
    }

    /* Main Container Padding & Boundary Alignment */
    .block-container {
        padding-top: 4.75rem !important;
        padding-bottom: 3.5rem !important;
        max-width: 1280px !important;
        margin-left: auto !important;
        margin-right: auto !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
    }

    /* Page Header */
    .page-header {
        margin-bottom: 1.5rem;
        padding-bottom: 0.85rem;
        border-bottom: 1px solid #2A3545;
    }

    .page-title {
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        color: #F3F6FC !important;
        letter-spacing: -0.025em !important;
        margin: 0 !important;
        line-height: 1.2 !important;
    }

    .page-subtitle {
        font-size: 0.86rem !important;
        color: #9AA9BC !important;
        margin-top: 0.35rem !important;
        margin-bottom: 0 !important;
        line-height: 1.4 !important;
    }

    /* KPI Metric Cards - Premium Elevated Surfaces */
    .kpi-card {
        background: #171F2B;
        border: 1px solid #2A3545;
        border-radius: 8px;
        padding: 1.15rem 1.25rem;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
        transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }

    .kpi-card:hover {
        border-color: #38475E;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.35);
    }

    .kpi-card-warning {
        border-color: rgba(245, 158, 11, 0.45) !important;
        background: linear-gradient(180deg, #1C2330 0%, #171F2B 100%) !important;
    }

    .kpi-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0.45rem;
    }

    .kpi-title {
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #9AA9BC;
    }

    .kpi-icon-badge {
        width: 28px;
        height: 28px;
        border-radius: 6px;
        background: #1C2634;
        border: 1px solid #2A3545;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #9AA9BC;
        flex-shrink: 0;
    }

    .kpi-icon-badge-warning {
        background: rgba(245, 158, 11, 0.12) !important;
        border-color: rgba(245, 158, 11, 0.4) !important;
        color: #F59E0B !important;
    }

    .kpi-value {
        font-size: 1.85rem;
        font-weight: 700;
        letter-spacing: -0.025em;
        color: #F3F6FC;
        line-height: 1.15;
        margin: 0.25rem 0;
    }

    .kpi-value-warning {
        color: #F59E0B !important;
    }

    .kpi-footnote {
        font-size: 0.74rem;
        color: #9AA9BC;
        margin-top: 0.35rem;
        line-height: 1.3;
    }

    /* Elevated Chart Panel Container */
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        background: #171F2B !important;
        border: 1px solid #2A3545 !important;
        border-radius: 8px !important;
        padding: 1.15rem 1.25rem 0.75rem 1.25rem !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25) !important;
    }

    .chart-panel {
        background: #171F2B;
        border: 1px solid #2A3545;
        border-radius: 8px;
        padding: 1.1rem 1.25rem 0.5rem 1.25rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
    }

    .chart-panel-header {
        margin-bottom: 0.65rem;
    }

    .chart-panel-title {
        font-size: 0.95rem;
        font-weight: 600;
        color: #F3F6FC;
        letter-spacing: -0.01em;
        margin: 0;
    }

    .chart-panel-subtitle {
        font-size: 0.76rem;
        color: #9AA9BC;
        margin-top: 0.2rem;
    }

    /* Section Subheadings */
    .section-heading {
        font-size: 0.95rem;
        font-weight: 600;
        color: #F3F6FC;
        margin-top: 1.25rem;
        margin-bottom: 0.6rem;
    }

    /* Info Callouts */
    .info-callout {
        background: #171F2B;
        border: 1px solid #2A3545;
        border-left: 3px solid #14B8A6;
        border-radius: 6px;
        padding: 0.85rem 1.1rem;
        font-size: 0.84rem;
        color: #9AA9BC;
        margin-bottom: 1.1rem;
    }

    .info-callout-warning {
        border-left-color: #F59E0B !important;
    }

    .info-callout-danger {
        border-left-color: #F87171 !important;
    }

    /* Form Controls & Buttons */
    div.stButton > button {
        border-radius: 6px !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        border: 1px solid #14B8A6 !important;
        background-color: #14B8A6 !important;
        color: #0B0F14 !important;
        padding: 0.5rem 1.15rem !important;
        transition: all 0.15s ease !important;
    }

    div.stButton > button:hover:not(:disabled) {
        background-color: #0D9488 !important;
        border-color: #0D9488 !important;
        color: #FFFFFF !important;
    }

    div.stButton > button:disabled {
        background-color: #171F2B !important;
        border-color: #2A3545 !important;
        color: #64748B !important;
        cursor: not-allowed !important;
    }

    div.destructive-btn > div.stButton > button {
        background-color: rgba(248, 113, 113, 0.12) !important;
        border-color: #F87171 !important;
        color: #F87171 !important;
    }

    div.destructive-btn > div.stButton > button:hover:not(:disabled) {
        background-color: #EF4444 !important;
        border-color: #EF4444 !important;
        color: #FFFFFF !important;
    }

    /* Inputs, Selectboxes, and Textareas */
    div[data-baseweb="input"], div[data-baseweb="select"] {
        border-radius: 6px !important;
        background-color: #171F2B !important;
        border-color: #2A3545 !important;
    }

    div[data-baseweb="input"] input {
        color: #F3F6FC !important;
    }

    div[data-baseweb="input"]:focus-within, div[data-baseweb="select"]:focus-within {
        border-color: #14B8A6 !important;
        box-shadow: 0 0 0 1px #14B8A6 !important;
    }

    /* Sidebar Navigation Links */
    [data-testid="stSidebar"] {
        background-color: #111720 !important;
        border-right: 1px solid #2A3545 !important;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] > div {
        gap: 0.25rem !important;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        display: flex !important;
        align-items: center !important;
        background-color: transparent !important;
        border: 1px solid transparent !important;
        border-left: 3px solid transparent !important;
        border-radius: 6px !important;
        padding: 0.55rem 0.85rem !important;
        margin: 0 0 0.2rem 0 !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
        background-color: #171F2B !important;
        border-color: #2A3545 !important;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
        background-color: rgba(20, 184, 166, 0.12) !important;
        border-color: rgba(20, 184, 166, 0.25) !important;
        border-left: 3px solid #14B8A6 !important;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label > div:first-child {
        display: none !important;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label p {
        font-size: 0.88rem !important;
        font-weight: 500 !important;
        color: #9AA9BC !important;
        margin: 0 !important;
        display: flex !important;
        align-items: center !important;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p {
        color: #F3F6FC !important;
        font-weight: 600 !important;
    }

    /* Sidebar Navigation Line Icons */
    [data-testid="stSidebar"] [data-testid="stRadio"] label:nth-of-type(1) p::before,
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input[value="Overview"]) p::before {
        content: "";
        display: inline-block;
        width: 15px;
        height: 15px;
        margin-right: 0.65rem;
        background-color: currentColor;
        -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect width='7' height='9' x='3' y='3' rx='1'/%3E%3Crect width='7' height='5' x='14' y='3' rx='1'/%3E%3Crect width='7' height='9' x='14' y='12' rx='1'/%3E%3Crect width='7' height='5' x='3' y='16' rx='1'/%3E%3C/svg%3E") no-repeat center / contain;
        mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect width='7' height='9' x='3' y='3' rx='1'/%3E%3Crect width='7' height='5' x='14' y='3' rx='1'/%3E%3Crect width='7' height='9' x='14' y='12' rx='1'/%3E%3Crect width='7' height='5' x='3' y='16' rx='1'/%3E%3C/svg%3E") no-repeat center / contain;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label:nth-of-type(2) p::before,
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input[value="Products"]) p::before {
        content: "";
        display: inline-block;
        width: 15px;
        height: 15px;
        margin-right: 0.65rem;
        background-color: currentColor;
        -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m7.5 4.27 9 5.15'/%3E%3Cpath d='M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z'/%3E%3Cpath d='m3.3 7 8.7 5 8.7-5'/%3E%3Cpath d='M12 22V12'/%3E%3C/svg%3E") no-repeat center / contain;
        mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m7.5 4.27 9 5.15'/%3E%3Cpath d='M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z'/%3E%3Cpath d='m3.3 7 8.7 5 8.7-5'/%3E%3Cpath d='M12 22V12'/%3E%3C/svg%3E") no-repeat center / contain;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label:nth-of-type(3) p::before,
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input[value="Suppliers"]) p::before {
        content: "";
        display: inline-block;
        width: 15px;
        height: 15px;
        margin-right: 0.65rem;
        background-color: currentColor;
        -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect width='16' height='20' x='4' y='2' rx='2' ry='2'/%3E%3Cpath d='M9 22v-4h6v4'/%3E%3Cpath d='M8 6h.01'/%3E%3Cpath d='M16 6h.01'/%3E%3Cpath d='M12 6h.01'/%3E%3Cpath d='M12 10h.01'/%3E%3Cpath d='M12 14h.01'/%3E%3Cpath d='M16 10h.01'/%3E%3Cpath d='M16 14h.01'/%3E%3Cpath d='M8 10h.01'/%3E%3Cpath d='M8 14h.01'/%3E%3C/svg%3E") no-repeat center / contain;
        mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect width='16' height='20' x='4' y='2' rx='2' ry='2'/%3E%3Cpath d='M9 22v-4h6v4'/%3E%3Cpath d='M8 6h.01'/%3E%3Cpath d='M16 6h.01'/%3E%3Cpath d='M12 6h.01'/%3E%3Cpath d='M12 10h.01'/%3E%3Cpath d='M12 14h.01'/%3E%3Cpath d='M16 10h.01'/%3E%3Cpath d='M16 14h.01'/%3E%3Cpath d='M8 10h.01'/%3E%3Cpath d='M8 14h.01'/%3E%3C/svg%3E") no-repeat center / contain;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label:nth-of-type(4) p::before,
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input[value="Stock Movements"]) p::before {
        content: "";
        display: inline-block;
        width: 15px;
        height: 15px;
        margin-right: 0.65rem;
        background-color: currentColor;
        -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m16 3 4 4-4 4'/%3E%3Cpath d='M20 7H4'/%3E%3Cpath d='m8 21-4-4 4-4'/%3E%3Cpath d='M4 17h16'/%3E%3C/svg%3E") no-repeat center / contain;
        mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m16 3 4 4-4 4'/%3E%3Cpath d='M20 7H4'/%3E%3Cpath d='m8 21-4-4 4-4'/%3E%3Cpath d='M4 17h16'/%3E%3C/svg%3E") no-repeat center / contain;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label:nth-of-type(5) p::before,
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input[value="Reports"]) p::before {
        content: "";
        display: inline-block;
        width: 15px;
        height: 15px;
        margin-right: 0.65rem;
        background-color: currentColor;
        -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cline x1='12' x2='12' y1='20' y2='10'/%3E%3Cline x1='18' x2='18' y1='20' y2='4'/%3E%3Cline x1='6' x2='6' y1='20' y2='16'/%3E%3C/svg%3E") no-repeat center / contain;
        mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cline x1='12' x2='12' y1='20' y2='10'/%3E%3Cline x1='18' x2='18' y1='20' y2='4'/%3E%3Cline x1='6' x2='6' y1='20' y2='16'/%3E%3C/svg%3E") no-repeat center / contain;
    }

    /* Tabs Styling */
    div[data-testid="stTabs"] button {
        font-size: 0.88rem !important;
        font-weight: 500 !important;
        color: #9AA9BC !important;
        border-bottom: 2px solid transparent !important;
        padding: 0.6rem 1.1rem !important;
    }

    div[data-testid="stTabs"] button[aria-selected="true"] {
        color: #F3F6FC !important;
        border-bottom: 2px solid #14B8A6 !important;
        font-weight: 600 !important;
    }

    /* Dataframe Table Container */
    div[data-testid="stDataFrame"] {
        border: 1px solid #2A3545 !important;
        border-radius: 8px !important;
        background-color: #171F2B !important;
        overflow: hidden !important;
    }

    /* Expander Container */
    div[data-testid="stExpander"] {
        border: 1px solid #2A3545 !important;
        border-radius: 6px !important;
        background-color: #171F2B !important;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Database Connection & Helper Utilities
# -----------------------------------------------------------------------------
@st.cache_resource(show_spinner="Connecting to MongoDB...")
def _connect():
    db = get_database()
    initialize_database(db)  # Idempotent: strict validators + indexes only
    return db


def _df(docs, columns=None) -> pd.DataFrame:
    df = pd.DataFrame(docs)
    if df.empty:
        return df
    df = df.drop(columns=[c for c in ("_id",) if c in df.columns])
    for col in df.columns:
        if col.endswith("_at") or col.endswith("_date"):
            df[col] = pd.to_datetime(df[col]).dt.strftime("%Y-%m-%d %H:%M")
    return df[columns] if columns else df


def _run(action, success=None):
    """Executes a service call; displays meaningful error alerts without silencing exceptions."""
    try:
        result = action()
        if success:
            st.success(success(result) if callable(success) else success)
        return result
    except AppError as exc:
        st.error(f"Validation constraint: {exc}")
    except PyMongoError as exc:
        st.error(f"Database error: {exc}")
    return None


def _money(x) -> str:
    return f"{CUR}{x:,.2f}"


# Safe Connection Bootstrap
try:
    db = _connect()
except DatabaseConnectionError as exc:
    st.error(f"Connection Failure: {exc}")
    st.info("Ensure the local MongoDB Server service is running or check your MONGODB_URI environment variable.")
    st.stop()


# -----------------------------------------------------------------------------
# Sidebar Navigation & System Monitor
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
        <div style="padding: 0.25rem 0 1.25rem 0; border-bottom: 1px solid #2A3545; margin-bottom: 1.25rem;">
            <div style="display: flex; align-items: center; gap: 0.75rem;">
                <div style="width: 32px; height: 32px; border-radius: 7px; background: rgba(20, 184, 166, 0.12); border: 1px solid rgba(20, 184, 166, 0.28); display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#14B8A6" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m7.5 4.27 9 5.15"/><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/></svg>
                </div>
                <div>
                    <div style="font-size: 1.08rem; font-weight: 700; color: #F3F6FC; letter-spacing: -0.02em; line-height: 1.2;">Retailerz</div>
                    <div style="font-size: 0.7rem; color: #9AA9BC; font-weight: 600; letter-spacing: 0.04em;">INVENTORY ANALYTICS</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "Navigation",
        [
            "Overview",
            "Products",
            "Suppliers",
            "Stock Movements",
            "Reports"
        ],
        label_visibility="collapsed"
    )

    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
    st.markdown("---")

    # Compact, understated MongoDB connection status panel
    try:
        db.client.server_info()
        status_text = "Connected"
        status_color = "#14B8A6"
        status_bg = "rgba(20, 184, 166, 0.12)"
    except Exception:
        status_text = "Disconnected"
        status_color = "#F87171"
        status_bg = "rgba(248, 113, 113, 0.12)"

    st.markdown(f"""
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 0.55rem 0.8rem; background: #171F2B; border: 1px solid #2A3545; border-radius: 6px; font-size: 0.76rem; color: #9AA9BC;">
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <span style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background-color: {status_color};"></span>
                <span style="color: #9AA9BC; font-weight: 500;">Database</span>
            </div>
            <span style="background: {status_bg}; color: {status_color}; font-weight: 600; font-size: 0.7rem; padding: 0.12rem 0.5rem; border-radius: 4px; border: 1px solid {status_color}33;">
                {status_text}
            </span>
        </div>
    """, unsafe_allow_html=True)


# =============================================================================
# 1. OVERVIEW PAGE
# =============================================================================
def page_overview():
    st.markdown("""
        <div class="page-header">
            <h1 class="page-title">Overview</h1>
            <p class="page-subtitle">Summary of current inventory levels, capital valuation, and category distribution.</p>
        </div>
    """, unsafe_allow_html=True)

    # MongoDB KPI Aggregation
    s = an.dashboard_summary(db)
    low_stock_count = s.get("low_stock_count", 0)

    # 4 Consistent Elevated KPI Cards
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-header">
                    <span class="kpi-title">Total Products</span>
                    <div class="kpi-icon-badge">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m7.5 4.27 9 5.15"/><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/></svg>
                    </div>
                </div>
                <div class="kpi-value">{s['total_products']}</div>
                <div class="kpi-footnote">Active inventory items</div>
            </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-header">
                    <span class="kpi-title">Units in Stock</span>
                    <div class="kpi-icon-badge">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.29 7 12 12 20.71 7"/><line x1="12" y1="22" x2="12" y2="12"/></svg>
                    </div>
                </div>
                <div class="kpi-value">{s['total_units']:,}</div>
                <div class="kpi-footnote">Physical units on hand</div>
            </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-header">
                    <span class="kpi-title">Estimated Inventory Value</span>
                    <div class="kpi-icon-badge">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                    </div>
                </div>
                <div class="kpi-value">{_money(s['estimated_inventory_value'])}</div>
                <div class="kpi-footnote">Valuation at selling price</div>
            </div>
        """, unsafe_allow_html=True)
    with k4:
        card_class = "kpi-card kpi-card-warning" if low_stock_count > 0 else "kpi-card"
        badge_class = "kpi-icon-badge kpi-icon-badge-warning" if low_stock_count > 0 else "kpi-icon-badge"
        val_class = "kpi-value kpi-value-warning" if low_stock_count > 0 else "kpi-value"
        sub_text = "Items at or below safety threshold" if low_stock_count > 0 else "All stock levels healthy"
        st.markdown(f"""
            <div class="{card_class}">
                <div class="kpi-header">
                    <span class="kpi-title">Low-Stock Items</span>
                    <div class="{badge_class}">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                    </div>
                </div>
                <div class="{val_class}">{low_stock_count}</div>
                <div class="kpi-footnote">{sub_text}</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

    # Category Charts
    rows = an.inventory_value_by_category(db)
    if rows:
        df_cat = pd.DataFrame(rows)

        col_left, col_right = st.columns([1, 1])

        with col_left:
            with st.container(border=True):
                st.markdown("""
                    <div class="chart-panel-header">
                        <div class="chart-panel-title">Inventory Value by Category</div>
                        <div class="chart-panel-subtitle">Capital valuation per merchandise category</div>
                    </div>
                """, unsafe_allow_html=True)
                fig_bar = px.bar(
                    df_cat,
                    x="category",
                    y="estimated_inventory_value",
                    text="estimated_inventory_value",
                )
                fig_bar.update_traces(
                    marker_color="#14B8A6",
                    hovertemplate="<b>%{x}</b><br>Valuation: " + CUR + "%{y:,.2f}<extra></extra>",
                    texttemplate=f"{CUR}%{{text:,.2f}}",
                    textposition="outside",
                    textfont=dict(color="#9AA9BC", size=10, family="Inter"),
                    cliponaxis=False
                )
                fig_bar.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=10, r=10, t=20, b=10),
                    height=280,
                    xaxis=dict(showgrid=False, title="", tickfont=dict(color="#9AA9BC", size=11, family="Inter")),
                    yaxis=dict(showgrid=True, gridcolor="#2A3545", title="", tickfont=dict(color="#9AA9BC", size=11, family="Inter"))
                )
                st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

        with col_right:
            with st.container(border=True):
                st.markdown("""
                    <div class="chart-panel-header">
                        <div class="chart-panel-title">Units in Stock by Category</div>
                        <div class="chart-panel-subtitle">Physical inventory volume distribution</div>
                    </div>
                """, unsafe_allow_html=True)
                df_sorted_units = df_cat.sort_values(by="total_units", ascending=True)
                fig_h_bar = px.bar(
                    df_sorted_units,
                    x="total_units",
                    y="category",
                    orientation="h",
                    text="total_units"
                )
                fig_h_bar.update_traces(
                    marker_color="#60A5FA",
                    hovertemplate="<b>%{y}</b><br>Stock: %{x:,} units<extra></extra>",
                    texttemplate="%{text:,} units",
                    textposition="outside",
                    textfont=dict(color="#9AA9BC", size=10, family="Inter"),
                    cliponaxis=False
                )
                fig_h_bar.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=10, r=25, t=20, b=10),
                    height=280,
                    xaxis=dict(showgrid=True, gridcolor="#2A3545", title="", tickfont=dict(color="#9AA9BC", size=11, family="Inter")),
                    yaxis=dict(showgrid=False, title="", tickfont=dict(color="#9AA9BC", size=11, family="Inter"))
                )
                st.plotly_chart(fig_h_bar, use_container_width=True, config={"displayModeBar": False})

        # Category Breakdown Table
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        st.markdown('<div class="section-heading">Category Breakdown</div>', unsafe_allow_html=True)
        display_df = df_cat.copy()
        display_df.rename(columns={
            "category": "Category",
            "distinct_products": "Products",
            "product_count": "Products",
            "total_units": "Units in Stock",
            "estimated_inventory_value": "Estimated Value"
        }, inplace=True)
        cat_cols = [c for c in ["Category", "Products", "Units in Stock", "Estimated Value"] if c in display_df.columns]
        st.dataframe(
            display_df[cat_cols],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Category": st.column_config.TextColumn("Category", width="medium"),
                "Products": st.column_config.NumberColumn("Products", width="small", format="%d"),
                "Units in Stock": st.column_config.NumberColumn("Units in Stock", width="medium", format="%d"),
                "Estimated Value": st.column_config.NumberColumn("Estimated Value", width="medium", format=f"{CUR}%.2f"),
            }
        )
    else:
        st.info("No product data found in database. Run `python -m scripts.seed_data` to populate records.")


# =============================================================================
# 2. PRODUCTS PAGE
# =============================================================================
def page_products():
    st.markdown("""
        <div class="page-header">
            <h1 class="page-title">Products</h1>
            <p class="page-subtitle">Product specifications, pricing, stock levels, and safety thresholds.</p>
        </div>
    """, unsafe_allow_html=True)

    suppliers = sup.list_suppliers(db)
    supplier_ids = [s["supplier_id"] for s in suppliers]
    supplier_names = {s["supplier_id"]: s["name"] for s in suppliers}

    tab_browse, tab_add, tab_edit, tab_delete = st.tabs([
        "Browse",
        "Add Product",
        "Edit Product",
        "Delete Product"
    ])

    # --- TAB 1: BROWSE ---
    with tab_browse:
        f1, f2, f3 = st.columns([2, 1, 1])
        search = f1.text_input("Search", placeholder="Search by SKU or Name")
        cat = f2.selectbox("Category", ["All Categories"] + ps.list_categories(db))
        status = f3.selectbox("Stock Status", ["All", "Normal", "Low Stock", "Out of Stock"])

        status_mapping = {
            "All": None,
            "Normal": "normal",
            "Low Stock": "low",
            "Out of Stock": "out_of_stock"
        }

        products = _run(lambda: ps.list_products(
            db,
            search=search or None,
            category=None if cat == "All Categories" else cat,
            stock_status=status_mapping[status]
        )) or []

        st.caption(f"{len(products)} product(s) found")

        if products:
            p_df = _df(products)

            def get_status_text(row):
                qty = row.get("quantity_in_stock", 0)
                reorder = row.get("reorder_level", 0)
                if qty == 0:
                    return "Out of Stock"
                elif qty <= reorder:
                    return f"Low ({qty})"
                return "In Stock"

            p_df["Status"] = p_df.apply(get_status_text, axis=1)
            p_df["Unit Price"] = p_df["unit_price"].apply(_money)

            cols_order = ["sku", "name", "category", "supplier_id", "Unit Price", "quantity_in_stock", "reorder_level", "Status", "updated_at"]
            p_df_display = p_df[cols_order].rename(columns={
                "sku": "SKU",
                "name": "Name",
                "category": "Category",
                "supplier_id": "Supplier",
                "quantity_in_stock": "Stock",
                "reorder_level": "Reorder Level",
                "updated_at": "Last Updated"
            })
            st.dataframe(
                p_df_display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "SKU": st.column_config.TextColumn("SKU", width="small"),
                    "Name": st.column_config.TextColumn("Product Name", width="large"),
                    "Category": st.column_config.TextColumn("Category", width="medium"),
                    "Supplier": st.column_config.TextColumn("Supplier", width="small"),
                    "Unit Price": st.column_config.TextColumn("Unit Price", width="small"),
                    "Stock": st.column_config.NumberColumn("Stock", width="small", format="%d"),
                    "Reorder Level": st.column_config.NumberColumn("Reorder Level", width="small", format="%d"),
                    "Status": st.column_config.TextColumn("Status", width="small"),
                    "Last Updated": st.column_config.TextColumn("Last Updated", width="medium"),
                }
            )
        else:
            st.info("No matching products found.")

    # --- TAB 2: ADD PRODUCT ---
    with tab_add:
        if not supplier_ids:
            st.warning("Please create at least one supplier before adding products.")
        else:
            with st.form("form_add_product", clear_on_submit=False):
                st.markdown('<div class="section-heading">Product Details</div>', unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                new_sku = c1.text_input("SKU (Required)", placeholder="e.g. BEV-005")
                new_name = c2.text_input("Product Name (Required)", placeholder="e.g. Sparkling Apple Cider 750ml")

                new_cat = c1.text_input("Category (Required)", placeholder="e.g. Beverages")
                new_supplier = c2.selectbox(
                    "Supplier Reference (Required)",
                    supplier_ids,
                    format_func=lambda sid: f"{sid} - {supplier_names.get(sid, '')}"
                )

                new_price = c1.number_input("Unit Price ($)", min_value=0.0, step=0.10, format="%.2f")
                new_opening = c2.number_input("Opening Stock Quantity", min_value=0, step=1, value=0)
                new_reorder = c1.number_input("Reorder Level Threshold", min_value=0, step=1, value=15)

                if st.form_submit_button("Add Product"):
                    _run(
                        lambda: ps.create_product(
                            db, new_sku, new_name, new_cat, new_supplier,
                            new_price, int(new_opening), int(new_reorder)
                        ),
                        lambda p: f"Product '{p['sku']}' ({p['name']}) added successfully."
                    )

    # --- TAB 3: EDIT PRODUCT ---
    with tab_edit:
        all_prods = ps.list_products(db)
        if all_prods:
            sku_list = [p["sku"] for p in all_prods]
            edit_sku = st.selectbox("Select Product to Edit", sku_list, key="sel_edit_sku")
            curr = ps.get_product(db, edit_sku)

            st.caption("Note: Current stock quantities are updated strictly via the Stock Movements ledger.")

            with st.form("form_edit_product"):
                c1, c2 = st.columns(2)
                e_name = c1.text_input("Product Name", value=curr["name"])
                e_cat = c2.text_input("Category", value=curr["category"])

                sup_idx = supplier_ids.index(curr["supplier_id"]) if curr["supplier_id"] in supplier_ids else 0
                e_supplier = c1.selectbox("Supplier Reference", supplier_ids, index=sup_idx, format_func=lambda s: f"{s} - {supplier_names.get(s, '')}")
                e_price = c2.number_input("Unit Price ($)", min_value=0.0, step=0.10, value=float(curr["unit_price"]), format="%.2f")
                e_reorder = c1.number_input("Reorder Level", min_value=0, step=1, value=int(curr["reorder_level"]))

                if st.form_submit_button("Save Changes"):
                    _run(
                        lambda: ps.update_product(
                            db, edit_sku, name=e_name, category=e_cat,
                            supplier_id=e_supplier, unit_price=e_price, reorder_level=int(e_reorder)
                        ),
                        "Product updated successfully."
                    )
        else:
            st.info("No products available to edit.")

    # --- TAB 4: DELETE PRODUCT ---
    with tab_delete:
        all_prods = ps.list_products(db)
        if all_prods:
            del_sku = st.selectbox("Select Product", [p["sku"] for p in all_prods], key="sel_del_sku")
            history_count = len(ss.list_movements(db, del_sku, limit=500))

            if history_count > 0:
                st.markdown(f"""
                    <div class="info-callout" style="border-left: 3px solid #F59E0B;">
                        <strong>Deletion Restricted:</strong> Product <code>{del_sku}</code> has {history_count} stock movement record(s). 
                        Products with transaction history cannot be deleted to preserve the audit trail.
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.info(f"Product `{del_sku}` has no movement history and can be safely deleted.")

            confirmed = st.checkbox("Confirm permanent deletion of product", key="confirm_del_prod")
            st.markdown('<div class="destructive-btn">', unsafe_allow_html=True)
            if st.button("Delete Product", disabled=(history_count > 0 or not confirmed)):
                _run(lambda: ps.delete_product(db, del_sku), f"Deleted product {del_sku}.")
            st.markdown('</div>', unsafe_allow_html=True)


# =============================================================================
# 3. SUPPLIERS PAGE
# =============================================================================
def page_suppliers():
    st.markdown("""
        <div class="page-header">
            <h1 class="page-title">Suppliers</h1>
            <p class="page-subtitle">Vendor directory, contact profiles, and supplied product relationships.</p>
        </div>
    """, unsafe_allow_html=True)

    tab_dir, tab_add, tab_edit, tab_del = st.tabs([
        "Directory",
        "Add Supplier",
        "Edit Supplier",
        "Delete Supplier"
    ])

    with tab_dir:
        search = st.text_input("Search Suppliers", placeholder="Filter by ID, Name, City, or Contact")
        suppliers = sup.list_suppliers(db, search or None)
        sup_df = _df(suppliers)
        if not sup_df.empty:
            sup_df_disp = sup_df.rename(columns={
                "supplier_id": "Supplier ID",
                "name": "Business Name",
                "contact_person": "Contact Person",
                "phone": "Telephone",
                "email": "Email",
                "city": "City",
                "created_at": "Created At"
            })
            sup_cols = [c for c in ["Supplier ID", "Business Name", "Contact Person", "Telephone", "Email", "City"] if c in sup_df_disp.columns]
            st.dataframe(
                sup_df_disp[sup_cols],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Supplier ID": st.column_config.TextColumn("Supplier ID", width="small"),
                    "Business Name": st.column_config.TextColumn("Business Name", width="large"),
                    "Contact Person": st.column_config.TextColumn("Contact Person", width="medium"),
                    "Telephone": st.column_config.TextColumn("Telephone", width="medium"),
                    "Email": st.column_config.TextColumn("Email", width="medium"),
                    "City": st.column_config.TextColumn("City", width="small"),
                }
            )
        else:
            st.info("No suppliers registered.")

    with tab_add:
        with st.form("form_add_supplier"):
            st.markdown('<div class="section-heading">Supplier Information</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            sid = c1.text_input("Supplier ID (Required)", placeholder="e.g. SUP-006")
            sname = c2.text_input("Business Name (Required)", placeholder="Apex Distribution Co.")
            contact = c1.text_input("Contact Person", placeholder="Jane Doe")
            phone = c2.text_input("Telephone", placeholder="+91-555-0199")
            email = c1.text_input("Email", placeholder="orders@apexdist.example.com")
            city = c2.text_input("City", placeholder="Mumbai")

            if st.form_submit_button("Add Supplier"):
                _run(
                    lambda: sup.create_supplier(db, sid, sname, contact, phone, email, city),
                    lambda s: f"Supplier '{s['supplier_id']}' created successfully."
                )

    with tab_edit:
        suppliers = sup.list_suppliers(db)
        if suppliers:
            sel_sid = st.selectbox("Select Supplier", [s["supplier_id"] for s in suppliers], key="edit_sup_sel")
            s_obj = sup.get_supplier(db, sel_sid)
            with st.form("form_edit_sup"):
                c1, c2 = st.columns(2)
                e_name = c1.text_input("Business Name", value=s_obj["name"])
                e_contact = c2.text_input("Contact Person", value=s_obj.get("contact_person", ""))
                e_phone = c1.text_input("Telephone", value=s_obj.get("phone", ""))
                e_email = c2.text_input("Email", value=s_obj.get("email", ""))
                e_city = c1.text_input("City", value=s_obj.get("city", ""))

                if st.form_submit_button("Save Changes"):
                    _run(
                        lambda: sup.update_supplier(
                            db, sel_sid, name=e_name, contact_person=e_contact,
                            phone=e_phone, email=e_email, city=e_city
                        ),
                        "Supplier updated successfully."
                    )

    with tab_del:
        suppliers = sup.list_suppliers(db)
        if suppliers:
            del_sid = st.selectbox("Select Supplier to Delete", [s["supplier_id"] for s in suppliers], key="del_sup_sel")
            linked_products = len(ps.list_products(db, supplier_id=del_sid))
            if linked_products > 0:
                st.markdown(f"""
                    <div class="info-callout" style="border-left: 3px solid #F59E0B;">
                        <strong>Deletion Restricted:</strong> Supplier <code>{del_sid}</code> supplies {linked_products} active product(s). 
                        Reassign these products before deleting this supplier.
                    </div>
                """, unsafe_allow_html=True)
            confirmed_sup = st.checkbox("Confirm permanent deletion of supplier", key="confirm_del_sup")
            st.markdown('<div class="destructive-btn">', unsafe_allow_html=True)
            if st.button("Delete Supplier", disabled=(linked_products > 0 or not confirmed_sup)):
                _run(lambda: sup.delete_supplier(db, del_sid), f"Deleted supplier {del_sid}.")
            st.markdown('</div>', unsafe_allow_html=True)


# =============================================================================
# 4. STOCK MOVEMENTS PAGE
# =============================================================================
def page_stock():
    st.markdown("""
        <div class="page-header">
            <h1 class="page-title">Stock Movements</h1>
            <p class="page-subtitle">Record inventory receipts, customer dispatches, and manual adjustments.</p>
        </div>
    """, unsafe_allow_html=True)

    products = ps.list_products(db)
    if not products:
        st.info("No products found in the database.")
        return

    # Notification banner for completed transaction
    flash = st.session_state.pop("flash", None)
    if flash:
        st.success(flash)

    prod_map = {p["sku"]: f"{p['sku']} - {p['name']} ({p['category']})" for p in products}
    sku = st.selectbox("Select Product", list(prod_map.keys()), format_func=prod_map.get)
    current = ps.get_product(db, sku)

    curr_stock = current["quantity_in_stock"]
    reorder = current["reorder_level"]
    price = current["unit_price"]

    # Product Overview Metrics
    m1, m2, m3 = st.columns(3)
    with m1:
        c_class = "kpi-card kpi-card-warning" if curr_stock <= reorder else "kpi-card"
        b_class = "kpi-icon-badge kpi-icon-badge-warning" if curr_stock <= reorder else "kpi-icon-badge"
        v_class = "kpi-value kpi-value-warning" if curr_stock <= reorder else "kpi-value"
        st.markdown(f"""
            <div class="{c_class}">
                <div class="kpi-header">
                    <span class="kpi-title">Available Stock</span>
                    <div class="{b_class}">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.29 7 12 12 20.71 7"/><line x1="12" y1="22" x2="12" y2="12"/></svg>
                    </div>
                </div>
                <div class="{v_class}">{curr_stock:,}</div>
                <div class="kpi-footnote">Physical units on hand</div>
            </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-header">
                    <span class="kpi-title">Reorder Level</span>
                    <div class="kpi-icon-badge">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                    </div>
                </div>
                <div class="kpi-value">{reorder}</div>
                <div class="kpi-footnote">Minimum safety threshold</div>
            </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-header">
                    <span class="kpi-title">Unit Selling Price</span>
                    <div class="kpi-icon-badge">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                    </div>
                </div>
                <div class="kpi-value">{_money(price)}</div>
                <div class="kpi-footnote">Current catalog list price</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

    # Operation Form
    op_type = st.radio(
        "Movement Classification",
        ["IN", "OUT", "ADJUSTMENT"],
        horizontal=True,
        format_func=lambda x: {
            "IN": "Receipt (IN)",
            "OUT": "Dispatch (OUT)",
            "ADJUSTMENT": "Adjustment (Cycle Count / Write-off)"
        }[x]
    )

    with st.form("form_stock_movement", clear_on_submit=False):
        c_qty, c_reason = st.columns([1, 2])
        if op_type == "ADJUSTMENT":
            qty = c_qty.number_input("Adjustment Quantity (Signed, Non-Zero)", step=1, value=1)
        else:
            qty = c_qty.number_input("Quantity (Positive Integer)", min_value=1, step=1, value=1)
        
        reason = c_reason.text_input("Operational Reason (Required)", placeholder="e.g. Supplier delivery, Customer sale, Damaged stock")

        # Projected balance preview
        projected = curr_stock + qty if op_type == "IN" else (curr_stock - qty if op_type == "OUT" else curr_stock + qty)
        if projected < 0:
            st.markdown(f'<div style="color: #F87171; font-size: 0.82rem; margin-top: 0.25rem;">Warning: Stock would drop to {projected}. Out-of-stock operation will be rejected.</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="color: #8B949E; font-size: 0.82rem; margin-top: 0.25rem;">Projected balance: {curr_stock} → {projected} units</div>', unsafe_allow_html=True)

        if st.form_submit_button(f"Record {op_type}"):
            action_fn = {"IN": ss.stock_in, "OUT": ss.stock_out, "ADJUSTMENT": ss.adjust_stock}[op_type]
            res = _run(lambda: action_fn(db, sku, int(qty), reason))
            if res:
                st.session_state["flash"] = (
                    f"Recorded {op_type} ({res['movement']['movement_id']}): "
                    f"Stock updated from {res['previous_quantity']} to {res['quantity_in_stock']}."
                )
                st.rerun()

    # Movement History Table
    st.markdown('<div class="section-heading">Recent Movements</div>', unsafe_allow_html=True)
    filter_col1, filter_col2 = st.columns([1, 3])
    only_current = filter_col1.checkbox("Filter by selected product only", value=True)
    limit = filter_col2.slider("Maximum rows", min_value=10, max_value=100, value=25)

    movements = ss.list_movements(db, sku if only_current else None, limit=limit)
    if movements:
        m_df = _df(movements)
        m_df_disp = m_df.rename(columns={
            "movement_id": "Movement ID",
            "sku": "SKU",
            "movement_type": "Type",
            "quantity": "Quantity",
            "reason": "Reason",
            "movement_date": "Date & Time"
        })
        mov_cols = [c for c in ["Movement ID", "SKU", "Type", "Quantity", "Reason", "Date & Time"] if c in m_df_disp.columns]
        st.dataframe(
            m_df_disp[mov_cols],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Movement ID": st.column_config.TextColumn("Movement ID", width="medium"),
                "SKU": st.column_config.TextColumn("SKU", width="small"),
                "Type": st.column_config.TextColumn("Type", width="small"),
                "Quantity": st.column_config.NumberColumn("Quantity", width="small", format="%d"),
                "Reason": st.column_config.TextColumn("Reason", width="large"),
                "Date & Time": st.column_config.TextColumn("Date & Time", width="medium"),
            }
        )
    else:
        st.info("No movements recorded.")


# =============================================================================
# 5. REPORTS PAGE (AGGREGATION PIPELINES)
# =============================================================================
def _show_pipeline_card(title, description, pipeline_json):
    with st.expander(f"Inspect MongoDB Pipeline ({title})"):
        st.markdown(f"<span style='color: #8B949E; font-size: 0.82rem;'>{description}</span>", unsafe_allow_html=True)
        st.code(json.dumps(pipeline_json, indent=2), language="json")


def page_reports():
    st.markdown("""
        <div class="page-header">
            <h1 class="page-title">Reports</h1>
            <p class="page-subtitle">Multi-stage MongoDB aggregation pipelines computed natively inside the database.</p>
        </div>
    """, unsafe_allow_html=True)

    t1, t2, t3, t4, t5 = st.tabs([
        "Low Stock",
        "Category Valuation",
        "Movement Flow",
        "Supplier Summary",
        "Ledger Audit"
    ])

    # --- PIPELINE 1: LOW STOCK ---
    with t1:
        st.markdown('<div class="section-heading">Low-Stock Products</div>', unsafe_allow_html=True)
        st.caption("Products where available quantity is at or below the reorder threshold.")

        low_stock = an.low_stock_products(db)
        if low_stock:
            df_low = pd.DataFrame(low_stock)
            df_low["Shortage Units"] = df_low["reorder_level"] - df_low["available_quantity"]

            fig_low = px.bar(
                df_low,
                x="name",
                y="available_quantity",
                text="available_quantity"
            )
            fig_low.update_traces(
                marker_color="#F59E0B",
                hovertemplate="<b>%{x}</b><br>Available: %{y:,} units<extra></extra>",
                textposition="outside",
                textfont=dict(color="#9AA9BC", size=10, family="Inter")
            )
            fig_low.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=260,
                margin=dict(l=10, r=10, t=25, b=10),
                xaxis=dict(showgrid=False, title="", tickfont=dict(color="#9AA9BC", size=11, family="Inter")),
                yaxis=dict(showgrid=True, gridcolor="#2A3545", title="Units", tickfont=dict(color="#9AA9BC", size=11, family="Inter"))
            )
            st.plotly_chart(fig_low, use_container_width=True, config={"displayModeBar": False})

            display_low = df_low.rename(columns={
                "sku": "SKU",
                "name": "Product Name",
                "category": "Category",
                "available_quantity": "Available Quantity",
                "reorder_level": "Reorder Level"
            })
            low_cols = [c for c in ["SKU", "Product Name", "Category", "Available Quantity", "Reorder Level", "Shortage Units"] if c in display_low.columns]
            st.dataframe(
                display_low[low_cols],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "SKU": st.column_config.TextColumn("SKU", width="small"),
                    "Product Name": st.column_config.TextColumn("Product Name", width="large"),
                    "Category": st.column_config.TextColumn("Category", width="medium"),
                    "Available Quantity": st.column_config.NumberColumn("Available Quantity", width="small", format="%d"),
                    "Reorder Level": st.column_config.NumberColumn("Reorder Level", width="small", format="%d"),
                    "Shortage Units": st.column_config.NumberColumn("Shortage Units", width="small", format="%d"),
                }
            )
        else:
            st.success("All stock levels are currently above reorder thresholds.")

        _show_pipeline_card("Pipeline 1: Low Stock", "Evaluates $lte condition between quantity_in_stock and reorder_level using $expr in $match stage.", an.LOW_STOCK_PIPELINE)

    # --- PIPELINE 2: CATEGORY VALUATION ---
    with t2:
        st.markdown('<div class="section-heading">Inventory Value by Category</div>', unsafe_allow_html=True)
        st.caption("Estimated inventory value based on current selling prices.")

        val_rows = an.inventory_value_by_category(db)
        if val_rows:
            df_val = pd.DataFrame(val_rows)
            fig_val = px.bar(
                df_val,
                x="category",
                y="estimated_inventory_value",
                text="estimated_inventory_value"
            )
            fig_val.update_traces(
                marker_color="#14B8A6",
                hovertemplate="<b>%{x}</b><br>Valuation: " + CUR + "%{y:,.2f}<extra></extra>",
                texttemplate=f"{CUR}%{{text:,.2f}}",
                textposition="outside",
                textfont=dict(color="#9AA9BC", size=10, family="Inter")
            )
            fig_val.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=260,
                margin=dict(l=10, r=10, t=25, b=10),
                xaxis=dict(showgrid=False, title="", tickfont=dict(color="#9AA9BC", size=11, family="Inter")),
                yaxis=dict(showgrid=True, gridcolor="#2A3545", title="", tickfont=dict(color="#9AA9BC", size=11, family="Inter"))
            )
            st.plotly_chart(fig_val, use_container_width=True, config={"displayModeBar": False})

            disp_val = df_val.rename(columns={
                "category": "Category",
                "distinct_products": "Products",
                "product_count": "Products",
                "total_units": "Units in Stock",
                "estimated_inventory_value": "Estimated Value"
            })
            val_cols = [c for c in ["Category", "Products", "Units in Stock", "Estimated Value"] if c in disp_val.columns]
            st.dataframe(
                disp_val[val_cols],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Category": st.column_config.TextColumn("Category", width="medium"),
                    "Products": st.column_config.NumberColumn("Products", width="small", format="%d"),
                    "Units in Stock": st.column_config.NumberColumn("Units in Stock", width="medium", format="%d"),
                    "Estimated Value": st.column_config.NumberColumn("Estimated Value", width="medium", format=f"{CUR}%.2f"),
                }
            )

        _show_pipeline_card("Pipeline 2: Valuation", "Groups products by category and sums quantity_in_stock multiplied by unit_price.", an.INVENTORY_BY_CATEGORY_PIPELINE)

    # --- PIPELINE 3: MOVEMENT FLOW ---
    with t3:
        st.markdown('<div class="section-heading">Stock Movement Flow by Category</div>', unsafe_allow_html=True)
        st.caption("Comparison of received (IN) versus issued (OUT) quantities per category.")

        mov_rows = an.stock_movement_by_category(db)
        if mov_rows:
            df_mov = pd.DataFrame(mov_rows)
            fig_flow = px.bar(
                df_mov,
                x="category",
                y=["total_in_quantity", "total_out_quantity"],
                barmode="group",
                color_discrete_sequence=["#14B8A6", "#60A5FA"],
                labels={"value": "Units", "variable": "Type"}
            )
            fig_flow.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=280,
                margin=dict(l=10, r=10, t=15, b=10),
                legend=dict(font=dict(color="#9AA9BC", size=11, family="Inter"), orientation="h", y=1.15),
                xaxis=dict(showgrid=False, title="", tickfont=dict(color="#9AA9BC", size=11, family="Inter")),
                yaxis=dict(showgrid=True, gridcolor="#2A3545", title="", tickfont=dict(color="#9AA9BC", size=11, family="Inter"))
            )
            st.plotly_chart(fig_flow, use_container_width=True, config={"displayModeBar": False})

            disp_mov = df_mov.rename(columns={
                "category": "Category",
                "movement_count": "Transactions",
                "total_in_quantity": "Units In",
                "total_out_quantity": "Units Out",
                "net_adjustment_quantity": "Adjustments"
            })
            mov_cols = [c for c in ["Category", "Transactions", "Units In", "Units Out", "Adjustments"] if c in disp_mov.columns]
            st.dataframe(
                disp_mov[mov_cols],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Category": st.column_config.TextColumn("Category", width="medium"),
                    "Transactions": st.column_config.NumberColumn("Transactions", width="small", format="%d"),
                    "Units In": st.column_config.NumberColumn("Units In", width="small", format="%d"),
                    "Units Out": st.column_config.NumberColumn("Units Out", width="small", format="%d"),
                    "Adjustments": st.column_config.NumberColumn("Adjustments", width="small", format="%d"),
                }
            )

        _show_pipeline_card("Pipeline 3: Movement Flow", "Performs $lookup from stock_movements to products, unwinds, and groups by category.", an.MOVEMENT_BY_CATEGORY_PIPELINE)

    # --- PIPELINE 4: SUPPLIER SUMMARY ---
    with t4:
        st.markdown('<div class="section-heading">Supplier Summary</div>', unsafe_allow_html=True)
        st.caption("Inventory exposure and product count per supplier.")

        sup_rows = an.supplier_inventory_summary(db)
        if sup_rows:
            df_sup = pd.DataFrame(sup_rows)
            fig_sup = px.bar(
                df_sup,
                x="supplier_name",
                y="estimated_inventory_value",
                text="estimated_inventory_value"
            )
            fig_sup.update_traces(
                marker_color="#14B8A6",
                hovertemplate="<b>%{x}</b><br>Valuation: " + CUR + "%{y:,.2f}<extra></extra>",
                texttemplate=f"{CUR}%{{text:,.2f}}",
                textposition="outside",
                textfont=dict(color="#9AA9BC", size=10, family="Inter")
            )
            fig_sup.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=260,
                margin=dict(l=10, r=10, t=25, b=10),
                xaxis=dict(showgrid=False, title="", tickfont=dict(color="#9AA9BC", size=11, family="Inter")),
                yaxis=dict(showgrid=True, gridcolor="#2A3545", title="", tickfont=dict(color="#9AA9BC", size=11, family="Inter"))
            )
            st.plotly_chart(fig_sup, use_container_width=True, config={"displayModeBar": False})

            disp_sup = df_sup.rename(columns={
                "supplier_id": "Supplier ID",
                "supplier_name": "Supplier Name",
                "city": "City",
                "product_count": "Products",
                "estimated_inventory_value": "Estimated Value"
            })
            sup_cols = [c for c in ["Supplier ID", "Supplier Name", "City", "Products", "Estimated Value"] if c in disp_sup.columns]
            st.dataframe(
                disp_sup[sup_cols],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Supplier ID": st.column_config.TextColumn("Supplier ID", width="small"),
                    "Supplier Name": st.column_config.TextColumn("Supplier Name", width="large"),
                    "City": st.column_config.TextColumn("City", width="medium"),
                    "Products": st.column_config.NumberColumn("Products", width="small", format="%d"),
                    "Estimated Value": st.column_config.NumberColumn("Estimated Value", width="medium", format=f"{CUR}%.2f"),
                }
            )

        _show_pipeline_card("Pipeline 4: Supplier Summary", "Joins products to suppliers using $lookup and groups to calculate inventory value.", an.SUPPLIER_SUMMARY_PIPELINE)

    # --- DATA INTEGRITY AUDIT ---
    with t5:
        st.markdown('<div class="section-heading">Data Integrity Audit</div>', unsafe_allow_html=True)
        st.caption("Reconciliation: Current Stock == Sum(IN) - Sum(OUT) + Sum(ADJUSTMENT).")

        mismatches = an.stock_consistency_mismatches(db)
        if mismatches:
            st.error(f"Integrity alert: {len(mismatches)} product(s) disagree with movement ledger.")
            st.dataframe(_df(mismatches), use_container_width=True, hide_index=True)
        else:
            st.markdown("""
                <div class="kpi-card" style="border-left: 3px solid #14B8A6; max-width: 600px;">
                    <div style="font-weight: 600; color: #14B8A6; font-size: 0.95rem; margin-bottom: 0.25rem;">
                        Ledger Integrity Verified
                    </div>
                    <div style="font-size: 0.82rem; color: #9AA9BC;">
                        Every product's current stock matches the net sum of all historical stock movement records.
                    </div>
                </div>
            """, unsafe_allow_html=True)

        _show_pipeline_card("Integrity Audit Pipeline", "Uses $lookup and $reduce to compute net historical stock and compares with quantity_in_stock.", an.CONSISTENCY_PIPELINE)


# -----------------------------------------------------------------------------
# Router
# -----------------------------------------------------------------------------
PAGES = {
    "Overview": page_overview,
    "Products": page_products,
    "Suppliers": page_suppliers,
    "Stock Movements": page_stock,
    "Reports": page_reports
}

PAGES[page]()
