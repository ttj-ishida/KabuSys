# KabuSys

日本株向けの自動売買プラットフォームのコアライブラリ（ミニマル実装）。  
データ収集（J-Quants / RSS ニュース）、ETL パイプライン、DuckDB ベースのスキーマ定義、データ品質チェック、監査ログ（発注→約定のトレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、日本株の自動売買に必要なデータ基盤と周辺機能を提供するライブラリ群です。主に以下を目的としています。

- J-Quants API からの株価・財務・市場カレンダー取得
- RSS フィードからのニュース収集と銘柄紐付け
- DuckDB によるデータ保管（Raw / Processed / Feature / Execution 層）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- 監査ログ（シグナル→発注→約定 のトレース）
- 設定管理（環境変数 / .env 自動読み込み）

設計上のポイント:
- API レート制限やリトライ（指数バックオフ）を考慮した実装
- 冪等性（ON CONFLICT）を意識した DB 保存
- SSRF, XML Bomb 等への防御（news_collector）
- 品質チェックを行い問題を収集（Fail-Fast ではなく報告）

---

## 主な機能一覧

- 設定管理
  - .env / .env.local の自動読み込み（必要に応じて無効化可能）
  - 必須環境変数の検証（取得時に例外を送出）

- データ関連（kabusys.data）
  - jquants_client
    - get_id_token: リフレッシュトークンから id token を取得
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
    - レートリミッタ・リトライ・401 自動リフレッシュ・ページネーション対応
    - DuckDB に対する冪等保存関数（save_*）
  - news_collector
    - RSS 取得（gzip 対応、受信サイズ制限）
    - URL 正規化・トラッキングパラメータ除去・記事ID生成（SHA-256）
    - SSRF 対策（スキーム検証・プライベートホスト拒否・リダイレクト検査）
    - DuckDB への冪等保存（INSERT ... RETURNING を利用）
    - 銘柄コード抽出（テキスト中の 4 桁コード）
  - schema
    - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層）
    - init_schema(db_path) でテーブル作成（冪等）
  - pipeline
    - 差分 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
    - run_daily_etl による一括実行
  - calendar_management
    - 営業日判定・前後営業日取得・カレンダー更新ジョブ
  - audit
    - 監査ログ用スキーマ（signal_events, order_requests, executions 等）
    - init_audit_schema / init_audit_db
  - quality
    - 欠損値、スパイク（前日比）、重複、日付不整合チェック
    - QualityIssue を返す（severity: error / warning）

- その他
  - execution, strategy, monitoring パッケージ（インターフェース用のプレースホルダ）

---

## セットアップ手順

前提:
- Python 3.10+ を推奨（typing の一部構文を使用）
- DuckDB を利用するため `duckdb` パッケージが必要
- RSS XML の安全なパースに `defusedxml` を使用

1. リポジトリをチェックアウト / コピー

2. 依存パッケージをインストール（例）
   - pip を使う例:
     pip install duckdb defusedxml

   （プロジェクトに requirements ファイルがあればそちらを利用してください。）

3. 環境変数の設定
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API のパスワード
     - SLACK_BOT_TOKEN: Slack 通知用 BOT トークン
     - SLACK_CHANNEL_ID: 通知先チャネル ID
   - 任意 / デフォルトあり:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）

   - .env 自動読み込み:
     - プロジェクトルート（.git または pyproject.toml がある場所）から .env を自動ロードします。
     - 読み込み順: OS 環境 > .env.local > .env
     - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

4. DuckDB スキーマ初期化
   - 例: Python REPL / スクリプトで
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

   - 監査ログ専用 DB を初期化する場合:
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（簡単な例）

- J-Quants トークン取得
  - get_id_token は settings.jquants_refresh_token をデフォルトで使います。
  - 例:
    from kabusys.data.jquants_client import get_id_token
    id_token = get_id_token()  # settings.jquants_refresh_token を使用

- 株価・財務データの fetch + 保存
  - 例:
    import duckdb
    from kabusys.data import jquants_client as jq
    conn = duckdb.connect("data/kabusys.duckdb")
    records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
    saved = jq.save_daily_quotes(conn, records)

