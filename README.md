KabuSys
=======

KabuSys は日本株向けの自動売買プラットフォームのコアライブラリ群です。データ収集（J-Quants 等）、DuckDB ベースのデータレイヤー、特徴量計算（ファクター群）、ETL パイプライン、ニュース収集、品質チェック、監査ログなどを提供し、戦略実装や発注層と組み合わせて自動売買システムを構築するための基盤を担います。

概要
----

主な目的・設計方針:

- DuckDB を中心としたローカル DB に生データ／加工データ／特徴量／発注関連テーブルを保持。
- J-Quants API 経由で株価・財務・マーケットカレンダーを取得（レート制御・リトライ・自動トークンリフレッシュ実装）。
- RSS からのニュース収集と銘柄抽出（SSRF 対策・gzip 上限・トラッキング削除・冪等保存）。
- ETL は差分更新＋バックフィルで運用向けに堅牢化。品質チェックで欠損・スパイク・重複・日付不整合を検出。
- 研究用モジュールで IC / forward returns / ファクター計算を提供。外部依存を最小化して標準ライブラリ中心に実装。

主な機能一覧
------------

- データ取得・保存
  - J-Quants クライアント: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB へ冪等保存 (save_daily_quotes, save_financial_statements, save_market_calendar)
- ETL / パイプライン
  - run_daily_etl: 市場カレンダー → 株価 → 財務 → 品質チェック の一括処理
  - run_prices_etl / run_financials_etl / run_calendar_etl（差分更新・バックフィル対応）
- データ品質チェック
  - 欠損 / スパイク (急騰・急落) / 重複 / 日付不整合の検出
- ニュース収集
  - RSS フィード取得、前処理、raw_news への冪等保存、記事→銘柄紐付け
  - SSRF 対策・受信サイズ制限・トラッキングパラメータ除去・記事 ID は URL の SHA-256 による生成
- スキーマ管理
  - DuckDB のスキーマ定義と初期化（raw / processed / feature / execution / audit 層）
  - init_schema, init_audit_schema, init_audit_db など
- 研究・特徴量
  - モメンタム / ボラティリティ / バリュー ファクター計算
  - forward returns, IC（Spearman ρ）, factor summary, zscore_normalize
- 監査ログ
  - signal_events, order_requests, executions などトレーサビリティ用テーブルの初期化

セットアップ手順
--------------

前提

- Python 3.10 以上（コード内の型注釈や PEP604 の "X | Y" 構文を使用）
- pip が利用可能

1. リポジトリをクローン（あるいはパッケージソースを取得）

2. 仮想環境作成・有効化（任意だが推奨）
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

3. 必要パッケージのインストール
   - 最低限必要なサードパーティ:
     - duckdb
     - defusedxml
   - 例:
     ```
     pip install duckdb defusedxml
     ```
   - （パッケージ配布形式がある場合は `pip install -e .` 等を利用）

4. 環境変数設定 (.env の自動読み込み)
   - プロジェクトルートに .env / .env.local を配置すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを抑止）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD     : kabu ステーション API パスワード（発注層利用時）
     - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID      : 通知先 Slack チャンネル ID
   - 任意 / デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト INFO
     - KABUS_API_BASE_URL — デフォルト http://localhost:18080/kabusapi
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db

使い方（簡単な例）
-----------------

Python API 経由での基本操作例

- DuckDB スキーマ初期化:
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL 実行:
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を省略すると今日
  print(result.to_dict())
  ```

- J-Quants から株価取得（低レベル）:
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

- ニュース収集ジョブを実行:
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  print(res)
  ```

- 研究用: モメンタム計算 / IC 計算:
  ```python
  from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, zscore_normalize
  momentum = calc_momentum(conn, target_date=date(2024,1,31))
  fwd = calc_forward_returns(conn, target_date=date(2024,1,31))
  ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")
  ```

設定・環境変数の詳細
--------------------

- 自動 .env ロード
  - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）から .env と .env.local を順に読み込みます。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - テスト時などに自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- 主要な環境変数（要件）
  - JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン。jquants_client が ID トークンを取得するのに使用します。
  - KABU_API_PASSWORD (必須): kabu API のパスワード（発注連携を行う場合）。
  - SLACK_BOT_TOKEN (必須): Slack 通知に使用。
  - SLACK_CHANNEL_ID (必須): Slack 通知先チャンネル ID。
  - KABU_API_BASE_URL (任意): kabu API のベース URL。default: http://localhost:18080/kabusapi
  - DUCKDB_PATH (任意): DuckDB ファイルのデフォルトパス。default: data/kabusys.duckdb
  - SQLITE_PATH (任意): SQLite（監視用途等）ファイル。default: data/monitoring.db
  - KABUSYS_ENV (任意): development | paper_trading | live（本番運用時は live を設定）
  - LOG_LEVEL (任意): ログレベル（INFO 等）

データベース・スキーマ
--------------------

- init_schema(db_path) により以下層のテーブルが作成されます（代表例）:
  - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
  - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature Layer: features, ai_scores
  - Execution Layer: signals, signal_queue, orders, trades, positions, portfolio_performance
  - Audit 層（監査用）: signal_events, order_requests, executions（init_audit_schema／init_audit_db で初期化）

ディレクトリ構成（主要ファイル）
------------------------------

（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント、保存ユーティリティ
    - news_collector.py      — RSS 取得・正規化・DB保存・銘柄抽出
    - schema.py              — DuckDB スキーマ定義 / init_schema
    - stats.py               — zscore_normalize 等の統計ユーティリティ
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - features.py            — 公開インターフェース（zscore の再エクスポート）
    - calendar_management.py — market_calendar 管理・判定ユーティリティ
    - audit.py               — 監査ログテーブル初期化
    - etl.py                 — ETLResult の公開
    - quality.py             — 品質チェック（欠損・スパイク・重複・日付不整合）
  - research/
    - __init__.py
    - feature_exploration.py — forward returns, IC, factor_summary, rank
    - factor_research.py     — momentum / volatility / value の計算
  - strategy/                — 戦略関連パッケージ（エントリポイント等）
  - execution/               — 発注実装パッケージ（証券会社連携等）
  - monitoring/              — 監視・メトリクス用パッケージ

注意事項 / 運用上のヒント
-----------------------

- J-Quants のレート制限（120 req/min）に合わせた内部レート制御とリトライを実装済みですが、外部で大量取得を行う場合は注意してください。
- ETL の差分取得とバックフィルは API の後出し修正を吸収するために重要です（デフォルト backfill_days=3）。
- DuckDB のトランザクションや ON CONFLICT を利用して冪等性を保っていますが、外部から DB を触る場合はスキーマ制約を尊重してください。
- 本リポジトリはデータ取得・研究・監査・ETL・ニュース収集など基盤を提供します。発注（実際の金銭移動）や戦略のロジックは別層（strategy / execution）で実装し、paper_trading/live の挙動を切り替えて運用してください。

貢献・拡張
---------

- 研究用のファクター追加、品質チェックの拡張、ニュースソースの追加、監査項目の拡張などモジュール設計に沿って拡張可能です。
- テストを容易にするため、jquants_client の id_token 注入や news_collector._urlopen のモックポイントなどが用意されています。

ライセンス
----------

- （この README ではライセンス情報がソース内に明記されていないため、実プロジェクトでは適切なライセンスを明示してください）

お問い合わせ
------------

- 実装上の不明点や運用面の質問があれば、リポジトリの issue / 担当者に問い合わせてください。

以上。README に記載したサンプルコード・環境変数等は、実際の運用前にローカル環境で十分にテストしてください。