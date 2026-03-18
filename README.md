# KabuSys

日本株向け自動売買プラットフォームのライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集、マーケットカレンダー管理、監査ログ（発注〜約定のトレーサビリティ）といった機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株に対するデータプラットフォームと自動売買基盤のためのモジュール群です。主な目的は以下です。

- J-Quants API からの株価日足・財務データ・マーケットカレンダーの取得と DuckDB への保存（冪等処理対応）
- RSS ベースのニュース収集とニュース⇄銘柄の紐付け
- ETL（差分更新・バックフィル）パイプラインとデータ品質チェック
- マーケットカレンダーを用いた営業日判定ユーティリティ
- 監査ログ（シグナル→発注→約定のトレース用テーブル）初期化ツール

設計上のポイント:
- API レート制限・リトライ・トークン自動リフレッシュ対応
- Look-ahead bias 対策のため fetched_at を UTC で記録
- DuckDB に対する冪等保存（ON CONFLICT を利用）
- ニュース収集での SSRF / XML Bomb / サイズ制限などのセキュリティ対策

---

## 機能一覧

- 環境変数・設定読み込み（自動でプロジェクトルートの `.env` / `.env.local` を読み込み）
- J-Quants クライアント
  - fetch_daily_quotes（株価日足）
  - fetch_financial_statements（四半期財務）
  - fetch_market_calendar（JPX カレンダー）
  - save_* 系関数で DuckDB に冪等保存
  - レートリミット、再試行、401 時のトークンリフレッシュ対応
- ETL
  - 差分更新（最終取得日からの差分、自動バックフィル）
  - run_daily_etl による一括 ETL + 品質チェック実行
- ニュース収集
  - RSS フィード取得（gzip/リダイレクト/SSRF 対策）
  - 記事ID は正規化 URL の SHA-256（先頭32文字）
  - raw_news や news_symbols への冪等保存
  - 銘柄コード抽出（4桁数字、known_codes に基づく）
- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job による夜間差分更新
- データ品質チェック
  - 欠損値、スパイク（前日比閾値）、重複、日付不整合を検出
  - QualityIssue 型で結果を返す（error / warning）
- 監査ログ初期化（signal_events / order_requests / executions 等の DDL とインデックス）

---

## 前提条件

- Python 3.9+（型注釈や一部の構文を想定）
- 必要ライブラリ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS 取得）

インストール方法は環境に応じて調整してください。最低限 pip で上記パッケージを入れてください。

例:
pip install duckdb defusedxml

（プロジェクト配布用に setup/pyproject がある場合は pip install -e . 等でインストール）

---

## 環境変数 / 設定

自動でプロジェクトルート（.git もしくは pyproject.toml がある親ディレクトリ）を探索し、`.env` と `.env.local` を読み込みます。自動ロードを無効化する場合:

- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください

主に使用する環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト development
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）

settings オブジェクト経由で Python から参照できます:
from kabusys.config import settings
settings.jquants_refresh_token

---

## セットアップ手順

1. リポジトリをクローンし、依存をインストール
   - pip install -r requirements.txt または個別に pip install duckdb defusedxml など

2. .env を作成
   - プロジェクトルートに `.env` を置くと自動読み込みされます
   - 例（最低限の例）:
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

3. DuckDB スキーマ初期化
   - Python REPL またはスクリプト内で:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - 監査ログ専用 DB を分ける場合:
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")

4. （任意）SQLite 等の監視 DB の設定（環境変数 SQLITE_PATH を設定）

---

## 使い方

以下は主要な利用例と API 呼び出し例です。

- DuckDB 初期化:
  from kabusys.data.schema import init_schema
  conn = init_schema(settings.duckdb_path)

- 日次 ETL 実行:
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())

  run_daily_etl は市場カレンダー取得 → 株価取得 → 財務取得 → 品質チェック を順に実行します。戻り値は ETLResult（取得件数・保存件数・品質問題等を含む）。

- J-Quants から単体データを取得して保存:
  from kabusys.data import jquants_client as jq
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)

  jquants_client は内部でレート制限・リトライ・トークンリフレッシュを行います。

- ニュース収集（RSS）:
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  # results は {source_name: 新規保存数} の辞書

- カレンダー更新バッチ:
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)

- 監査ログスキーマ初期化（既存の conn に追加）:
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

---

## 実装上の注意点 / 詳細

- 自動 .env 読み込み
  - OS 環境変数 > .env.local > .env の優先順位でロードされます
  - テストのため KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

- J-Quants クライアント
  - 1 分間 120 req を守るための RateLimiter を実装
  - リトライ: 最大 3 回（指数バックオフ）、HTTP 408/429/5xx をリトライ対象
  - 401 を受けた場合はリフレッシュトークンで自動的に id_token を更新して再試行（1 回のみ）
  - fetch_* 系はページネーションに対応

- ニュース収集
  - defusedxml を利用して XML 攻撃を防止
  - RSS フィードの受信サイズを MAX_RESPONSE_BYTES（10 MB）で制限
  - リダイレクト時にスキームとホストが private でないかチェック（SSRF 対策）
  - 記事ID は正規化 URL の SHA-256 先頭32文字で生成（utm 等は除去）

- データ品質チェック
  - 欠損・重複・スパイク・日付不整合の検査を提供
  - 各チェックは QualityIssue を返し、ETL はチェック結果に応じて呼び出し元が判断する設計

- マーケットカレンダー
  - DB にデータがあればそれを優先。未登録は曜日ベース（平日＝営業日）でフォールバック
  - next_trading_day / prev_trading_day は最大探索日数を設定して無限ループを防止

---

## ディレクトリ構成

プロジェクトの主要ファイルとディレクトリは下記の通りです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                (環境変数 / Settings 管理)
  - data/
    - __init__.py
    - jquants_client.py      (J-Quants API クライアント + 保存)
    - news_collector.py      (RSS ニュース取得・保存・銘柄抽出)
    - schema.py              (DuckDB スキーマ定義・初期化)
    - pipeline.py            (ETL パイプライン / run_daily_etl 等)
    - calendar_management.py (マーケットカレンダー管理)
    - audit.py               (監査ログ DDL / 初期化)
    - quality.py             (データ品質チェック)
  - strategy/
    - __init__.py            (戦略関連モジュールのためのプレースホルダ)
  - execution/
    - __init__.py            (注文実行関連モジュールのためのプレースホルダ)
  - monitoring/
    - __init__.py            (監視・モニタリング関連のプレースホルダ)

---

## 開発 / 貢献

- コントリビューションやバグ報告は PR / Issue でお願いします。
- テストや CI は現状の実装に合わせて追加してください。外部 API 呼び出し部分はモック可能な設計になっています（例: news_collector._urlopen の差し替え）。

---

## ライセンス

このリポジトリのライセンス情報はプロジェクトに付随する LICENSE ファイルを参照してください。

---

以上が本リポジトリの README です。必要であれば、セットアップ手順の OS 固有のコマンド（例: virtualenv / poetry / pipenv）や、より詳細な .env.example、テストの実行方法、CI 設定例なども追記できます。どの項目を詳しく書き足しましょうか？