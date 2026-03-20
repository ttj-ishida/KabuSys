# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
J-Quants API や RSS ニュース、DuckDB を使ってデータ取得・整形・特徴量生成・シグナル生成を行い、発注・監査までのワークフローを想定したモジュール群を提供します。

主な設計方針：
- DuckDB をローカルに保持してデータを層（Raw / Processed / Feature / Execution）で管理
- ルックアヘッドバイアス対策（計算は target_date 時点のデータのみ）
- 冪等性（DB への保存は ON CONFLICT 等で上書き・スキップ）
- 外部 API 呼び出しはデータ層（jquants_client）に集約
- テスト容易性を考慮した設計（ID トークン注入や自動.envロード無効化など）

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env / .env.local を自動ロード（必要に応じて無効化可能）
  - 必須環境変数を Settings 経由で一元参照
- Data（kabusys.data）
  - J-Quants API クライアント（認証・ページネーション・レート制御・リトライ）
  - DuckDB スキーマ定義と初期化（init_schema）
  - ETL パイプライン（差分取得・バックフィル・品質チェック） run_daily_etl / run_*_etl
  - RSS ベースのニュース収集・テキスト前処理・記事保存（SSRF 対策・サイズ制限・トラッキング除去）
  - 市場カレンダー管理（営業日判定・次/前営業日・一括更新ジョブ）
  - 統計ユーティリティ（Zスコア正規化 等）
- Research（kabusys.research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算・IC（Information Coefficient）計算・ファクター統計
- Strategy（kabusys.strategy）
  - 特徴量作成（build_features: raw factor の統合・ユニバースフィルタ・Zスコア正規化・features テーブルへの保存）
  - シグナル生成（generate_signals: features+ai_scores から final_score を計算し BUY/SELL を signals テーブルへ保存）
- Execution / Audit（構造あり）
  - signals / signal_queue / orders / trades / positions / audit テーブル定義（監査ログ・トレーサビリティ）

---

## 前提（依存ライブラリ）

最低限必要な Python パッケージ（プロジェクトの setup によるが、主要依存）:
- duckdb
- defusedxml

インストール例（ローカル開発環境）:
pip install duckdb defusedxml

パッケージとしてプロジェクトをインストールする方法がある場合はそれに従ってください（例: pip install -e . / poetry install）。

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置

2. 必要パッケージをインストール
   - 例:
     pip install duckdb defusedxml

3. 環境変数を設定
   - .env または環境変数で以下を設定してください（必須項目は Settings にて参照され、未設定時に ValueError が発生します）:

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必要な場合）
- SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID: Slack 通知対象チャネル ID

任意 / デフォルトあり:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / ...（デフォルト: INFO）
- DUCKDB_PATH: DuckDB データベースファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

例 .env:
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
LOG_LEVEL=INFO

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから init_schema を呼ぶ：
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

   - :memory: を渡すとインメモリ DB を使用します（テスト用）:
     conn = init_schema(":memory:")

---

## 使い方（主要なワークフロー例）

以下は代表的な操作の例です。実行は Python スクリプトから行います。

1) DB 初期化（1回）
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")

2) 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）
from datetime import date
from kabusys.data.pipeline import run_daily_etl
res = run_daily_etl(conn, target_date=date.today())
print(res.to_dict())

3) 特徴量作成（build_features）
from datetime import date
from kabusys.strategy import build_features
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")

4) シグナル生成（generate_signals）
from kabusys.strategy import generate_signals
total = generate_signals(conn, target_date=date.today(), threshold=0.60)
print(f"signals generated: {total}")

5) ニュース収集ジョブ（RSS から raw_news・news_symbols 保存）
from kabusys.data.news_collector import run_news_collection
# known_codes はテキスト中の4桁銘柄コード抽出に利用
known_codes = {"7203", "6758", "9984", ...}
results = run_news_collection(conn, known_codes=known_codes)
print(results)

6) カレンダー更新ジョブ（夜間バッチ）
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")

補足:
- run_daily_etl は内部で calendar を先に取得し、営業日調整（非営業日は直近営業日に調整）を行います。
- build_features / generate_signals は DuckDB のテーブル（prices_daily, raw_financials, features, ai_scores, positions 等）に依存します。ETL 実行と整合させてください。

---

## 環境変数の自動読み込みについて

- パッケージはプロジェクトルート（.git または pyproject.toml が存在する親ディレクトリ）を探索して .env / .env.local を自動で読み込みます。
- 読み込み順:
  1. OS 環境変数（最優先）
  2. .env（存在すれば未設定のキーをセット）
  3. .env.local（上書き、ただし OS 環境変数は保護）
- テストや特殊環境で自動読み込みを無効化したい場合:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主要ファイル）

プロジェクト内の主要なモジュール・ファイルを抜粋しています。

src/kabusys/
- __init__.py
- config.py                             # 環境設定管理
- data/
  - __init__.py
  - jquants_client.py                   # J-Quants API クライアント（取得・保存）
  - news_collector.py                   # RSS ニュース収集・保存
  - schema.py                           # DuckDB スキーマ定義・初期化
  - stats.py                            # 統計ユーティリティ（zscore_normalize）
  - pipeline.py                         # ETL パイプライン run_daily_etl 等
  - calendar_management.py              # カレンダー管理 / 更新ジョブ
  - features.py                         # 再エクスポート（zscore_normalize）
  - audit.py                             # 監査ログ関連 DDL（途中まで）
- research/
  - __init__.py
  - feature_exploration.py               # 将来リターン, IC, summary 等
  - factor_research.py                    # mom/vol/value のファクター計算
- strategy/
  - __init__.py
  - feature_engineering.py               # build_features（raw factor -> features）
  - signal_generator.py                  # generate_signals（final_score 計算）
- execution/                              # 発注/実行層（パッケージ構成あり）
- monitoring/                             # 監視・メトリクス（ディレクトリ用意）

ドキュメント参照: DataPlatform.md, StrategyModel.md, Research/* など（ソース内コメントで仕様を参照可能）。

---

## 開発・運用上の注意

- DuckDB のファイル（デフォルト data/kabusys.duckdb）はプロダクションで大きくなります。バックアップやディスク管理に注意してください。
- J-Quants の API レート制限（120 req/min）や認証ロジックを実装済みですが、運用時は API 利用規約・課金にご注意ください。
- ニュース取得は外部 URL を開くため SSRF 対策やサイズ制限を実装していますが、追加のネットワークポリシーで保護することを推奨します。
- generate_signals はデフォルトで Bear レジーム検知時に BUY を抑制するロジックを含みます。運用ルールはパラメータで調整可能です。
- 自動発注層（実際の送信）を実装する場合は、order_requests / audit テーブルを用いた冪等性確保・監査を行ってください。

---

## テスト・デバッグ

- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効にすると環境に依存しないテストが書きやすくなります。
- DuckDB の :memory: モードを使えばテスト用 DB を簡単に生成できます。
  conn = init_schema(":memory:")

---

この README はソースコード内のドキュメント文字列・コメントに基づいて作成しています。詳細な仕様（StrategyModel.md / DataPlatform.md 等）や追加の運用手順はリポジトリ内の設計ドキュメントを参照してください。