# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ取得・ETL、ニュース収集、カレンダー管理、データ品質チェック、DuckDB スキーマ／監査ログ周りのユーティリティを提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構築するための基盤ライブラリです。主に以下を目的としています。

- J-Quants API から市場データ（株価・財務・マーケットカレンダー）を安全かつ冪等に取得・保存する。
- RSS ベースのニュース収集と銘柄紐付けを行い、特徴量や戦略に供給する。
- DuckDB ベースのデータレイヤ（Raw / Processed / Feature / Execution / Audit）を定義・初期化する。
- ETL（差分取得・バックフィル・品質チェック）を容易に実行できるパイプラインを提供する。
- API レート制御、リトライ、SSRF 対策、XML の安全パースなどセキュリティ／信頼性を考慮した設計。

---

## 主な機能一覧

- J-Quants クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レートリミット（120 req/min）制御
  - リトライ（指数バックオフ、最大3回）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 向けテーブル定義
  - 冪等なテーブル作成、インデックス定義
  - audit 用スキーマ（signal_events / order_requests / executions）

- ETL パイプライン
  - 差分取得（最終取得日からの差分）、バックフィル設定、品質チェック統合
  - run_daily_etl による一括実行（calendar → prices → financials → quality）

- ニュース収集モジュール
  - RSS フィードの取得（gzip 対応）、XML の安全パース（defusedxml）
  - URL 正規化（トラッキングパラメータ除去）と記事ID（SHA-256先頭32文字）生成
  - SSRF 対策（スキーム確認・プライベートIP拒否）、受信サイズ制限
  - raw_news / news_symbols への冪等保存（INSERT ... RETURNING を利用）

- カレンダー管理
  - 営業日判定、前後営業日取得、期間内営業日列挙
  - calendar_update_job による差分更新（バックフィル含む）

- データ品質チェック
  - 欠損・重複・スパイク（前日比）・日付不整合の検出
  - QualityIssue 構造で問題を報告

---

## セットアップ手順

※このリポジトリに requirements ファイルが付属していない想定のため、主要な依存のみ記載しています。実プロジェクトでは pyproject.toml / requirements.txt を参照してください。

1. Python 環境（推奨: 3.9+）を準備
   - 仮想環境を作成・有効化
     - python -m venv .venv
     - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb defusedxml

   - 追加で HTTP/ログ周りに必要なパッケージがあれば適宜インストールしてください。

3. 環境変数の設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID — Slack チャネル ID（必須）
   - 任意 / デフォルト:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

   - .env のフォーマットはシェルの KEY=VAL、クォートやコメントもサポートします。詳細は kabusys.config._parse_env_line の実装に準拠。

4. データベース初期化
   - DuckDB スキーマを初期化します（親ディレクトリがなければ自動生成）。
     - 例:
       from kabusys.data import schema
       conn = schema.init_schema("data/kabusys.duckdb")

---

## 使い方（代表的な API）

以下はライブラリの主要なユースケース例です。

- DuckDB スキーマ初期化
  - Python REPL やスクリプトから:
    from kabusys.data.schema import init_schema
    from kabusys.config import settings
    conn = init_schema(settings.duckdb_path)

- J-Quants トークン取得
  - from kabusys.data.jquants_client import get_id_token
    id_token = get_id_token()  # settings.jquants_refresh_token を使用して取得

- 日次 ETL 実行
  - from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn)  # target_date を渡して任意日で実行可能
    print(result.to_dict())

  - run_daily_etl の処理:
    1) カレンダー ETL（先読み）
    2) 株価 ETL（差分・バックフィル）
    3) 財務データ ETL（差分・バックフィル）
    4) 品質チェック（デフォルトで有効）

- ニュース収集と保存
  - from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
    results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
    print(results)  # {source_name: 新規保存件数}

  - 個別 RSS 取得:
    from kabusys.data.news_collector import fetch_rss
    articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")

- カレンダー関係ユーティリティ
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day, prev_trading_day, get_trading_days
    trading = is_trading_day(conn, date.today())

- 品質チェック（個別／一括）
  - from kabusys.data.quality import run_all_checks
    issues = run_all_checks(conn)
    for i in issues: print(i)

- 監査ログの初期化
  - from kabusys.data.audit import init_audit_schema
    init_audit_schema(conn)
  - 監査専用 DB を作る場合:
    from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit.duckdb")

注意点:
- J-Quants API にはレート制限があり、モジュール側で固定間隔スロットリングを行います。
- HTTP エラーに対するリトライや 401 時のトークン自動更新などの耐障害性ロジックを含みます。
- RSS 取得は SSRF に対する事前検証、リダイレクト検査、受信サイズ制限、gzip 解凍後の検査など安全対策があります。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token
- KABU_API_PASSWORD (必須) — kabu API のパスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定するとプロジェクトルートの .env 自動読み込みを無効化

---

## ディレクトリ構成（抜粋）

プロジェクト内の主要ファイル／モジュール:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定の管理（.env 自動ロード等）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py      — RSS 取得・前処理・保存
    - schema.py              — DuckDB スキーマ定義・初期化
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - audit.py               — 監査ログ（signal/order/execution）スキーマ
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py            — 戦略関連（実装候補／拡張ポイント）
  - execution/
    - __init__.py            — 発注／約定管理（実装候補／拡張ポイント）
  - monitoring/
    - __init__.py            — 監視／メトリクス（実装候補）

簡易ツリー:
- src/
  - kabusys/
    - config.py
    - __init__.py
    - data/
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - calendar_management.py
      - audit.py
      - quality.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

---

## 開発・拡張ポイント

- strategy / execution / monitoring パッケージは拡張用のエントリポイントになっています。戦略実装やブローカー連携をここに追加してください。
- news_collector の既知銘柄セット（known_codes）による紐付けロジックを強化して、NER や外部マッピングを導入可能です。
- ロギング／監視は SLACK 通知やメトリクス収集（Prometheus など）を追加すると運用性が向上します。
- DB の運用: DuckDB をファイルで運用する場合はバックアップや VACUUM（必要に応じて）を検討してください。

---

もし README に追加してほしい内容（例: 依存パッケージの厳密な一覧、実行スクリプト例、CI 設定、.env.example のテンプレートなど）があれば教えてください。必要に応じてサンプル .env.example や実行スクリプトも作成します。