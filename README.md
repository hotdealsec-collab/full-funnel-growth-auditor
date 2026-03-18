# 🚀 フルファネル・成長監査システム (Full-Funnel Growth Auditor)

このプロジェクトは、**Adjust** (広告費)、**社内Admin** (売上/残存)、**GA4** (行動ログ/画面遷移) の異なる4つのデータソースを統合し、キャンペーンごとの「ユーザーの迷い」と「成長のボトルネック」を特定するためのAI監査ツールです。



## 🛠️ 主な機能

- **4-Way データ統合**: 異なるフォーマットの4つのCSVファイルを「campaign」を基準に自動結合。
- **GA4 データクレンジング**: GA4特有のヘッダー（上部9行）の自動スキップおよび日本語カラム名の正規化。
- **AI 戦略プレイブック**: 統合データに基づき、AIが即座に実行可能なマーケティング施策を提案。
- **高度な分析指標**:
    - **迷い指数 (Wandering Index)**: 詳細ページ内での回遊停滞を数値化。
    - **転換効率 (Conv. Efficiency)**: 詳細からコンテンツ閲覧への遷移効率を算出。
- **インタラクティブな可視化**: リテンション・コホート分析、予算配分 vs ROAS 効率分析などのチャートを提供。

## 📊 必要な入力データ (CSV)

監査を開始するには、以下の4つのファイルが必要です。

1. **Adjust**: 広告費、インストール数、OS情報（campaign, spend, installs, os）
2. **Internal Admin**: 売上、リテンション情報（campaign, revenue, d1_retention, d7_retention）
3. **GA4 Event**: 行動ログ。`セッションのキャンペーン`, `イベント名`, `イベント数` を含む（上部9行は自動スキップ）。
4. **GA4 Screen**: 画面遷移ログ。`ページパスとスクリーン クラス`, `表示回数` を含む（上部9行は自動スキップ）。

## 🚀 セットアップ方法

### 1. リポジトリのクローン
```bash
git clone [https://github.com/your-username/full-funnel-growth-auditor.git](https://github.com/your-username/full-funnel-growth-auditor.git)
cd full-funnel-growth-auditor
