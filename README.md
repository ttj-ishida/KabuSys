KabuSys
=======

日本株向けの自動売買 / 研究用ライブラリ群です。ファクター計算、特徴量生成、シグナル生成、ポートフォリオ構築、バックテスト基盤、データ取得（J-Quants）やニュース収集など、アルゴリズム運用に必要な主要コンポーネントを含みます。

要点
- 言語: Python（型注釈に | を使っているため Python 3.10+ を想定）
- DB: DuckDB を主に利用（ローカル .duckdb ファイルやインメモリ）
- ネットワーク: J-Quants API から株価・財務・カレンダー等を取得
- セキュリティ: RSS 取得時の SSRF 対策、XML パースの安全化（defusedxml）など

主な機能
- データ収集
  - J-Quants API クライアント（jquants_client）：日足・財務・上場情報・カレンダーの取得＋DuckDB への保存（冪等）
  - ニュース収集（news_collector）：RSS 取得、記事前処理、raw_news / news_symbols への保存、銘柄抽出（4桁コード）
- 研究用ファクター計算（research）
  - calc_momentum / calc_volatility / calc_value：prices_daily / raw_financials を使ってファクターを計算
  - feature_exploration: 将来リターン、IC、要約統計など
- 特徴量生成・シグナル生成（strategy）
  - feature_engineering.build_features：生ファクターを正規化して features テーブルへ出力
  - signal_generator.generate_signals：features + ai_scores を統合して BUY/SELL シグナルを生成して signals テーブルへ出力
- ポートフォリオ構築（portfolio）
  - 銘柄選定（select_candidates）、配分（等金額・スコア加重）、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイジング（リスクベース等）
- バックテスト（backtest）
  - エンジン（run_backtest）: 本番 DB をコピーしたインメモリ環境でバックテストを実行
  - シミュレータ（PortfolioSimulator）：擬似約定、スリッページ・手数料モデル、日次評価を保持
  - メトリクス（BacktestMetrics）：CAGR、Sharpe、MaxDD、勝率、Payoff 等を算出

セットアップ手順（開発環境向け）
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - duckdb, defusedxml などが必要です。最低限:
     - pip install duckdb defusedxml
   - プロジェクトに pyproject.toml / requirements.txt があればそちらを利用してください。
4. パッケージを editable install（任意）
   - pip install -e .

環境変数 / 設定
- 自動で .env / .env.local をプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 主要な環境変数（Settings クラスで参照）:
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
  - KABU_API_BASE_URL (任意) — デフォルト http://localhost:18080/kabusapi
  - SLACK_BOT_TOKEN (必須) — Slack Bot トークン
  - SLACK_CHANNEL_ID (必須) — 通知先チャンネルID
  - DUCKDB_PATH (任意) — default: data/kabusys.duckdb
  - SQLITE_PATH (任意) — default: data/monitoring.db
  - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
  - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- .env のパースはシェル形式（export も許可）をサポートし、クォートやコメント処理に注意した実装になっています。

使い方（主要な例）

1) バックテスト（CLI）
- 事前準備:
  - DuckDB ファイルに prices_daily, features, ai_scores, market_regime, market_calendar, stocks 等が格納されている必要があります（スキーマの初期化は kabusys.data.schema.init_schema を利用）。
- 実行例:
  - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db path/to/kabusys.duckdb
  - 主要なオプション: --cash, --slippage, --commission, --max-position-pct, --allocation-method, --max-utilization, --max-positions, --risk-pct, --stop-loss-pct, --lot-size
- 戻り値は標準出力に要約が表示され、内部では run_backtest() が BacktestResult（history, trades, metrics）を返します。

2) Python API からバックテストを呼ぶ
- 例:
  from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest
  conn = init_schema("path/to/kabusys.duckdb")
  result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
  conn.close()
- result.metrics で各評価指標にアクセスできます。

