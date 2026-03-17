# KabuSys

日本株向け自動売買基盤コンポーネント群（ライブラリ）

このリポジトリはデータ取得・ETL・品質チェック・ニュース収集・監査ログ・マーケットカレンダー管理などを提供する内部ライブラリ群です。J-Quants API と連携して株価・財務・カレンダー等のデータを取得し、DuckDB に保存・管理するための機能を中心に構成されています。

---

## 主な特徴（機能一覧）

- 環境変数ベースの設定管理（.env 自動読み込み、必要変数チェック）
- J-Quants API クライアント
  - 日次株価（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）順守（固定間隔スロットリング）
  - リトライ（指数バックオフ、対象: 408/429/5xx）、401 時はトークン自動リフレッシュ
  - ページネーション対応、fetched_at による取得時刻トレース
- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution / Audit レイヤのDDL定義
  - インデックス作成、冪等なテーブル作成
- ETL パイプライン
  - 差分取得（最終取得日からの差分 + バックフィル）
  - 市場カレンダーの先読み（lookahead）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
- RSS ベースのニュース収集モジュール
  - URL 正規化・トラッキングパラメータ除去、SSRF 対策、gzip / サイズ上限対策
  - 重複防止（記事ID は正規化 URL の SHA-256 の先頭 32 文字）
  - DuckDB への冪等保存（INSERT ... RETURNING）
  - 銘柄コード抽出（テキスト中の4桁数字）
- マーケットカレンダー管理・営業日ロジック
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - DB の calendar を優先、未登録日は曜日ベースでフォールバック
- 監査ログ（audit）モジュール
  - signal → order_request → execution までのトレース用テーブル群、UTC タイムゾーン固定

---

## 前提 / 要件

- Python 3.10 以上（PEP 604 型注釈（|）を使用）
- 主要依存ライブラリ（例）
  - duckdb
  - defusedxml
- 標準ライブラリの urllib、json、logging、datetime 等を利用

（実運用・開発用に requirements.txt / pyproject.toml をプロジェクト側で用意してください）

---

## セットアップ手順

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（例）
   - pip install duckdb defusedxml

   ※ 実際は pyproject.toml / requirements.txt がある場合はそちらを使ってください。

3. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を配置すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化）。
   - 必須環境変数（アプリ起動時にチェックされます）:

     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知に使う Bot トークン（必須）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）

   - 任意（デフォルトあり）:
     - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV — 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
     - LOG_LEVEL — ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト: INFO）

   - .env の例（プロジェクトルートに `.env` を新規作成）:

     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. データベース初期化
   - DuckDB スキーマ初期化例（Python REPL / スクリプト）:

     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)
     ```

   - 監査ログ専用スキーマ初期化:

     ```python
     from kabusys.data.audit import init_audit_db
     conn_audit = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（主要な実行例）

- J-Quants の ID トークン取得:

  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使う
  ```

- 日次 ETL を実行する（市場カレンダー取得 → 株価・財務差分取得 → 品質チェック）:

  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

  主なオプション:
  - target_date: ETL の対象日（省略で今日）
  - run_quality_checks: 品質チェックを行うか（デフォルト True）
  - backfill_days: 後出し修正吸収用のバックフィル日数（デフォルト 3）

- RSS ニュース収集ジョブ:

  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = init_schema("data/kabusys.duckdb")
  # known_codes は銘柄抽出に使う有効銘柄コードセット（例: 上場銘柄リスト）
  stats = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
  print(stats)  # {source_name: 新規保存件数}
  ```

- マーケットカレンダー関連ユーティリティ:

  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = init_schema("data/kabusys.duckdb")
  import datetime
  d = datetime.date(2025, 1, 1)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

- データ品質チェックの個別実行:

  ```python
  from kabusys.data.quality import run_all_checks
  conn = init_schema("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

---

## 環境変数自動読み込みについて

- .env / .env.local をプロジェクトルート（.git または pyproject.toml のある階層）から自動読み込みします。
  - 読み込み順: OS 環境変数 > .env.local (> override True) > .env
  - OS 側の既存環境変数は保護されます（上書きされません）。
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Settings クラスで必須値を取得する際に未設定だと ValueError が送出されます。

---

## ディレクトリ構成

リポジトリ内の主要ファイル / モジュール（本 README は提供されたコードベースに基づく概略です）:

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py          — J-Quants API クライアント（取得・保存）
      - news_collector.py          — RSS ニュース収集・解析・保存
      - schema.py                  — DuckDB スキーマ定義・初期化
      - pipeline.py                — ETL パイプライン（run_daily_etl 等）
      - calendar_management.py     — マーケットカレンダー更新 & 営業日ロジック
      - audit.py                   — 監査ログ（signal/order/execution）テーブル
      - quality.py                 — データ品質チェック
    - strategy/
      - __init__.py                — 戦略関連（実装はここから拡張）
    - execution/
      - __init__.py                — 発注 / ブローカ連携（拡張ポイント）
    - monitoring/
      - __init__.py                — 監視・メトリクス（拡張ポイント）

---

## 運用上の注意点 / 設計上のポイント

- J-Quants API のレート制限（120 req/min）やリトライ挙動は jquants_client に実装されています。外部呼び出し時はこの挙動を理解したうえで利用してください。
- DuckDB への保存は多くが冪等（ON CONFLICT DO UPDATE / DO NOTHING）になるよう設計されています。外部から直接データを投入する際は一貫性・主キー制約に留意してください。
- RSS フィード取得は SSRF・XML Bomb 対策（スキーム検証、プライベートアドレス検査、受信サイズ上限、defusedxml）を行っています。取得元 URL の入力を外部から受け取る場合は十分に検証してください。
- 日次 ETL は品質チェックで検出された問題を一覧化しますが、ETL 自体は可能な限り継続します（Fail-Fast ではない）。運用側で重大問題（error）の検出時の挙動を決める必要があります。
- すべてのタイムスタンプは UTC を原則として扱う設計になっています（監査 DB は明示的に TimeZone='UTC' を設定）。

---

何か使い方や設計の意図・API 詳細について追加のドキュメントが必要でしたら教えてください。README を実際の実行コマンドや CI 手順に合わせて調整できます。