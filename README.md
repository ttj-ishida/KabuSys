# KabuSys

日本株自動売買プラットフォーム向けのコアライブラリ（データ取得・ETL・品質チェック・監査ログなど）。

このリポジトリは、J-Quants API や RSS フィードからデータを収集・保存し、DuckDB に格納して戦略/実行層へ提供するための基盤機能を実装しています。

---

## 概要

KabuSys は以下を目的としたモジュール群を提供します。

- J-Quants API からの株価（日足）・財務・市場カレンダーの取得（レートリミット・リトライ・トークン自動リフレッシュ対応）
- RSS フィードからのニュース収集と銘柄紐付け（SSRF対策、トラッキングパラメータ除去、gzip上限チェック）
- DuckDB に対するスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得、バックフィル、品質チェックの統合）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル → 発注 → 約定までのトレーサビリティ）

設計上のポイント：
- 冪等性を重視（DB保存は ON CONFLICT 句で重複を排除）
- Look-ahead バイアス防止のため fetched_at や UTC タイムスタンプを保存
- ネットワーク/セキュリティ対策（SSRF、XMLパースの hardening、受信サイズ制限等）

---

## 主な機能一覧

- config
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）
  - settings オブジェクトから設定値を取得
- data.jquants_client
  - get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()
  - DuckDB へ保存する save_* 関数（save_daily_quotes / save_financial_statements / save_market_calendar）
  - レートリミット・リトライ・401 トークン自動更新を実装
- data.news_collector
  - fetch_rss(), save_raw_news(), save_news_symbols(), run_news_collection()
  - URL 正規化・トラッキング削除・記事 ID（SHA-256 先頭32文字）による冪等性
  - SSRF 対策、gzip サイズ制限、defusedxml による XML ハードニング
- data.schema
  - init_schema(db_path), get_connection(db_path)
  - Raw/Processed/Feature/Execution レイヤーのテーブル定義とインデックス
- data.pipeline
  - run_prices_etl(), run_financials_etl(), run_calendar_etl(), run_daily_etl()
  - 差分更新・バックフィル・品質チェックの統合
- data.quality
  - check_missing_data(), check_spike(), check_duplicates(), check_date_consistency(), run_all_checks()
  - QualityIssue データクラスを返し、エラー／警告を詳細に報告
- data.audit
  - init_audit_schema(conn), init_audit_db(db_path)
  - シグナル・発注要求・約定の監査テーブルとインデックス

---

## セットアップ手順

前提: Python 3.10+（型注釈の union 演算子などを想定）。

1. 仮想環境の作成（推奨）
   - macOS/Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 依存パッケージのインストール（代表的な依存）
   ```
   pip install duckdb defusedxml
   ```
   - 実運用ではログ送信や Slack 統合等の追加パッケージが必要になる可能性があります。

3. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（自動読み込みはデフォルトで有効）。
   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須環境変数の例（最低限）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     SLACK_BOT_TOKEN=your_slack_bot_token
     SLACK_CHANNEL_ID=your_slack_channel_id
     KABU_API_PASSWORD=your_kabu_pass
     ```
   - 任意 / デフォルト:
     ```
     KABUSYS_ENV=development       # development | paper_trading | live
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_DISABLE_AUTO_ENV_LOAD=   # 1 にすると自動読み込みOFF
     ```

4. DB 初期化（DuckDB）
   - Python スクリプトから:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)
     ```
   - 監査ログを追加する場合:
     ```python
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)
     ```

---

## 使い方（主要な例）

- 日次 ETL 実行（最小例）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # target_date を渡さなければ今日が対象
  print(result.to_dict())
  ```

- J-Quants から特定銘柄の株価を取得して保存
  ```python
  import duckdb
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  id_token = get_id_token()  # settings.jquants_refresh_token を使用
  records = fetch_daily_quotes(id_token=id_token, code="7203", date_from=None, date_to=None)
  saved = save_daily_quotes(conn, records)
  print("saved", saved)
  ```

- RSS ニュース収集ジョブ（既知銘柄セットを使った紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  known_codes = {"7203", "6758", "9984"}  # 例
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- 品質チェックを単独で実行
  ```python
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabuステーション API のベース URL (デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH — SQLite（monitoring等）ファイルパス (デフォルト: data/monitoring.db)
- KABUSYS_ENV — 環境 (development | paper_trading | live)
- LOG_LEVEL — ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化する場合に "1"

注意: Settings の未設定必須キーにアクセスすると ValueError が発生します。

---

## ディレクトリ構成

以下は主要なモジュール構成（src 配下）です。パッケージは `kabusys`。

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数 / 設定読み込みロジック
    - data/
      - __init__.py
      - schema.py              # DuckDB スキーマ定義・初期化
      - jquants_client.py      # J-Quants API クライアント（取得 + 保存）
      - pipeline.py            # ETL パイプライン（差分取得・品質チェック統合）
      - news_collector.py      # RSS ニュースの取得・DB保存・銘柄抽出
      - quality.py             # データ品質チェック
      - audit.py               # 監査ログ（シグナル→発注→約定の追跡）
      - audit.py
      - pipeline.py
      - audit.py
    - strategy/
      - __init__.py
      (戦略モジュールを置く想定フォルダ)
    - execution/
      - __init__.py
      (発注 / ブローカー接続の実装を置く想定フォルダ)
    - monitoring/
      - __init__.py
      (監視 / アラート連携等)

---

## 設計上の注意点・運用上のヒント

- 自動 .env 読み込みはプロジェクトルートを .git または pyproject.toml で検出します。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- J-Quants API は 120 req/min のレート制限に従う実装です。大量一括リクエストを行う場合は注意してください。
- DuckDB の初期化は init_schema() で行ってください。既存テーブルはスキップされるため冪等に実行できます。
- ニュース収集では外部 URL の検証（スキーム・プライベートIP 等）と受信上限を実装していますが、追加でプロキシやタイムアウトの運用制御が必要な場合は fetch_rss の引数や _urlopen をモック/差し替え可能です。
- 品質チェックは警告/エラーを返す設計です。ETL 実行は可能な限り継続して情報を収集し、呼び出し側が停止判定を行えるようにしています。

---

## 開発・テスト

- 単体テストやモックを用いた外部通信の切り離しを推奨します。news_collector._urlopen、jquants_client._request 等をモックすると容易にテスト可能です。
- ロギングは標準ライブラリの logging を使用しているため、ハンドラやフォーマッタをアプリケーション側で設定してください。

---

## 付記

この README は現行コードベース（src/kabusys 以下）に基づいています。戦略層（strategy）や発注実装（execution）、監視（monitoring）は骨子のみが用意されており、実運用ではブローカー API 統合、リスク管理、ポートフォリオ最適化、バックテスト基盤などの追加実装が必要です。

問題点や追加したい機能があれば、どの部分を拡張したいか教えてください。README の改善や具体的なスニペットも追加できます。