# KabuSys — 日本株自動売買システム

短い説明
- KabuSys は日本株向けのデータプラットフォームと戦略エンジンを備えた自動売買基盤です。  
  主に J-Quants からの市場データ収集（OHLCV・財務・カレンダー）、DuckDB によるデータ格納、研究用ファクター計算、特徴量生成、シグナル生成、ニュース収集、発注・監査のためのスキーマを提供します。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API 例）
- ディレクトリ構成（主要ファイルの説明）
- 環境変数（.env 例）

プロジェクト概要
- データ取得：J-Quants API から株価・財務・マーケットカレンダーを差分取得（レート制限・リトライ・トークン自動リフレッシュ対応）
- データ格納：DuckDB に Raw / Processed / Feature / Execution 層のテーブルを定義・保存（冪等保存）
- 研究：ファクター計算（モメンタム・バリュー・ボラティリティ等）、将来リターン / IC 計算、統計サマリー等
- 戦略：特徴量正規化・結合（features テーブル作成）、AI スコア統合 → final_score による BUY / SELL シグナル生成（signals テーブル）
- ニュース：RSS フィード収集 → raw_news 保存、記事から銘柄コード抽出
- カレンダー管理：JPX カレンダーを取得・営業日判定ユーティリティ提供
- ETL パイプライン：日次 ETL（calendar / prices / financials）＋品質チェック
- 監査：シグナル→発注→約定までトレースする監査テーブル群

機能一覧（要約）
- jquants_client
  - API 呼び出し、ページネーション、トークン管理、レスポンス保存（raw_prices / raw_financials / market_calendar）
- data.schema
  - DuckDB のスキーマ定義・初期化（init_schema）
- data.pipeline
  - 差分 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
- data.news_collector
  - RSS 取得・前処理・DB 保存・銘柄抽出・SSRF 対策・サイズ制限
- research
  - calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials 参照）
  - calc_forward_returns / calc_ic / factor_summary / rank
- strategy
  - build_features（特徴量作成 → features テーブルへ UPSERT）
  - generate_signals（features + ai_scores → signals に BUY/SELL を書き込む）
- calendar_management
  - 営業日判定 / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- 統計ユーティリティ
  - zscore_normalize（クロスセクション Z スコア正規化）
- 監査（audit）
  - signal_events / order_requests / executions など監査用テーブル

セットアップ手順（開発用）
- 前提
  - Python >= 3.10（PEP 604 の型合成（|）を使用）
  - DuckDB（Python パッケージ duckdb）
  - defusedxml（RSS パーシング安全対策）
  - ネットワーク接続（J-Quants API 使用時）
- インストール（例）
  - 仮想環境作成・有効化:
    - python -m venv .venv
    - source .venv/bin/activate  (Linux/macOS)
    - .venv\Scripts\activate     (Windows)
  - 依存インストール（プロジェクトに requirements.txt がない場合は最低限）:
    - pip install duckdb defusedxml
  - または（パッケージ配布がある場合）:
    - pip install -e .
- 環境変数
  - 必須:
    - JQUANTS_REFRESH_TOKEN
    - KABU_API_PASSWORD
    - SLACK_BOT_TOKEN
    - SLACK_CHANNEL_ID
  - 任意/デフォルト:
    - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
    - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
    - SQLITE_PATH (デフォルト: data/monitoring.db)
    - KABUSYS_ENV: development / paper_trading / live (デフォルト development)
    - LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト INFO)
  - 自動 .env ロードを無効化したい場合:
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DB 初期化
  - サンプル:
    - from kabusys.config import settings
      from kabusys.data.schema import init_schema
      conn = init_schema(settings.duckdb_path)
  - ":memory:" を使ってテスト用インメモリ DB も可能: init_schema(":memory:")

使い方（主要 API 例）
- init_schema（DuckDB スキーマ作成）
  - Python REPL / スクリプト例:
    - from kabusys.config import settings
      from kabusys.data.schema import init_schema
      conn = init_schema(settings.duckdb_path)
