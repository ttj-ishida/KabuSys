# KabuSys

日本株向け自動売買 / データプラットフォームライブラリ

---

## プロジェクト概要

KabuSys は日本株の自動売買とデータパイプラインを支援する Python ライブラリです。J-Quants API や RSS フィードからのデータ取得、DuckDB によるスキーマ定義・保存、ETL パイプライン、データ品質チェック、監査ログなどを備え、戦略・実行・監視レイヤーと連携するための基盤機能を提供します。

設計のポイント:
- J-Quants API に対するレート制限・リトライ・トークン自動リフレッシュ
- DuckDB を用いた三層（Raw / Processed / Feature）スキーマ設計
- RSS ニュース収集における SSRF 対策・XML 安全対策・トラッキングパラメータ除去
- ETL の差分更新・バックフィル・品質チェック
- 発注・約定に関する監査ログ（監査スキーマ）

---

## 主な機能一覧

- 環境変数/設定管理（自動 .env ロード、設定ラッパー）
- J-Quants API クライアント
  - 日足（OHLCV）・財務データ・マーケットカレンダー取得
  - レートリミッタ、指数バックオフリトライ、401 時の自動トークンリフレッシュ
  - DuckDB への冪等保存（ON CONFLICT）
- RSS ベースのニュース収集（トラッキング削除、ID は正規化 URL の SHA-256）
  - XML の安全パース（defusedxml）
  - SSRF/プライベートアドレス対策、応答サイズ上限
  - raw_news / news_symbols への保存（トランザクション・チャンク挿入）
- DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック統合）
- マーケットカレンダー管理（営業日判定/翌営業日/前営業日/期間取得）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）

---

## 要件

- Python 3.10+
- 依存ライブラリ（例）
  - duckdb
  - defusedxml
- （実行環境により）ネットワークアクセス（J-Quants / RSS）

requirements.txt や pyproject.toml がある場合はそれに従ってインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクト配布形式に合わせて）pip install -e .

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動ロードされます（優先度: OS 環境 > .env.local > .env）。
   - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。

必須の環境変数（コード内 Settings を参照）:
- JQUANTS_REFRESH_TOKEN  — J-Quants リフレッシュトークン
- KABU_API_PASSWORD      — kabuステーション API 用パスワード
- SLACK_BOT_TOKEN        — Slack 通知用
- SLACK_CHANNEL_ID       — Slack チャンネル ID

任意 / デフォルト付き:
- KABUSYS_ENV            — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL              — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUS_API_BASE_URL     — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            — SQLite（監視用）データベースパス（デフォルト: data/monitoring.db）

例 `.env`（簡易）
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_pass
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（基本例）

以下はライブラリをインポートして各機能を使う最小例です。

- DuckDB スキーマ初期化
  Python REPL やスクリプトで:
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")
  # 監査テーブルを追加する場合
  from kabusys.data import audit
  audit.init_audit_schema(conn)

- J-Quants トークン取得（明示的に取得したい場合）
  from kabusys.data import jquants_client as jq
  id_token = jq.get_id_token()  # settings.jquants_refresh_token を利用

- 日次 ETL （市場カレンダー・株価・財務・品質チェックを実行）
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())

- RSS ニュース収集の実行（既存 DuckDB 接続に保存）
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 銘柄コードセット（抽出に使用）
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)  # {source_name: saved_count}

- 個別関数の例
  - jquants_client.fetch_daily_quotes(...)
  - news_collector.fetch_rss(url, source)
  - data.quality.run_all_checks(conn, target_date=...)

注意点:
- run_daily_etl 等はネットワーク・API 叩くため、J-Quants トークンやネットワーク状態が必要です。
- ETL は差分取得を行います。最終取得日やバックフィル幅はパラメータで制御可能です。

---

## 主な API と挙動（要点）

- 設定管理 (kabusys.config.settings)
  - 環境変数から値を読み取り、必須変数が未設定なら ValueError を投げる
  - 自動でプロジェクトルートの .env / .env.local をロード（無効化可能）

- J-Quants クライアント (kabusys.data.jquants_client)
  - RateLimiter による 120 req/min 制御
  - リトライ（指数バックオフ、最大3回）
  - 401 を受けた場合、refresh token から id_token を再取得して 1 回リトライ
  - fetch_* 系はページネーション対応
  - save_* は DuckDB に対して ON CONFLICT DO UPDATE を行い冪等保存

- News Collector (kabusys.data.news_collector)
  - RSS の URL 正規化、トラッキングパラメータ除去、SHA-256 ベースの記事ID生成
  - defusedxml による安全な XML パース
  - SSRF 対策: スキーム検査、リダイレクト先のホストがプライベートか判定して拒否
  - レスポンスサイズ上限（10 MB）によるメモリ DoS 対策
  - DB へのバルク挿入はチャンク化・トランザクションで実行し、実際に挿入された ID を返す

- Schema (kabusys.data.schema)
  - init_schema(db_path) で全テーブルとインデックスを作成（冪等）
  - get_connection(db_path) は接続のみ（初回は init_schema を呼ぶこと）

- ETL Pipeline (kabusys.data.pipeline)
  - run_daily_etl(conn, target_date=None, ...) がトップレベルの ETL ワークフロー
  - ETLResult に処理の統計・品質問題を格納

- Quality (kabusys.data.quality)
  - 欠損 (missing_data)、重複 (duplicates)、スパイク (spike)、日付整合性 (date_consistency) をチェック
  - run_all_checks でまとめて実行し QualityIssue 列挙を返す

- Calendar Management (kabusys.data.calendar_management)
  - 営業日判定、next/prev_trading_day、期間内の営業日一覧取得
  - calendar_update_job で夜間バッチ的にカレンダーを更新可能

- Audit (kabusys.data.audit)
  - signal_events / order_requests / executions の監査テーブルを初期化する関数を提供

---

## ディレクトリ構成

（ライブラリルートの src/kabusys を想定）

- src/kabusys/
  - __init__.py                 — パッケージ定義、バージョン
  - config.py                   — 環境変数・設定管理、.env 自動ロード
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（取得 + DuckDB 保存）
    - news_collector.py         — RSS ニュース収集・保存ロジック
    - schema.py                 — DuckDB スキーマ定義・初期化
    - pipeline.py               — ETL パイプライン（差分取得・品質チェック統合）
    - calendar_management.py    — 市場カレンダー管理・営業日ユーティリティ
    - audit.py                  — 監査ログテーブル定義・初期化
    - quality.py                — データ品質チェック
  - strategy/
    - __init__.py               — 戦略関連（拡張ポイント）
  - execution/
    - __init__.py               — 発注・実行関連（拡張ポイント）
  - monitoring/
    - __init__.py               — 監視関連（拡張ポイント）

---

## テスト・開発時のヒント

- 自動 .env ロードを無効にして明示的に環境を制御したい場合:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- news_collector._urlopen はテストでモック可能（外部ネットワーク依存を切るため）
- J-Quants 呼び出しは rate limiter により 120 req/min に制限されるため、テスト時は注意

---

必要であれば、README に以下を追加できます:
- 具体的なコマンド例（systemd / cron / Airflow での定期実行サンプル）
- .env.example（テンプレート）
- CI / テストの実行手順

追加希望があれば教えてください。