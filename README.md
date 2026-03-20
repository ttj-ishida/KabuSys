# KabuSys

日本株向け自動売買基盤ライブラリ（KabuSys）。  
J-Quants / RSS 等からのデータ取得、DuckDB を用いたデータ基盤、特徴量生成、戦略シグナル生成、監査/発注レイヤのスキーマを提供します。

概要
- データ取得：J-Quants API から日次株価・財務・市場カレンダーを取得（rate-limit / retry / token refresh 対応）
- ニュース取得：RSS 収集、テキスト前処理、銘柄抽出、DB 保存
- ETL：差分取得・保存・品質チェックを行う日次パイプライン
- 研究用モジュール：ファクター計算・特徴量探索（IC, forward returns 等）
- 戦略：特徴量正規化 → シグナル生成（BUY / SELL）
- DB スキーマ：Raw / Processed / Feature / Execution 層を備えた DuckDB スキーマ定義と初期化
- 監査：シグナル→発注→約定のトレーサビリティ用テーブル

機能一覧
- kabusys.config: .env / 環境変数の自動読み込みと設定オブジェクト（必須キーの検証）
- kabusys.data.jquants_client: J-Quants API クライアント（ページング・リトライ・トークン自動更新）
- kabusys.data.news_collector: RSS 取得、正規化、raw_news/ news_symbols への保存（SSRF対策、サイズ制限）
- kabusys.data.schema: DuckDB のテーブル定義と init_schema()
- kabusys.data.pipeline: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl 等の ETL ジョブ
- kabusys.data.calendar_management: 営業日判定・next/prev_trading_day 等
- kabusys.data.stats: zscore_normalize 等の統計ユーティリティ
- kabusys.research: calc_momentum・calc_volatility・calc_value、IC / forward returns / factor summary
- kabusys.strategy.feature_engineering: 生ファクターの正規化・ユニバースフィルタ・features テーブルへの保存
- kabusys.strategy.signal_generator: final_score の計算、BUY/SELL シグナル生成、signals テーブルへの保存
- 監査／execution 層（schema に定義）：signal_events, order_requests, executions など

前提条件
- Python 3.10+
- 必須外部パッケージ（例）:
  - duckdb
  - defusedxml
（ネットワーク要求は標準ライブラリ urllib を使用）

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン／チェックアウト
2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （開発中で package 配布ファイルがある場合）pip install -e .
4. 環境変数を用意（.env）
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

推奨の .env（例）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

（注）Settings クラスは以下の環境変数を必須としているので、実際に呼び出される前に設定してください：
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

基本的な使い方（例）
- DuckDB スキーマ初期化
  python -c "from kabusys.data import schema; schema.init_schema('data/kabusys.duckdb')"

- 日次 ETL を実行（簡易）
  python - <<'PY'
  from datetime import date
  import duckdb
  from kabusys.data import schema, pipeline
  conn = schema.init_schema('data/kabusys.duckdb')
  res = pipeline.run_daily_etl(conn, target_date=date.today())
  print(res.to_dict())
  PY

- 特徴量（features）生成
  python - <<'PY'
  from datetime import date
  import duckdb
  from kabusys.data import schema
  from kabusys.strategy import build_features
  conn = schema.get_connection('data/kabusys.duckdb')
  count = build_features(conn, date.today())
  print('features upserted:', count)
  PY

- シグナル生成
  python - <<'PY'
  from datetime import date
  import duckdb
  from kabusys.data import schema
  from kabusys.strategy import generate_signals
  conn = schema.get_connection('data/kabusys.duckdb')
  total = generate_signals(conn, date.today())
  print('signals written:', total)
  PY

- ニュース収集ジョブ（既知銘柄セットを指定）
  python - <<'PY'
  from kabusys.data import schema, news_collector
  conn = schema.get_connection('data/kabusys.duckdb')
  known_codes = {'7203','6758',...}  # 事前に有効銘柄セットを用意
  results = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(results)
  PY

環境設定の注意点
- 自動 .env 読み込み順序: OS 環境変数 > .env.local > .env
- テスト等で自動読み込みを抑制するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- Settings.env の有効値: development / paper_trading / live
- Settings.log_level は DEBUG/INFO/WARNING/ERROR/CRITICAL

主要 API サマリ（プログラム的に利用する際）
- kabusys.data.schema
  - init_schema(db_path) → DuckDB 接続（テーブル作成）
  - get_connection(db_path)
- kabusys.data.jquants_client
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
- kabusys.data.pipeline
  - run_daily_etl(...)
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold=None, weights=None)
- kabusys.data.news_collector
  - fetch_rss(url, source)
  - save_raw_news(conn, articles)
  - run_news_collection(conn, sources=None, known_codes=None)

ディレクトリ構成（主要ファイル抜粋）
- src/kabusys/
  - __init__.py
  - config.py                # 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント
    - news_collector.py
    - schema.py              # DuckDB スキーマ定義 & init
    - pipeline.py            # ETL パイプライン
    - calendar_management.py
    - stats.py               # 統計ユーティリティ
    - features.py
    - audit.py               # 監査ログ関連DDL
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/                # 発注・実行関連（空モジュール／拡張ポイント）
  - monitoring/               # 監視系（将来の拡張）
  - ...（その他モジュール）

設計上のポイント / 注意事項
- ルックアヘッドバイアス対策：target_date 時点で利用可能なデータのみを使用する方針
- 冪等性：DB への保存は ON CONFLICT / INSERT ... DO UPDATE 等を活用して冪等操作を保証
- ネットワーク安全性：news_collector は SSRF 対策、受信サイズ制限、gzip 解凍チェック等を実装
- レート制御：J-Quants クライアントは固定スロットリングとリトライ（429/408/5xx 等）に対応
- 設定不足（必須環境変数未設定）は Settings のアクセス時に ValueError を送出

トラブルシューティング（よくある問題）
- ValueError: 環境変数が設定されていません → .env または環境変数を確認
- DuckDB 接続エラー → パスの権限 / ディレクトリ作成権限を確認（schema.init_schema は親ディレクトリを作成します）
- J-Quants 401 → J-Quants の refresh token を確認（Settings.jquants_refresh_token）
- RSS から記事が取れない → URL スキーム・リダイレクト先のホストがプライベートかどうかを確認

拡張ポイント
- execution 層: 証券会社 API（kabuステーション等）とのインテグレーション実装
- risk management / portfolio construction: portfolio_targets, orders の生成ロジック
- モデル改善: ai_scores の導入・学習パイプライン接続

ライセンス・貢献
- この README はコードベースの説明を目的としています。実運用用途へ適用する場合は十分なテスト・監査を行ってください。貢献・バグ報告はリポジトリの issue / PR を利用してください。

以上。README の内容や追加で載せたい利用例（cron 用の実行例、systemd ユニット、Dockerfile 例など）があれば教えてください。必要に応じて追記します。