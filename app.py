import pandas as pd
import numpy as np
import streamlit as st
import altair as alt

# --- Page Config ---
st.set_page_config(page_title="Full-Funnel Growth Auditor", layout="wide", initial_sidebar_state="expanded")

# --- UI Styling ---
def apply_style():
    st.markdown("""
    <style>
        .stApp { background-color: #0f172a; color: #f8fafc; }
        .stMetric { background-color: #1e293b; padding: 20px; border-radius: 12px; border: 1px solid #334155; }
        .info-card { background-color: #1e293b; padding: 1.5rem; border-radius: 12px; border: 1px solid #334155; margin: 1rem 0; }
    </style>
    """, unsafe_allow_html=True)

# --- Logic: Data Processing ---
def load_and_merge(files):
    # Load with GA4 specific logic (skip 9 rows)
    adj = pd.read_csv(files['adjust'])
    adm = pd.read_csv(files['admin'])
    ga_ev = pd.read_csv(files['ga4_event'], skiprows=9)
    ga_sc = pd.read_csv(files['ga4_screen'], skiprows=9)

    # Normalize campaign keys
    for df in [adj, adm]:
        df['campaign'] = df['campaign'].astype(str).str.strip().str.lower()
    
    # GA4 Event Pivot
    ga_ev['campaign'] = ga_ev['セッションのキャンペーン'].astype(str).str.strip().str.lower()
    ev_pivoted = ga_ev[ga_ev['イベント名'].isin(['PRODUCT_HOME_OBJECT_EVENT', 'OPEN_PRODUCT_HOME', 'OPEN_VIEWER'])]\
        .pivot_table(index='campaign', columns='イベント名', values='イベント数', aggfunc='sum').fillna(0).reset_index()

    # GA4 Screen Grouping
    ga_sc['campaign'] = ga_sc['セッションのキャンペーン'].astype(str).str.strip().str.lower()
    ga_sc['screen_group'] = ga_sc['ページパスとスクリーン クラス'].apply(lambda x: 'Home' if 'Home' in str(x) else ('Viewer' if 'Viewer' in str(x) else 'Other'))
    sc_pivoted = ga_sc.pivot_table(index='campaign', columns='screen_group', values='表示回数', aggfunc='sum').fillna(0).reset_index()

    # Sequential Join
    m = pd.merge(adj, adm, on='campaign', how='outer')
    m = pd.merge(m, ev_pivoted, on='campaign', how='left')
    m = pd.merge(m, sc_pivoted, on='campaign', how='left')
    return m.fillna(0)

def calc_metrics(df):
    df['wandering_index'] = df['PRODUCT_HOME_OBJECT_EVENT'] / df['OPEN_PRODUCT_HOME'].replace(0, np.nan)
    df['conv_efficiency'] = (df['OPEN_VIEWER'] / df['OPEN_PRODUCT_HOME'].replace(0, np.nan)) * 100
    df['status'] = df['wandering_index'].apply(lambda x: 'Critical' if x > 1.3 else ('Warning' if x > 1.0 else 'Normal'))
    return df

# --- UI: Rendering ---
def main():
    apply_style()
    st.title("🚀 Full-Funnel Growth Auditor")
    
    # Sidebar Uploaders
    with st.sidebar:
        st.header("📁 Data Upload")
        f_adj = st.file_uploader("Adjust CSV", type="csv")
        f_adm = st.file_uploader("Admin CSV", type="csv")
        f_gev = st.file_uploader("GA4 Event CSV", type="csv")
        f_gsc = st.file_uploader("GA4 Screen CSV", type="csv")
    
    if all([f_adj, f_adm, f_gev, f_gsc]):
        files = {'adjust': f_adj, 'admin': f_adm, 'ga4_event': f_gev, 'ga4_screen': f_gsc}
        df = calc_metrics(load_and_merge(files))
        
        # Dashboard
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Spend", f"${df['spend'].sum():,.0f}")
        c2.metric("Avg. Wandering", f"{df['wandering_index'].mean():.2f}")
        c3.metric("Avg. Conv. Eff.", f"{df['conv_efficiency'].mean():.1f}%")
        
        st.subheader("📋 Campaign Audit Results")
        st.dataframe(df, use_container_width=True)
        
        # Download
        st.download_button("📥 Download Result", df.to_csv(index=False).encode('utf-8-sig'), "audit_result.csv", "text/csv")
    else:
        st.info("Please upload all 4 files in the sidebar to start analysis.")

if __name__ == "__main__":
    main()
