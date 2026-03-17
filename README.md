# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ取得・ETL、ニュース収集、マーケットカレンダー管理、データ品質チェック、監査ログなどの基盤機能を提供します。

---

## 概要

KabuSys は以下の目的で設計された Python パッケージです。

- J-Quants API から株価・財務・市場カレンダーを取得し DuckDB に保存する ETL パイプライン
- RSS からニュースを収集して記事と銘柄の紐付けを行うニュース収集モジュール
- 市場カレンダー（JPX）の管理と営業日判定ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注・約定・監査用のスキーマ/初期化機能（監査ログ）

設計上のポイント：
- API レート制御、リトライ、トークン自動更新を備えた堅牢な API クライアント
- DuckDB への冪等保存（ON CONFLICT / DO UPDATE / DO NOTHING）による再実行安全性
- SSRF/ZIP爆弾等を考慮したニュース取得のセキュリティ対策
- 日次 ETL の差分更新・バックフィル機能と品質チェック

---

## 主な機能一覧

- データ取得（src/kabusys/data/jquants_client.py）
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダー取得
  - レート制御（120 req/min）、指数バックオフ、401 時のトークン自動リフレッシュ
  - DuckDB への冪等保存関数（raw_prices / raw_financials / market_calendar）

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - run_daily_etl: 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分取得・バックフィル・品質チェック（quality モジュール）を統合

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード取得、URL 正規化・トラッキング除去、記事 ID の SHA-256 ハッシュ化
  - SSRF 回避、レスポンスサイズ制限、gzip 対応、DuckDB へのバルク挿入（RETURNING 使用）
  - 記事と銘柄コードの紐付け機能

- マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - 夜間バッチ更新ジョブ（calendar_update_job）

- データ品質チェック（src/kabusys/data/quality.py）
  - 欠損、スパイク（前日比閾値）、重複、日付不整合の検出
  - QualityIssue オブジェクトで詳細を返す

- スキーマ定義（src/kabusys/data/schema.py）
  - DuckDB の Raw / Processed / Feature / Execution 層のテーブルとインデックス定義
  - init_schema() / get_connection() による初期化・接続取得

- 監査ログ（src/kabusys/data/audit.py）
  - signal_events / order_requests / executions の監査テーブル定義と初期化
  - init_audit_schema / init_audit_db

- 設定管理（src/kabusys/config.py）
  - .env 自動読み込み（プロジェクトルートを自動検出）／環境変数から設定取得
  - 必須設定の取得ヘルパー、環境（development/paper_trading/live）判定

---

## 要求環境

- Python 3.10 以上（コード内での型注釈に | 形式を使用）
- 主な依存パッケージ（開発環境で pip install してください）:
  - duckdb
  - defusedxml
- 標準ライブラリ: urllib, json, logging, datetime 等

（依存をまとめた pyproject.toml / requirements.txt がある場合はそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローン（例）
   git clone <repo_url>
   cd <repo>

2. 仮想環境を作成・有効化（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   pip install duckdb defusedxml

   （プロジェクトに pyproject.toml / requirements.txt がある場合はそちらを使用）

4. 環境変数の設定
   - プロジェクトルートに .env を置くか OS 環境変数を利用します。
   - 自動読み込みはデフォルトで有効。自動読み込みを無効化するには:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB スキーマ初期化（例）
   Python REPL またはスクリプト内で:
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")

---

## 必須 / 推奨環境変数

主に src/kabusys/config.py を参照します。最低限以下を設定してください:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID — 通知先 Slack チャンネル ID

オプション（デフォルトあり）:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — デフォルトの DuckDB パス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

.env の書式は typical な KEY=VALUE 形式で、export にも対応します（詳しくは config.py 内の実装を参照）。

---

## 使い方（例）

- DuckDB スキーマを初期化
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")

- 日次 ETL を実行する（シンプルな例）
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")  # 既に init_schema 済みと仮定
  result = run_daily_etl(conn)
  print(result.to_dict())

- ニュース収集ジョブを実行する
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 実運用では銘柄一覧を用意
  stats = run_news_collection(conn, known_codes=known_codes)
  print(stats)

- カレンダー夜間更新ジョブ
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"saved: {saved}")

- 監査スキーマを追加する
  from kabusys.data.audit import init_audit_schema
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")
  init_audit_schema(conn)

注意点:
- 実行時は settings（環境変数）が正しく設定されている必要があります。
- J-Quants API 利用はレート制限・認証要件に注意してください。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 にして環境依存を切ると便利です。

---

## ディレクトリ構成（概要）

src/kabusys/
- __init__.py — パッケージ定義（__version__ 等）
- config.py — 環境変数・設定の自動読み込みと Settings クラス

src/kabusys/data/
- __init__.py
- jquants_client.py — J-Quants API クライアント（取得/保存/認証/リトライ/レート制御）
- news_collector.py — RSS 収集・前処理・DB 保存・銘柄抽出
- pipeline.py — ETL パイプライン（run_daily_etl 等）
- schema.py — DuckDB スキーマ定義と初期化（init_schema / get_connection）
- calendar_management.py — カレンダー管理（営業日判定、update job）
- audit.py — 監査ログ用スキーマ初期化
- quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）

src/kabusys/strategy/
- __init__.py — 戦略関連のエントリ（実装ファイルはここに追加）

src/kabusys/execution/
- __init__.py — 発注・ブローカー連携の実装を配置

src/kabusys/monitoring/
- __init__.py — 監視・メトリクス関連の実装を配置

---

## 開発・テストのヒント

- 自動 .env ロードは config.py によりプロジェクトルート（.git または pyproject.toml）から行われます。テスト時に自動ロードを無効にしたい場合:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- news_collector の _urlopen はテストでモック可能（安全な外部依存を取り除けます）。

- DuckDB の :memory: を使えばインメモリ DB で高速に単体テストが実行できます：
  conn = schema.init_schema(":memory:")

---

## 参考・補足

- スキーマや ETL の詳細は各モジュールの docstring に設計方針や注意点が記載されています。実装や拡張を行う際はまず該当ファイルを参照してください。
- 実運用では SLACK 連携、kabuステーション API（発注）等の外部依存を安全に扱うための追加設定・テストが必要です。

---

必要であれば README に以下も追記できます：
- 依存関係の正確な一覧（requirements.txt）
- CI 用の実行手順例（GitHub Actions）
- よくあるトラブルシューティング（API トークンの更新方法など）

要望があれば追記します。