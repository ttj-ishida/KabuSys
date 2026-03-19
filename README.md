KabuSys
=======

日本株向けの自動売買プラットフォーム（ライブラリ）です。  
本リポジトリはデータ収集（J-Quants）、ETL、特徴量生成、戦略スコア算出、ニュース収集、監査記録などを含むデータパイプラインと策略レイヤーの実装を提供します。

主な用途
- J-Quants API から株価・財務・カレンダーを取得して DuckDB に永続化
- データ品質チェックと日次 ETL の実行
- 研究で算出した生ファクターから戦略用特徴量（features）を構築
- 特徴量と AI スコアを統合してシグナル（BUY/SELL）を生成
- RSS からニュースを収集して記事・銘柄紐付けを行う
- 発注/約定/ポジション管理のためのスキーマと監査ログ基盤

機能一覧
- データ取得・保存
  - J-Quants API クライアント（認証、ページネーション、レート制御、リトライ、トークン自動更新）
  - raw_prices / raw_financials / market_calendar の取得・保存（冪等）
- ETL パイプライン
  - 差分取得（最終取得日から差分・バックフィル）と保存
  - market_calendar の先読み
  - ETL 実行結果の集約（ETLResult）
- データベース
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution / Audit 層）
  - init_schema による初期化
- 研究 / 戦略
  - ファクター計算（momentum / volatility / value）
  - 特徴量作成（Z スコア正規化、ユニバースフィルタ、クリップ）
  - シグナル生成（コンポーネントスコアの合成、Bear レジーム抑制、エグジット判定）
- ニュース収集
  - RSS フェッチ（SSRF 対策、サイズ上限、XML パースの安全化）
  - 記事正規化・ID 生成・raw_news への冪等保存
  - テキスト内の銘柄コード抽出と news_symbols 保存
- 汎用ユーティリティ
  - クロスセクション Z スコア正規化（data.stats）
  - カレンダー管理（営業日判定、次/前営業日、営業日範囲取得）
  - 監査ログ（signal_events / order_requests / executions 等）

セットアップ手順（ローカル開発向け）
- 推奨 Python バージョン
  - Python 3.10 以上（typing の「|」や型ヒントを使用）
- 仮想環境作成（例）
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージ（最低限）
  - pip install --upgrade pip
  - pip install duckdb defusedxml
  - （必要に応じて）pip install -e . などでパッケージ化して利用
- 環境変数 / .env
  - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - 主な必要環境変数:
    - JQUANTS_REFRESH_TOKEN (必須): J-Quants の refresh token
    - KABU_API_PASSWORD (必須): kabuステーション API パスワード
    - KABU_API_BASE_URL (任意): デフォルト http://localhost:18080/kabusapi
    - SLACK_BOT_TOKEN (必須): Slack 通知用トークン
    - SLACK_CHANNEL_ID (必須): Slack チャンネル ID
    - DUCKDB_PATH (任意): DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
    - SQLITE_PATH (任意): 監視用 SQLite（デフォルト data/monitoring.db）
    - KABUSYS_ENV (任意): development / paper_trading / live（デフォルト development）
    - LOG_LEVEL (任意): DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
  - .env の書き方はシェル形式（KEY=VALUE）で、クォートや export 形式に対応します。

簡易 .env 例
（実際のトークンは機密情報のためソース管理しないでください）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

基本的な使い方（サンプル）
- DB 初期化
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")
    - ":memory:" を使うとインメモリ DB が作れます
- 日次 ETL 実行
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    res = run_daily_etl(conn, target_date=date.today())
    print(res.to_dict())
- 特徴量構築
  - from kabusys.strategy import build_features
    count = build_features(conn, date.today())
    print(f"features upserted: {count}")
- シグナル生成
  - from kabusys.strategy import generate_signals
    total = generate_signals(conn, date.today())
    print(f"signals written: {total}")
- RSS ニュース収集
  - from kabusys.data.news_collector import run_news_collection
    results = run_news_collection(conn, sources=None, known_codes=None)
    print(results)
- J-Quants からのデータ取得（上位 API）
  - from kabusys.data import jquants_client as jq
    records = jq.fetch_daily_quotes(date_from=..., date_to=...)
    jq.save_daily_quotes(conn, records)

注意点 / 設計方針（抜粋）
- 自動ロードされる .env はプロジェクトルート（.git や pyproject.toml があるディレクトリ）を基準に検索します。パッケージ配布後やテストで自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API のレート制限（120 req/min）を内部で尊重する実装になっています。
- DuckDB への書き込みは可能な限り冪等化（ON CONFLICT）されています。
- ルックアヘッドバイアスを避けるため、各計算は target_date 時点のデータのみを参照して設計されています。
- 外部ネットワーク入出力（RSS / API）には SSRF 対策やサイズ制限、XML パースの安全化を実装しています。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数管理（.env 自動読込 / Settings）
  - execution/                — 発注実行層（空のパッケージ）
  - strategy/
    - __init__.py
    - feature_engineering.py  — features テーブル作成（正規化・ユニバースフィルタ）
    - signal_generator.py     — final_score 計算・BUY/SELL シグナル生成
  - research/
    - __init__.py
    - factor_research.py      — momentum / volatility / value の計算
    - feature_exploration.py  — 将来リターン・IC・統計サマリー
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント + 保存ロジック
    - news_collector.py       — RSS 取得・前処理・保存・銘柄抽出
    - schema.py               — DuckDB スキーマ定義と init_schema
    - pipeline.py             — ETL（run_daily_etl など）
    - stats.py                — zscore_normalize 等の統計ユーティリティ
    - features.py             — data.stats の再エクスポート
    - calendar_management.py  — カレンダー更新・営業日判定ユーティリティ
    - audit.py                — 監査ログ用スキーマ（signal_events / order_requests / executions 等）
- pyproject.toml (想定)
- .env.example (推奨して作成すること)

ログ / デバッグ
- 環境変数 LOG_LEVEL でログレベルを制御できます（デフォルト INFO）。
- ランタイムの警告やトラブルは logger を通じて出力されます（各モジュールに logger が定義されています）。

よくある運用フロー（例）
1. init_schema でデータベースとテーブルを初期化
2. cron / Airflow / GitHub Actions で nightly に run_daily_etl を実行してデータを更新
3. 研究環境で factor_research を使って生ファクターを検証
4. build_features で戦略用特徴量を作成
5. generate_signals で日次シグナルを作成し、signal_queue へ投入
6. 実運用では execution 層が signal_queue を取って発注・約定を処理し、audit テーブルで追跡

開発 / 貢献
- 新機能追加やバグ修正はまず issue を作成してください。
- コードスタイル・型チェックを導入する場合は pyproject.toml に設定を追加してください。

免責
- 本プロジェクトは学術的/研究的サンプル実装です。実際の運用で使用する場合は、取引リスク・法令遵守・証券会社 API の仕様を十分に確認し、十分なテストを行ってください。

以上が README の概要です。必要であれば、セットアップのコマンド例（requirements.txt / dev-requirements）やより詳細な API 使用例、CI/CD やデプロイ手順を追記します。どの情報を優先で追加しますか？