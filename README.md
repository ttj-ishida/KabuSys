KabuSys
=======

日本株向けの自動売買 / データ基盤ライブラリ（軽量リサーチ + ETL + 戦略）のコア実装群です。
このリポジトリは DuckDB を用いたデータレイヤ（Raw / Processed / Feature / Execution）と、
J-Quants API / RSS からのデータ取得、特徴量作成・シグナル生成・ETL パイプラインなどを提供します。

主な目的
- J-Quants 等から取得した市場データを DuckDB に保存・管理する
- 研究用ファクターを計算・正規化して features テーブルを生成する
- features / AI スコアに基づいて売買シグナルを生成する
- RSS ニュース収集、銘柄抽出を行い raw_news / news_symbols に保存する
- 発注・約定・ポジション管理のためのスキーマ（監査ログを含む）を提供する

特徴 / 機能一覧
- データ取得
  - J-Quants API クライアント（ページネーション対応、トークン自動リフレッシュ、レート制御、リトライ）
  - RSS フィード収集（SSRF 対策、gzip・サイズ制限、トラッキングパラメータ除去）
- データ格納
  - DuckDB 用スキーマ（raw_prices / prices_daily / raw_financials / raw_news / features / signals / orders / executions / positions など）
  - init_schema() による冪等なスキーマ初期化
- ETL パイプライン
  - run_daily_etl(): カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック
  - 差分更新・バックフィル対応（最終取得日からの再取得）
- 研究・特徴量
  - factor_research: momentum / volatility / value 等のファクター計算（prices_daily / raw_financials のみ参照）
  - feature_engineering: ファクター合成・ユニバースフィルタ・Zスコア正規化・features テーブルへの UPSERT
  - research.feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリ
- 戦略
  - signal_generator: features と ai_scores を統合して final_score を計算、BUY/SELL シグナル生成（冪等）
  - 重み・閾値のカスタマイズ、Bear レジーム判定、エグジット（ストップロス等）
- セキュリティ・耐障害設計
  - RSS: private IP / redirect の検査、XML 攻撃対策（defusedxml）
  - J-Quants: レート制御、リトライ、401 リフレッシュ
  - DB 操作はトランザクションで原子性を確保（BEGIN/COMMIT/ROLLBACK）

必要条件（主な依存）
- Python 3.10+
- duckdb
- defusedxml
（その他 Python 標準ライブラリを利用。ネットワークは urllib を使用）

インストール（開発環境）
- 仮想環境作成（任意）
  python -m venv .venv
  source .venv/bin/activate  # macOS/Linux
  .venv\Scripts\activate     # Windows

- 必要パッケージのインストール（例）
  pip install duckdb defusedxml

- 開発インストール（プロジェクトルートで）
  pip install -e .

環境変数 / 設定
このプロジェクトは環境変数（またはプロジェクトルートの .env / .env.local）を参照して動作します。自動で .env を読み込む仕組みが組み込まれており、テストなどで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（README 内で最低限必要なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（省略時: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

例 (.env)
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

セットアップ手順（最小）
1. 依存パッケージをインストール
   pip install duckdb defusedxml

2. .env を作成して必要な環境変数をセット

3. DuckDB スキーマ初期化（Python REPL またはスクリプト）
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ディレクトリがなければ自動作成

4. （任意）初回 ETL を実行してデータを取得
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl
   # 上の conn は init_schema の戻り値
   result = run_daily_etl(conn, target_date=date.today())

よく使う使い方（コード例）
- スキーマ初期化
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- ETL（市場カレンダー・株価・財務の差分取得）
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  res = run_daily_etl(conn, target_date=date.today())
  print(res.to_dict())

- 特徴量作成（feature engineering）
  from datetime import date
  from kabusys.strategy import build_features
  n = build_features(conn, target_date=date.today())
  print(f"features upserted: {n}")

- シグナル生成
  from datetime import date
  from kabusys.strategy import generate_signals
  total = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print(f"signals generated: {total}")

- ニュース収集ジョブ
  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄抽出に用いる有効コードの set（None なら抽出スキップ）
  stats = run_news_collection(conn, known_codes={"7203","6758"})
  print(stats)

- J-Quants API を直接叩く（トークン取得等）
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  token = get_id_token()
  data = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

運用時の注意点 / ヒント
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索します。CIやテストで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB の初期化は init_schema() を一度実行してください。既存テーブルはスキップされるので冪等です。
- jquants_client は 120 req/min のレートに合わせて内部でスロットリングします。大量のデータ取得時は注意してください。
- RSS 収集は外部のフィードに依存するため、予期せぬ XML レイアウトやサイズ超過により空結果を返すことがあります。ログを確認してください。
- features の正規化では Z スコアを使用し ±3 でクリップするため、外れ値耐性が組み込まれています。
- signal_generator は Bear レジーム判定やエグジット（ストップロス）を実装していますが、実際の売買執行は execution 層（発注 API）に依存します。本コードは発注 API への直接依存を持たない設計です。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                    : 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py          : J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py         : RSS 収集・前処理・DB 保存
    - schema.py                 : DuckDB スキーマ定義と init_schema()
    - stats.py                  : zscore_normalize 等の統計ユーティリティ
    - pipeline.py               : 日次 ETL パイプライン run_daily_etl 等
    - features.py               : data.stats の再エクスポート
    - calendar_management.py    : market_calendar 管理（営業日判定等）
    - audit.py                  : 監査ログのスキーマ（signal_events / order_requests / executions）
    - (その他: quality 等のモジュール想定)
  - research/
    - __init__.py
    - factor_research.py        : momentum / value / volatility の計算
    - feature_exploration.py    : forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py    : features の構築（ユニバースフィルタ・正規化）
    - signal_generator.py       : final_score 計算・BUY/SELL シグナル生成
  - execution/                   : 発注・実行関連（空/__init__用意）
  - monitoring/                  : 監視・メトリクス（将来実装想定）

ロギング
- 各モジュールは標準 logging を利用しています。LOG_LEVEL 環境変数で出力レベルを制御してください。

テスト / 開発メモ
- DB を破壊したくない場合は DuckDB の ":memory:" を指定して get_connection/init_schema を使えます。
- config の自動 .env 読み込みはテストでの副作用を避けるために KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ライセンス / コントリビュート
- （この README はコードベースに基づく概要ドキュメントです。実際のライセンス表記や貢献ガイドラインはリポジトリルートに追加してください。）

補足
- 詳細な設計仕様（StrategyModel.md / DataPlatform.md / DataSchema.md 等）はコード内の docstring に要約が含まれています。実運用・監査・リスク管理の要件に合わせて拡張してください。

問題報告・改善提案は Issue を立ててください。必要なら README を翻訳・追記します。