KabuSys — 日本株自動売買プラットフォーム (README)
=======================================

概要
----
KabuSys は日本株のデータ収集・特徴量作成・シグナル生成・発注管理までを想定した自動売買基盤のコアライブラリです。  
主に以下レイヤーを備えています。

- データ収集 (J-Quants API 経由で日足・財務・市場カレンダー・RSS ニュース)
- ETL パイプライン（差分取得・保存・品質チェック）
- 研究 (factor 計算、特徴量探索、Z スコア正規化)
- 戦略（特徴量合成・スコア計算・BUY/SELL シグナル生成）
- 実行/監査（DB スキーマ、signals / order / executions / positions 等の定義）

このリポジトリはライブラリ実装が主で、実行用の CLI やデーモンは別途ラッパーで組み合わせて運用します。

主な機能
---------
- J-Quants API クライアント（ページネーション対応、レートリミット、トークン自動リフレッシュ、リトライ）
- DuckDB ベースの DB スキーマ定義と初期化（init_schema）
- ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- ニュース収集（RSS 取得・SSRF 対策・前処理・DB 保存）
- 研究用ファクター計算（momentum / volatility / value）
- 特徴量作成（build_features: 正規化・ユニバースフィルタ・日付単位で冪等保存）
- シグナル生成（generate_signals: コンポーネントスコア、AI スコア統合、BUY/SELL 生成）
- マーケットカレンダー管理（営業日判定・next/prev_trading_day 等）
- 監査ログ設計（signal_events, order_requests, executions 等のDDL、トレーサビリティ配慮）
- 汎用統計ユーティリティ（zscore_normalize 等）

セットアップ
-----------
注意: 以下はこのコードベースを開発/実行するための一般的な手順です。プロジェクトに pyproject.toml / requirements.txt がある場合はそれに合わせてください。

1. Python 環境
   - 推奨: Python 3.9+（コードは型注釈を利用しています）
   - 仮想環境の作成:
     - python -m venv .venv
     - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - 最低限必要と想定されるパッケージ:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - (プロジェクト配布版があれば) pip install -e .

3. 環境変数 / .env
   - 設定は環境変数またはプロジェクトルートの .env / .env.local から自動読み込みされます（src/kabusys/config.py）。
   - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用）。
   - 必須環境変数（Settings で require されるもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API のパスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意 / デフォルトあり:
     - KABU_API_BASE_URL — デフォルト "http://localhost:18080/kabusapi"
     - DUCKDB_PATH — デフォルト "data/kabusys.duckdb"
     - SQLITE_PATH — デフォルト "data/monitoring.db"
     - KABUSYS_ENV — one of development / paper_trading / live (default: development)
     - LOG_LEVEL — one of DEBUG/INFO/WARNING/ERROR/CRITICAL (default: INFO)
   - .env の書式やコメント処理は config._parse_env_line が処理します。 .env.example を参照してください（存在する場合）。

4. DB 初期化
   - DuckDB の初期スキーマ作成:
     - Python REPL またはスクリプト内で:
       from kabusys.data.schema import init_schema, get_connection
       conn = init_schema("data/kabusys.duckdb")
     - init_schema は親ディレクトリを自動作成します。":memory:" も使用可能。

基本的な使い方（サンプル）
------------------------

以下はライブラリ API を使う最小例です。運用用のラッパー（CLI や cron ジョブ）を別途作成して利用してください。

1. DB を初期化して日次 ETL を実行する
   - 例:
     from kabusys.data.schema import init_schema
     from kabusys.data.pipeline import run_daily_etl
     conn = init_schema("data/kabusys.duckdb")
     result = run_daily_etl(conn)  # target_date を指定可能
     print(result.to_dict())

2. 特徴量（features）を作成する
   - 特定の日付の features を構築:
     from kabusys.strategy import build_features
     from kabusys.data.schema import get_connection
     import duckdb
     conn = get_connection("data/kabusys.duckdb")
     build_count = build_features(conn, target_date=date(2025, 1, 31))
     print(f"features built: {build_count}")

3. シグナル生成
   - features と ai_scores を参照して signals を作成:
     from kabusys.strategy import generate_signals
     conn = get_connection("data/kabusys.duckdb")
     total = generate_signals(conn, target_date=date(2025, 1, 31))
     print(f"signals written: {total}")

4. ニュース収集ジョブ（RSS）
   - fetch + DB 保存 + 銘柄紐付け:
     from kabusys.data.news_collector import run_news_collection
     conn = get_connection("data/kabusys.duckdb")
     known_codes = {"7203", "6758", ...}  # 既知の銘柄コードセット
     results = run_news_collection(conn, sources=None, known_codes=known_codes)
     print(results)

5. カレンダー更新ジョブ
   - calendar_update_job を夜間で実行:
     from kabusys.data.calendar_management import calendar_update_job
     conn = get_connection("data/kabusys.duckdb")
     saved = calendar_update_job(conn)
     print(f"calendar saved: {saved}")

注記（設計上の重要点）
---------------------
- 冪等性: DB 保存処理は ON CONFLICT / DO UPDATE や INSERT … ON CONFLICT DO NOTHING として冪等に実装されています。日付単位での置換 (DELETE+INSERT) を行う箇所もあります。
- ルックアヘッドバイアス対策: ファクター・シグナル生成は target_date 時点のデータのみを用いる設計になっています（future data を参照しない）。
- 安全対策: RSS 取得は SSRF 対策、XML 攻撃対策（defusedxml）、応答サイズ上限などを実装しています。J-Quants API はレートリミットとリトライ/トークンリフレッシュを考慮しています。
- 実行層（execution）や監査（audit）はスキーマが用意されているため、外部ブローカーとの連携ロジックを実装すればトレース可能なワークフローになります。

ディレクトリ構成
-----------------
（主要ファイル・モジュール抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得 + 保存）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - news_collector.py      — RSS 収集・前処理・保存
    - schema.py              — DuckDB スキーマ定義 / init_schema
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - features.py            — features の再エクスポート
    - calendar_management.py — 市場カレンダー管理
    - audit.py               — 監査ログ DDL（signal_events / order_requests / executions 等）
  - research/
    - __init__.py
    - factor_research.py     — momentum / volatility / value の計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — build_features: ファクター正規化・ユニバースフィルタ
    - signal_generator.py    — generate_signals: final_score 計算と信号生成
  - execution/               — 発注 / 実行関連（初期状態）
  - monitoring/              — 監視・メトリクス（初期状態）

付録: よく使う API
------------------
- settings = kabusys.config.settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.slack_bot_token, settings.slack_channel_id, settings.duckdb_path, settings.env, settings.log_level, settings.is_live 等

- DB / スキーマ
  - init_schema(db_path) -> DuckDB 接続（スキーマ作成）
  - get_connection(db_path) -> DuckDB 接続（既存 DB）

- ETL
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)

- 研究 / 戦略
  - kabusys.research.calc_momentum / calc_volatility / calc_value
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold=0.6, weights=None)

サポート / 開発
----------------
- テストや CI 実行時は環境変数自動読み込みを無効化することを推奨します:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 実運用では KABUSYS_ENV を paper_trading / live に設定し、ログレベルや発注先の挙動を切り替えてください。

ライセンス / その他
-------------------
- 本 README はコードベースに基づく簡易ドキュメントです。実運用前に各モジュールのロジック、外部 API の仕様、セキュリティ要件を十分にレビューしてください。

もし README に追加したい具体的な実行例（スクリプト、Docker-compose、systemd ユニットファイル等）があれば、それに合わせて追記します。