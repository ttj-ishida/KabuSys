KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けのデータ取得・ETL・特徴量生成・シグナル生成・発注監査までを想定したライブラリ群です。  
主な設計ポイントは以下です。

- DuckDB をデータ層として利用し、Raw → Processed → Feature → Execution の多層スキーマを提供
- J-Quants API から株価・財務・カレンダーを取得するクライアント（ページング・レート制御・トークン自動リフレッシュ対応）
- ニュース収集（RSS）→ 前処理 → DB 保存 → 銘柄抽出の一連処理
- 研究用モジュール（ファクター計算・特徴量探索）と戦略モジュール（特徴量正規化・シグナル生成）
- 再現性・冪等性を重視（ETL 保存は ON CONFLICT / UPSERT、日次処理は日付単位の置換）
- SSRF・XML Bomb 等への防御（news_collector）や API レート制御・リトライ等の堅牢化

機能一覧
--------
主要機能（モジュール別）

- kabusys.config
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 環境変数のラップ（必須変数チェック、環境/ログレベル判定など）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存関数）
  - schema: DuckDB スキーマ定義と初期化（init_schema）
  - pipeline: ETL（run_daily_etl 等）、差分取得／バックフィルの自動化、品質チェック呼び出しフック
  - news_collector: RSS 収集、前処理、raw_news 保存、銘柄紐付け
  - calendar_management: 市場カレンダー管理・営業日判定
  - stats: Zスコア正規化等の統計ユーティリティ
- kabusys.research
  - factor_research: モメンタム / バリュー / ボラティリティ等のファクター計算（prices_daily/raw_financials を参照）
  - feature_exploration: 将来リターン、IC 計算、統計サマリー等の研究用関数
- kabusys.strategy
  - feature_engineering.build_features: 研究で計算した raw factor を正規化・フィルタして features テーブルへ保存
  - signal_generator.generate_signals: features / ai_scores / positions を統合して BUY/SELL シグナルを生成・signals テーブルへ保存
- kabusys.execution / monitoring（発注・監視周りの骨組み / 監査ログモジュールあり）

セットアップ手順
----------------

1. 前提

   - Python 3.10 以上（型アノテーション（X | None）等を使用）
   - DuckDB（Python パッケージ）
   - defusedxml（RSS パースの安全化）
   - （必要に応じて）その他運用で使うライブラリ（例: Slack 通知ライブラリ等）

2. 仮想環境作成（推奨）

   - venv 例:
     python -m venv .venv
     source .venv/bin/activate

3. 依存パッケージインストール（最小例）

   pip install duckdb defusedxml

   （プロジェクトが requirements.txt を持つ場合はそちらを使用してください）

4. 環境変数設定

   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数（config.Settings によりアクセス）:

     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）

   - オプション / 既定値:

     - KABUSYS_ENV — 実行環境（development / paper_trading / live）、既定: development
     - LOG_LEVEL — ログレベル（DEBUG, INFO, ...）、既定: INFO
     - DUCKDB_PATH — DuckDB ファイルパス、既定: data/kabusys.duckdb
     - SQLITE_PATH — 監視用 SQLite パス、既定: data/monitoring.db

   - サンプル .env（例）
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456789
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

5. DB 初期化

   Python REPL またはスクリプトで DuckDB スキーマを作成します:

   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

使い方（主要ワークフロー例）
--------------------------

以下はライブラリ API を直接呼び出す最小の例です。運用ではジョブスケジューラ（cron 等）やワーカーでこれらを呼びます。

1. DuckDB の初期化（1回）

   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

2. 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）

   from kabusys.data.pipeline import run_daily_etl
   from kabusys.data.schema import init_schema
   from datetime import date

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())

   - run_daily_etl は内部で J-Quants API 呼び出し（jquants_client）→ 保存（save_*）を行います。
   - id_token を外部から注入してテスト可能。

3. 特徴量作成（戦略用）

   from kabusys.strategy import build_features
   from kabusys.data.schema import get_connection
   from datetime import date

   conn = get_connection("data/kabusys.duckdb")
   n = build_features(conn, target_date=date.today())
   print(f"features upserted: {n}")

4. シグナル生成

   from kabusys.strategy import generate_signals
   from kabusys.data.schema import get_connection
   from datetime import date

   conn = get_connection("data/kabusys.duckdb")
   count = generate_signals(conn, target_date=date.today(), threshold=0.6)
   print(f"signals generated: {count}")

5. ニュース収集ジョブ（RSS）

   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import get_connection
   from datetime import date

   conn = get_connection("data/kabusys.duckdb")
   known_codes = {"7203","6758", ...}  # 既知の銘柄コードセット
   res = run_news_collection(conn, sources=None, known_codes=known_codes)
   print(res)  # {source_name: saved_count, ...}

注意点 / 運用メモ
----------------

- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- J-Quants API にはレート制限・リトライロジックを実装済みですが、クライアント側から過度な同時呼び出しを行わないでください。
- news_collector は SSRF・大量データ対策（最大レスポンスサイズ・gzip 解凍後の上限等）を組み込んでいますが、運用では監視を行ってください。
- DuckDB のファイルはバックアップ/スナップショットを検討してください。大容量データを扱う場合はディスク容量とIOを監視してください。
- run_daily_etl 等は独立したステップごとに例外を捕捉してエラー情報を ETLResult.errors に蓄積します。エラー発生時の挙動は呼び出し側でログや通知を行ってください。

ディレクトリ構成
----------------

主要なソースツリー（src/kabusys/ 以下）:

- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py        — J-Quants API クライアント（取得/保存）
  - news_collector.py       — RSS 取得・前処理・DB 保存
  - schema.py               — DuckDB スキーマ定義と init_schema / get_connection
  - pipeline.py             — ETL パイプライン（run_daily_etl 等）
  - stats.py                — zscore_normalize 等
  - calendar_management.py  — 市場カレンダー管理
  - audit.py                — 監査ログ用 DDL（signal_events, order_requests, executions 等）
  - features.py             — feature 公開ラッパ
- research/
  - __init__.py
  - factor_research.py      — momentum/value/volatility ファクター計算
  - feature_exploration.py  — 将来リターン / IC / サマリー
- strategy/
  - __init__.py
  - feature_engineering.py  — build_features
  - signal_generator.py     — generate_signals
- execution/                 — 発注実装用の骨組み（空の __init__ など）
- monitoring/                — 監視・メトリクス収集のための補助モジュール（存在する場合）

（上記はコードベースから抽出した主要ファイル群です。）

ライセンス・貢献
----------------
- 本リポジトリにライセンスファイルが含まれている場合はそちらに従ってください。
- バグ報告や改善提案は Issue を通じてお願いします。パッチは Pull Request を歓迎します。

付録: 参考 API（抜粋）
--------------------

- init_schema(db_path) → DuckDB 接続（スキーマ作成）
- get_connection(db_path) → 既存 DB へ接続
- run_daily_etl(conn, target_date, ...) → 日次 ETL 実行（ETLResult を返す）
- build_features(conn, target_date) → features テーブル生成
- generate_signals(conn, target_date, threshold, weights) → signals 生成
- run_news_collection(conn, sources, known_codes) → RSS 収集＆保存

質問やドキュメント補足が必要であれば、どの機能について詳しく知りたいかを教えてください。必要に応じてサンプルコードや運用ガイド（cron 設定例、Slack 通知例など）を追加します。