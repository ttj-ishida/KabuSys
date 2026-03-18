KabuSys
=======

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
DuckDB を用いたデータレイヤ設計、J-Quants からのデータ取得（OHLCV・財務・カレンダー）、RSS ベースのニュース収集、特徴量計算・研究ユーティリティ、ETL パイプライン、データ品質チェック、監査ログなどを備えています。

概要
----
KabuSys は以下の要件を想定した内部ライブラリ群です。

- J-Quants API を用いて日本株の市場データ・財務データ・取引カレンダーを取得
- DuckDB に Raw / Processed / Feature / Execution 層のスキーマを持つデータベースを構築
- RSS からニュースを収集して記事保存・銘柄紐付けを行う
- ETL（差分取得・保存・品質チェック）を自動化
- ファクター計算（モメンタム・ボラティリティ・バリュー等）・IC 計算・Zスコア正規化などのリサーチユーティリティ
- 発注・監査用のスキーマ（監査ログ）を提供

主な機能
--------
- 環境設定読み込み（.env / .env.local 自動読み込み、または環境変数）
- J-Quants API クライアント（ページネーション・レート制御・リトライ・トークン自動更新）
- DuckDB スキーマの初期化（init_schema）と接続ユーティリティ
- ETL パイプライン（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェックの順で差分同期
- ニュース収集（RSS fetch / 正規化 / DB 保存 / 銘柄抽出）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- リサーチ用ファクター計算（calc_momentum, calc_volatility, calc_value 等）および IC / 統計サマリ
- 統計ユーティリティ（zscore 正規化）
- 監査ログスキーマ（signal / order / execution のトレースを UUID で追跡）

動作要件（推奨）
----------------
- Python 3.10 以上（型ヒントの | 演算子を使用）
- 依存ライブラリ（最低限）:
  - duckdb
  - defusedxml

セットアップ手順
----------------

1. リポジトリをクローンしてワークディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージ化されている場合は pip install -e . 等）

4. 環境変数設定
   - プロジェクトルートに .env を置くと自動で読み込まれます（.env.local は上書き）。  
     自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 必須環境変数（Settings クラスで参照）
     - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD      — kabuステーション API パスワード
     - SLACK_BOT_TOKEN        — Slack 通知に使う Bot token
     - SLACK_CHANNEL_ID       — Slack チャネル ID
   - 任意（デフォルト値あり）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）

   例（.env）
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=CXXXXXXXX
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb

使い方（基本例）
----------------

- 設定値取得
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  print(settings.env, settings.is_live)
  ```

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL の実行（J-Quants から差分取得して保存・品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を省略すると今日が対象
  print(result.to_dict())
  ```

- ニュース収集ジョブ（RSS 取得 → 保存 → 銘柄紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  # known_codes は有効な銘柄コードのセット (例: {'7203','6758',...})
  stats = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(stats)
  ```

- ファクター計算（研究用）
  ```python
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
  from datetime import date

  target = date(2025, 1, 31)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)

  forwards = calc_forward_returns(conn, target, horizons=[1,5,21])
  ic = calc_ic(mom, forwards, factor_col="mom_1m", return_col="fwd_1d")
  summary = factor_summary(mom, ["mom_1m", "ma200_dev"])
  ```

- Z スコア正規化
  ```python
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(mom, ["mom_1m", "mom_3m"])
  ```

便利な注意点
- .env/.env.local はプロジェクトルート（.git または pyproject.toml を起点）から自動読み込みされます。CI やテストで自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants クライアントは内部でレートリミット（120 req/min）、リトライ、ID トークンの自動リフレッシュを実装しています。
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE / DO NOTHING）を考慮しています。

ディレクトリ構成（主要ファイル）
-------------------------------

src/kabusys/
- __init__.py
- config.py
  - 環境変数 / 設定の読み込みロジック（.env 自動読み込み、Settings クラス）
- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント、fetch/save 関数群
  - news_collector.py
    - RSS 収集、前処理、記事保存、銘柄抽出ロジック
  - schema.py
    - DuckDB の DDL 定義と init_schema / get_connection
  - stats.py
    - zscore_normalize などの統計ユーティリティ
  - pipeline.py
    - ETL パイプライン（run_daily_etl など）
  - features.py
    - 特徴量ユーティリティの公開インターフェース
  - calendar_management.py
    - market_calendar 管理・営業日判定ユーティリティ
  - audit.py
    - 監査ログ用スキーマと初期化ロジック
  - etl.py
    - ETL 関連 API の再エクスポート
  - quality.py
    - データ品質チェック（欠損・スパイク・重複・日付不整合）
- research/
  - __init__.py
    - 研究用関数の再エクスポート
  - feature_exploration.py
    - 将来リターン計算、IC、統計サマリ、rank 等
  - factor_research.py
    - momentum / volatility / value の計算
- strategy/
  - __init__.py
  - （戦略モデル等はここに実装）
- execution/
  - __init__.py
  - （発注・執行ロジックはここに実装）
- monitoring/
  - __init__.py
  - （監視・メトリクス関連はここに実装）

開発者向けメモ
---------------
- DuckDB スキーマは複数レイヤ（Raw / Processed / Feature / Execution / Audit）で設計されており、DDL は schema.py / audit.py にまとめられています。初回は init_schema() → 必要に応じて init_audit_schema() を実行してください。
- research モジュールは外部ライブラリに依存せず（標準ライブラリ + duckdb）で記述されています。大規模処理の際は DuckDB 側の SQL/ウィンドウ関数活用を優先してください。
- news_collector は SSRF 対策や XML パースの安全化（defusedxml）などを行っています。外部接続部分（_urlopen）はテストでモック可能に設計されています。

ライセンス / 貢献
-----------------
（本テンプレートではライセンス記載がありません。必要に応じて LICENSE を追加してください。）

お問い合わせ
------------
実装上の疑問やバグ報告、改善提案があればリポジトリの Issue を立ててください。