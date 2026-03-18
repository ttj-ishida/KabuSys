# KabuSys

日本株自動売買システム（ライブラリ）

このリポジトリは、J-Quants API や RSS ニュースを用いて市場データを収集・整形し、
戦略層・発注層・監査ログ層を備えた日本株用自動売買基盤の一部を実装した Python パッケージです。

主に以下を提供します。
- J-Quants からの日次株価・財務・市場カレンダーの取得クライアント（レート制御・リトライ・トークン自動リフレッシュ対応）
- RSS からのニュース収集と DuckDB への安全な保存（SSRF/圧縮爆弾対策、トラッキングパラメータ除去）
- DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- 市場カレンダー管理・営業日判定ロジック
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）
- データ品質チェック（欠損・重複・スパイク・日付不整合の検出）
- 環境変数ベースの設定読み込み（.env 自動読み込み機能）

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - レート制御（120 req/min）、リトライ（指数バックオフ）、401 受信時のトークン自動リフレッシュ
  - DuckDB へ冪等的に保存する save_* 関数

- data/news_collector.py
  - RSS フィード取得・パース・前処理（URL除去・空白正規化）
  - 記事ID は正規化 URL の SHA-256（先頭32文字）
  - SSRF 対策、受信サイズ制限、gzip 解凍対策
  - DuckDB へ冪等保存（INSERT ... RETURNING）と銘柄紐付け

- data/schema.py
  - DuckDB のテーブル定義（Raw / Processed / Feature / Execution 層）と初期化関数 init_schema()

- data/pipeline.py
  - 日次 ETL 実行 run_daily_etl（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新ロジック、backfill のサポート、ETL 結果オブジェクト ETLResult

- data/calendar_management.py
  - market_calendar のバッチ更新（calendar_update_job）
  - 営業日判定・次/前営業日取得・期間内営業日列挙

- data/audit.py
  - 監査ログ用テーブル・インデックス定義
  - init_audit_schema / init_audit_db による監査用 DB 初期化
  - トレース階層（business_date → strategy_id → signal_id → order_request_id → broker_order_id）

- data/quality.py
  - check_missing_data, check_duplicates, check_spike, check_date_consistency
  - run_all_checks による一括実行（QualityIssue オブジェクトで返却）

- config.py
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - 必須変数取得（_require）や環境フラグ（is_live / is_paper / is_dev）
  - 自動ロードを無効にする KABUSYS_DISABLE_AUTO_ENV_LOAD

---

## セットアップ手順

前提: Python 3.9+（コードは typing の Union | 形式を使用しています）を推奨します。

1. リポジトリをクローン
   - git clone ...

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール
   - 必須: duckdb, defusedxml
   - 例:
     - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt があればそれを使用してください）

4. 環境変数の設定
   - プロジェクトルートに .env を作成（.env.example を参考に）
   - 必須環境変数（config.Settings 参照）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
     - SLACK_BOT_TOKEN: Slack Bot トークン（必須）
     - SLACK_CHANNEL_ID: Slack チャンネルID（必須）
   - 任意:
     - KABU_API_BASE_URL: デフォルト "http://localhost:18080/kabusapi"
     - DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
     - SQLITE_PATH: デフォルト "data/monitoring.db"
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
   - 自動 .env ロードはデフォルトで有効（プロジェクトルート探索）。無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")  # デフォルトパスは設定で上書き可

6. 監査用 DB 初期化（任意）
   - from kabusys.data.audit import init_audit_db
   - audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（簡単な例）

- DuckDB を初期化して日次 ETL を実行する例:

  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # 引数で target_date 等を指定可能
  print(result.to_dict())
  ```

- J-Quants から株価（取込・保存）だけを実行する例:

  ```python
  from datetime import date
  import duckdb
  from kabusys.data import jquants_client as jq

  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date.today())
  saved = jq.save_daily_quotes(conn, records)
  print(f"fetched={len(records)} saved={saved}")
  ```

- RSS ニュース収集を実行する例:

  ```python
  import duckdb
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = duckdb.connect("data/kabusys.duckdb")
  known_codes = {"7203", "6758"}  # 例: 有効な銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- 監査スキーマを DB に追加する例:

  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.audit import init_audit_schema

  conn = init_schema("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

---

## 設計上の注意点 / セキュリティ

- J-Quants クライアントは API レート制限（120 req/min）を尊重します。大量リクエスト時は適宜配慮してください。
- ニュース収集は SSRF 対策（リダイレクト検査・プライベートIP拒否）、受信サイズ制限、defusedxml を用いた安全な XML パースを実装しています。
- DuckDB への保存は可能な限り冪等（ON CONFLICT）を利用しています。
- 時刻・fetched_at は UTC を基本に扱い、Look-ahead Bias を防止するために取得時刻を明示的に保存します。
- .env 自動ロードはプロジェクトルートの .git または pyproject.toml を起点に探索します。自動ロードを無効化したいテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

（src 配下がパッケージルート）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存）
    - news_collector.py        — RSS ニュース収集・前処理・保存
    - schema.py                — DuckDB スキーマ定義・初期化
    - pipeline.py              — ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py   — 市場カレンダー管理・営業日判定
    - audit.py                 — 監査ログ（トレーサビリティ）
    - quality.py               — データ品質チェック
  - strategy/
    - __init__.py              — 戦略（プレースホルダ）
    (戦略関連のモジュールをここに追加)
  - execution/
    - __init__.py              — 発注/ブローカー連携（プレースホルダ）
  - monitoring/
    - __init__.py              — モニタリング関連（プレースホルダ）

---

## 開発・運用のヒント

- 単体テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使い、明示的に環境を注入することを推奨します。
- ETL のバックフィル日数やスパイク閾値は data.pipeline.run_daily_etl の引数で調整可能です。
- news_collector.extract_stock_codes は簡易的に 4 桁数字を抽出する実装です。より精度を上げたい場合は辞書照合や NLP を導入してください。
- DuckDB は軽量かつ高速でローカル分析に適しています。運用時は定期的な VACUUM/バックアップを検討してください。

---

この README はコードベースからの抜粋に基づき作成しています。実運用や詳細な設定・追加依存ライブラリについてはプロジェクトの他ドキュメント（.env.example、DataPlatform.md 等）をご参照ください。質問や補足が必要であればお知らせください。