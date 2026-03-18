import pandas as pd
import numpy as np
import streamlit as st
import altair as alt

# --- 1. Page Configuration & CSS Styling ---
st.set_page_config(page_title="Full-Funnel Growth Auditor", layout="wide", initial_sidebar_state="expanded")

def apply_custom_style():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        .stApp { background-color: #0f172a; color: #f8fafc; }
        .stMetric { background-color: #1e293b; padding: 20px; border-radius: 12px; border: 1px solid #334155; }
        .ai-card { 
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            padding: 2rem; border-radius: 16px; border: 1px solid #60a5fa; 
            margin-bottom: 2rem; box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }
        .status-tag { padding: 4px 8px; border-radius: 6px; font-weight: bold; font-size: 0.85rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Data Processing Logic ---
def load_and_merge(files):
    # Load Data (GA4 skip 9 rows)
    adj = pd.read_csv(files['adjust'])
    adm = pd.read_csv(files['admin'])
    ga_ev = pd.read_csv(files['ga4_event'], skiprows=9)
    ga_sc = pd.read_csv(files['ga4_screen'], skiprows=9)

    # Normalize campaign keys
    for df in [adj, adm]:
        df['campaign'] = df['campaign'].astype(str).str.strip().str.lower()
    
    # GA4 Event Pivot (Using Exact Japanese Column Names)
    ga_ev['campaign'] = ga_ev['セッションのキャンペーン'].astype(str).str.strip().str.lower()
    ev_pivoted = ga_ev[ga_ev['イベント名'].isin(['PRODUCT_HOME_OBJECT_EVENT', 'OPEN_PRODUCT_HOME', 'OPEN_VIEWER'])]\
        .pivot_table(index='campaign', columns='イベント名', values='イベント数', aggfunc='sum').fillna(0).reset_index()

    # GA4 Screen Grouping
    ga_sc['campaign'] = ga_sc['セッションのキャンペーン'].astype(str).str.strip().str.lower()
    col_screen = 'ページパスとスクリーン クラス'
    ga_sc['screen_group'] = ga_sc[col_screen].apply(lambda x: 'Home' if 'Home' in str(x) else ('Viewer' if 'Viewer' in str(x) else 'Other'))
    sc_pivoted = ga_sc.pivot_table(index='campaign', columns='screen_group', values='表示回数', aggfunc='sum').fillna(0).reset_index()

    # 4-Way Join
    m = pd.merge(adj, adm, on='campaign', how='outer')
    m = pd.merge(m, ev_pivoted, on='campaign', how='left')
    m = pd.merge(m, sc_pivoted, on='campaign', how='left')
    return m.fillna(0)

def calc_metrics(df):
    # 지표 계산
    df['wandering_index'] = df['PRODUCT_HOME_OBJECT_EVENT'] / df['OPEN_PRODUCT_HOME'].replace(0, np.nan)
    df['conv_efficiency'] = (df['OPEN_VIEWER'] / df['OPEN_PRODUCT_HOME'].replace(0, np.nan)) * 100
    
    # 상태 판정
    def get_status(row):
        if row['wandering_index'] > 1.3: return '🔥 Critical'
        if row['wandering_index'] > 1.0: return '⚠️ Warning'
        return '✅ Normal'
    
    df['status'] = df.apply(get_status, axis=1)
    
    # 세그먼트 분류
    df['segment'] = df['campaign'].apply(lambda x: 'ACe' if 'ace' in str(x) else ('ACi' if 'aci' in str(x) else 'Other'))
    return df

# --- 3. AI Strategic Analytics (Japanese Comment Generator) ---
def render_ai_analysis(df):
    avg_wandering = df['wandering_index'].mean()
    critical_count = len(df[df['status'] == '🔥 Critical'])
    top_efficiency = df.nlargest(1, 'conv_efficiency')['campaign'].values[0]
    
    st.markdown(f"""
    <div class="ai-card">
        <h2 style="color: #60a5fa; margin-top:0;">🤖 AI 戦略分析インサイト (Marketing Playbook)</h2>
        <p style="font-size: 1.1rem; line-height: 1.6;">
            現在のデータセットを分析した結果、全体の平均 <b>Wandering Index（ユーザーの迷い）</b> は 
            <span style="color: #f87171; font-weight:bold;">{avg_wandering:.2f}</span> です。
            特に <b>{critical_count}件</b> のキャンペーンにおいて、詳細ページでの離脱や回遊の停滞が確認されました。
        </p>
        <hr style="border: 0.5px solid #334155; margin: 1.5rem 0;">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div>
                <h4 style="color: #fbbf24;">📍 運用改善アクション (Action Plan)</h4>
                <ul style="font-size: 0.95rem;">
                    <li><b>ACeセグメントの最適化:</b> Wandering Indexが高いキャンペーンでは、バナー素材と詳細ページの作品ジャンルの一致性を再確認してください。</li>
                    <li><b>CVR向上のための導線修正:</b> 効率が良い <b>{top_efficiency}</b> の設定を参考に、他のキャンペーンの「今すぐ読む」ボタンの配置をA/Bテストしてください。</li>
                </ul>
            </div>
            <div>
                <h4 style="color: #10b981;">📈 スケール推奨 (Scale-up)</h4>
                <ul style="font-size: 0.95rem;">
                    <li><b>予算配分の再検討:</b> 効率値が50%を超え、かつWandering Indexが1.0未満の優良キャンペーンへの予算集中を推奨します。</li>
                    <li><b>リテンション強化:</b> Viewer到達後の継続率を高めるため、作品の「お気に入り登録」イベントとの相関分析を次ステップとして推奨します。</li>
                </ul>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- 4. Main UI Rendering ---
def main():
    apply_custom_style()
    
    # Sidebar
    with st.sidebar:
        st.title("📁 Data Center")
        st.markdown("---")
        f_adj = st.file_uploader("1. Adjust CSV (広告データ)", type="csv")
        f_adm = st.file_uploader("2. Admin CSV (社内実績)", type="csv")
        f_gev = st.file_uploader("3. GA4 Event CSV (行動ログ)", type="csv")
        f_gsc = st.file_uploader("4. GA4 Screen CSV (画面ログ)", type="csv")
        st.info("※ GA4データは上部9行を自動スキップします。")

    if all([f_adj, f_adm, f_gev, f_gsc]):
        # Data Load
        files = {'adjust': f_adj, 'admin': f_adm, 'ga4_event': f_gev, 'ga4_screen': f_gsc}
        df = calc_metrics(load_and_merge(files))
        
        # Title
        st.title("🚀 Full-Funnel Growth Auditor")
        
        # A. Executive Metrics
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("合計広告費 (Spend)", f"${df['spend'].sum():,.0f}")
        m2.metric("合計売上 (Revenue)", f"${df['revenue'].sum():,.0f}")
        m3.metric("迷い指数 (Avg. Wandering)", f"{df['wandering_index'].mean():.2f}")
        m4.metric("転換効率 (Avg. Conv. Eff.)", f"{df['conv_efficiency'].mean():.1f}%")
        m5.metric("警告対象 (Critical)", f"{len(df[df['status'] == '🔥 Critical'])}건")

        # B. AI Analysis Section (New!)
        render_ai_analysis(df)

        # C. Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 ユーザー・ファンネル (User Funnel)")
            funnel_data = pd.DataFrame({
                'Stage': ['Installs', 'Detail Views', 'Viewer Entry', 'Revenue Users'],
                'Count': [df['installs'].sum(), df['OPEN_PRODUCT_HOME'].sum(), df['OPEN_VIEWER'].sum(), df['activated_users'].sum()]
            })
            funnel_chart = alt.Chart(funnel_data).mark_bar(color='#3b82f6', cornerRadiusEnd=8).encode(
                x=alt.X('Count:Q', title="ユーザー数"),
                y=alt.Y('Stage:N', sort='-x', title="ステップ")
            ).properties(height=350)
            st.altair_chart(funnel_chart, use_container_width=True)

        with col2:
            st.subheader("🔍 UX摩擦分析 (Friction Analysis)")
            scatter = alt.Chart(df).mark_circle(size=120).encode(
                x=alt.X('wandering_index:Q', title="Wandering Index (迷い)"),
                y=alt.Y('conv_efficiency:Q', title="転換効率 (%)"),
                color=alt.Color('status:N', scale=alt.Scale(domain=['✅ Normal', '⚠️ Warning', '🔥 Critical'], range=['#10b981', '#fbbf24', '#f87171'])),
                tooltip=['campaign', 'wandering_index', 'conv_efficiency', 'status']
            ).properties(height=350).interactive()
            st.altair_chart(scatter, use_container_width=True)

        # D. Data Table
        st.subheader("📋 キャンペーン別詳細監査レポート")
        st.dataframe(df.style.format({
            'spend': '${:,.0f}', 'revenue': '${:,.0f}', 
            'wandering_index': '{:.2f}', 'conv_efficiency': '{:.1f}%'
        }), use_container_width=True)
        
        # Download Center
        st.sidebar.markdown("---")
        st.sidebar.download_button(
            "📥 統合結果をダウンロード", 
            df.to_csv(index=False).encode('utf-8-sig'), 
            "audit_result.csv", 
            "text/csv",
            use_container_width=True
        )
    else:
        st.warning("⚠️ サイドバーから4つのCSVファイルをすべてアップロードしてください。")

if __name__ == "__main__":
    main()
