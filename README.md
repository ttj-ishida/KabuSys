KabuSys
======

日本株向けの自動売買（データプラットフォーム＋戦略）ライブラリです。  
DuckDB をローカル DB として使い、J-Quants API や RSS からデータを収集・加工し、特徴量作成→シグナル生成までのワークフローを提供します。

バージョン
---------
0.1.0

概要
----
KabuSys は以下の機能を持つモジュール群を提供します。

- データ収集・保存（J-Quants API 経由の株価・財務・市場カレンダー）
- RSS を使ったニュース収集と銘柄紐付け
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック連携）
- 研究用ファクター計算（モメンタム/ボラティリティ/バリュー 等）
- 特徴量エンジニアリング（正規化・ユニバースフィルタ）
- 戦略のシグナル生成（スコア統合・BUY/SELL の生成）
- マーケットカレンダー運用ユーティリティ・監査ログ（トレーサビリティ）
- 設定管理（.env 自動ロード、必須環境変数の取得）

主な機能一覧
--------------
- data.jquants_client: J-Quants API クライアント（レート制限／リトライ／トークン自動更新／DuckDB への冪等保存）
- data.news_collector: RSS 取得・前処理・raw_news 保存・銘柄抽出と紐付け
- data.schema: DuckDB の DDL（テーブル群・インデックス）と init_schema()
- data.pipeline: 日次 ETL（差分取得・backfill・品質チェック）と個別 ETL ジョブ
- data.calendar_management: market_calendar 周りの判定・next/prev_trading_day・夜間更新ジョブ
- data.stats / data.features: Z スコア正規化等の統計ユーティリティ
- research.factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算
- research.feature_exploration: 将来リターン・IC（Spearman）・統計サマリー
- strategy.feature_engineering: 生ファクター → 正規化 → features テーブルへの保存
- strategy.signal_generator: features + ai_scores を統合して final_score を計算 → signals を作成
- config: .env 自動ロード、必須設定の取得（settings オブジェクト）
- audit: 発注〜約定の監査ログ用スキーマ（監査/冗長トレーサビリティ）

動作要件
--------
- Python >= 3.10（型注記に | 演算子を使用）
- パッケージ例（最低限）:
  - duckdb
  - defusedxml
  - そのほか標準ライブラリのみで動く部分も多いですが、HTTP や DB 操作のため上記が必要です。

セットアップ手順
----------------

1. リポジトリをクローンし、仮想環境を作成・有効化する（例: venv / poetry / pipenv）。

2. 依存パッケージをインストールする（例）:
   - pip install duckdb defusedxml

3. 環境変数を設定する:
   - プロジェクトルートに .env ファイルを置くと自動で読み込まれます（config モジュール参照）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD      — kabu API のパスワード（execution 層利用時）
     - SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID       — Slack チャネル ID
   - 任意 / デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト "development"
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト "INFO"
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db
   - テスト等で自動 .env ロードを無効にする場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. DuckDB スキーマを初期化する（例）:
   - Python REPL またはスクリプトで:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

使い方（主要 API と例）
---------------------

- 設定を参照する:
    from kabusys.config import settings
    token = settings.jquants_refresh_token
    db_path = settings.duckdb_path

- DB スキーマ初期化:
    from kabusys.data.schema import init_schema
    conn = init_schema(settings.duckdb_path)

- 日次 ETL を実行する:
    from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn)  # target_date を省略すると今日
    print(result.to_dict())

- 特徴量作成（features テーブル作成）:
    from kabusys.strategy import build_features
    from datetime import date
    cnt = build_features(conn, date(2025, 1, 15))
    print(f"upserted features: {cnt}")

- シグナル生成:
    from kabusys.strategy import generate_signals
    from datetime import date
    total = generate_signals(conn, date(2025, 1, 15))
    print(f"signals generated: {total}")

- RSS ニュース収集（raw_news + news_symbols 保存）:
    from kabusys.data.news_collector import run_news_collection
    # known_codes は銘柄抽出に使う既知コードの集合（None の場合は抽出スキップ）
    res = run_news_collection(conn, known_codes={"7203", "6758"})
    print(res)

- カレンダー夜間更新ジョブ:
    from kabusys.data.calendar_management import calendar_update_job
    saved = calendar_update_job(conn)
    print(f"calendar saved: {saved}")

- 注意点:
  - 多くの関数は DuckDB の接続 (duckdb.DuckDBPyConnection) を受け取ります。init_schema() は DB を作成して接続を返しますが、get_connection() で既存DBに接続することも可能です。
  - J-Quants API 呼び出しは内部でレート制御とリトライを行います。401 時は自動でトークンをリフレッシュします。
  - ETL は差分取得 + backfill を行い、品質チェックは quality モジュール（本コードベースの一部）と連携します。

設定（.env / 環境変数）
--------------------
主な必須環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu API のパスワード（execution を使う場合）
- SLACK_BOT_TOKEN — Slack 通知の Bot トークン（通知を行う場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID（通知を行う場合）

その他（デフォルト値あり）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- LOG_LEVEL — デフォルト INFO
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml の存在を検出）にある .env / .env.local を自動で読み込みます。無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイル）
-------------------------------

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理（settings）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（fetch / save）
    - news_collector.py            — RSS 取得・前処理・保存・銘柄抽出
    - schema.py                    — DuckDB スキーマ定義と init_schema
    - stats.py                     — 統計ユーティリティ（zscore_normalize）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - features.py                  — features の公開インターフェース（再エクスポート）
    - calendar_management.py       — 市場カレンダー管理 / 更新ジョブ
    - audit.py                     — 監査ログ（signal_events, order_requests, executions）
    - (その他: quality.py など想定)
  - research/
    - __init__.py
    - factor_research.py           — momentum/volatility/value の計算
    - feature_exploration.py       — forward returns, IC, factor summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py       — 生ファクター正規化 → features
    - signal_generator.py          — final_score 計算 → signals テーブル生成
  - execution/                      — 発注・約定関連（パッケージとして存在）
  - monitoring/                     — 監視・通知用（パッケージとして存在）

開発メモ / 設計方針（抜粋）
-------------------------
- ルックアヘッドバイアス対策: ファクター計算・シグナル生成は target_date 時点の情報のみを使用する設計。
- 冪等性: DB 保存は ON CONFLICT / INSERT ... DO UPDATE / DO NOTHING を基本とし冪等性を確保。
- 安全性: RSS パーシングは defusedxml、SSRF 対策や受信サイズ制限（MAX_RESPONSE_BYTES）を実装。
- API 安定性: J-Quants リクエストはレート制限・指数バックオフ・トークン自動更新を実装。

ライセンス / 貢献
-----------------
（本 README では記載なし。リポジトリに LICENSE ファイルがあれば従ってください。）

問い合わせ
----------
コードや使い方に関して不明点があれば、リポジトリの issue やプロジェクトの担当者に問い合わせてください。

以上。README の内容はコードベースの注釈・ docstring に基づいて作成しています。実際に運用する際は .env.example を用意し、必要なテスト・監査を行ってください。