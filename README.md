# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
DuckDB をデータ層に用い、J-Quants 等から市況・財務・ニュースを取得して ETL → 特徴量作成 → シグナル生成 → 発注（execution 層）へと繋ぐことを想定したモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアス対策（target_date 時点のデータのみを使用）
- 冪等性（DB 保存は ON CONFLICT / トランザクションで安全に）
- ネットワーク操作に対する堅牢なハンドリング（リトライ、レート制御、SSRF 対策 等）
- Research / Data / Strategy / Execution の分離

---

## 機能一覧

- 環境設定管理
  - .env もしくは OS 環境変数から設定読込（自動ロード機能付き）
- Data 層
  - J-Quants API クライアント（株価・財務・マーケットカレンダー）
    - レートリミット・リトライ・トークン自動リフレッシュ対応
  - RSS ニュース収集（SSRF 対策・トラッキング除去・記事ID冪等性）
  - DuckDB スキーマ定義・初期化（raw / processed / feature / execution 層）
  - ETL パイプライン（差分取得・バックフィル・品質チェック呼び出し）
  - マーケットカレンダー管理（営業日判定、next/prev/trading_days 等）
  - 統計ユーティリティ（Zスコア正規化等）
- Research 層
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 将来リターン計算 / IC（Spearman） / 統計サマリー
- Strategy 層
  - 特徴量生成（research 結果の正規化・ユニバースフィルタ適用 → features テーブルに保存）
  - シグナル生成（features / ai_scores / positions を統合 → BUY/SELL を signals テーブルへ）
- Execution / Audit（テーブル定義を含む）
  - 発注・約定・ポジション・監査ログのスキーマ

---

## 必要条件（動作環境）

- Python 3.10+
- 主要依存例（プロジェクトの packaging に従って適宜インストールしてください）:
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API、RSS フィード など）

---

## 環境変数（主なもの）

このパッケージは .env ファイルまたは OS 環境変数から設定を読み込みます。自動ロードはプロジェクトルート（.git または pyproject.toml）を探索して行われます。無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — development / paper_trading / live（default: development）
- LOG_LEVEL — DEBUG/INFO/...
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）

.env の読み込み順序: OS 環境 > .env.local > .env

---

## セットアップ手順（例）

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （必要に応じて他のパッケージを追加）

3. 環境変数を設定
   - プロジェクトルートに `.env` を作成し必要なキーを設定するか、OS 環境変数で設定する。
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=yyyy
     SLACK_BOT_TOKEN=zzzz
     SLACK_CHANNEL_ID=C0123456789

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - init_schema は必要なディレクトリを作成し、全テーブル・インデックスを作成します（冪等）。

---

## 使い方（基本的な利用例）

以下は簡単な Python コマンド例です。環境変数が正しく設定されている前提です。

- データベース初期化
  python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

- 日次 ETL を実行（市場カレンダー → 株価 → 財務 → 品質チェック）
  python -c "from kabusys.data.schema import init_schema; from kabusys.data.pipeline import run_daily_etl; conn = init_schema('data/kabusys.duckdb'); res = run_daily_etl(conn); print(res.to_dict())"

- 特徴量のビルド（特定日）
  python -c "import datetime; from kabusys.data.schema import init_schema; from kabusys.strategy import build_features; conn = init_schema('data/kabusys.duckdb'); print(build_features(conn, datetime.date(2024,3,1)))"

- シグナル生成（特定日）
  python -c "import datetime; from kabusys.data.schema import init_schema; from kabusys.strategy import generate_signals; conn = init_schema('data/kabusys.duckdb'); print(generate_signals(conn, datetime.date.today()))"

- ニュース収集ジョブ（RSS の既定ソースを使用）
  python -c "from kabusys.data.schema import init_schema; from kabusys.data.news_collector import run_news_collection; conn = init_schema('data/kabusys.duckdb'); print(run_news_collection(conn))"

- カレンダー更新ジョブ（先読み）
  python -c "from kabusys.data.schema import init_schema; from kabusys.data.calendar_management import calendar_update_job; conn = init_schema('data/kabusys.duckdb'); print(calendar_update_job(conn))"

注意:
- 上記サンプルは簡易例です。本番的な運用ではログ設定、例外処理、ジョブスケジューラ（cron / Airflow / Task runner 等）との統合を推奨します。
- J-Quants API 呼び出しはレート制限・リトライ等を行いますが、運用環境のトークンやネットワークポリシーに応じて監視してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール構成（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py            — J-Quants API クライアント（取得・保存）
      - news_collector.py            — RSS 収集・保存・銘柄紐付け
      - schema.py                    — DuckDB スキーマ定義・初期化
      - pipeline.py                  — ETL パイプライン（差分取得・品質チェック）
      - stats.py                     — 統計ユーティリティ（zscore 等）
      - calendar_management.py       — マーケットカレンダー管理
      - audit.py                     — 監査 / 発注トレーサビリティ DDL（部分）
      - features.py                  — data.stats の公開ラッパ
    - research/
      - __init__.py
      - factor_research.py           — モメンタム/ボラティリティ/バリュー計算
      - feature_exploration.py       — 将来リターン / IC / サマリー
    - strategy/
      - __init__.py
      - feature_engineering.py       — features テーブル構築（正規化・ユニバース）
      - signal_generator.py          — final_score 計算・BUY/SELL 生成
    - execution/                      — 発注 / execution 層（パッケージ有り）
    - monitoring/                     — 監視用モジュール（存在する場合）

各モジュールは docstring とロジック内コメントで設計仕様（StrategyModel.md / DataPlatform.md 等）に基づく実装方針が示されています。

---

## ロギングとデバッグ

- settings.log_level（LOG_LEVEL 環境変数）でログレベルを制御します（デフォルト: INFO）。
- 各モジュールは logger を使って詳細ログ / 警告 / エラーハンドリングを行います。デバッグ実行時は LOG_LEVEL=DEBUG を推奨します。

---

## 開発上の注意点

- Python 型注釈（| など）を使用しているため Python 3.10 以上を想定しています。
- DuckDB はバージョン差で SQL 構文の互換性や制約のサポート状況が変わる場合があるため、使用する DuckDB バージョンと互換性を確認してください（FK / ON DELETE 等の制約は一部注記あり）。
- .env の自動読み込みはプロジェクトルート探索に基づくため、パッケージ配布後の挙動やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して制御できます。

---

## 今後の拡張案（参考）

- execution 層と実際の証券会社 API の接続ラッパー実装（約定ハンドリング、再試行ポリシー）
- AI スコア生成パイプラインの追加（ai_scores テーブルを計算して統合）
- Web UI / ダッシュボードによる監視・アラート
- CI / テストスイートの整備（ユニットテスト・統合テスト用のモック）

---

問い合わせやコントリビュートを行う際は、まずモジュール内 docstring とログを参照してください。本 README は実装の概要を示すもので、詳細は各ソースの docstring（関数・クラスコメント）を参照してください。