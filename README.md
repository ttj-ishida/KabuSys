# KabuSys

日本株向け自動売買／データパイプライン基盤ライブラリ

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するための共通ライブラリ群です。  
主にデータ収集（J‑Quants API / RSS ニュース）、ETL パイプライン、データ品質チェック、マーケットカレンダー管理、監査ログ（発注〜約定トレーサビリティ）などの機能を提供します。  
設計上、API レート制御・リトライ、冪等性（ON CONFLICT）、SSRF 対策、データ品質チェック等を盛り込み、実運用を意識した堅牢さを重視しています。

パッケージエントリポイント: `kabusys`（バージョン: 0.1.0）

---

## 主な機能一覧

- config
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）
  - 必須環境変数取得ヘルパー（`settings` オブジェクト）
  - 環境モード判定（development / paper_trading / live）
- data.jquants_client
  - J‑Quants API クライアント（株価日足 / 財務 / マーケットカレンダー）
  - レート制御（120 req/min 固定間隔スロットリング）
  - リトライ（指数バックオフ、401時の自動トークンリフレッシュ）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- data.news_collector
  - RSS フィードからのニュース収集、前処理、DuckDB 保存（raw_news）
  - トラッキングパラメータ除去・URL 正規化・SHA256 ベースの記事ID生成
  - SSRF 対策、gzip 上限チェック、XML の安全パース（defusedxml）
  - 銘柄コード抽出 + news_symbols への紐付け機能
- data.schema
  - DuckDB 用スキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - テーブル作成・インデックス作成の初期化関数（idempotent）
- data.pipeline
  - 差分 ETL（市場カレンダー・株価・財務）／日次 ETL の統合実行
  - バックフィル（後出し修正吸収）・品質チェック呼び出し（quality モジュール）
- data.calendar_management
  - market_calendar を使った営業日判定、next/prev_trading_day、範囲検索等
  - calendar 更新ジョブ（JPX カレンダー差分取得）
- data.quality
  - 欠損、重複、スパイク（前日比）・日付不整合（未来日・非営業日）検出
  - QualityIssue 型で問題を返し、ETL 側で扱える設計
- data.audit
  - 発注〜約定の監査テーブル群（signal_events / order_requests / executions）
  - 監査用スキーマ初期化（UTC タイムゾーン固定）
- strategy / execution / monitoring
  - パッケージ構成上の名前空間（戦略・発注・監視ロジックを追加するための場所）

---

## 要件（推奨）

- Python 3.10+（型ヒントに union 代替表記などを使用）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml

（実プロジェクトでは setup.py / pyproject.toml または requirements.txt を用意してください）

---

## 環境変数（重要）

以下は本ライブラリが参照する主な環境変数です。`.env` / `.env.local` をプロジェクトルートに置くと自動読み込みされます（ただし自動ロードを無効化することも可能）。

必須（例）
- JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API 用パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）

任意 / デフォルト
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）。デフォルト: INFO
- DUCKDB_PATH — DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視用 SQLite パス。デフォルト: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効にする場合は `1` を設定

.env 読み込みの挙動
- プロジェクトルートは `pyproject.toml` または `.git` を起点に自動検出します（cwd 非依存）。
- 読み込み優先順位: OS 環境 > .env.local > .env
- `.env` のパースはコメント、export プレフィックス、クォート、エスケープ等に対応します。

必須値が欠けると `settings` の該当プロパティで `ValueError` が上がります。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - 例: git clone ...

2. 仮想環境を作成・有効化
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要パッケージをインストール
   - 例（最低限）:
     ```
     pip install duckdb defusedxml
     ```
   - 実運用では pyproject.toml / requirements.txt に沿ってインストールしてください。

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成（または OS 環境変数で設定）。
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     ```

5. DuckDB スキーマ初期化
   - Python REPL などで:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)
     ```
   - 監査ログ専用 DB を使う場合:
     ```python
     from kabusys.data.audit import init_audit_db
     conn_audit = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（代表的な例）

- settings の利用:
  ```python
  from kabusys.config import settings

  token = settings.jquants_refresh_token
  print(settings.env, settings.log_level)
  ```

- DB 初期化:
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL 実行:
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # target_date は省略で今日
  print(result.to_dict())
  ```

- ニュース収集ジョブ:
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  # known_codes を渡すと銘柄紐付けを行う（例: 全上場銘柄のセット）
  results = run_news_collection(conn, known_codes={"7203", "6758"})
  print(results)  # {source_name: saved_count, ...}
  ```

- J‑Quants トークン取得（低レベル）:
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使う
  ```

- 品質チェック（個別実行）:
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn)
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

注意点
- J‑Quants API 呼び出しはレート制御とリトライを行いますが、運用時は追加の同時実行制御やバッチ設計を検討してください。
- ETL は各ステップを独立してエラーハンドリングするため、部分失敗しても全体が継続され結果オブジェクトにエラー情報が蓄積されます。

---

## 主要 API（要約）

- kabusys.config
  - settings — 環境設定オブジェクト（プロパティ経由で取得）
- kabusys.data.jquants_client
  - get_id_token(...)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
- kabusys.data.news_collector
  - fetch_rss(url, source)
  - save_raw_news(conn, articles)
  - save_news_symbols(conn, news_id, codes)
  - run_news_collection(conn, sources=None, known_codes=None)
- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
- kabusys.data.calendar_management
  - is_trading_day(conn, d), next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- kabusys.data.quality
  - run_all_checks(...)
- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

---

## ディレクトリ構成

リポジトリの主要部分（src 配下）例:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/               # 発注・約定関連（名前空間）
      - __init__.py
    - strategy/                # 戦略ロジック（名前空間）
      - __init__.py
    - monitoring/              # 監視（名前空間）
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py      # J‑Quants API クライアント（fetch / save）
      - news_collector.py      # RSS ニュース収集・前処理・保存
      - schema.py              # DuckDB スキーマ定義 / 初期化
      - pipeline.py            # ETL パイプライン（差分取得・品質チェック）
      - calendar_management.py # 市場カレンダー管理
      - audit.py               # 監査ログ（発注→約定 トレーサビリティ）
      - quality.py             # データ品質チェック

---

## 運用上の考慮事項（補足）

- セキュリティ:
  - RSS パーサは defusedxml を使用して XML 攻撃を防いでいます。
  - ニュース収集時は SSRF 対策（スキーム検証、ホストのプライベートアドレスチェック、リダイレクト検査）を実施しています。
- データ整合性:
  - J‑Quants から取得したデータは取得時刻（UTC）を記録し、Look‑ahead bias を防ぐ設計を意識しています。
  - DuckDB への保存は冪等（ON CONFLICT）設計で再実行耐性があります。
- 監査/トレーサビリティ:
  - 発注・約定に関する監査スキーマを提供。order_request_id を冪等キーとして二重発注を防止できます。
- テスト:
  - 一部低レベルの I/O (例: news_collector._urlopen) はモックしやすい設計になっています。

---

## 貢献 / 変更点管理

この README はコードベースの概略をまとめたものです。実運用／デプロイのためには次の整備を推奨します:

- pyproject.toml / requirements.txt に依存関係を明記
- CI で DuckDB を使ったユニットテスト（インメモリ DB）を用意
- .env.example をリポジトリに追加（必須変数のテンプレート）
- ロギング設定・メトリクス・監視（Prometheus など）の導入

---

必要があれば、README に含める手順のコマンド一覧やサンプル .env.example、ユースケースごとの詳しいチュートリアル（ETL スケジューリング、戦略の組み込み、発注フローなど）を追加できます。どの部分を詳しくしたいか教えてください。