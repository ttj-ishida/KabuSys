# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群です。データ収集（J-Quants）、DuckDB ベースのデータ格納・スキーマ、ファクター計算、特徴量作成、シグナル生成、ニュース収集、ETL パイプライン、および監査記録のためのユーティリティを提供します。

---

## プロジェクト概要

KabuSys は日本株の研究〜本番運用までを想定したモジュール群です。主な設計方針は以下です。

- データは DuckDB に永続化（Raw / Processed / Feature / Execution 層のスキーマを定義）
- J-Quants API を経由した株価・財務・カレンダーの差分取得（レート制御・リトライ・トークン自動リフレッシュ）
- research 層で計算した生ファクターを加工して strategy 用特徴量を構築
- 特徴量と AI スコアを統合して売買シグナルを生成（BUY / SELL）
- ニュース収集（RSS）と銘柄紐付け機能
- ETL / バッチジョブ用のヘルパー（差分更新・バックフィル・品質チェック）
- 監査テーブル群によるトレーサビリティ（signal → order → execution）

---

## 機能一覧

- データ層
  - DuckDB スキーマの初期化（init_schema）
  - raw_prices / raw_financials / market_calendar / features / signals など豊富なテーブル定義
- データ取得
  - J-Quants API クライアント（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - レート制御・リトライ・トークン自動リフレッシュを実装
- ETL
  - 日次 ETL パイプライン（run_daily_etl）— カレンダー・株価・財務の差分取得と品質チェック
  - 個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
- research / strategy
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 特徴量作成（build_features）: Z スコア正規化・ユニバースフィルタ・日付単位の冪等保存
  - シグナル生成（generate_signals）: final_score 計算、Bear レジーム抑制、BUY/SELL 書き込み
- ニュース収集
  - RSS フィード取得と前処理（fetch_rss）
  - raw_news の保存と銘柄抽出・紐付け（save_raw_news / extract_stock_codes / run_news_collection）
  - SSRF/サイズ/XML 攻撃対策を組み込み
- ユーティリティ
  - 統計ユーティリティ（zscore_normalize）
  - マーケットカレンダー管理（is_trading_day / next_trading_day / prev_trading_day / calendar_update_job）
  - 監査ログ用 DDL（signal_events / order_requests / executions など）

---

## 前提条件

- Python 3.10 以上（型アノテーションで | を使用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード）

実行環境に合わせて追加で以下やその他ライブラリが必要になる場合があります（ログ設定や Slack 通知等）。

---

## セットアップ手順

1. リポジトリをクローンし virtualenv を作成・有効化

   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール

   例（最低限）:

   ```bash
   pip install duckdb defusedxml
   ```

   プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください（例: pip install -e .）。

3. 環境変数を設定

   - .env ファイルをプロジェクトルートに置くと自動で読み込まれます（.env.local は .env の上書き）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須環境変数（Settings で参照）:

   - JQUANTS_REFRESH_TOKEN = <あなたの J-Quants リフレッシュトークン>
   - KABU_API_PASSWORD = <kabuステーション API パスワード>
   - SLACK_BOT_TOKEN = <Slack Bot Token>
   - SLACK_CHANNEL_ID = <Slack Channel ID>

   任意・デフォルトあり:

   - KABUSYS_ENV = development | paper_trading | live  (default: development)
   - LOG_LEVEL = DEBUG|INFO|WARNING|ERROR|CRITICAL (default: INFO)
   - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (default: data/kabusys.duckdb)
   - SQLITE_PATH (default: data/monitoring.db)

   サンプル .env:

   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡単な例）

以下は最小限の操作例です。実行前に環境変数を設定してください。

1. DuckDB スキーマ初期化

   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   ```

   これにより必要なテーブルが作成されます（冪等）。

2. 日次 ETL を実行（J-Quants からデータ取得 -> 保存 -> 品質チェック）

   ```python
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)
   print(result.to_dict())
   ```

3. 特徴量作成（build_features）

   ```python
   from datetime import date
   from kabusys.strategy import build_features

   count = build_features(conn, target_date=date.today())
   print(f"features upserted: {count}")
   ```

4. シグナル生成（generate_signals）

   ```python
   from kabusys.strategy import generate_signals
   from datetime import date

   total = generate_signals(conn, target_date=date.today())
   print(f"signals written: {total}")
   ```

5. ニュース収集ジョブの実行

   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import init_schema
   # known_codes は銘柄一覧（例: set(['7203','6758',...])）があれば紐付け可能
   res = run_news_collection(conn, known_codes=None)
   print(res)
   ```

6. カレンダー更新（夜間バッチ）

   ```python
   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn)
   print("saved calendar rows:", saved)
   ```

注意点:
- 各 API は冪等（既存行は上書きやスキップ）を考慮して実装されています。
- run_daily_etl 等は個々のステップ失敗時も他ステップを継続し、結果にエラー情報を返します。

---

## 環境変数一覧（要確認）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, デフォルトあり)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意)
- SQLITE_PATH (任意)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 (自動 .env 読み込みを無効化)

---

## ディレクトリ構成

リポジトリ内の主要なファイル／モジュールは次のとおりです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py       — RSS 収集・前処理・DB 保存
    - schema.py               — DuckDB スキーマ定義 / init_schema
    - stats.py                — zscore_normalize 等の統計ユーティリティ
    - pipeline.py             — ETL パイプライン / run_daily_etl 等
    - calendar_management.py  — カレンダー管理 / calendar_update_job 等
    - features.py             — public re-export (zscore_normalize)
    - audit.py                — 監査ログ用 DDL（signal_events 等）
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算（momentum/volatility/value）
    - feature_exploration.py  — IC / forward returns / summary
  - strategy/
    - __init__.py
    - feature_engineering.py  — build_features（正規化・ユニバースフィルタ等）
    - signal_generator.py     — generate_signals（最終スコア計算・BUY/SELL）
  - execution/                — 発注 / execution 層（雛形）
  - monitoring/               — 監視・メトリクス用（雛形）

各モジュールには docstring に設計方針や処理フローが詳細に記載されています。実装を追うことで運用フローを把握できます。

---

## 開発・貢献

- コードはモジュール単位でテスト可能な設計です（外部 API 呼び出しは引数で id_token を注入する等の工夫あり）。
- PR や issue は歓迎します。重要な設計変更はドキュメントと互換性に注意して行ってください。

---

## 参考 / 注意事項

- 本リポジトリは売買戦略の実行を支援するライブラリ群であり、取引に関わる最終的な判断や資金管理は運用者の責任です。
- 実際の資金を伴う運用（live 環境）を行う場合は、十分なテスト・リスク管理・監査ログ確認を行ってください。
- J-Quants API の利用には別途認証情報・利用規約の確認が必要です。

---

必要であれば、README にサンプルスクリプトや運用フロー図、CI 設定、より詳細な .env.example を追記できます。どの部分を拡充したいか教えてください。