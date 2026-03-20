# KabuSys (README) — 日本語

バージョン: 0.1.0

概要
----
KabuSys は日本株向けの自動売買プラットフォームのコアライブラリです。  
主に以下を提供します。

- J-Quants からの市場データ取得と DuckDB への保存（ETL）
- ニュース収集・前処理・銘柄紐付け
- ファクター計算（Momentum / Value / Volatility / Liquidity 等）
- 特徴量（features）構築と戦略シグナル生成
- 市場カレンダー管理、監査ログ（発注→約定のトレーサビリティ）
- 実行（execution）層のスキーマとインターフェース（発注は外部ブローカー連携を想定）

設計上の要点:
- DuckDB を中心としたオンディスク DB（:memory: も可）
- ルックアヘッドバイアス防止（target_date 時点のデータのみを使用）
- ETL/保存は冪等（ON CONFLICT / INSERT ... DO UPDATE または DO NOTHING）
- J-Quants API へはレート制御・リトライ・トークン自動更新を実装
- ニュース収集は SSRF 等の安全対策、XML ディフェンスを実装

機能一覧
--------
主なモジュールと代表的な機能:

- kabusys.config
  - 環境変数の自動ロード（.env / .env.local、無効化可能）
  - 必須設定チェック・環境モード（development / paper_trading / live）

- kabusys.data
  - jquants_client: J-Quants API クライアント（フェッチ・保存）
    - fetch_daily_quotes / save_daily_quotes
    - fetch_financial_statements / save_financial_statements
    - fetch_market_calendar / save_market_calendar
  - schema: DuckDB スキーマ定義と初期化（init_schema / get_connection）
  - pipeline: 日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - news_collector: RSS 収集・前処理・DB 保存（fetch_rss / save_raw_news / run_news_collection）
  - calendar_management: 営業日判定・next/prev_trading_day 等
  - stats: zscore_normalize（クロスセクション正規化） 等
  - features: 再エクスポート（zscore_normalize）

- kabusys.research
  - calc_momentum / calc_volatility / calc_value（ファクター計算）
  - calc_forward_returns / calc_ic / factor_summary / rank（探索・評価）

- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold, weights)

- kabusys.execution / kabusys.monitoring
  - 実行層・監視に関するインターフェース（発展的実装を想定）

セットアップ手順
----------------

1. クローン & インストール（開発環境想定）
   - 仮想環境（venv 等）を作成して有効化してください。
   - 依存パッケージ（例: duckdb, defusedxml）をインストールしてください。
     例:
     ```
     pip install duckdb defusedxml
     ```
   - パッケージを開発モードでインストールする場合:
     ```
     pip install -e .
     ```

2. 環境変数の準備
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（読み込みは __file__ 基準で親ディレクトリを探索）。
   - 必須環境変数（少なくとも以下を設定してください）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD     : kabuステーション API のパスワード
     - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID
   - 任意 / デフォルト:
     - KABU_API_BASE_URL     : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH           : sqlite 用監視 DB（デフォルト: data/monitoring.db）
     - KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL             : DEBUG / INFO / ...（デフォルト: INFO）
   - 自動ロードを無効にする:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

3. DuckDB スキーマ初期化
   - アプリ起動前にスキーマを作成します。Python REPL やスクリプトで:
     ```python
     import kabusys.data.schema as schema
     conn = schema.init_schema("data/kabusys.duckdb")  # デフォルトパス
     conn.close()
     ```

使い方（基本例）
----------------

- 日次 ETL（市場データ取得 → 保存 → 品質チェック）
  ```python
  from datetime import date
  import kabusys.data.pipeline as pipeline
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  conn.close()
  ```

- 特徴量構築（features テーブルへ書き込み）
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  n = build_features(conn, target_date=date.today())
  print(f"features upserted: {n}")
  conn.close()
  ```

- シグナル生成（signals テーブルへ書き込み）
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print(f"signals generated: {total}")
  conn.close()
  ```

- ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  conn.close()
  ```

- J-Quants データ取得（個別呼び出し）
  ```python
  from kabusys.data import jquants_client as jq
  from datetime import date

  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  # 保存は save_daily_quotes を使用
  ```

実行上の注意
-------------
- J-Quants API のレート制限（120 req/min）・リトライ・401 自動リフレッシュに対応しています。ただし大量バッチを回す場合は運用上の配慮が必要です。
- news_collector は SSRF や XML Attack に配慮した実装（ホスト検証・defusedxml・応答サイズ上限など）を行っています。
- ETL は冪等的に設計されていますが、最初のスキーマ作成（init_schema）は一度実行しておくことを推奨します。
- 環境 (KABUSYS_ENV) によって運用上の挙動（本番/ペーパートレード等）を分離できます。live 環境では実発注や機密情報の扱いに注意してください。

ディレクトリ構成
----------------
（主要ファイルを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - pipeline.py
      - schema.py
      - stats.py
      - calendar_management.py
      - features.py
      - audit.py
      - execution/        (execution 関連の実装)
      - ...その他
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - monitoring/         (監視・メトリクス用コード)
    - execution/          (発注連携用コード)

（README 用のツリー表示例）
```
src/kabusys/
├─ __init__.py
├─ config.py
├─ data/
│  ├─ jquants_client.py
│  ├─ news_collector.py
│  ├─ schema.py
│  ├─ pipeline.py
│  └─ ...
├─ research/
│  ├─ factor_research.py
│  └─ feature_exploration.py
├─ strategy/
│  ├─ feature_engineering.py
│  └─ signal_generator.py
└─ ...
```

追加資料 / 設計ドキュメント
------------------------
コード内の docstring やコメントに設計方針（StrategyModel.md, DataPlatform.md 等）への参照が多数あります。実運用・バックテストや発注連携を行う際はそれらの設計仕様に基づいたさらなる実装・検証が必要です。

ライセンス / 責任
-----------------
本リポジトリは金融データ・取引を扱うため、実運用で使用する前に十分な検証、監査、法的/コンプライアンス面の確認を行ってください。実際の売買や資金を扱う運用は自己責任で行ってください。

お問い合わせ
------------
実装に関する質問や改善提案はコード内コメント／issue に記載してください。