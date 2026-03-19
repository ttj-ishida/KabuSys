KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買／データプラットフォーム用ライブラリです。  
J-Quants API から市場データ・財務データ・カレンダーを取得し、DuckDB 上で ETL → ファクター計算 → シグナル生成 → 実行（発注／監査）といったワークフローをサポートします。研究（research）向け機能と本番（execution）向け機能が分離され、ルックアヘッドバイアス防止や冪等性・監査性を重視した設計になっています。

主な機能
---------
- J-Quants API クライアント（差分取得、ページング、トークン自動更新、レート制御）
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（日次差分更新・バックフィル・品質チェック）
- 特徴量計算（Momentum / Volatility / Value 等）
- 特徴量のクロスセクション Z スコア正規化ユーティリティ
- シグナル生成（コンポーネントスコア合成、Bear レジーム制御、BUY/SELL 判定、signals テーブルへの書き込み）
- ニュース収集（RSS フィード → raw_news、記事正規化・SSRF 対策・銘柄抽出）
- 市場カレンダー管理（営業日判定、next/prev_trading_day、夜間更新ジョブ）
- 発注／監査用の DB 構造（signal_events / order_requests / executions 等）
- 研究補助（将来リターン計算、IC 計算、ファクター統計サマリ）

セットアップ手順
----------------

1. Python と仮想環境
   - 推奨: Python 3.9+ を使用してください（コードは型ヒントに合わせて新しい機能も利用）。
   - 仮想環境を作成して有効化します。
     - macOS / Linux:
       - python -m venv .venv
       - source .venv/bin/activate
     - Windows:
       - python -m venv .venv
       - .venv\Scripts\activate

2. 依存パッケージのインストール
   - 必要な主な外部依存:
     - duckdb
     - defusedxml
   - インストール例:
     - pip install duckdb defusedxml
   - （パッケージ化されている場合は pip install -e . 等）

3. 環境変数の準備
   - プロジェクトルートに .env（または .env.local）を作成することで自動で読み込まれます。
   - 必須環境変数（config.Settings で必須とされるもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants の refresh token
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
     - SLACK_CHANNEL_ID — 通知先 Slack チャンネル ID
   - 任意／デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | …) — デフォルト: INFO
     - KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視 DB 等（デフォルト: data/monitoring.db）
   - .env の例:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - KABU_API_PASSWORD=your_kabu_password
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - DUCKDB_PATH=data/kabusys.duckdb
     - KABUSYS_ENV=development

   - 自動ロードを無効にする:
     - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みをスキップします（テスト用）。

4. DuckDB スキーマの初期化
   - Python REPL もしくはスクリプトから:
     - from kabusys.data.schema import init_schema
     - from kabusys.config import settings
     - conn = init_schema(settings.duckdb_path)
   - メモリ DB で試す場合:
     - conn = init_schema(":memory:")

使い方（主要ワークフロー例）
---------------------------

- DB 初期化（1回だけ）
  - Python:
    - from kabusys.data.schema import init_schema
    - from kabusys.config import settings
    - conn = init_schema(settings.duckdb_path)

- 日次 ETL（市場カレンダー・株価・財務データの差分取得）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)  # デフォルトで今日を対象に実行
  - result.to_dict() などで結果を確認

- 特徴量の構築
  - from kabusys.strategy import build_features
  - from datetime import date
  - n = build_features(conn, date(2024, 1, 1))  # target_date の features を作成

- シグナル生成
  - from kabusys.strategy import generate_signals
  - total = generate_signals(conn, date(2024, 1, 1))
  - generate_signals は signals テーブルに BUY/SELL を日付単位で置換（冪等）

- ニュース収集（RSS）
  - from kabusys.data.news_collector import run_news_collection
  - known_codes = {"7203", "6758", ...}  # 有効な銘柄コードセット
  - results = run_news_collection(conn, known_codes=known_codes)
  - results は各ソースの新規保存件数を返す

- カレンダー夜間更新ジョブ
  - from kabusys.data.calendar_management import calendar_update_job
  - saved = calendar_update_job(conn)

- jquants の手動トークン取得（必要に応じて）
  - from kabusys.data.jquants_client import get_id_token
  - token = get_id_token()  # settings.jquants_refresh_token を利用

注意事項・トラブルシューティング
--------------------------------
- DuckDB のバージョン:
  - スキーマや一部 SQL の互換性を保つため、比較的新しい DuckDB を使用してください。
- ネットワーク／API:
  - J-Quants API のレート制限を尊重するため、fetch 関数は内部でレート制御・リトライを行います。
  - 401 エラーは自動でリフレッシュを試みます（リフレッシュトークンが有効であることを確認してください）。
- RSS / ニュース:
  - fetch_rss は SSRF 対策・gzip サイズ制限・XML パース防御（defusedxml）を実施しています。RSS のレスポンスが大きすぎるとスキップされます。
- 環境変数:
  - 必須変数が不足していると Settings のプロパティで ValueError が発生します。.env.example を参考に .env を準備してください。
- 自動読み込み:
  - config モジュールはプロジェクトルート（.git または pyproject.toml を起点）を探索して .env/.env.local を自動読み込みします。挙動を停止するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- トランザクション:
  - 多くの DB 保存処理はトランザクションで保護されています。例外発生時は自動でロールバックするよう設計されていますが、DB ファイルの整合性・アクセス権には注意してください。

ディレクトリ構成（主要ファイル／モジュール）
----------------------------------------
（パッケージは src/kabusys 以下にあります）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数/設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（fetch/save）
    - schema.py             — DuckDB スキーマ定義と init_schema/get_connection
    - pipeline.py           — ETL パイプライン（run_daily_etl, run_prices_etl 等）
    - stats.py              — zscore_normalize 等の統計ユーティリティ
    - features.py           — zscore_normalize の再エクスポート
    - news_collector.py     — RSS 収集・前処理・DB 保存
    - calendar_management.py— 市場カレンダー管理（営業日判定・更新ジョブ）
    - audit.py              — 発注/約定の監査ログ DDL（signal_events 等）
    - pipeline.py           — ETL 実行ロジック（差分取得・バックフィル）
  - research/
    - __init__.py
    - factor_research.py    — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py— 将来リターン / IC / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py— features テーブル構築（正規化・フィルタ）
    - signal_generator.py   — final_score 計算、BUY/SELL シグナル生成
  - execution/
    - __init__.py
    - （発注実装はここに置く想定）
  - monitoring/
    - （監視・Slack 通知等の実装想定）

開発/拡張のヒント
-----------------
- 研究用コード（research/*.py）は本番実行層に依存しないように設計されています。DuckDB の prices_daily / raw_financials テーブルのみ参照することで、安全に解析が行えます。
- シグナル → 発注 → 約定 のフローは監査テーブルで UUID によるチェーンを保つ設計です。実際のブローカ接続は execution 層で実装してください。
- テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、テスト専用の環境変数を注入して動作検証すると安定します。

補足
----
本 README はコードベースの公開 API と主要なワークフローをまとめたものです。詳細な設計仕様はコード内の docstring（StrategyModel.md / DataPlatform.md 等参照）を参照してください。必要であればサンプルスクリプトやさらに詳細な運用手順（cron / CI ジョブ、Slack 通知設定、kabuステーション接続手順など）も追記できます。