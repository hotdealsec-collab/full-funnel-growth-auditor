import pandas as pd
import numpy as np
import streamlit as st
import altair as alt

# --- 1. Page Configuration & Style ---
st.set_page_config(page_title="フルファネル・成長監査システム Pro", layout="wide", initial_sidebar_state="expanded")

def apply_custom_style():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');
        html, body, [class*="css"] { font-family: 'Noto Sans JP', sans-serif; }
        .stApp { background-color: #0f172a; color: #f8fafc; }
        .stMetric { background-color: #1e293b; padding: 20px; border-radius: 12px; border: 1px solid #334155; }
        .ai-card { 
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            padding: 2rem; border-radius: 16px; border: 1px solid #60a5fa; 
            margin-bottom: 2rem; box-shadow: 0 4px 25px rgba(0,0,0,0.4);
        }
        .bottleneck-tag {
            background-color: #ef4444; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; margin-right: 8px;
        }
        .section-title { color: #60a5fa; font-weight: bold; margin-top: 2rem; margin-bottom: 1.5rem; border-left: 5px solid #60a5fa; padding-left: 12px; font-size: 1.4rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Data Processing Logic ---
def load_and_merge(files):
    adj = pd.read_csv(files['adjust'])
    adm = pd.read_csv(files['admin'])
    ga_ev = pd.read_csv(files['ga4_event'], skiprows=9)
    ga_sc = pd.read_csv(files['ga4_screen'], skiprows=9)

    for df in [adj, adm]:
        df['campaign'] = df['campaign'].astype(str).str.strip().str.lower()
    
    # GA4 Event Pivot
    ga_ev['campaign'] = ga_ev['セッションのキャンペーン'].astype(str).str.strip().str.lower()
    ev_pivoted = ga_ev[ga_ev['イベント名'].isin(['PRODUCT_HOME_OBJECT_EVENT', 'OPEN_PRODUCT_HOME', 'OPEN_VIEWER'])]\
        .pivot_table(index='campaign', columns='イベント名', values='イベント数', aggfunc='sum').fillna(0).reset_index()

    # GA4 Screen Grouping
    ga_sc['campaign'] = ga_sc['セッションのキャンペーン'].astype(str).str.strip().str.lower()
    col_screen = 'ページパスとスクリーン クラス'
    ga_sc['screen_group'] = ga_sc[col_screen].apply(lambda x: 'Home' if 'Home' in str(x) else ('Viewer' if 'Viewer' in str(x) else 'Other'))
    sc_pivoted = ga_sc.pivot_table(index='campaign', columns='screen_group', values='表示回数', aggfunc='sum').fillna(0).reset_index()

    m = pd.merge(adj, adm, on='campaign', how='outer')
    m = pd.merge(m, ev_pivoted, on='campaign', how='left')
    m = pd.merge(m, sc_pivoted, on='campaign', how='left')
    return m.fillna(0)

def calc_metrics(df):
    # 基本指標の計算
    df['wandering_index'] = df['PRODUCT_HOME_OBJECT_EVENT'] / df['OPEN_PRODUCT_HOME'].replace(0, np.nan)
    df['conv_efficiency'] = (df['OPEN_VIEWER'] / df['OPEN_PRODUCT_HOME'].replace(0, np.nan)) * 100
    df['roas'] = (df['revenue'] / df['spend'].replace(0, np.nan)) * 100
    
    # ボトルネック判定ロジック
    # 1. 導線摩擦: クリックは多いがページ遷移が伴わない場合
    # 2. 遷移不全: スクリーン表示回数に対してイベント発生が極端に低い場合
    df['home_engagement'] = df['OPEN_PRODUCT_HOME'] / df['Home'].replace(0, np.nan)
    
    def detect_bottleneck(row):
        issues = []
        if row['wandering_index'] > 1.5: issues.append("UX摩擦 (Home)")
        if row['home_engagement'] < 0.2: issues.append("クリック率低迷 (Home)")
        if row['conv_efficiency'] < 10: issues.append("転換の壁 (Viewer)")
        return ", ".join(issues) if issues else "最適化済み"

    df['bottleneck_type'] = df.apply(detect_bottleneck, axis=1)
    df['status'] = df['wandering_index'].apply(lambda x: '🔥 危険 (Critical)' if x > 1.3 else ('⚠️ 警告 (Warning)' if x > 1.0 else '✅ 正常 (Normal)'))
    df['segment'] = df['campaign'].apply(lambda x: 'ACe' if 'ace' in str(x) else ('ACi' if 'aci' in str(x) else 'その他'))
    return df

# --- 3. AI Analysis & Bottleneck Display ---
def render_ai_analysis(df):
    avg_wandering = df['wandering_index'].mean()
    critical_df = df[df['status'] == '🔥 危険 (Critical)'].head(5)
    
    st.markdown(f"""
    <div class="ai-card">
        <h2 style="color: #60a5fa; margin-top:0;">🤖 AI 成長監査・ボトルネック警告</h2>
        <p>全体の「迷い指数」平均は <b>{avg_wandering:.2f}</b> です。以下のキャンペーンで<b>クラス間の不整合</b>が検出されました。</p>
        <div style="margin-top: 15px;">
    """, unsafe_allow_html=True)
    
    if not critical_df.empty:
        for _, row in critical_df.iterrows():
            st.markdown(f"""
            <div style="background: rgba(239, 68, 68, 0.1); border-left: 4px solid #ef4444; padding: 10px; margin-bottom: 8px; border-radius: 4px;">
                <span class="bottleneck-tag">警告</span> 
                <b>{row['campaign']}</b>: <span style="color: #f87171;">{row['bottleneck_type']}</span> 
                (迷い指数: {row['wandering_index']:.2f} / 転換率: {row['conv_efficiency']:.1f}%)
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("✅ 現在、重大なボトルネックは検出されていません。")
        
    st.markdown("</div></div>", unsafe_allow_html=True)

# --- 4. Main UI Rendering ---
def main():
    apply_custom_style()
    
    with st.sidebar:
        st.title("📁 データセンター")
        f_adj = st.file_uploader("1. Adjust (広告費)", type="csv")
        f_adm = st.file_uploader("2. Admin (社内実績)", type="csv")
        f_gev = st.file_uploader("3. GA4 イベント", type="csv")
        f_gsc = st.file_uploader("4. GA4 スクリーン", type="csv")

    if all([f_adj, f_adm, f_gev, f_gsc]):
        df = calc_metrics(load_and_merge({'adjust': f_adj, 'admin': f_adm, 'ga4_event': f_gev, 'ga4_screen': f_gsc}))
        
        st.title("🚀 フルファネル・成長監査システム")
        
        # A. Top Metrics
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("合計広告費", f"${df['spend'].sum():,.0f}")
        m2.metric("合計売上", f"${df['revenue'].sum():,.0f}")
        m3.metric("平均迷い指数", f"{df['wandering_index'].mean():.2f}")
        m4.metric("平均転換効率", f"{df['conv_efficiency'].mean():.1f}%")
        m5.metric("ボトルネック件数", f"{len(df[df['bottleneck_type'] != '最適化済み'])}件")

        render_ai_analysis(df)

        # B. 新設：クラス別ボトルネック詳細分析
        st.markdown("<h3 class='section-title'>🔍 クラス別ボトルネック分析 (Class Deep Dive)</h3>", unsafe_allow_html=True)
        col_f1, col_f2 = st.columns(2)
        
        with col_f1:
            st.write("📊 **スクリーン表示 vs イベント発生 (Friction Map)**")
            bubble_chart = alt.Chart(df).mark_circle().encode(
                x=alt.X('Home:Q', title="Home スクリーン表示数"),
                y=alt.Y('PRODUCT_HOME_OBJECT_EVENT:Q', title="Home クリックイベント数"),
                size=alt.Size('wandering_index:Q', scale=alt.Scale(range=[100, 1000]), title="迷い指数"),
                color=alt.Color('status:N', scale=alt.Scale(domain=['✅ 正常 (Normal)', '⚠️ 警告 (Warning)', '🔥 危険 (Critical)'], range=['#10b981', '#fbbf24', '#f87171'])),
                tooltip=['campaign', 'Home', 'PRODUCT_HOME_OBJECT_EVENT', 'bottleneck_type']
            ).properties(height=350).interactive()
            st.altair_chart(bubble_chart, use_container_width=True)

        with col_f2:
            st.write("📉 **ボトルネック種類の分布**")
            issue_counts = df['bottleneck_type'].str.split(', ').explode().value_counts().reset_index()
            issue_counts.columns = ['Issue', 'Count']
            issue_chart = alt.Chart(issue_counts[issue_counts['Issue'] != '最適化済み']).mark_bar(color='#f87171', cornerRadiusEnd=10).encode(
                x=alt.X('Count:Q', title="件数"),
                y=alt.Y('Issue:N', sort='-x', title=None)
            ).properties(height=350)
            st.altair_chart(issue_chart, use_container_width=True)

        # C. 既存の主要分析チャート
        st.markdown("<h3 class='section-title'>📈 高度な多角分析</h3>", unsafe_allow_html=True)
        col_c1, col_c2 = st.columns(2)
        
        with col_c1:
            st.write("📊 **ユーザー・ファンネル (User Funnel)**")
            funnel_data = pd.DataFrame({
                'ステップ': ['Installs', 'Detail Views', 'Viewer Entry', 'Revenue Users'],
                'ユーザー数': [df['installs'].sum(), df['OPEN_PRODUCT_HOME'].sum(), df['OPEN_VIEWER'].sum(), df['activated_users'].sum()]
            })
            st.altair_chart(alt.Chart(funnel_data).mark_bar(color='#3b82f6').encode(x='ユーザー数:Q', y=alt.Y('ステップ:N', sort='-x')), use_container_width=True)

        with col_c2:
            st.write("🗓️ **リテンション・コホート**")
            h_data = df.melt(id_vars=['campaign'], value_vars=['d1_retention', 'd7_retention'], var_name='経過', value_name='率')
            st.altair_chart(alt.Chart(h_data).mark_rect().encode(x='経過:N', y='campaign:N', color='率:Q'), use_container_width=True)

        # D. Data Table (既存のスタイル維持 + ボトルネック列追加)
        st.markdown("<h3 class='section-title'>📋 監査データ一覧</h3>", unsafe_allow_html=True)
        st.dataframe(df.style.format({
            'spend': '${:,.0f}', 'revenue': '${:,.0f}', 'wandering_index': '{:.2f}', 'conv_efficiency': '{:.1f}%'
        }), use_container_width=True)
        
        st.sidebar.download_button("📥 統合データをCSVで保存", df.to_csv(index=False).encode('utf-8-sig'), "full_audit_jp_pro.csv", use_container_width=True)
    else:
        st.warning("👋 サイドバーから4つのCSVファイルをすべてアップロードしてください。")

if __name__ == "__main__":
    main()