3) 特徴量生成 / シグナル生成（DuckDB 接続を使う）
- build_features(conn, target_date) — features テーブルに日付単位で UPSERT
- generate_signals(conn, target_date, threshold=0.6) — signals テーブルに BUY/SELL を書き込む（デフォルト重みは StrategyModel.md に基づく）

4) J-Quants からデータ取得と保存
- get_id_token(), fetch_daily_quotes(), save_daily_quotes(conn, records) などの関数を利用して取得→保存パイプラインを作れます。
- 例（おおまか）:
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  records = fetch_daily_quotes(date_from=..., date_to=...)
  conn = init_schema("path/to/kabusys.duckdb")
  save_daily_quotes(conn, records)

5) ニュース収集ジョブ
- run_news_collection(conn, sources=None, known_codes=None)
  - sources: {source_name: rss_url}。デフォルトに Yahoo Finance のビジネス RSS が含まれます。
  - known_codes: 銘柄抽出に使う有効な銘柄コードセット（指定しない場合は紐付けスキップ）
- fetch_rss(url, source) と save_raw_news(conn, articles) を組み合わせて使えます。

実装上の重要な挙動・設計
- look-ahead bias に配慮:
  - 特徴量・シグナル生成は target_date 時点の利用可能データのみを用いる設計。
  - J-Quants のデータは fetched_at を記録して取得タイミングを追跡可能にしています。
- 冪等性:
  - DuckDB への保存処理は ON CONFLICT（または INSERT ... DO NOTHING / RETURNING）を用いて冪等化されています。
- エラー・再試行・レート制御:
  - jquants_client は固定間隔によるレート制限、指数バックオフ、特定の HTTP ステータスでの再試行、401 に対するトークン自動リフレッシュを内蔵。
- セキュリティ:
  - news_collector は RSS 取得時に SSRF 対策、受信サイズ制限、defusedxml による安全な XML パースを行います。

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / 設定管理（Settings）
  - data/
    - jquants_client.py — J-Quants API クライアント（取得 + DuckDB 保存ユーティリティ）
    - news_collector.py — RSS 取得、記事前処理、raw_news / news_symbols 保存
    - (その他 schema, calendar_management 等の補助モジュールを参照する実装がある想定)
  - research/
    - factor_research.py — momentum / volatility / value 等のファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー等
  - strategy/
    - feature_engineering.py — 生ファクターの正規化・features テーブルへの書込み
    - signal_generator.py — features + ai_scores → final_score → signals 生成
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 株数決定、aggregate cap、単元丸め、部分約定処理
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - backtest/
    - engine.py — バックテストのメインループ（run_backtest）
    - simulator.py — PortfolioSimulator（擬似約定・履歴管理）
    - metrics.py — バックテスト評価指標計算
    - run.py — CLI エントリポイント（python -m kabusys.backtest.run）
    - clock.py — 将来的な時間制御用
  - portfolio/、strategy/、research/、backtest/ はそれぞれ __init__.py で主要 API をエクスポートしています。

注意事項 / 推奨
- DuckDB スキーマの初期化は kabusys.data.schema.init_schema() を使うことを想定しています（スキーマファイルはコードベースに含まれる別モジュールで定義されている想定）。
- 本コードは「研究環境」と「運用環境」での振る舞い（paper_trading / live）を切り替える設定を持ちます。live で実際の発注を行うコンポーネント（execution 層）やモニタリングはこのリポジトリの別ファイルで実装される想定です。
- API トークンやパスワードは .env に保存する際は取り扱いに注意し、公開リポジトリには含めないでください。

この README はコードベースの実装内容（モジュール、関数名、挙動）を元に作成しています。実際の運用やデプロイ、CI/CD の手順、詳細なテーブルスキーマ、追加の依存関係はプロジェクトルートの pyproject.toml / requirements.txt / .env.example / docs を参照してください。必要であれば README に「例: .env.example の内容」や「スキーマ定義の抜粋」を追加できます。