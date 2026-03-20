KabuSys
=======

日本株向けの自動売買プラットフォーム用ライブラリ（ライブラリ層）。  
データ取得（J-Quants）、DuckDB ベースのデータ永続化、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログ等のユーティリティを含みます。

要点
----
- 言語: Python 3.10+
- DB: DuckDB（ローカルファイルまたは :memory:）
- 主な依存: duckdb, defusedxml（外部パッケージはプロジェクト環境で導入してください）
- .env/.env.local をプロジェクトルートから自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

機能一覧
--------
- データ取得 / 保存（J-Quants API クライアント）
  - 株価日足（fetch_daily_quotes / save_daily_quotes）
  - 財務データ（fetch_financial_statements / save_financial_statements）
  - マーケットカレンダー（fetch_market_calendar / save_market_calendar）
  - レート制限・リトライ・トークン自動リフレッシュ対応
- DuckDB スキーマ管理
  - init_schema() によるテーブル作成（冪等）
  - get_connection() で既存 DB に接続
- ETL パイプライン
  - run_daily_etl() による日次差分取得（calendar, prices, financials）＋品質チェック
- 研究用 / 戦略用機能
  - ファクター計算（mom、volatility、value）
  - クロスセクション Z スコア正規化
  - 特徴量作成（build_features）
  - シグナル生成（generate_signals）: BUY / SELL 生成、Bear レジーム抑制、エグジット判定
- ニュース収集
  - RSS フィード取得（SSRF/サイズ/Gzip 対策、トラッキングパラメータ除去）
  - raw_news, news_symbols への冪等保存
- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job: 夜間差分更新ジョブ
- 監査ログ（audit テーブル群）
  - signal_events, order_requests, executions 等によるトレース

セットアップ手順
--------------
1. 必要な Python バージョンを用意（Python 3.10 以上を推奨）。
2. 仮想環境を作る（任意）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール:
   - pip install duckdb defusedxml
   - （プロジェクトがパッケージ化されている場合は pip install -e .）
4. 環境変数を設定:
   - プロジェクトルートの .env（または .env.local）に必要なキーを記載します。
   - 自動ロードは config モジュールが .git または pyproject.toml の位置から探します。
5. DuckDB スキーマ初期化:
   - Python REPL / スクリプトで init_schema() を呼びます（下記使用例参照）。

必須 / 推奨環境変数
------------------
以下はライブラリ内で参照される代表的な環境変数です（.env に記載）:

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン（get_id_token に使用）。

- KABU_API_PASSWORD (必須)  
  kabuステーション API のパスワード（execution 層で使用想定）。

- KABU_API_BASE_URL (任意)  
  kabuAPI ベース URL。デフォルト: http://localhost:18080/kabusapi

- SLACK_BOT_TOKEN (必須)  
  Slack 通知用 Bot トークン（monitoring/通知で使用）。

- SLACK_CHANNEL_ID (必須)  
  Slack チャンネル ID。

- DUCKDB_PATH (任意)  
  デフォルトの DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）。

- SQLITE_PATH (任意)  
  監視用 SQLite 等に使うパス（デフォルト: data/monitoring.db）。

- KABUSYS_ENV (任意)  
  実行環境: development / paper_trading / live（デフォルト: development）

- LOG_LEVEL (任意)  
  ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

- KABUSYS_DISABLE_AUTO_ENV_LOAD (任意)  
  値を 1 にすると .env 自動読み込みを無効化（テスト用）。

使い方（基本例）
---------------

1) DuckDB スキーマ初期化
- Python スクリプト例:
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  # conn は duckdb.DuckDBPyConnection
  ```

2) 日次 ETL（J-Quants からデータ取得 → DB 保存 → 品質チェック）
- 最小実行例:
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を省略すると今日
  print(result.to_dict())
  ```

3) 特徴量の構築（strategy.feature_engineering.build_features）
- 例:
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  # conn: DuckDB 接続（init_schema で作成済み）
  n = build_features(conn, date(2024, 1, 5))
  print(f"features upserted: {n}")
  ```

4) シグナル生成（strategy.signal_generator.generate_signals）
- 例:
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  total = generate_signals(conn, date(2024, 1, 5))
  print(f"signals written: {total}")
  ```

5) ニュース収集（RSS）
- 例:
  ```python
  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄抽出に使うコード集合（例: {"7203", "6758", ...}）
  res = run_news_collection(conn, known_codes=set(["7203","6758"]))
  print(res)  # {source_name: saved_count}
  ```

6) カレンダー関係ユーティリティ
- is_trading_day, next_trading_day など:
  ```python
  from datetime import date
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  print(is_trading_day(conn, date(2024,1,2)))
  print(next_trading_day(conn, date(2024,1,2)))
  ```

開発 / テストのヒント
--------------------
- テストや一時的な実行ではインメモリ DB を使えます:
  - conn = init_schema(":memory:")
- .env 自動ロードを無効化したい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- jquants_client の API 呼び出しはネットワークに依存するため、ユニットテストでは get_id_token / _request / _urlopen 等をモックしてください。
- news_collector の HTTP 部分は _urlopen をモックしてエンドツーエンドのネットワーク呼び出しを防げます。

ディレクトリ構成
----------------
（主要ファイルと役割の概観、src/kabusys 以下）

- kabusys/
  - __init__.py
  - config.py  -- 環境変数・設定の管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py       -- J-Quants API クライアント（取得/保存ユーティリティ）
    - schema.py               -- DuckDB スキーマ定義・初期化
    - pipeline.py             -- ETL パイプライン（日次ジョブ等）
    - stats.py                -- 統計ユーティリティ（zscore_normalize）
    - features.py             -- features 再エクスポート
    - news_collector.py       -- RSS 収集と raw_news 保存
    - calendar_management.py  -- market_calendar 管理・判定ロジック
    - audit.py                -- 監査ログ用 DDL / 初期化（別途使用想定）
    - execution/ (実行系モジュール用のプレースホルダ)
  - research/
    - __init__.py
    - factor_research.py      -- ファクター計算（momentum, value, volatility）
    - feature_exploration.py  -- 研究用の IC / 将来リターン / 要約統計
  - strategy/
    - __init__.py
    - feature_engineering.py  -- features テーブル作成（正規化・フィルタ等）
    - signal_generator.py     -- final_score 計算、BUY/SELL シグナル生成
  - monitoring/ (モニタリング用モジュール等)
  - execution/ (発注・約定処理などの実装を想定)

設計上の注意点
--------------
- ルックアヘッドバイアス防止: 特徴量計算・シグナル生成は target_date 時点の情報のみ使用する設計です。
- 冪等性: DB 保存処理は可能な限り ON CONFLICT / INSERT ... DO UPDATE / INSERT ... DO NOTHING 等で冪等化されています。
- トレース性: audit モジュールなどで UUID ベースの監査ログを想定しており、信頼性の高いトレーサビリティを確保する方針です。
- 外部 API の呼び出しは rate limit・リトライ・トークン自動更新等に配慮した実装です。

ライセンス・貢献
---------------
- 本リポジトリにライセンス表記が含まれている場合はそちらに従ってください。コントリビュートやバグ報告は issue / PR を通してください。

問い合わせ
----------
実行上の問題や改善提案があれば、リポジトリの issue を利用してください。README の補足やサンプルスクリプトを用意する場合は随時追加します。