- RSS ニュース収集
  - fetch_rss + save_raw_news の流れ:
    from kabusys.data.news_collector import fetch_rss, save_raw_news, DEFAULT_RSS_SOURCES
    conn = duckdb.connect("data/kabusys.duckdb")
    articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
    new_ids = save_raw_news(conn, articles)

- 日次 ETL の実行（推奨の入り口）
  - run_daily_etl は市場カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック を実行します。
    from kabusys.data.pipeline import run_daily_etl
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")
    result = run_daily_etl(conn)  # today を対象に実行
    print(result.to_dict())

- カレンダー更新ジョブ
  - calendar_update_job(conn) を定期実行することで market_calendar を最新に保ちます。

- 監査ログ初期化
  - init_audit_schema(conn) または init_audit_db("...") を使用して監査テーブルを用意します。

---

## 重要な実装上の注意（設計ポインタ）

- jquants_client
  - API レートは 120 req/min に合わせて固定間隔のスロットリングを行います。
  - リトライ: 最大 3 回（指数バックオフ）、HTTP 408/429/5xx をリトライ対象。
  - 401 を受けた場合、リフレッシュして 1 回だけ再試行します。
  - 取得時に fetched_at を UTC タイムスタンプで保存し、Look-ahead Bias を防ぐ設計。

- news_collector
  - 受信サイズを制限（10 MB）してメモリ DoS を防止。
  - defusedxml を使用し XML ベースの攻撃（XML Bomb 等）を防ぐ。
  - リダイレクト時にスキーム・ホストの事前検証を行い SSRF を防止。

- DB 保存
  - 多くの保存処理で ON CONFLICT（DO UPDATE / DO NOTHING）や INSERT ... RETURNING を使い冪等性と挿入結果の正確な取得を両立しています。
  - init_schema は存在チェックを行い冪等にテーブルを作成します。

- 環境変数の自動読み込み
  - パッケージロード時にプロジェクトルートを探索して .env, .env.local を読み込みます。テスト等で自動ロードを禁止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## ディレクトリ構成

リポジトリ内の主要ファイル／モジュール（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                     # 環境変数・設定管理（.env 自動読み込み）
    - data/
      - __init__.py
      - jquants_client.py           # J-Quants API クライアント（取得 & 保存ロジック）
      - news_collector.py           # RSS ニュース収集・保存・銘柄抽出
      - schema.py                   # DuckDB スキーマ定義・初期化
      - pipeline.py                 # ETL パイプライン（run_daily_etl 等）
      - calendar_management.py      # カレンダー管理（営業日判定・更新ジョブ）
      - audit.py                    # 監査ログ（シグナル→発注→約定のトレース）
      - quality.py                  # データ品質チェック
      - (その他 ETL/ユーティリティ)
    - strategy/                      # 戦略モジュール（プレースホルダ）
    - execution/                     # 発注実行モジュール（プレースホルダ）
    - monitoring/                    # 監視関連（プレースホルダ）

---

## 環境変数一覧（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意 / デフォルトあり:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト INFO
- KABU_API_BASE_URL — デフォルト http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化

注意: settings（kabusys.config.Settings）を通してプロパティとしてアクセスできます。必須値が未設定の場合は ValueError が発生します。

---

## ログと監視

- 各モジュールは標準の logging を使用します。LOG_LEVEL でログレベルを制御してください。
- ETL の結果や品質問題は run_daily_etl の戻り値（ETLResult）で取得できます。ETLResult.to_dict() で簡単にシリアライズできます。

---

## 開発 / テスト時のヒント

- 自動 .env ロードが邪魔な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してからインポートしてください。
- news_collector._urlopen 等のネットワーク依存部はモックしやすい設計（テストで差し替え可能）になっています。
- DuckDB は :memory: を指定すればインメモリ DB としてテストできます（init_schema(":memory:")）。

---

必要に応じて README にサンプル .env.example、CI 実行方法や運用上の注意（証券会社 API の安全運用、発注の冪等制御、実運用時のリスク管理）を追加してください。README の拡張が必要なら、どの項目を詳述するか教えてください。