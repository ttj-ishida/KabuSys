KabuSys
======

バージョン: 0.1.0

概要
----
KabuSys は日本株向けの自動売買（データプラットフォーム + 戦略）ライブラリです。  
主な目的は次のとおりです。

- J-Quants API からのデータ取得（株価・財務・マーケットカレンダー）
- DuckDB を使ったデータレイク（Raw / Processed / Feature / Execution 層）の管理
- 研究用ファクター計算・特徴量エンジニアリング
- 戦略シグナル生成（BUY / SELL）
- RSS ベースのニュース収集と銘柄紐付け
- カレンダー管理・ETL パイプライン・品質チェック等の運用ユーティリティ

主な機能
--------
- データ取得/API クライアント
  - J-Quants API クライアント（認証・リトライ・レートリミット・ページネーション対応）
  - データ保存（raw_prices / raw_financials / market_calendar など）を冪等に保存する save_* 関数
- ETL / データ管理
  - duckdb スキーマ初期化（init_schema）
  - 差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - カレンダー管理（営業日判定・前後営業日探索・calendar_update_job）
  - 品質チェック（quality モジュール：欠損・スパイク等の検出。コード参照）
- データ処理・特徴量
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_engineering: ファクター正規化（Z-score）・ユニバースフィルタ・features テーブルへの保存
  - data.stats.zscore_normalize（再利用可能な統計ユーティリティ）
- 戦略
  - signal_generator: features / ai_scores から最終スコアを計算して BUY/SELL シグナル生成
  - build_features / generate_signals が公開 API
- ニュース収集
  - RSS 取得 → 前処理 → raw_news に冪等保存 → 銘柄抽出・news_symbols に紐付け
  - SSRF 対策・サイズ制限・トラッキングパラメータ除去等の安全対策を備える
- 監査・実行レイヤ
  - スキーマに execution / audit 用テーブルを含む（signal_queue, orders, trades, executions 等）
- 設定管理
  - 環境変数 / .env ファイルから設定を読み込む settings（自動ロード機能）
  - KABUSYS_ENV（development / paper_trading / live）やログレベルの検証

セットアップ手順
----------------

前提
- Python 3.10+（コード内で型注釈に X | Y を利用しているため）
- pip が利用できること

1. リポジトリをクローン / パッケージを配置
   - 開発時: プロジェクトルートをチェックアウトし、src/ 配下がパッケージルートになります。

2. 依存パッケージのインストール（例）
   - 最低限必要な外部依存:
     - duckdb
     - defusedxml
   - 開発環境では下記のようにインストールします（プロジェクトに requirements.txt があればそちらを使ってください）:
     - pip install duckdb defusedxml
   - 開発インストール（プロジェクトルートで）:
     - pip install -e .

3. 環境変数設定
   - プロジェクトルートに .env または .env.local を作成してください（config モジュールは自動でプロジェクトルートを探索して読み込みます）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN   — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD       — kabuステーション API パスワード
     - SLACK_BOT_TOKEN         — Slack 通知に使う Bot トークン
     - SLACK_CHANNEL_ID        — Slack 通知先チャンネル ID
   - 任意（デフォルトがあるもの）:
     - KABUSYS_ENV             — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL               — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると自動 .env 読み込みを無効化
     - KABU_API_BASE_URL       — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH             — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH             — SQLite（監視 DB 等、デフォルト: data/monitoring.db）

   - .env のパースはシェル互換（export KEY=val、クォート、コメントの扱い等）に対応しています。

4. DuckDB スキーマ初期化
   - Python REPL / スクリプトで次を実行して初期化します:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")  # ディレクトリは自動作成されます

使い方（主要なワークフロー例）
----------------------------

1) DuckDB の初期化（1回だけ）
- 例:
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")

2) 日次 ETL（市場カレンダー・株価・財務の差分取得 + 品質チェック）
- 例:
  - from datetime import date
  - from kabusys.data.schema import get_connection, init_schema
  - from kabusys.data.pipeline import run_daily_etl
  - conn = init_schema("data/kabusys.duckdb")
  - result = run_daily_etl(conn, target_date=date.today())
  - print(result.to_dict())

3) 特徴量ビルド（戦略用 features テーブル作成）
- 例:
  - from datetime import date
  - import duckdb
  - from kabusys.strategy import build_features
  - conn = duckdb.connect("data/kabusys.duckdb")
  - count = build_features(conn, target_date=date.today())
  - print(f"features upserted: {count}")

