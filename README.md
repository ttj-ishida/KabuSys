# KabuSys

KabuSys は日本株のデータプラットフォームと戦略実行基盤を統合した自動売買システムのライブラリです。J-Quants や RSS 等からデータを取得して DuckDB に格納し、特徴量作成、シグナル生成、発注監査までのワークフローをサポートします。

## 主な特徴
- データ取得（J-Quants）と差分 ETL（株価、財務、マーケットカレンダー）
- DuckDB ベースのスキーマ管理と冪等保存（ON CONFLICT 対応）
- 研究用ファクター計算（Momentum / Volatility / Value 等）
- クロスセクション Z スコア正規化ユーティリティ
- 戦略用特徴量作成（features テーブルへの UPSERT）とシグナル生成（signals テーブル）
- ニュース収集（RSS）と銘柄抽出・紐付け
- カレンダー管理（営業日判定 / next/prev trading day）
- 発注・約定・監査ログ用スキーマ（監査トレーサビリティを考慮）
- 設定は環境変数または `.env` で管理（自動読み込み機能あり）

## 依存 / 推奨環境
- Python 3.10+
- 必要なライブラリ（例）
  - duckdb
  - defusedxml
  - （標準ライブラリのみで実装されているモジュールも多いです）
- ネットワーク接続（J-Quants API、RSS フィード）

※ pyproject.toml / requirements.txt がある場合はそちらに従ってください。

## セットアップ

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境の作成・有効化（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール（例）
   ```bash
   pip install duckdb defusedxml
   # またはプロジェクトに合わせた requirements を使用
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（自動読み込みはデフォルトで有効）。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必須項目（例）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu API のパスワード（発注連携用）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — 通知用 Slack 設定
     - DUCKDB_PATH, SQLITE_PATH — DB ファイルパス（省略時は defaults）

   例 `.env`（実際の値を置き換えてください）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   KABU_API_PASSWORD=xxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化
   Python REPL やスクリプトから DuckDB を初期化します。
   ```python
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")  # ":memory:" でインメモリ DB 可
   ```

## 使い方（代表的なワークフロー）

- 日次 ETL（市場カレンダー・株価・財務の差分取得＋品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量作成（research モジュールで算出した raw factor を正規化し features テーブルへ）
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  count = build_features(conn, target_date=date(2025, 1, 31))
  print("upserted features:", count)
  ```

- シグナル生成（features / ai_scores / positions を参照して BUY/SELL を signals に書き込む）
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2025, 1, 31), threshold=0.6)
  print("signals generated:", total)
  ```

- ニュース収集（RSS から raw_news へ保存し、銘柄紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # known_codes は抽出時に使用する有効な銘柄コードのセット（省略可）
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  print(results)
  ```

- カレンダー更新ジョブ（夜間バッチ）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved calendar rows:", saved)
  ```

## 環境変数一覧（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（発注連携時必須）
- KABU_API_BASE_URL: kabu API ベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化（1 を設定）

設定はモジュール `kabusys.config.settings` からプロパティとして取得できます。

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数/設定の自動読み込み・検証
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（リトライ・レート制御・保存ロジック）
    - news_collector.py — RSS 取得 / 正規化 / DB 保存
    - schema.py — DuckDB スキーマ定義と init_schema/get_connection
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理（営業日判定・更新ジョブ）
    - stats.py — Z スコア正規化など統計ユーティリティ
    - features.py — zscore_normalize の再エクスポート
    - audit.py — 発注/約定の監査ログ定義（DDL）
  - research/
    - __init__.py
    - factor_research.py — Momentum/Volatility/Value などの計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — features テーブル作成（正規化・フィルタ）
    - signal_generator.py — final_score 計算と signals 生成
  - execution/ — （発注実行関連のプレースホルダ / 実装分離）
  - monitoring/ — （監視/メトリクス関連）

各モジュールは設計方針や注意点（ルックアヘッドバイアス回避、冪等性、トランザクション制御など）がドキュメントとして冒頭にまとめられています。

## 運用上の注意
- DuckDB のファイルはバックアップを推奨します。大規模データではファイルサイズが大きくなる場合があります。
- J-Quants API のレート制限（デフォルト 120 req/min）に注意してください。クライアント側でスロットリングを実装済みです。
- 実運用（live）への接続前に必ず paper_trading 環境で十分に検証してください。KABUSYS_ENV を "live" に設定すると実取引向けフラグが有効になる設計です。
- ニュース収集は外部 RSS に依存します。SSRF 対策や受信サイズ制限を実装していますが、ファイアウォールやプロキシ設定に注意してください。

---

README に載せきれない詳細な仕様（StrategyModel.md、DataPlatform.md、各設計ドキュメント）や API の利用条件はリポジトリ内の設計ドキュメントを参照してください。質問や具体的な実装・運用例が必要であれば、用途（ETL 実行、戦略開発、発注連携など）を教えてください。