KabuSys — 日本株自動売買システム（README 日本語版）

プロジェクト概要
- KabuSys は日本株向けのデータプラットフォームと戦略パイプラインを備えた自動売買フレームワークです。
- 主な機能は「データ収集（J-Quants）→ ETL → 特徴量計算 → シグナル生成 → 発注監査」の流れをサポートします。
- DuckDB をデータ層として利用し、研究（research）モジュールと運用（strategy / execution）モジュールを分離した設計です。
- ルックアヘッドバイアスや冪等性（idempotency）、API レート制限・リトライやセキュリティ（RSS の SSRF 対策等）を考慮した実装になっています。

主な機能一覧
- データ取得 / 保存
  - J-Quants API クライアント（価格、財務、マーケットカレンダー） — jquants_client
  - RSS ニュース収集と記事→銘柄紐付け — news_collector
  - DuckDB スキーマ定義・初期化 — data.schema
- ETL パイプライン
  - 日次差分 ETL（市場カレンダー／株価／財務） — data.pipeline.run_daily_etl
  - 差分取得・バックフィル・品質チェック統合
- 特徴量・研究
  - ファクター計算（Momentum / Volatility / Value 等） — research.factor_research
  - 特徴量探索（IC, forward returns, summary 等） — research.feature_exploration
  - Zスコア正規化ユーティリティ — data.stats / data.features
- 戦略
  - 特徴量の正規化・合成と features テーブル保存 — strategy.feature_engineering.build_features
  - features と ai_scores を統合して売買シグナルを生成 → signals テーブルへ保存 — strategy.signal_generator.generate_signals
- 実行 / 監査（基盤）
  - DuckDB 上の execution 用スキーマ（signals, orders, trades, positions, audit 等）
  - 監査ログテーブル（signal_events / order_requests / executions）設計

必要な環境・依存
- Python 3.8+（型ヒントと標準ライブラリを利用）
- 必須 Python パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリのみで動作する部分が多いですが、実行環境では上記パッケージをインストールしてください。

セットアップ手順
1. リポジトリをクローン
   - git clone <リポジトリURL>
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （必要に応じて他のパッケージを追加）
4. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くことで自動読み込みされます（優先度: OS 環境 > .env.local > .env）。
   - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 必須環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabu API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
     - SLACK_CHANNEL_ID — Slack 通知先チャンネルID（必須）
   - 任意 / デフォルトあり:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG / INFO / ...（デフォルト: INFO）
     - KABU_API_BASE_URL — kabusapi のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
5. データベース初期化
   - Python REPL またはスクリプトで DuckDB スキーマを初期化します。例:
     - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

使い方（概要と例）
- 基本的なワークフロー
  1. DuckDB のスキーマ初期化（初回のみ）
  2. 日次 ETL を実行して価格・財務・カレンダーデータを取得・保存
  3. feature を構築（build_features）
  4. シグナル生成（generate_signals）
  5. execution 層で発注 → 実行結果を audit/実行ログへ保存

- 例: Python スクリプトから日次ETL 実行
  - from kabusys.data.schema import init_schema, get_connection
    from kabusys.data.pipeline import run_daily_etl
    conn = init_schema("data/kabusys.duckdb")  # 既存DBはスキップして接続
    result = run_daily_etl(conn)
    print(result.to_dict())

- 例: 特徴量作成
  - from kabusys.data.schema import get_connection
    from kabusys.strategy import build_features
    import duckdb, datetime
    conn = duckdb.connect("data/kabusys.duckdb")
    cnt = build_features(conn, datetime.date(2025, 1, 15))
    print(f"features upserted: {cnt}")

- 例: シグナル生成
  - from kabusys.strategy import generate_signals
    import duckdb, datetime
    conn = duckdb.connect("data/kabusys.duckdb")
    total = generate_signals(conn, datetime.date(2025, 1, 15))
    print(f"signals written: {total}")

- 例: RSS ニュース収集ジョブ
  - from kabusys.data.news_collector import run_news_collection
    from kabusys.data.schema import get_connection
    conn = get_connection("data/kabusys.duckdb")
    results = run_news_collection(conn, known_codes={'7203','6758'})
    print(results)

環境変数（サンプル .env）
- .env（プロジェクトルート）
  - JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
  - KABU_API_PASSWORD=あなたの_kabu_api_password
  - SLACK_BOT_TOKEN=xoxb-...
  - SLACK_CHANNEL_ID=C01234567
  - DUCKDB_PATH=data/kabusys.duckdb
  - KABUSYS_ENV=development
  - LOG_LEVEL=INFO

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py  — 環境変数/設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得・保存）
    - news_collector.py      — RSS 収集・保存・紐付け
    - schema.py              — DuckDB スキーマ定義 / init_schema
    - stats.py               — Zスコア等汎用統計関数
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理
    - features.py            — data.stats の再エクスポート
    - audit.py               — 発注・約定の監査ログ定義
    - (その他)
  - research/
    - __init__.py
    - factor_research.py     — momentum/volatility/value の計算
    - feature_exploration.py — forward returns / IC / summaries
  - strategy/
    - __init__.py
    - feature_engineering.py — features テーブル構築（正規化・フィルタ）
    - signal_generator.py    — final_score 計算とシグナル生成
  - execution/               — 発注・実行モジュール（未実装ファイル含む）
  - monitoring/              — 監視・メトリクス用（DB: sqlite 等）

設計上の注意点（要点）
- 自動ロードされる .env はプロジェクトルート（.git or pyproject.toml を探索）から読み込みます。テストなどで無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ETL / feature / signal の各処理は「target_date 時点で利用可能なデータのみ」を用いる設計で、ルックアヘッドバイアスを避けます。
- 多くの DB 操作は冪等（ON CONFLICT / トランザクション）で実装されています。
- J-Quants API 呼び出しはレート制限とリトライ・トークン自動更新を備えています。
- RSS 収集は SSRF / XML Bomb / サイズ上限などセキュリティ対策を講じています。

トラブルシューティング
- DuckDB のテーブルが見つからない場合は init_schema() を実行してスキーマを作成してください。
- 環境変数の未設定で ValueError が発生する場合は .env を確認してください（設定名は大文字）。
- J-Quants の認証エラーが出る場合は JQUANTS_REFRESH_TOKEN を確認してください。

ライセンス・貢献
- （ここにライセンス情報、貢献ガイドを記載してください。リポジトリに合わせて追記してください）

以上。必要であれば、README に載せるコマンド例や CI / デプロイ手順、詳細な環境（Python バージョン・pip freeze の requirements.txt）を追加で作成します。どの情報を追加しますか？