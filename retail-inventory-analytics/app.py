"""
Retail Inventory & Stock Analytics - Streamlit Business Intelligence Dashboard.
Built for Academic Task 2 (CSE494 - Intelligent NoSQL Databases).
All metrics, CRUD, and analytics are calculated directly inside MongoDB via PyMongo.
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
# Page Configuration & Styling
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Retailerz | MongoDB Inventory Intelligence",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

CUR = config.CURRENCY_SYMBOL

# High-end Minimalist Dark Theme CSS
CUSTOM_CSS = """
<style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    code, pre {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Pinned Streamlit Top Bar - Permanently on top even when scrolling down */
    header[data-testid="stHeader"] {
        background: rgba(11, 15, 25, 0.95) !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        z-index: 999990 !important;
    }

    header[data-testid="stHeader"]::before {
        content: "📦 Retailerz";
        position: absolute;
        left: 4.8rem;
        top: 50%;
        transform: translateY(-50%);
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        font-size: 1.15rem;
        font-weight: 800;
        color: #F8FAFC;
        letter-spacing: -0.02em;
        pointer-events: none;
    }

    header[data-testid="stHeader"]::after {
        content: "Inventory Intelligence  •  MongoDB [retail_inventory]";
        position: absolute;
        left: 14.5rem;
        top: 50%;
        transform: translateY(-50%);
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        font-size: 0.74rem;
        font-weight: 600;
        color: #38BDF8;
        background: rgba(56, 189, 248, 0.12);
        border: 1px solid rgba(56, 189, 248, 0.25);
        border-radius: 9999px;
        padding: 0.18rem 0.65rem;
        pointer-events: none;
    }

    @media (max-width: 900px) {
        header[data-testid="stHeader"]::after {
            display: none !important;
        }
    }

    /* Main Container Padding - clears the top fixed bar */
    .block-container {
        padding-top: 2.2rem !important;
        padding-bottom: 2.5rem !important;
        max-width: 96% !important;
    }

    /* Sticky App Header Bar */
    .top-app-header {
        position: sticky;
        top: 3.75rem;
        z-index: 999;
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: rgba(15, 23, 42, 0.92);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 0.65rem 1.25rem;
        margin-bottom: 1.4rem;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.45);
    }

    .brand-cluster {
        display: flex;
        align-items: center;
        gap: 0.65rem;
    }

    .brand-icon-box {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.25) 0%, rgba(6, 182, 212, 0.25) 100%);
        border: 1px solid rgba(16, 185, 129, 0.4);
        border-radius: 8px;
        padding: 0.25rem 0.5rem;
        font-size: 1.15rem;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .brand-logo-text {
        font-size: 1.25rem;
        font-weight: 800;
        color: #F8FAFC;
        letter-spacing: -0.02em;
    }

    .brand-edition-badge {
        font-size: 0.7rem;
        font-weight: 600;
        color: #38BDF8;
        background: rgba(56, 189, 248, 0.12);
        border: 1px solid rgba(56, 189, 248, 0.25);
        border-radius: 6px;
        padding: 0.15rem 0.5rem;
        letter-spacing: 0.03em;
        margin-left: 0.35rem;
    }

    .header-system-status {
        display: flex;
        align-items: center;
        gap: 0.55rem;
        font-size: 0.8rem;
        color: #94A3B8;
        font-weight: 500;
    }

    .pulse-dot {
        width: 8px;
        height: 8px;
        background-color: #10B981;
        border-radius: 50%;
        box-shadow: 0 0 8px #10B981;
        display: inline-block;
    }

    /* Page Headings - Solid, Crisp, Non-clipped typography */
    .page-main-title {
        font-size: 2.1rem !important;
        font-weight: 800 !important;
        letter-spacing: -0.025em !important;
        color: #FFFFFF !important;
        line-height: 1.35 !important;
        margin-top: 0 !important;
        margin-bottom: 0.25rem !important;
        padding-bottom: 4px !important;
        display: block !important;
        overflow: visible !important;
    }
    
    .page-main-subtitle {
        font-size: 0.92rem !important;
        color: #94A3B8 !important;
        line-height: 1.5 !important;
        margin-bottom: 1.35rem !important;
        display: block !important;
    }

    /* KPI Cards */
    .kpi-container {
        background: linear-gradient(145deg, rgba(30, 41, 59, 0.45) 0%, rgba(15, 23, 42, 0.6) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 1.25rem 1.4rem;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.35);
        transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.25s ease;
        position: relative;
        overflow: hidden;
    }
    .kpi-container:hover {
        transform: translateY(-3px);
        border-color: rgba(16, 185, 129, 0.35);
    }
    .kpi-label {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #94A3B8;
        margin-bottom: 0.4rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }
    .kpi-value {
        font-size: 1.85rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: #F8FAFC;
        line-height: 1.2;
    }
    .kpi-sub {
        font-size: 0.75rem;
        color: #64748B;
        margin-top: 0.4rem;
    }

    /* Status Badges */
    .badge {
        display: inline-flex;
        align-items: center;
        padding: 0.2rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.02em;
    }
    .badge-success {
        background: rgba(16, 185, 129, 0.12);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.25);
    }
    .badge-warning {
        background: rgba(245, 158, 11, 0.12);
        color: #FBBF24;
        border: 1px solid rgba(245, 158, 11, 0.25);
    }
    .badge-danger {
        background: rgba(239, 68, 68, 0.12);
        color: #F87171;
        border: 1px solid rgba(239, 68, 68, 0.25);
    }
    .badge-info {
        background: rgba(56, 189, 248, 0.12);
        color: #38BDF8;
        border: 1px solid rgba(56, 189, 248, 0.25);
    }

    /* Live Preview Card */
    .preview-card {
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1rem 1.25rem;
        margin-bottom: 1.2rem;
    }

    /* Section Headers */
    .section-title {
        font-size: 1.2rem;
        font-weight: 700;
        color: #F1F5F9;
        letter-spacing: -0.01em;
        margin-top: 1rem;
        margin-bottom: 0.8rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    /* Pipeline Callout */
    .pipeline-badge {
        background: rgba(99, 102, 241, 0.12);
        border: 1px solid rgba(99, 102, 241, 0.3);
        color: #A5B4FC;
        padding: 0.3rem 0.8rem;
        border-radius: 8px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 0.6rem;
    }

    /* Form Buttons */
    div.stButton > button:first-child {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Database Connection & Helper Utilities
# -----------------------------------------------------------------------------
@st.cache_resource(show_spinner="Establishing PyMongo connection to MongoDB...")
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
        st.error(f"❌ Business Rule: {exc}")
    except PyMongoError as exc:
        st.error(f"❌ MongoDB Database Error: {exc}")
    return None


def _money(x) -> str:
    return f"{CUR}{x:,.2f}"


# Safe Connection Bootstrap
try:
    db = _connect()
except DatabaseConnectionError as exc:
    st.error(f"❌ Connection Failure: {exc}")
    st.info("Ensure the local MongoDB Server service is running or check your MONGODB_URI environment variable.")
    st.stop()


# -----------------------------------------------------------------------------
# Sidebar Navigation & System Monitor
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
        <div style="padding: 0.5rem 0 1rem 0;">
            <div style="font-size: 1.35rem; font-weight: 800; color: #F8FAFC; letter-spacing: -0.02em;">
                📦 Retailerz
            </div>
            <div style="font-size: 0.75rem; color: #94A3B8; font-weight: 500;">
                Intelligent NoSQL Inventory Engine
            </div>
        </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "Navigation",
        [
            "📊 Dashboard",
            "🛒 Product Catalog",
            "🏭 Supplier Directory",
            "🔄 Stock Operations",
            "📈 Deep Analytics"
        ],
        label_visibility="collapsed"
    )

    st.markdown("---")
    
    # Real-time MongoDB System Status Box
    try:
        client_info = db.client.server_info()
        mongo_version = client_info.get("version", "8.x")
        status_dot = "🟢"
    except Exception:
        mongo_version = "Offline"
        status_dot = "🔴"

    st.markdown(f"""
        <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 0.85rem; font-size: 0.78rem;">
            <div style="font-weight: 600; color: #E2E8F0; margin-bottom: 0.35rem; display: flex; align-items: center; justify-content: space-between;">
                <span>Database Connection</span>
                <span>{status_dot}</span>
            </div>
            <div style="color: #94A3B8;">Engine: <b style="color: #CBD5E1;">MongoDB v{mongo_version}</b></div>
            <div style="color: #94A3B8;">Database: <code style="color: #38BDF8; font-size: 0.75rem;">{db.name}</code></div>
            <div style="color: #94A3B8;">Driver: <code style="color: #A5B4FC; font-size: 0.75rem;">PyMongo 4.x</code></div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    st.caption("Academic Task 2 | CSE494 Intelligent NoSQL")


def render_top_bar():
    """Renders a persistent top branding bar so Retailerz is always clearly identified, even when the sidebar is collapsed."""
    st.markdown(f"""
        <div class="top-app-header">
            <div class="brand-cluster">
                <div class="brand-icon-box">📦</div>
                <div>
                    <span class="brand-logo-text">Retailerz</span>
                    <span class="brand-edition-badge">Inventory Intelligence</span>
                </div>
            </div>
            <div class="header-system-status">
                <span class="pulse-dot"></span>
                <span>Active Database: <strong style="color: #38BDF8;">{db.name}</strong> (MongoDB v{mongo_version})</span>
            </div>
        </div>
    """, unsafe_allow_html=True)


# =============================================================================
# 1. DASHBOARD PAGE
# =============================================================================
def page_dashboard():
    st.markdown('<h1 class="page-main-title">Executive Inventory Dashboard</h1>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-main-subtitle">Real-time inventory valuation, stock health metrics, and category aggregations from MongoDB</div>',
        unsafe_allow_html=True
    )

    # MongoDB KPI Aggregation
    s = an.dashboard_summary(db)
    low_stock_count = s.get("low_stock_count", 0)

    # 4 Sleek KPI Cards
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f"""
            <div class="kpi-container">
                <div class="kpi-label">🏷️ Total Products</div>
                <div class="kpi-value">{s['total_products']}</div>
                <div class="kpi-sub">Across 5 retail categories</div>
            </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
            <div class="kpi-container">
                <div class="kpi-label">📦 Units In Stock</div>
                <div class="kpi-value">{s['total_units']:,}</div>
                <div class="kpi-sub">Total physical stock balance</div>
            </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
            <div class="kpi-container">
                <div class="kpi-label">💎 Est. Inventory Value</div>
                <div class="kpi-value">{_money(s['estimated_inventory_value'])}</div>
                <div class="kpi-sub">At current selling prices</div>
            </div>
        """, unsafe_allow_html=True)
    with k4:
        badge_class = "badge-danger" if low_stock_count > 0 else "badge-success"
        st.markdown(f"""
            <div class="kpi-container">
                <div class="kpi-label">⚠️ Stock Alerts</div>
                <div class="kpi-value" style="color: {'#F87171' if low_stock_count > 0 else '#34D399'};">
                    {low_stock_count}
                </div>
                <div class="kpi-sub"><span class="badge {badge_class}">≤ Reorder Threshold</span></div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # Category Breakdown Visualizations
    rows = an.inventory_value_by_category(db)
    if rows:
        df_cat = pd.DataFrame(rows)

        col_chart1, col_chart2 = st.columns([3, 2])

        with col_chart1:
            st.markdown('<div class="section-title">📊 Inventory Value by Category</div>', unsafe_allow_html=True)
            fig_bar = px.bar(
                df_cat,
                x="category",
                y="estimated_inventory_value",
                text="estimated_inventory_value",
                color="category",
                color_discrete_sequence=["#10B981", "#3B82F6", "#8B5CF6", "#F59E0B", "#EC4899"],
            )
            fig_bar.update_traces(
                texttemplate=f"{CUR}%{{text:,.2f}}",
                textposition="outside",
                marker=dict(line=dict(width=0))
            )
            fig_bar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                showlegend=False,
                margin=dict(l=10, r=10, t=25, b=10),
                height=320,
                xaxis=dict(showgrid=False, title="", tickfont=dict(color="#94A3B8")),
                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)", title="", tickfont=dict(color="#94A3B8"))
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_chart2:
            st.markdown('<div class="section-title">🍩 Unit Share by Category</div>', unsafe_allow_html=True)
            fig_donut = px.pie(
                df_cat,
                names="category",
                values="total_units",
                hole=0.6,
                color_discrete_sequence=["#10B981", "#3B82F6", "#8B5CF6", "#F59E0B", "#EC4899"]
            )
            fig_donut.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                showlegend=True,
                legend=dict(font=dict(color="#94A3B8", size=11), orientation="h", yanchor="bottom", y=-0.25),
                margin=dict(l=10, r=10, t=10, b=30),
                height=320
            )
            st.plotly_chart(fig_donut, use_container_width=True)

        # Category Summary Table
        st.markdown('<div class="section-title">📋 Category Breakdown (MongoDB Aggregated)</div>', unsafe_allow_html=True)
        display_df = df_cat.copy()
        display_df["estimated_inventory_value"] = display_df["estimated_inventory_value"].apply(_money)
        display_df.rename(columns={
            "category": "Category",
            "total_units": "Units in Stock",
            "estimated_inventory_value": "Estimated Valuation",
            "distinct_products": "Product Count"
        }, inplace=True)
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No product data found. Run `python -m scripts.seed_data` to initialize sample inventory.")


