# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買システム用ライブラリです。データ収集（J‑Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを含むデータ・戦略基盤を提供します。設計においてはルックアヘッドバイアス回避、冪等性、API レート制御、堅牢なエラー処理・トランザクション管理を重視しています。

---

## 主な機能

- データ取得（J‑Quants API クライアント）
  - 株価日足、財務データ、マーケットカレンダーのページネーション対応取得
  - レート制御、リトライ、トークン自動リフレッシュ
- DuckDB スキーマ定義・初期化（冪等）
  - Raw / Processed / Feature / Execution 層のテーブル群
- ETL パイプライン
  - 差分取得・バックフィル機能、品質チェックフック
  - 日次一括 ETL エントリーポイント
- 特徴量計算（research）
  - Momentum / Volatility / Value の定量ファクター計算
  - クロスセクション Z スコア正規化ユーティリティ
- 特徴量合成とシグナル生成（strategy）
  - features と ai_scores を統合して final_score を計算
  - BUY/SELL シグナルの生成（Bear レジーム抑制、ストップロス判定など）
- ニュース収集（RSS）
  - RSS の安全取得（SSRF 対策、gzip サイズチェック、XML の安全パース）
  - 記事の正規化、ID 生成（URL 正規化 → SHA256）、DB 保存、銘柄抽出
- マーケットカレンダー管理（営業日判定、next/prev/get_trading_days）
- 監査ログ（signal → order → execution のトレーサビリティ）

---

## セットアップ手順

以下は推奨セットアップ手順の一例です。環境に応じて調整してください。

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（project が公開されている場合は pip install -e . など）
   - 本リポジトリでは明示的な requirements.txt は含まれていませんが、主要な依存は少なくとも以下を想定しています。
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

4. 環境変数（.env）の準備
   - プロジェクトルートに `.env`（および必要に応じ `.env.local`）を置くと自動で読み込まれます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数（このコードベースで参照される主なもの）:
     - JQUANTS_REFRESH_TOKEN — J‑Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
   - 任意 / デフォルトあり:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）

   - サンプル（.env.example）
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     KABU_API_PASSWORD=your_kabu_password_here
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     ```

5. データベース初期化
   - DuckDB スキーマを作成して接続を得ます（スクリプトや REPL から実行）。
   - 例:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - ":memory:" を渡すとインメモリで初期化できます（テスト用）。

---

## 使い方（代表的な API）

以下は主要機能を呼び出す最小の使用例です。詳細は各モジュールの docstring を参照してください。

- DuckDB の初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェックを順に実行）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # 引数で target_date などを指定可能
  print(result.to_dict())
  ```

- 特徴量構築（features テーブルへの書き込み）
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  n = build_features(conn, date(2024, 1, 31))
  print(f"features upserted: {n}")
  ```

- シグナル生成（signals テーブルへの書き込み）
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, date(2024, 1, 31))
  print(f"signals written: {total}")
  ```

- ニュース収集ジョブ（RSS ソースから記事収集→保存→銘柄紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- マーケットカレンダー更新ジョブ（夜間バッチ）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

- 設定参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

- J‑Quants の ID トークン取得（必要時）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用
  ```

注意点:
- 多くの関数は DuckDB コネクション（duckdb.DuckDBPyConnection）を引数に取ります。`init_schema` で返される connection を使うか、`get_connection` で接続を取得してください。
- ETL や API 呼び出しはネットワークや API レートに依存します。ログとリトライ挙動を確認して運用してください。

---

## 環境変数（要点）

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を探索）から行われます。自動ロードを無効にするには:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- 主要な設定（Settings クラスによって公開されます）
  - jquants_refresh_token (JQUANTS_REFRESH_TOKEN) — 必須
  - kabu_api_password (KABU_API_PASSWORD) — 必須
  - kabu_api_base_url (KABU_API_BASE_URL) — デフォルト: http://localhost:18080/kabusapi
  - slack_bot_token (SLACK_BOT_TOKEN) — 必須
  - slack_channel_id (SLACK_CHANNEL_ID) — 必須
  - duckdb_path (DUCKDB_PATH) — デフォルト: data/kabusys.duckdb
  - sqlite_path (SQLITE_PATH) — デフォルト: data/monitoring.db
  - env (KABUSYS_ENV) — development / paper_trading / live
  - log_level (LOG_LEVEL) — DEBUG/INFO/WARNING/ERROR/CRITICAL

---

## ディレクトリ構成

主要ファイル・モジュールの構成は下記の通りです（src/kabusys/ 配下の抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                          — 環境設定のロード / Settings
  - data/
    - __init__.py
    - jquants_client.py                 — J‑Quants API クライアント（取得・保存）
    - news_collector.py                 — RSS ベースのニュース収集
    - schema.py                         — DuckDB スキーマ定義・初期化
    - stats.py                          — 統計ユーティリティ (zscore_normalize)
    - pipeline.py                       — ETL パイプライン（run_daily_etl など）
    - features.py                       — features の再エクスポート
    - calendar_management.py            — カレンダージョブ & 営業日ユーティリティ
    - audit.py                          — 監査ログ用スキーマ DDL（signal/order/execution）
    - execution/                        — 発注関連（空 __init__ が存在）
  - research/
    - __init__.py
    - factor_research.py                — Momentum/Volatility/Value の計算
    - feature_exploration.py            — IC/forward returns/summary utilities
  - strategy/
    - __init__.py
    - feature_engineering.py            — features の作成（build_features）
    - signal_generator.py               — シグナル生成（generate_signals）
  - monitoring/                         — 監視系（DB/監査/Slack 連携等想定、ファイルは省略可能）
  - execution/                          — 発注実行層の実装が入る想定（今は空 __init__）

（上記はコードベース内の docstring やモジュール名から抜粋した主要箇所です。細かいファイルはリポジトリを参照してください。）

---

## 運用上の注意 / 設計上の留意点

- ルックアヘッドバイアス対策: 多くの処理は target_date 時点で利用可能なデータのみを使うよう設計されています（取得時刻のトレースも行っています）。
- 冪等性: データ保存（DuckDB への INSERT）は ON CONFLICT 系句やトランザクションで冪等性を確保しています。
- API レート管理: J‑Quants クライアントは最小間隔スロットリングとリトライ（指数バックオフ）を行います。
- セキュリティ: RSS 収集は SSRF 対策や defusedxml による XML 安全パースを行っています。
- 環境分離: KABUSYS_ENV により開発 / ペーパートレード / 本番を切替。is_live / is_paper / is_dev で判定できます。
- ストップロスやトレーリングストップ等の取引ルールは一部未実装箇所があります。運用前に仕様を確認してください（docstring に未実装箇所の注記あり）。

---

## 開発者向け / 参考

- 各モジュールは docstring に処理フロー・設計方針が詳述されています。実装や拡張時はまず docstring を確認してください。
- テストやローカル実行時に自動 .env 読み込みを無効化したい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DuckDB を用いたローカル実行は高速で簡便です。大きなバックフィル・バッチ実行ではファイル DB を使用してください（デフォルト: data/kabusys.duckdb）。

---

README の内容や利用例をプロジェクト実装・運用ポリシーに合わせてカスタマイズしたい場合は、どの項目を追加／修正したいか教えてください。