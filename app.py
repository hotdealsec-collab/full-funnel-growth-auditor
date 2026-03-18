import pandas as pd
import numpy as np
import streamlit as st
import altair as alt

# --- 1. ページ設定とスタイル (Page Config & Style) ---
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
        .section-title { color: #60a5fa; font-weight: bold; margin-bottom: 1.5rem; border-left: 5px solid #60a5fa; padding-left: 12px; font-size: 1.4rem; }
        .status-tag { padding: 3px 10px; border-radius: 20px; font-weight: bold; font-size: 0.8rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. データ処理ロ직 (Data Integration) ---
def load_and_merge(files):
    # GA4データは上部9行をスキップしてロード
    adj = pd.read_csv(files['adjust'])
    adm = pd.read_csv(files['admin'])
    ga_ev = pd.read_csv(files['ga4_event'], skiprows=9)
    ga_sc = pd.read_csv(files['ga4_screen'], skiprows=9)

    for df in [adj, adm]:
        df['campaign'] = df['campaign'].astype(str).str.strip().str.lower()
    
    # GA4 Event Pivot (日本語のカラム名に対応)
    ga_ev['campaign'] = ga_ev['セッションのキャンペーン'].astype(str).str.strip().str.lower()
    ev_pivoted = ga_ev[ga_ev['イベント名'].isin(['PRODUCT_HOME_OBJECT_EVENT', 'OPEN_PRODUCT_HOME', 'OPEN_VIEWER'])]\
        .pivot_table(index='campaign', columns='イベント名', values='イベント数', aggfunc='sum').fillna(0).reset_index()

    # GA4 Screen Grouping
    ga_sc['campaign'] = ga_sc['セッションのキャンペーン'].astype(str).str.strip().str.lower()
    col_screen = 'ページパスとスクリーン クラス'
    ga_sc['screen_group'] = ga_sc[col_screen].apply(lambda x: 'Home' if 'Home' in str(x) else ('Viewer' if 'Viewer' in str(x) else 'Other'))
    sc_pivoted = ga_sc.pivot_table(index='campaign', columns='screen_group', values='表示回数', aggfunc='sum').fillna(0).reset_index()

    # 4-Way Join (Adjust + Admin + GA4 Event + GA4 Screen)
    m = pd.merge(adj, adm, on='campaign', how='outer')
    m = pd.merge(m, ev_pivoted, on='campaign', how='left')
    m = pd.merge(m, sc_pivoted, on='campaign', how='left')
    return m.fillna(0)

def calc_metrics(df):
    # 主要指標の計算
    df['wandering_index'] = df['PRODUCT_HOME_OBJECT_EVENT'] / df['OPEN_PRODUCT_HOME'].replace(0, np.nan)
    df['conv_efficiency'] = (df['OPEN_VIEWER'] / df['OPEN_PRODUCT_HOME'].replace(0, np.nan)) * 100
    df['roas'] = (df['revenue'] / df['spend'].replace(0, np.nan)) * 100
    
    # ステータス判定
    df['status'] = df['wandering_index'].apply(lambda x: '🔥 危険 (Critical)' if x > 1.3 else ('⚠️ 警告 (Warning)' if x > 1.0 else '✅ 正常 (Normal)'))
    
    # セグメント分類 (キャンペーン名に基づいた抽出)
    df['segment'] = df['campaign'].apply(lambda x: 'ACe' if 'ace' in str(x) else ('ACi' if 'aci' in str(x) else 'その他'))
    return df

# --- 3. AI 戦略分析エンジン (AI Strategic Insights) ---
def render_ai_analysis(df):
    avg_wandering = df['wandering_index'].mean()
    critical_list = df[df['wandering_index'] > 1.3]['campaign'].tolist()
    top_roas_campaign = df.nlargest(1, 'roas')['campaign'].values[0]
    
    st.markdown(f"""
    <div class="ai-card">
        <h2 style="color: #60a5fa; margin-top:0;">🤖 AI 戦略分析インサイト (Marketing Playbook)</h2>
        <p style="font-size: 1.1rem; line-height: 1.6;">
            分析の結果、現在の全体の平均<b>「迷い指数 (Wandering Index)」</b>は <span style="color: #f87171; font-weight:bold;">{avg_wandering:.2f}</span> です。
            一部のキャンペーンでユーザーが詳細ページにて「次に何をすべきか」迷っている兆候が見られます。
        </p>
        <hr style="border: 0.5px solid #334155; margin: 1.5rem 0;">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 25px;">
            <div>
                <h4 style="color: #fbbf24;">📍 最優先改善タスク</h4>
                <ul style="font-size: 0.95rem; line-height: 1.8;">
                    <li><b>ユーザー摩擦の解消:</b> 迷い指数が高いキャンペーン（{", ".join(critical_list[:2])}など）は、作品詳細ページの「今すぐ読む」ボタンの視認性を高めてください。</li>
                    <li><b>クリエイティブの整合性:</b> ACeセグメントの転換効率が低い場合、広告バナーと着地ページの作品ミスマッチを修正してください。</li>
                </ul>
            </div>
            <div>
                <h4 style="color: #10b981;">📈 スケール推奨戦略</h4>
                <ul style="font-size: 0.95rem; line-height: 1.8;">
                    <li><b>予算配分の最適化:</b> 転換効率が最も高い <b>{top_roas_campaign}</b> の成功パターンを他のACiキャンペーンに横展開してください。</li>
                    <li><b>LTV向上の施策:</b> Viewer到達率が高い層に対し、リテンションを高めるためのアプリ内プッシュ通知のシナリオを強化してください。</li>
                </ul>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- 4. メイン UI レンダリング (Main UI) ---
def main():
    apply_custom_style()
    
    # サイドバー: ファイルアップローダー
    with st.sidebar:
        st.title("📁 データセンター")
        st.markdown("---")
        f_adj = st.file_uploader("1. Adjust (広告費データ)", type="csv")
        f_adm = st.file_uploader("2. Admin (社内実績データ)", type="csv")
        f_gev = st.file_uploader("3. GA4 イベント (行動ログ)", type="csv")
        f_gsc = st.file_uploader("4. GA4 スクリーン (画面ログ)", type="csv")
        st.info("💡 GA4データは自動的にクレンジングされます。")

    if all([f_adj, f_adm, f_gev, f_gsc]):
        # データ統合と計算
        files = {'adjust': f_adj, 'admin': f_adm, 'ga4_event': f_gev, 'ga4_screen': f_gsc}
        df = calc_metrics(load_and_merge(files))
        
        st.title("🚀 フルファネル・成長監査システム")
        
        # A. エグゼクティブ・メトリクス
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("合計広告費", f"${df['spend'].sum():,.0f}")
        m2.metric("合計売上", f"${df['revenue'].sum():,.0f}")
        m3.metric("平均迷い指数", f"{df['wandering_index'].mean():.2f}")
        m4.metric("平均転換効率", f"{df['conv_efficiency'].mean():.1f}%")
        m5.metric("危険対象 (件数)", f"{len(df[df['status'] == '🔥 危険 (Critical)'])}件")

        # B. AI 戦略分析セクション
        render_ai_analysis(df)

        # C. 可視化チャート
        st.markdown("<h3 class='section-title'>📈 詳細分析レポート</h3>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            # 1. リテンション・コホート (D1 vs D7)
            st.write("🗓️ **リテンション分析 (1日目 vs 7日目)**")
            heatmap_data = df.melt(id_vars=['campaign'], value_vars=['d1_retention', 'd7_retention'], var_name='経過', value_name='率')
            heatmap_data['経過'] = heatmap_data['経過'].replace({'d1_retention': '1日目', 'd7_retention': '7日目'})
            
            heatmap = alt.Chart(heatmap_data).mark_rect().encode(
                x=alt.X('経過:N', title=None, sort=['1日目', '7日目']),
                y=alt.Y('campaign:N', title="キャンペーン"),
                color=alt.Color('率:Q', scale=alt.Scale(scheme='viridis'), title="残存率"),
                tooltip=['campaign', '経過', '率']
            ).properties(height=400)
            st.altair_chart(heatmap, use_container_width=True)

        with col2:
            # 2. セグメント比較 (バブルチャート)
            st.write("💰 **予算配分 vs ROAS 効率分析**")
            bubble = alt.Chart(df).mark_circle().encode(
                x=alt.X('spend:Q', title="広告費 (Spend)"),
                y=alt.Y('roas:Q', title="ROAS (%)"),
                size=alt.Size('installs:Q', title="インストール数", scale=alt.Scale(range=[100, 2000])),
                color=alt.Color('status:N', scale=alt.Scale(domain=['✅ 正常 (Normal)', '⚠️ 警告 (Warning)', '🔥 危険 (Critical)'], range=['#10b981', '#fbbf24', '#f87171']), title="ステータス"),
                tooltip=['campaign', 'spend', 'roas', 'installs']
            ).properties(height=400).interactive()
            st.altair_chart(bubble, use_container_width=True)

        # D. 監査テーブル
        st.markdown("<h3 class='section-title'>📋 キャンペーン別詳細監査データ</h3>", unsafe_allow_html=True)
        st.dataframe(df.style.format({
            'spend': '${:,.0f}', 'revenue': '${:,.0f}', 
            'wandering_index': '{:.2f}', 'conv_efficiency': '{:.1f}%',
            'd1_retention': '{:.1%}', 'd7_retention': '{:.1%}', 'roas': '{:.1f}%'
        }), use_container_width=True)
        
        # ダウンロードセンター
        st.sidebar.markdown("---")
        st.sidebar.download_button(
            "📥 統合データをCSVで保存", 
            df.to_csv(index=False).encode('utf-8-sig'), 
            "growth_audit_jp_final.csv", 
            "text/csv",
            use_container_width=True
        )
    else:
        st.warning("👋 サイドバーから4つのCSVファイルをすべてアップロードしてください。分析を開始します。")

if __name__ == "__main__":
    main()