# =============================================================================
# 2. PRODUCT MANAGEMENT PAGE
# =============================================================================
def page_products():
    st.markdown('<h1 class="page-main-title">Product Catalog Management</h1>', unsafe_allow_html=True)
    st.markdown('<div class="page-main-subtitle">Search, filter, register, update, and manage products with schema validation</div>', unsafe_allow_html=True)

    suppliers = sup.list_suppliers(db)
    supplier_ids = [s["supplier_id"] for s in suppliers]
    supplier_names = {s["supplier_id"]: s["name"] for s in suppliers}

    tab_browse, tab_add, tab_edit, tab_delete = st.tabs([
        "🔍 Browse & Filter",
        "➕ Register Product",
        "✏️ Edit Details",
        "🗑️ Safe Deletion"
    ])

    # --- TAB 1: BROWSE ---
    with tab_browse:
        f1, f2, f3 = st.columns([2, 1, 1])
        search = f1.text_input("Search SKU or Name", placeholder="e.g. BEV-001 or Orange Juice")
        cat = f2.selectbox("Filter Category", ["All Categories"] + ps.list_categories(db))
        status = f3.selectbox("Stock Status Filter", ["All", "In Stock (Normal)", "Low Stock", "Out of Stock"])

        status_mapping = {
            "All": None,
            "In Stock (Normal)": "normal",
            "Low Stock": "low",
            "Out of Stock": "out_of_stock"
        }

        products = _run(lambda: ps.list_products(
            db,
            search=search or None,
            category=None if cat == "All Categories" else cat,
            stock_status=status_mapping[status]
        )) or []

        st.caption(f"Showing **{len(products)}** matching product document(s) from MongoDB")

        if products:
            p_df = _df(products)
            # Add status badges
            def get_status_label(row):
                qty = row.get("quantity_in_stock", 0)
                reorder = row.get("reorder_level", 0)
                if qty == 0:
                    return "🔴 Out of Stock"
                elif qty <= reorder:
                    return f"🟡 Low ({qty} ≤ {reorder})"
                return "🟢 In Stock"

            p_df["Health Status"] = p_df.apply(get_status_label, axis=1)
            p_df["Unit Price"] = p_df["unit_price"].apply(_money)

            cols_order = ["sku", "name", "category", "supplier_id", "Unit Price", "quantity_in_stock", "reorder_level", "Health Status", "updated_at"]
            st.dataframe(p_df[cols_order], use_container_width=True, hide_index=True)
        else:
            st.info("No matching products found.")

    # --- TAB 2: REGISTER ---
    with tab_add:
        if not supplier_ids:
            st.warning("⚠️ No suppliers found. Please register at least one supplier before adding products.")
        else:
            with st.form("form_add_product", clear_on_submit=False):
                st.markdown("##### Product Specifications")
                c1, c2 = st.columns(2)
                new_sku = c1.text_input("Product SKU * (Unique Identifier)", placeholder="e.g. BEV-005")
                new_name = c2.text_input("Product Name *", placeholder="e.g. Sparkling Apple Cider 750ml")

                new_cat = c1.text_input("Category *", placeholder="e.g. Beverages")
                new_supplier = c2.selectbox(
                    "Supplier *",
                    supplier_ids,
                    format_func=lambda sid: f"{sid} — {supplier_names.get(sid, '')}"
                )

                new_price = c1.number_input("Selling Unit Price ($) *", min_value=0.0, step=0.10, format="%.2f")
                new_opening = c2.number_input("Opening Stock Quantity", min_value=0, step=1, value=0, help="Creates matching Opening Stock movement")
                new_reorder = c1.number_input("Reorder Threshold Level *", min_value=0, step=1, value=15)

                st.caption("ℹ️ Fields marked with * are strictly enforced by MongoDB JSON Schema validation.")

                if st.form_submit_button("Register Product Document"):
                    _run(
                        lambda: ps.create_product(
                            db, new_sku, new_name, new_cat, new_supplier,
                            new_price, int(new_opening), int(new_reorder)
                        ),
                        lambda p: f"✅ Product '{p['sku']}' ({p['name']}) successfully created in MongoDB!"
                    )

    # --- TAB 3: EDIT ---
    with tab_edit:
        all_prods = ps.list_products(db)
        if all_prods:
            sku_list = [p["sku"] for p in all_prods]
            edit_sku = st.selectbox("Select Product to Edit", sku_list, key="sel_edit_sku")
            curr = ps.get_product(db, edit_sku)

            st.caption("🔒 SKU and Stock Quantities are locked here. Stock changes are strictly recorded in the Stock Ledger.")

            with st.form("form_edit_product"):
                c1, c2 = st.columns(2)
                e_name = c1.text_input("Product Name", value=curr["name"])
                e_cat = c2.text_input("Category", value=curr["category"])

                sup_idx = supplier_ids.index(curr["supplier_id"]) if curr["supplier_id"] in supplier_ids else 0
                e_supplier = c1.selectbox("Supplier Reference", supplier_ids, index=sup_idx, format_func=lambda s: f"{s} — {supplier_names.get(s, '')}")
                e_price = c2.number_input("Unit Price ($)", min_value=0.0, step=0.10, value=float(curr["unit_price"]), format="%.2f")
                e_reorder = c1.number_input("Reorder Level", min_value=0, step=1, value=int(curr["reorder_level"]))

                if st.form_submit_button("Update Product"):
                    _run(
                        lambda: ps.update_product(
                            db, edit_sku, name=e_name, category=e_cat,
                            supplier_id=e_supplier, unit_price=e_price, reorder_level=int(e_reorder)
                        ),
                        "✅ Product details updated successfully."
                    )
        else:
            st.info("No products available to edit.")

    # --- TAB 4: DELETE ---
    with tab_delete:
        all_prods = ps.list_products(db)
        if all_prods:
            del_sku = st.selectbox("Select Product for Deletion", [p["sku"] for p in all_prods], key="sel_del_sku")
            history_count = len(ss.list_movements(db, del_sku, limit=500))

            if history_count > 0:
                st.markdown(f"""
                    <div class="kpi-container" style="border-color: rgba(239, 68, 68, 0.4); margin-bottom: 1rem;">
                        <div style="font-weight: 700; color: #F87171; font-size: 1rem; margin-bottom: 0.4rem;">
                            🛡️ Audit Safeguard Active: Deletion Prohibited
                        </div>
                        <div style="font-size: 0.85rem; color: #CBD5E1;">
                            Product <code>{del_sku}</code> contains <b>{history_count} historical stock movement records</b>. 
                            MongoDB audit integrity prohibits deleting items with movement ledger history to prevent orphaned records.
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.info(f"Product `{del_sku}` has 0 movement records and is eligible for deletion.")

            confirmed = st.checkbox("I confirm that I want to permanently delete this product record")
            if st.button("Delete Product Document", disabled=(history_count > 0 or not confirmed)):
                _run(lambda: ps.delete_product(db, del_sku), f"✅ Deleted product {del_sku}.")


# =============================================================================
# 3. SUPPLIER MANAGEMENT PAGE
# =============================================================================
def page_suppliers():
    st.markdown('<h1 class="page-main-title">Supplier Directory</h1>', unsafe_allow_html=True)
    st.markdown('<div class="page-main-subtitle">Manage supplier accounts, business contact details, and referential constraints</div>', unsafe_allow_html=True)

    tab_view, tab_add, tab_edit, tab_del = st.tabs([
        "📋 Supplier Directory",
        "➕ Register Supplier",
        "✏️ Edit Supplier",
        "🗑️ Delete Supplier"
    ])

    with tab_view:
        search = st.text_input("Search Suppliers (ID, Name, City, or Contact)", placeholder="e.g. Harbor or Pune")
        suppliers = sup.list_suppliers(db, search or None)
        st.caption(f"Total Registered Suppliers: **{len(suppliers)}**")
        st.dataframe(_df(suppliers), use_container_width=True, hide_index=True)

    with tab_add:
        with st.form("form_add_supplier"):
            st.markdown("##### Supplier Profile")
            c1, c2 = st.columns(2)
            sid = c1.text_input("Supplier ID * (e.g. SUP-006)", placeholder="SUP-006")
            sname = c2.text_input("Supplier Business Name *", placeholder="Apex Distribution Co.")
            contact = c1.text_input("Contact Person", placeholder="Jane Doe")
            phone = c2.text_input("Telephone Number", placeholder="+91-555-0199")
            email = c1.text_input("Email Address", placeholder="orders@apexdist.example.com")
            city = c2.text_input("Operating City", placeholder="Mumbai")

            if st.form_submit_button("Create Supplier Document"):
                _run(
                    lambda: sup.create_supplier(db, sid, sname, contact, phone, email, city),
                    lambda s: f"✅ Created supplier '{s['supplier_id']}' ({s['name']})."
                )

    with tab_edit:
        suppliers = sup.list_suppliers(db)
        if suppliers:
            sel_sid = st.selectbox("Select Supplier to Edit", [s["supplier_id"] for s in suppliers], key="edit_sup_sel")
            s_obj = sup.get_supplier(db, sel_sid)
            with st.form("form_edit_sup"):
                c1, c2 = st.columns(2)
                e_name = c1.text_input("Business Name", value=s_obj["name"])
                e_contact = c2.text_input("Contact Person", value=s_obj.get("contact_person", ""))
                e_phone = c1.text_input("Phone", value=s_obj.get("phone", ""))
                e_email = c2.text_input("Email", value=s_obj.get("email", ""))
                e_city = c1.text_input("City", value=s_obj.get("city", ""))

                if st.form_submit_button("Save Supplier Changes"):
                    _run(
                        lambda: sup.update_supplier(
                            db, sel_sid, name=e_name, contact_person=e_contact,
                            phone=e_phone, email=e_email, city=e_city
                        ),
                        "✅ Supplier updated successfully."
                    )

    with tab_del:
        suppliers = sup.list_suppliers(db)
        if suppliers:
            del_sid = st.selectbox("Select Supplier to Remove", [s["supplier_id"] for s in suppliers], key="del_sup_sel")
            linked_products = len(ps.list_products(db, supplier_id=del_sid))
            if linked_products > 0:
                st.warning(f"⚠️ Supplier `{del_sid}` supplies **{linked_products} active product(s)**. Reassign or delete these products before deleting this supplier.")
            if st.button("Delete Supplier Document", disabled=linked_products > 0):
                _run(lambda: sup.delete_supplier(db, del_sid), f"✅ Deleted supplier {del_sid}.")


# =============================================================================
# 4. STOCK OPERATIONS PAGE
# =============================================================================
def page_stock():
    st.markdown('<h1 class="page-main-title">Stock Movement Operations</h1>', unsafe_allow_html=True)
    st.markdown('<div class="page-main-subtitle">Execute atomic Stock IN, Stock OUT, and Inventory Adjustments with concurrency safety</div>', unsafe_allow_html=True)

    products = ps.list_products(db)
    if not products:
        st.info("No products found in the database.")
        return

    # Notification banner for completed transaction
    flash = st.session_state.pop("flash", None)
    if flash:
        st.success(flash)

    prod_map = {p["sku"]: f"{p['sku']} — {p['name']} ({p['category']})" for p in products}
    sku = st.selectbox("Select Target Product", list(prod_map.keys()), format_func=prod_map.get)
    current = ps.get_product(db, sku)

    curr_stock = current["quantity_in_stock"]
    reorder = current["reorder_level"]
    price = current["unit_price"]

    # Product Overview Metrics
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Available Stock", curr_stock)
    with m2:
        st.metric("Reorder Threshold", reorder)
    with m3:
        st.metric("Unit Selling Price", _money(price))
    with m4:
        val_status = "🟢 Healthy" if curr_stock > reorder else ("🟡 Low Stock" if curr_stock > 0 else "🔴 Depleted")
        st.metric("Inventory Status", val_status)

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # Operation Mode
    op_type = st.radio(
        "Select Operation Classification",
        ["IN", "OUT", "ADJUSTMENT"],
        horizontal=True,
        format_func=lambda x: {
            "IN": "📥 Stock IN (Restock / Receipt)",
            "OUT": "📤 Stock OUT (Sale / Dispatch)",
            "ADJUSTMENT": "⚖️ Inventory Adjustment (Count / Shrinkage)"
        }[x]
    )

    with st.form("form_stock_movement", clear_on_submit=False):
        c_qty, c_reason = st.columns([1, 2])
        if op_type == "ADJUSTMENT":
            qty = c_qty.number_input("Adjustment Quantity (Signed, Non-Zero)", step=1, value=1, help="+ adds stock, - deducts stock. Cannot result in negative stock.")
        else:
            qty = c_qty.number_input("Movement Quantity (Positive Integer)", min_value=1, step=1, value=1)
        
        reason = c_reason.text_input("Operational Reason / Reference *", placeholder="e.g. PO-8921 Restock, Counter Sales, Damaged Write-off")

        # Projected stock calculation preview
        projected = curr_stock + qty if op_type == "IN" else (curr_stock - qty if op_type == "OUT" else curr_stock + qty)
        if projected < 0:
            st.markdown(f'<span style="color: #F87171; font-weight: 600;">⚠️ Projected Stock: {curr_stock} ➔ {projected} (REJECTED: Stock cannot be negative)</span>', unsafe_allow_html=True)
        else:
            st.markdown(f'<span style="color: #34D399; font-weight: 600;">ℹ️ Projected Stock Balance: {curr_stock} ➔ {projected}</span>', unsafe_allow_html=True)

        if st.form_submit_button(f"Commit {op_type} Transaction to MongoDB"):
            action_fn = {"IN": ss.stock_in, "OUT": ss.stock_out, "ADJUSTMENT": ss.adjust_stock}[op_type]
            res = _run(lambda: action_fn(db, sku, int(qty), reason))
            if res:
                st.session_state["flash"] = (
                    f"✅ Transaction Committed ({res['movement']['movement_id']}): "
                    f"Product {sku} stock updated from {res['previous_quantity']} to {res['quantity_in_stock']}."
                )
                st.rerun()

    # Movement History Ledger
    st.markdown('<div class="section-title">📜 Audit Trail: Movement Ledger</div>', unsafe_allow_html=True)
    filter_col1, filter_col2 = st.columns([1, 3])
    only_current = filter_col1.checkbox("Filter by selected product only", value=True)
    limit = filter_col2.slider("Maximum records to display", min_value=10, max_value=100, value=25)

    movements = ss.list_movements(db, sku if only_current else None, limit=limit)
    if movements:
        m_df = _df(movements)
        st.dataframe(m_df, use_container_width=True, hide_index=True)
    else:
        st.info("No movement records found.")


# =============================================================================
# 5. ANALYTICS PAGE (4 MANDATORY AGGREGATION PIPELINES)
# =============================================================================
def _show_pipeline_card(title, description, pipeline_json):
    with st.expander(f"🔍 Inspect MongoDB Aggregation Pipeline: {title}"):
        st.markdown(f"**Pipeline Rationale:** {description}")
        st.code(json.dumps(pipeline_json, indent=2), language="json")


def page_analytics():
    st.markdown('<h1 class="page-main-title">MongoDB Aggregation Analytics</h1>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-main-subtitle">Complex multi-stage aggregation pipelines computed 100% inside MongoDB (no manual Python calculations)</div>',
        unsafe_allow_html=True
    )

    t1, t2, t3, t4, t5 = st.tabs([
        "⚠️ 1. Low-Stock Alert",
        "💰 2. Value by Category",
        "🔄 3. Stock Movement Flow",
        "🏭 4. Supplier Valuation",
        "🛡️ Data Integrity Audit"
    ])

    # --- PIPELINE 1 ---
    with t1:
        st.markdown('<div class="pipeline-badge">Pipeline 1: Low-Stock Products</div>', unsafe_allow_html=True)
        st.markdown("Identifies items where `quantity_in_stock <= reorder_level` using `$match` with `$expr` comparison.")
        
        low_stock = an.low_stock_products(db)
        if low_stock:
            df_low = pd.DataFrame(low_stock)
            df_low["Shortage Units"] = df_low["reorder_level"] - df_low["available_quantity"]

            fig_low = px.bar(
                df_low,
                x="name",
                y=["available_quantity", "reorder_level"],
                barmode="group",
                color_discrete_sequence=["#EF4444", "#94A3B8"],
                labels={"value": "Quantity Units", "variable": "Metric"}
            )
            fig_low.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=280,
                margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(font=dict(color="#94A3B8"), orientation="h", y=1.1)
            )
            st.plotly_chart(fig_low, use_container_width=True)

            st.dataframe(df_low, use_container_width=True, hide_index=True)
        else:
            st.success("🎉 All stock levels are currently above reorder thresholds.")

        _show_pipeline_card("Pipeline 1: Low-Stock Products", "Uses $match with $expr to evaluate $lte comparison between two fields of the same document.", an.LOW_STOCK_PIPELINE)

    # --- PIPELINE 2 ---
    with t2:
        st.markdown('<div class="pipeline-badge">Pipeline 2: Inventory Value by Category</div>', unsafe_allow_html=True)
        st.markdown("Groups products by category and calculates total units, distinct products, and total inventory valuation (`quantity * unit_price`).")

        val_rows = an.inventory_value_by_category(db)
        if val_rows:
            df_val = pd.DataFrame(val_rows)
            fig_cat = px.bar(
                df_val,
                x="category",
                y="estimated_inventory_value",
                text="estimated_inventory_value",
                color="estimated_inventory_value",
                color_continuous_scale="Tealgrn"
            )
            fig_cat.update_traces(texttemplate=f"{CUR}%{{text:,.2f}}", textposition="outside")
            fig_cat.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=300,
                coloraxis_showscale=False,
                margin=dict(l=10, r=10, t=25, b=10)
            )
            st.plotly_chart(fig_cat, use_container_width=True)

            df_val_disp = df_val.copy()
            df_val_disp["estimated_inventory_value"] = df_val_disp["estimated_inventory_value"].apply(_money)
            st.dataframe(df_val_disp, use_container_width=True, hide_index=True)

        _show_pipeline_card("Pipeline 2: Inventory Value by Category", "Uses $group, $sum, and $multiply to aggregate stock quantities and selling prices per category.", an.INVENTORY_BY_CATEGORY_PIPELINE)

    # --- PIPELINE 3 ---
    with t3:
        st.markdown('<div class="pipeline-badge">Pipeline 3: Stock Movement Flow by Category</div>', unsafe_allow_html=True)
        st.markdown("Executes a `$lookup` join from `stock_movements` to `products`, unwinds the joined product document, and groups by category.")

        mov_rows = an.stock_movement_by_category(db)
        if mov_rows:
            df_mov = pd.DataFrame(mov_rows)
            fig_flow = px.bar(
                df_mov,
                x="category",
                y=["total_in_quantity", "total_out_quantity"],
                barmode="group",
                color_discrete_sequence=["#10B981", "#EF4444"],
                labels={"value": "Units Flowed", "variable": "Movement Type"}
            )
            fig_flow.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=300,
                margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(font=dict(color="#94A3B8"), orientation="h", y=1.1)
            )
            st.plotly_chart(fig_flow, use_container_width=True)

            st.dataframe(df_mov, use_container_width=True, hide_index=True)

        _show_pipeline_card("Pipeline 3: Movement by Category", "Uses $lookup to join product details, $unwind to flatten the array, and $cond within $sum to accumulate IN, OUT, and ADJUSTMENTS.", an.MOVEMENT_BY_CATEGORY_PIPELINE)

    # --- PIPELINE 4 ---
    with t4:
        st.markdown('<div class="pipeline-badge">Pipeline 4: Supplier Inventory Summary</div>', unsafe_allow_html=True)
        st.markdown("Joins `products` to `suppliers` with `$lookup`, calculates distinct products supplied, and computes total inventory value per supplier.")

        sup_rows = an.supplier_inventory_summary(db)
        if sup_rows:
            df_sup = pd.DataFrame(sup_rows)
            fig_sup = px.bar(
                df_sup,
                x="supplier_name",
                y="estimated_inventory_value",
                text="estimated_inventory_value",
                color="product_count",
                color_continuous_scale="Purp"
            )
            fig_sup.update_traces(texttemplate=f"{CUR}%{{text:,.2f}}", textposition="outside")
            fig_sup.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=300,
                coloraxis_showscale=False,
                margin=dict(l=10, r=10, t=25, b=10)
            )
            st.plotly_chart(fig_sup, use_container_width=True)

            df_sup_disp = df_sup.copy()
            df_sup_disp["estimated_inventory_value"] = df_sup_disp["estimated_inventory_value"].apply(_money)
            st.dataframe(df_sup_disp, use_container_width=True, hide_index=True)

        _show_pipeline_card("Pipeline 4: Supplier Summary", "Uses $lookup to connect products with suppliers and $group to compute supplier inventory share.", an.SUPPLIER_SUMMARY_PIPELINE)

    # --- INTEGRITY AUDIT ---
    with t5:
        st.markdown('<div class="pipeline-badge">Data Integrity Audit: Stock vs Movement History</div>', unsafe_allow_html=True)
        st.markdown("Verifies mathematical consistency: `Current Stock == Sum(IN) - Sum(OUT) + Sum(ADJUSTMENT)` using `$reduce` aggregation.")

        mismatches = an.stock_consistency_mismatches(db)
        if mismatches:
            st.error(f"⚠️ Audit Failure: {len(mismatches)} product(s) disagree with their movement ledger.")
            st.dataframe(_df(mismatches), use_container_width=True, hide_index=True)
        else:
            st.markdown("""
                <div class="kpi-container" style="border-color: rgba(16, 185, 129, 0.4);">
                    <div style="font-weight: 700; color: #34D399; font-size: 1.1rem; margin-bottom: 0.3rem;">
                        ✅ Ledger Integrity Verified: 100% Consistent
                    </div>
                    <div style="font-size: 0.88rem; color: #94A3B8;">
                        Every product's current stock in MongoDB matches the exact net sum of all historical stock movement records.
                    </div>
                </div>
            """, unsafe_allow_html=True)
        _show_pipeline_card("Stock Consistency Audit Pipeline", "Uses $lookup, $addFields, and $reduce to verify ledger balance against stored quantity.", an.CONSISTENCY_PIPELINE)


# -----------------------------------------------------------------------------
# Router
# -----------------------------------------------------------------------------
PAGES = {
    "📊 Dashboard": page_dashboard,
    "🛒 Product Catalog": page_products,
    "🏭 Supplier Directory": page_suppliers,
    "🔄 Stock Operations": page_stock,
    "📈 Deep Analytics": page_analytics
}

render_top_bar()
PAGES[page]()