4) シグナル生成（features と ai_scores から signals へ）
- 例:
  - from datetime import date
  - import duckdb
  - from kabusys.strategy import generate_signals
  - conn = duckdb.connect("data/kabusys.duckdb")
  - total = generate_signals(conn, target_date=date.today())
  - print(f"signals created: {total}")

5) ニュース収集（RSS）
- 例:
  - from kabusys.data.news_collector import run_news_collection
  - conn = duckdb.connect("data/kabusys.duckdb")
  - known_codes = {"7203", "6758", ...}  # 有効な銘柄コードセット
  - results = run_news_collection(conn, known_codes=known_codes)
  - print(results)

6) カレンダー更新バッチ
- 例:
  - from kabusys.data.calendar_management import calendar_update_job
  - conn = duckdb.connect("data/kabusys.duckdb")
  - saved = calendar_update_job(conn)
  - print(f"calendar saved: {saved}")

設定・挙動に関する補足
- 自動 .env 読み込み:
  - config.py はプロジェクトルート（.git または pyproject.toml がある場所）を起点に .env / .env.local を自動読み込みします。
  - 読み込み順: OS 環境 > .env.local (> override) > .env
  - テスト等で自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- settings API:
  - kabusys.config.settings 経由で各種設定値へアクセスできます（例: settings.jquants_refresh_token）。
  - KABUSYS_ENV は "development", "paper_trading", "live" のいずれかでなければ例外になります。
- 冪等性:
  - 多くの save_* 関数（データ保存）は ON CONFLICT や INSERT ... DO UPDATE / DO NOTHING を使い冪等に設計されています。
- セキュリティ設計:
  - RSS 収集は SSRF 対策、XML パースは defusedxml の使用、レスポンスサイズ制限などを実装しています。
  - J-Quants クライアントはレート制御（120 req/min）やリトライ、401 時のトークン自動リフレッシュを備えます。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要ファイルと簡単な目的説明です。

- __init__.py
  - パッケージバージョンと __all__ を定義
- config.py
  - 環境変数/設定の読み込みと検証（settings オブジェクト）
- data/
  - __init__.py
  - jquants_client.py        — J-Quants API クライアント（fetch_* / save_*）
  - news_collector.py       — RSS ニュース収集・前処理・DB 保存
  - schema.py               — DuckDB スキーマ定義・init_schema / get_connection
  - stats.py                — zscore_normalize 等の統計ユーティリティ
  - pipeline.py             — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py  — カレンダー管理・カレンダー更新ジョブ
  - audit.py                — 監査ログ / 発注トレーサビリティ用スキーマ
  - features.py             — data.stats の再エクスポート
- research/
  - __init__.py
  - factor_research.py      — momentum / volatility / value のファクター計算
  - feature_exploration.py  — 将来リターン計算 / IC / 統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py  — ファクター正規化・features テーブルへの UPSERT
  - signal_generator.py     — final_score 計算・BUY/SELL シグナル生成・signals への保存
- execution/
  - __init__.py
  - （発注・約定・ポジション管理の実装を想定）
- monitoring/
  - （監視・アラート・Slack 通知などの実装を想定）

開発・運用メモ
--------------
- DuckDB のファイルはデフォルトで data/kabusys.duckdb に作成されます。必要に応じて DUCKDB_PATH を設定してください。
- ログは標準的な logging を利用しているため、アプリ側でロガー設定（ハンドラ・レベル）を行ってください。
- production（live）環境では KABUSYS_ENV=live を設定してミスを防ぐバリデーションを有効にしてください。
- J-Quants API のリクエスト上限（120 req/min）を守る設計ですが、スケジュール運用時には API トークンや並列度に注意してください。

ライセンス・貢献
----------------
- この README ではライセンスファイルは含めていません。リポジトリの LICENSE を参照してください。
- バグ修正・機能追加の PR を歓迎します。テスト、型チェック、ドキュメントを併せて追加してください。

問い合わせ
----------
- ソースコードにドキュメントコメントを多く含めています。実装や API の詳細は該当モジュール（data/jquants_client.py, strategy/signal_generator.py 等）の docstring を参照してください。

以上。必要であれば、README に含めるサンプル .env.example や具体的なスクリプト（systemd / cron 用の起動スクリプト等）を追加で作成します。どの情報を追加したいか教えてください。