# KabuSys

バージョン: 0.1.0

日本株向けの自動売買プラットフォーム向けライブラリ。データ取得（J-Quants）、ETLパイプライン、データ品質チェック、ニュース収集、DuckDBスキーマ定義、監査ログ（発注→約定のトレーサビリティ）など、システム基盤の主要コンポーネントを提供します。

主な対象: 日本株のデータ収集・加工・監査ログを行うバックエンド処理（戦略・発注エンジンとは分離されたデータ/運用層）。

---

## 機能一覧

- J-Quants API クライアント
  - 株価日足（OHLCV）/財務情報/マーケットカレンダーの取得
  - レート制限（120 req/min）遵守、再試行（指数バックオフ）、401 に対するトークン自動リフレッシュ
  - 取得時刻（fetched_at）を記録して look-ahead bias を抑制

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス作成、冪等な初期化関数（init_schema）

- ETL パイプライン
  - 差分更新（最終取得日からの差分）とバックフィル（後出し修正吸収）
  - 市場カレンダー先読み、株価・財務の一括取得と保存
  - 品質チェック（欠損、重複、スパイク、日付不整合）

- ニュース収集（RSS）
  - RSS 取得・前処理（URL除去、空白正規化）
  - 記事ID は正規化 URL の SHA-256（先頭32文字）で冪等性を担保
  - SSRF対策、受信サイズ制限、gzip 対応
  - DuckDB への冪等保存（INSERT ... ON CONFLICT / RETURNING）

- 監査ログ（発注→約定のトレーサビリティ）
  - signal_events, order_requests, executions など監査用テーブル
  - UUID ベースのトレーサビリティとタイムスタンプ（UTC）

- データ品質チェック
  - 欠損データ検出、スパイク検出、重複チェック、日付整合性チェック
  - QualityIssue オブジェクトで問題を集約

---

## 必要要件（概略）

- Python 3.10+（型注釈に Union | 等を使用）
- 依存パッケージ（代表例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード）
- 各種環境変数（下記参照）

※ 実プロジェクトでは pyproject.toml / requirements.txt を用意して依存関係を固定してください。

---

## 環境変数（主なもの）

KabuSys は .env ファイル（プロジェクトルートの .env / .env.local）や OS 環境変数から設定を読み込みます。自動読み込みはプロジェクトルート（.git または pyproject.toml を検出）を基準に行われます。テストなどで自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション等の API パスワード（発注実装時）
- SLACK_BOT_TOKEN — 通知用 Slack Bot トークン
- SLACK_CHANNEL_ID — 通知先 Slack チャンネル ID

任意／デフォルトあり:
- KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視等で使う SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（"1" 等）

config.Settings 経由で型安全にアクセスできます（例: `from kabusys.config import settings`）。

---

## セットアップ手順（例）

1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境の作成と有効化
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール（代表例）
   - pip install duckdb defusedxml

   ※ 実プロジェクトでは requirements.txt / pyproject.toml を用意して `pip install -e .` 等を実行してください。

4. 環境変数ファイルを作成
   - プロジェクトルートに `.env` を置く（.env.local は上書き用）
   - 最小例:
     - JQUANTS_REFRESH_TOKEN=xxxxxxxx
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - KABUSYS_ENV=development

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから:
     - from kabusys.data import schema
     - conn = schema.init_schema("data/kabusys.duckdb")
   - 監査ログを別DBで管理する場合:
     - from kabusys.data import audit
     - audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
     - または既存 conn に対して audit.init_audit_schema(conn)

---

## 使い方（代表的な例）

以下はライブラリの主要機能を呼び出す際のサンプルコード例です。

- DuckDB スキーマ初期化
  - from kabusys.data import schema
  - conn = schema.init_schema(settings.duckdb_path)

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)
  - print(result.to_dict())

  パラメータで対象日やバックフィル日数、品質チェックの閾値を指定可能:
  - run_daily_etl(conn, target_date=date(2026,3,1), backfill_days=5, spike_threshold=0.4)

- J-Quants から株価を直接取得
  - from kabusys.data import jquants_client as jq
  - records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  - saved = jq.save_daily_quotes(conn, records)

- RSS ニュース収集と保存（既知銘柄セットを与えて銘柄紐付け）
  - from kabusys.data import news_collector as nc
  - articles = nc.fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  - new_ids = nc.save_raw_news(conn, articles)
  - # known_codes はセット（例: {"7203", "6758", ...}）
  - nc._save_news_symbols_bulk(conn, [(id, code) for id in new_ids for code in ["7203"]])  # 例

- 品質チェックを個別に実行
  - from kabusys.data import quality
  - issues = quality.run_all_checks(conn)
  - for i in issues: print(i)

- 監査ログ初期化
  - from kabusys.data import audit
  - # 既存 conn に追加
  - audit.init_audit_schema(conn)
  - # もしくは専用 DB を初期化
  - audit_conn = audit.init_audit_db("data/audit.duckdb")

---

## 自動 .env 読み込みについて

- 実装はプロジェクトルート（.git または pyproject.toml を探索）にある `.env` を自動的に読み込みます。
- 読み込み順:
  - OS 環境変数（最優先）
  - .env.local（override=True）
  - .env（override=False）
- 自動読み込みを無効にする:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env のパースはシェルライク（export プレフィックス、クォート、インラインコメント等に対応）です。

---

## ディレクトリ構成

（リポジトリの主要ファイル群の抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - pipeline.py
      - schema.py
      - audit.py
      - quality.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

主要モジュール:
- kabusys.config — 環境変数/設定管理
- kabusys.data.jquants_client — J-Quants API クライアント & DuckDB 保存
- kabusys.data.news_collector — RSS 取得と raw_news 保存
- kabusys.data.schema — DuckDB スキーマ初期化
- kabusys.data.pipeline — ETL パイプライン
- kabusys.data.audit — 監査ログテーブル初期化
- kabusys.data.quality — 品質チェック群

---

## 開発上の注意点・設計方針（抜粋）

- API 呼び出しはレート制限とリトライを考慮して実装されています（J-Quants: 120 req/min）。
- DuckDB への保存は冪等（ON CONFLICT）を基本とし、ETL を再実行しても整合性を保ちます。
- ニュース収集は SSRF/DoS 対策（スキーム検証、プライベートアドレス検出、受信サイズ上限、gzip 解凍後のサイズ検査）を行います。
- 監査ログは削除しない前提で設計され、発注→約定までの全履歴をトレース可能にします。
- 品質チェックは Fail-Fast ではなく全問題を収集し、呼び出し側で対処を判断する姿勢です。

---

## よくある操作（コマンド例）

- 開発用に最小セットで ETL を手動実行:
  - python -c "from kabusys.data import schema, pipeline; conn=schema.init_schema('data/kabusys.duckdb'); res=pipeline.run_daily_etl(conn); print(res.to_dict())"

- ニュース収集ジョブ（スクリプトから定期実行）:
  - python -c "from kabusys.data import schema, news_collector; conn=schema.init_schema('data/kabusys.duckdb'); news_collector.run_news_collection(conn)"

---

## ライセンス・貢献

本 README はコードベースの説明用です。実運用／配布には LICENSE を明示し、テスト・CI・依存固定等を整備してください。機能拡張（戦略層 / 実際の発注実装 / Slack 通知等）やテストの追加歓迎します。

---

必要であれば README に含める具体的な .env.example、依存ファイル（pyproject.toml / requirements.txt）、および実行スクリプト例（systemd timer / cron / GitHub Actions）のテンプレートも作成します。どの程度の詳細を追加しますか？