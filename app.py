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
            margin-bottom: 1rem; box-shadow: 0 4px 25px rgba(0,0,0,0.4);
        }
        .help-card {
            background: rgba(255, 255, 255, 0.05); padding: 1.5rem; border-radius: 12px; border: 1px dashed #475569; margin-bottom: 2rem;
        }
        .bottleneck-tag {
            background-color: #ef4444; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; margin-right: 8px;
        }
        .section-title { color: #60a5fa; font-weight: bold; margin-top: 2rem; margin-bottom: 1.5rem; border-left: 5px solid #60a5fa; padding-left: 12px; font-size: 1.4rem; }
        .guide-title { color: #94a3b8; font-size: 0.9rem; font-weight: bold; margin-bottom: 0.5rem; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Data Processing Logic (変更なし) ---
def load_and_merge(files):
    adj = pd.read_csv(files['adjust'])
    adm = pd.read_csv(files['admin'])
    ga_ev = pd.read_csv(files['ga4_event'], skiprows=9)
    ga_sc = pd.read_csv(files['ga4_screen'], skiprows=9)
    for df in [adj, adm]:
        df['campaign'] = df['campaign'].astype(str).str.strip().str.lower()
    ga_ev['campaign'] = ga_ev['セッションのキャンペーン'].astype(str).str.strip().str.lower()
    ev_pivoted = ga_ev[ga_ev['イベント名'].isin(['PRODUCT_HOME_OBJECT_EVENT', 'OPEN_PRODUCT_HOME', 'OPEN_VIEWER'])]\
        .pivot_table(index='campaign', columns='イベント名', values='イベント数', aggfunc='sum').fillna(0).reset_index()
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
    df['home_engagement'] = df['OPEN_PRODUCT_HOME'] / df['Home'].replace(0, np.nan)
    
    def detect_bottleneck(row):
        issues = []
        if row['wandering_index'] > 1.5: issues.append("UX摩擦 (Home)")
        if row['home_engagement'] < 0.2: issues.append("回遊率低迷 (Home)")
        if row['conv_efficiency'] < 10: issues.append("転換の壁 (Viewer)")
        return ", ".join(issues) if issues else "最適化済み"

    df['bottleneck_type'] = df.apply(detect_bottleneck, axis=1)
    df['status'] = df['wandering_index'].apply(lambda x: '🔥 危険 (Critical)' if x > 1.3 else ('⚠️ 警告 (Warning)' if x > 1.0 else '✅ 正常 (Normal)'))
    df['segment'] = df['campaign'].apply(lambda x: 'ACe' if 'ace' in str(x) else ('ACi' if 'aci' in str(x) else 'その他'))
    return df

# --- 3. AI Analysis & Guide Section ---
def render_ai_analysis(df):
    avg_wandering = df['wandering_index'].mean()
    critical_df = df[df['status'] != '✅ 正常 (Normal)'].sort_values('wandering_index', ascending=False).head(5)
    
    # A. AI 警告カード
    st.markdown(f"""
    <div class="ai-card">
        <h2 style="color: #60a5fa; margin-top:0;">🤖 AI 成長監査・ボトルネック警告</h2>
        <p>全体の「迷い指数」平均は <b>{avg_wandering:.2f}</b> です。以下のキャンペーンで対策が必要なボトルネックが検出されました。</p>
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

    # B. 分析ガイド（ヘルプセクション）
    with st.expander("💡 警告メッセージの解説と改善ガイド"):
        st.markdown("""
        <div class="help-card">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div>
                    <p class="guide-title">🚩 警告の種類と意味</p>
                    <ul style="font-size: 0.85rem; color: #cbd5e1;">
                        <li><b>UX摩擦 (Home):</b> ユーザーがホーム画面で何度も操作しているが、作品詳細へ遷移できていない「迷い」の状態。UIの複雑さが原因。</li>
                        <li><b>回遊率低迷 (Home):</b> 画面は見られているが、主要なボタンが押されていない。クリエイティブとコンテンツの不一致。</li>
                        <li><b>転換の壁 (Viewer):</b> 詳細ページまでは来るが、ビューアー（作品閲覧）に繋がらない。作品の魅力不足や課金障壁。</li>
                    </ul>
                </div>
                <div>
                    <p class="guide-title">🧪 迷い指数 (Wandering Index) とは</p>
                    <p style="font-size: 0.85rem; color: #cbd5e1;">
                        ユーザーが1つの目的（遷移）を達成するために、どれだけ余計な操作を行ったかを示す指標です。<br>
                        <b>1.3以上:</b> ユーザーが混乱し始めています。<br>
                        <b>1.5以上:</b> 明らかなUIの欠陥や、導線エラーの可能性が高い状態です。
                    </p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# --- 4. Main UI Rendering (以下、既存と同様) ---
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
        
        # 指標表示
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("合計広告費", f"${df['spend'].sum():,.0f}")
        m2.metric("合計売上", f"${df['revenue'].sum():,.0f}")
        m3.metric("平均迷い指数", f"{df['wandering_index'].mean():.2f}")
        m4.metric("平均転換効率", f"{df['conv_efficiency'].mean():.1f}%")
        m5.metric("ボトルネック件数", f"{len(df[df['bottleneck_type'] != '最適化済み'])}件")

        render_ai_analysis(df)

        # 既存のグラフ・テーブルセクション
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
            st.altair_chart(alt.Chart(issue_counts[issue_counts['Issue'] != '最適化済み']).mark_bar(color='#f87171', cornerRadiusEnd=10).encode(x='Count:Q', y=alt.Y('Issue:N', sort='-x')), use_container_width=True)

        st.markdown("<h3 class='section-title'>📋 監査データ一覧</h3>", unsafe_allow_html=True)
        st.dataframe(df.style.format({'spend': '${:,.0f}', 'revenue': '${:,.0f}', 'wandering_index': '{:.2f}', 'conv_efficiency': '{:.1f}%'}), use_container_width=True)
        st.sidebar.download_button("📥 統合データをCSVで保存", df.to_csv(index=False).encode('utf-8-sig'), "full_audit_pro.csv", use_container_width=True)
    else:
        st.warning("👋 サイドバーから4つのCSVファイルをすべてアップロードしてください。")

if __name__ == "__main__":
    main()