- 日次 ETL 実行（市場カレンダー / 株価 / 財務 の差分取得）
  - from datetime import date
    from kabusys.data.schema import init_schema
    from kabusys.data.pipeline import run_daily_etl
    conn = init_schema("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())
- 特徴量作成（features テーブル生成）
  - from datetime import date
    import duckdb
    from kabusys.strategy import build_features
    conn = duckdb.connect("data/kabusys.duckdb")
    n = build_features(conn, target_date=date(2024,1,1))
    print(f"features upserted: {n}")
- シグナル生成
  - from datetime import date
    import duckdb
    from kabusys.strategy import generate_signals
    conn = duckdb.connect("data/kabusys.duckdb")
    total = generate_signals(conn, target_date=date(2024,1,1), threshold=0.6)
    print(f"signals written: {total}")
- ニュース収集ジョブ（RSS 取得と保存）
  - from kabusys.data.news_collector import run_news_collection
    conn = duckdb.connect("data/kabusys.duckdb")
    results = run_news_collection(conn, known_codes={"7203","6758"})
    print(results)
- カレンダー更新ジョブ
  - from kabusys.data.calendar_management import calendar_update_job
    conn = duckdb.connect("data/kabusys.duckdb")
    saved = calendar_update_job(conn)
    print(f"calendar saved: {saved}")

注意点・運用メモ
- J-Quants API のレート制限（120 req/min）に合わせたスロットリングが組み込まれていますが、運用側でも実行頻度に配慮してください。
- run_daily_etl は品質チェックを行います。品質チェックで重大（error）な問題が検出された場合、ETLResult.has_quality_errors が True になりますが、ETL 自体は可能な限り継続して処理します。
- features / signals の生成処理はルックアヘッドバイアスに注意して target_date 時点のデータのみを使用する設計です。
- 自動環境変数ロード: パッケージはプロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動で読みます。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイルの説明）
- src/kabusys/
  - __init__.py
    - パッケージメタ（__version__ 等）
  - config.py
    - 環境変数読み込み・設定（Settings クラス）。.env 自動読み込み実装含む。
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（認証・取得・保存ユーティリティ）
    - schema.py
      - DuckDB のスキーマ定義と init_schema / get_connection
    - pipeline.py
      - ETL パイプライン（run_daily_etl など）
    - news_collector.py
      - RSS 取得・前処理・DB 保存・銘柄抽出
    - calendar_management.py
      - カレンダー更新 / 営業日ユーティリティ
    - features.py
      - zscore_normalize の公開再エクスポート
    - stats.py
      - zscore_normalize 等統計ユーティリティ
    - audit.py
      - 監査ログ用テーブル群（signal_events, order_requests, executions 等）
    - (その他)
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum / calc_volatility / calc_value
    - feature_exploration.py
      - calc_forward_returns / calc_ic / factor_summary / rank
  - strategy/
    - __init__.py
      - build_features, generate_signals を公開
    - feature_engineering.py
      - 特徴量作成ロジック（ユニバースフィルタ、Zスコア正規化、features への UPSERT）
    - signal_generator.py
      - final_score 計算、BUY/SELL シグナル生成、signals への書き込み
  - execution/
    - __init__.py
      - （将来的な発注/ブローカー連携モジュール用）
  - monitoring/
    - （監視・メトリクス用：現状は公開されているモジュールなしまたは未実装）
- README.md（このファイル）
- .env.example（後述）

.env.example（最低限の例）
- .env に以下を設定してください（値は実運用に合わせる）
  - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
  - KABU_API_PASSWORD=<kabu_api_password>
  - SLACK_BOT_TOKEN=<slack_bot_token>
  - SLACK_CHANNEL_ID=<slack_channel_id>
  - DUCKDB_PATH=data/kabusys.duckdb
  - KABUSYS_ENV=development
  - LOG_LEVEL=INFO

サポート / 貢献
- バグ報告や機能提案は Issue を作成してください。コントリビューションは歓迎します。
- 重要: 実際の発注（ライブ運用）を行う場合は、paper_trading 環境で十分なテストを行い、リスク管理（ストップロス・ポジション制限・監査）を確実に実装してください。

ライセンス
- プロジェクトに付属するライセンスファイルを参照してください（ここには記載がありません）。

以上。README に追加してほしい具体的なコマンドや CI / Docker / 実行スクリプトのテンプレート等があれば教えてください。必要に応じてサンプルスクリプトを作成します。