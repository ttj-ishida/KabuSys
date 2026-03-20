# KabuSys

KabuSys は日本株のデータプラットフォームと自動売買戦略のためのライブラリ群です。  
DuckDB をデータ層に用い、J-Quants からの市場データ取得、ニュース収集、特徴量生成、シグナル生成、ETL パイプライン、マーケットカレンダー管理、監査ログなどを一貫して扱えるよう設計されています。

---

## 主な特徴（機能一覧）

- データ取得・保存
  - J-Quants API クライアント（株価日足 / 財務データ / 市場カレンダー）  
    - レート制限遵守、リトライ、トークン自動リフレッシュ
  - RSS ベースのニュース収集（XML デコーディング防御、SSRF 対策、URL 正規化）
  - DuckDB に対する冪等的保存（ON CONFLICT / トランザクション利用）

- データ基盤（DuckDB スキーマ）
  - Raw / Processed / Feature / Execution 層に分かれたスキーマ定義
  - prices_daily, raw_prices, raw_financials, features, ai_scores, signals, orders, executions, positions, news_tables など多数のテーブル

- ETL パイプライン
  - 差分取得・バックフィル・品質チェックを含む日次 ETL（run_daily_etl）
  - 市場カレンダー先読み・更新ジョブ（calendar_update_job）

- 研究 / 戦略用ユーティリティ
  - ファクター計算（momentum / volatility / value）
  - 特徴量生成（Zスコア正規化、ユニバースフィルタ適用、features テーブルへの UPSERT）
  - シグナル生成（複数コンポーネントの重み付け合算、Bear レジーム抑制、BUY/SELL の判定と signals テーブルへの保存）
  - 研究用の指標（将来リターン計算、IC（Spearman）計算、ファクターサマリ）

- ニュース & テキスト処理
  - RSS 取得・解析・記事ID生成（URL 正規化 + SHA256）
  - 記事中からの銘柄コード抽出と news_symbols への紐付け

- 監査トレーサビリティ（audit）
  - signal → order_request → executions の一貫した監査ログ設計（トランザクション監査用テーブル）

---

## 必要条件 / 前提

- Python 3.10 以上（PEP 604 の | 型注釈などを使用）
- 必要となる主な Python パッケージ（最低限）
  - duckdb
  - defusedxml

（プロジェクトによっては追加の依存がある可能性があります。パッケージ化された要件ファイルがある場合はそちらを参照してください。）

---

## セットアップ手順

1. リポジトリをクローン（またはソースを取得）
   - git clone ...

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール
   - pip install duckdb defusedxml

   （プロジェクトに pyproject.toml / requirements.txt がある場合はそれに従ってください）
   - pip install -e .  （パッケージ化されている場合）

4. 環境変数の準備（.env）
   - プロジェクトルートに `.env` / `.env.local` を置くことで自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能）。
   - 必須の環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 例 (.env.example のイメージ):
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. DuckDB スキーマの初期化
   - Python REPL またはスクリプトで初期化:
     ```
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)
     ```
   - `":memory:"` を渡せばインメモリ DB になります（テスト用途）。

---

## 使い方（代表的な例）

下記は簡単な呼び出し例です。各関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。

- 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  ```
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量の構築（features テーブルへの保存）
  ```
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.strategy import build_features
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  n = build_features(conn, target_date=date.today())
  print("features upserted:", n)
  ```

- シグナル生成（signals テーブルへ保存）
  ```
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.strategy import generate_signals
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  total_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print("signals written:", total_signals)
  ```

- ニュース収集ジョブ（RSS から raw_news, news_symbols を作成）
  ```
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  # known_codes は銘柄コードの集合（抽出フィルタ）
  known_codes = {"7203", "6758", "9984", ...}
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: saved_count, ...}
  ```

- カレンダー更新（夜間バッチ）
  ```
  from kabusys.data.schema import init_schema
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  saved = calendar_update_job(conn)
  print("market_calendar saved:", saved)
  ```

- 設定の参照
  ```
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

注意点:
- ルックアヘッドバイアス回避のため、各計算は target_date 時点までのデータのみを参照する設計になっています。
- 各 DB 書き込みは日付単位で DELETE→INSERT（トランザクション）を行い、冪等性を確保しています。

---

## ディレクトリ構成（主要ファイル）

（ソースツリーは `src/kabusys` をルートパッケージと想定）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得 + 保存ユーティリティ）
    - news_collector.py          — RSS 取得・前処理・DB 保存
    - schema.py                  — DuckDB スキーマ定義 & init_schema / get_connection
    - stats.py                   — Zスコア正規化など統計ユーティリティ
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py     — market_calendar 管理・判定ロジック
    - audit.py                   — 監査ログ用スキーマ / 初期化（signal_events, order_requests, executions）
    - features.py                — data.stats の再エクスポート
    - (その他: quality モジュール等が存在する想定)
  - research/
    - __init__.py
    - factor_research.py         — momentum / volatility / value の計算
    - feature_exploration.py     — 将来リターン / IC / 統計サマリ等
  - strategy/
    - __init__.py
    - feature_engineering.py     — 生ファクターのマージ・ユニバースフィルタ・正規化・features 保存
    - signal_generator.py        — final_score 計算と BUY/SELL シグナル生成（signals 保存）
  - execution/
    - __init__.py                — 実行（ブローカー連携）層のプレースホルダ（実装は別途）
  - monitoring/                  — パッケージインターフェースに含まれる（実装がある場合）

（上記はコード断片から抽出した主要モジュール一覧です。実際のリポジトリはさらにファイルやドキュメントが存在する可能性があります。）

---

## 実運用上の注意／ベストプラクティス

- 機密情報（API トークンやパスワード）は .env / 環境変数で管理し、ソース管理にコミットしないでください。
- DuckDB ファイル（デフォルト: data/kabusys.duckdb）は定期バックアップを推奨します。
- J-Quants のレート制限や API 仕様変更に注意してください。jquants_client は基本的なリトライ・レート制御を行いますが、運用時はモニタリングが必要です。
- テストでは settings の自動 .env ロードを無効化するために KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用できます。
- Execution（発注）層はブローカー API 固有の実装が必要です。実運用前に冗長性・安全機構（冗長チェック、二重送信防止、監査ログ）を十分に確認してください。

---

## さらに読む（コード内ドキュメント）

各モジュール内に詳細な docstring と設計コメントが含まれています。実装の詳細やアルゴリズム仕様（例: StrategyModel.md / DataPlatform.md / DataSchema.md 参照箇所）はコードコメントから参照してください。

---

ご希望があれば、以下の追加ドキュメントを作成します：
- .env.example テンプレートファイル
- 具体的な運用手順（cron / バッチ化、監視アラート設定）
- execution 層の実装例（kabu ステーション連携）
- テストケースや CI 設定例

必要なものを教えてください。