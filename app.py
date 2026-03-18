import pandas as pd
import numpy as np
import streamlit as st
import altair as alt

# --- 1. Page Configuration & Style ---
st.set_page_config(page_title="フルファネル・成長監査システム", layout="wide", initial_sidebar_state="expanded")

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
    df['wandering_index'] = df['PRODUCT_HOME_OBJECT_EVENT'] / df['OPEN_PRODUCT_HOME'].replace(0, np.nan)
    df['conv_efficiency'] = (df['OPEN_VIEWER'] / df['OPEN_PRODUCT_HOME'].replace(0, np.nan)) * 100
    df['roas'] = (df['revenue'] / df['spend'].replace(0, np.nan)) * 100
    df['status'] = df['wandering_index'].apply(lambda x: '🔥 危険 (Critical)' if x > 1.3 else ('⚠️ 警告 (Warning)' if x > 1.0 else '✅ 正常 (Normal)'))
    df['segment'] = df['campaign'].apply(lambda x: 'ACe' if 'ace' in str(x) else ('ACi' if 'aci' in str(x) else 'その他'))
    return df

# --- 3. AI Analysis Section ---
def render_ai_analysis(df):
    avg_wandering = df['wandering_index'].mean()
    critical_count = len(df[df['status'] == '🔥 危険 (Critical)'])
    
    st.markdown(f"""
    <div class="ai-card">
        <h2 style="color: #60a5fa; margin-top:0;">🤖 AI 戦略分析インサイト</h2>
        <p>全体の「迷い指数」平均は <b>{avg_wandering:.2f}</b> です。現在、<b>{critical_count}件</b> のキャンペーンでUXの摩擦が大きく、改善の余地があります。</p>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 10px;">
            <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px;">
                <h4 style="color: #fbbf24; margin-top:0;">⚠️ ボトルネックの特定</h4>
                <p style="font-size: 0.9rem;">摩擦が高いキャンペーンは、クリエイティブと作品詳細ページの整合性を確認してください。</p>
            </div>
            <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px;">
                <h4 style="color: #10b981; margin-top:0;">🚀 最適化の方向性</h4>
                <p style="font-size: 0.9rem;">転換効率が高いセグメントへの予算集中と、Viewer到達後の課金誘導を強化しましょう。</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

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
        m5.metric("危険対象", f"{len(df[df['status'] == '🔥 危険 (Critical)'])}件")

        render_ai_analysis(df)

        # B. 핵심 시각화: 유저 퍼널 & UX 마찰 분석 (복구됨)
        st.markdown("<h3 class='section-title'>🎯 コア・ダイアグノシス (Core Diagnosis)</h3>", unsafe_allow_html=True)
        col_f1, col_f2 = st.columns(2)
        
        with col_f1:
            st.write("📊 **ユーザー・ファンネル (User Funnel)**")
            funnel_data = pd.DataFrame({
                'ステップ': ['Installs', 'Detail Views', 'Viewer Entry', 'Revenue Users'],
                'ユーザー数': [df['installs'].sum(), df['OPEN_PRODUCT_HOME'].sum(), df['OPEN_VIEWER'].sum(), df['activated_users'].sum()]
            })
            funnel_chart = alt.Chart(funnel_data).mark_bar(color='#3b82f6', cornerRadiusEnd=8).encode(
                x=alt.X('ユーザー数:Q'),
                y=alt.Y('ステップ:N', sort='-x')
            ).properties(height=350)
            st.altair_chart(funnel_chart, use_container_width=True)

        with col_f2:
            st.write("🔍 **UX摩擦分析 (Friction Analysis)**")
            
            scatter = alt.Chart(df).mark_circle(size=120).encode(
                x=alt.X('wandering_index:Q', title="迷い指数 (Wandering Index)"),
                y=alt.Y('conv_efficiency:Q', title="転換効率 (Conv. Efficiency %)"),
                color=alt.Color('status:N', scale=alt.Scale(domain=['✅ 正常 (Normal)', '⚠️ 警告 (Warning)', '🔥 危険 (Critical)'], range=['#10b981', '#fbbf24', '#f87171']), title="ステータス"),
                tooltip=['campaign', 'wandering_index', 'conv_efficiency', 'status']
            ).properties(height=350).interactive()
            st.altair_chart(scatter, use_container_width=True)

        # C. 고급 시각화: 리텐션 & 세그먼트 & 예산 효율
        st.markdown("<h3 class='section-title'>📈 高度な多角分析</h3>", unsafe_allow_html=True)
        col_a1, col_a2 = st.columns(2)
        
        with col_a1:
            st.write("🗓️ **リテンション・コホート (1日目 vs 7日目)**")
            h_data = df.melt(id_vars=['campaign'], value_vars=['d1_retention', 'd7_retention'], var_name='経過', value_name='率')
            h_data['経過'] = h_data['経過'].replace({'d1_retention': '1日目', 'd7_retention': '7日目'})
            heatmap = alt.Chart(h_data).mark_rect().encode(
                x=alt.X('経過:N', sort=['1日目', '7日目']),
                y=alt.Y('campaign:N'),
                color=alt.Color('率:Q', scale=alt.Scale(scheme='viridis'))
            ).properties(height=350)
            st.altair_chart(heatmap, use_container_width=True)

        with col_a2:
            st.write("📊 **セグメント別主要指標比較**")
            seg_data = df.groupby('segment').agg({'wandering_index':'mean', 'conv_efficiency':'mean'}).reset_index().melt(id_vars='segment')
            seg_chart = alt.Chart(seg_data).mark_bar().encode(
                x=alt.X('value:Q', title="スコア"),
                y=alt.Y('variable:N', title=None),
                color=alt.Color('segment:N'),
                row=alt.Row('segment:N', title=None)
            ).properties(height=80)
            st.altair_chart(seg_chart, use_container_width=True)

        st.write("💰 **予算配分 vs ROAS 効率分析**")
        bubble = alt.Chart(df).mark_circle().encode(
            x=alt.X('spend:Q', title="広告費 (Spend)"),
            y=alt.Y('roas:Q', title="ROAS (%)"),
            size=alt.Size('installs:Q', scale=alt.Scale(range=[100, 2000])),
            color=alt.Color('status:N'),
            tooltip=['campaign', 'spend', 'roas']
        ).properties(height=400).interactive()
        st.altair_chart(bubble, use_container_width=True)

        # D. Data Table
        st.markdown("<h3 class='section-title'>📋 監査データ一覧</h3>", unsafe_allow_html=True)
        st.dataframe(df.style.format({'spend': '${:,.0f}', 'revenue': '${:,.0f}', 'wandering_index': '{:.2f}', 'conv_efficiency': '{:.1f}%'}), use_container_width=True)
        
        st.sidebar.download_button("📥 統合データをCSVで保存", df.to_csv(index=False).encode('utf-8-sig'), "full_audit_jp.csv", use_container_width=True)
    else:
        st.warning("👋 サイドバーから4つのCSVファイルをすべてアップロードしてください。")

if __name__ == "__main__":
    main()
