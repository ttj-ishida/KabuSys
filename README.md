KabuSys — 日本株自動売買基盤
================================

概要
----
KabuSys は日本株向けのデータ基盤・リサーチ・自動売買フレームワークの骨組みを提供する Python パッケージです。  
DuckDB をデータベースとして用い、J‑Quants API から市場データ・財務データ・マーケットカレンダーを取得する ETL、ニュース収集、特徴量計算、品質チェック、監査ログ等の機能を含みます。  
設計方針として「本番 API へ不要にアクセスしない」「DuckDB での冪等保存」「Look‑ahead Bias を避ける追跡可能な fetched_at」などを重視しています。

主な機能
--------
- データ取得（J‑Quants API クライアント）
  - 日次株価（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得（ページネーション対応、トークン自動リフレッシュ、レート制御、リトライ）
- DuckDB スキーマ管理と初期化
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義と索引
- ETL パイプライン
  - 差分取得（最終取得日からの再取得・バックフィル）、品質チェックの実行（欠損・スパイク・重複・日付不整合）
- ニュース収集
  - RSS フィード取得、前処理、記事ID（正規化 URL → SHA256）による冪等保存、銘柄コード抽出（4桁コード）
- 研究用ユーティリティ（Research）
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）、将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化
- データ品質チェックモジュール
- 監査ログ（order_requests / executions）用スキーマと初期化補助

動作環境・依存
--------------
- Python 3.10 以上（型注釈で PEP 604 の | を使用）
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリで多くの処理を実装しているため、外部依存は最小化されています。
- インストール例（最低限の依存を pip で入れる例）:
  - pip install duckdb defusedxml

環境変数（設定）
----------------
kabusys は .env / .env.local または OS 環境変数から設定を読み込みます（自動ロード。プロジェクトルートは .git または pyproject.toml を基準に探索）。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数（必須）
- JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 通知用チャンネル ID（必須）

その他（任意・デフォルトあり）
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)。デフォルト "development"
- LOG_LEVEL — ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)。デフォルト "INFO"
- DUCKDB_PATH — DuckDB ファイルパス。デフォルト "data/kabusys.duckdb"
- SQLITE_PATH — SQLite（モニタリング用）パス。デフォルト "data/monitoring.db"

サンプル .env（参考）
- JQUANTS_REFRESH_TOKEN=your_refresh_token
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

セットアップ手順
---------------
1. Python 3.10+ を用意する
2. リポジトリをクローン（プロジェクトルートに .git / pyproject.toml があること）
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （必要に応じて他パッケージを追加）
4. 環境変数を設定（.env または .env.local をプロジェクトルートに作成）
5. DuckDB スキーマを初期化
   - 下記「使い方」の例参照

使い方（代表的なユースケース）
----------------------------

1) DuckDB スキーマ初期化（データ格納用）
- Python セッション内で:
  ```
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")
  # conn は duckdb.DuckDBPyConnection オブジェクト
  ```

2) 監査ログ用 DB / スキーマ初期化（別 DB に分離したい場合）
  ```
  from kabusys.data import audit
  conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
  ```

3) 日次 ETL 実行（J‑Quants から差分取得して DuckDB に保存）
  ```
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

4) ニュース収集ジョブの実行
  ```
  from kabusys.data.news_collector import run_news_collection
  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", ...}  # 有効な銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: 新規保存件数, ...}
  ```

5) 研究用（ファクター計算・IC 計算）
  ```
  from kabusys.research import calc_momentum, calc_forward_returns, calc_ic
  conn = init_schema("data/kabusys.duckdb")
  target = date(2024, 1, 31)
  factors = calc_momentum(conn, target)
  fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
  ic = calc_ic(factors, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)
  ```

6) 市場カレンダーの夜間更新ジョブ
  ```
  from kabusys.data.calendar_management import calendar_update_job
  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

ログと実行モード
----------------
- KABUSYS_ENV により実行モード判定（development / paper_trading / live）
  - settings.is_live, is_paper, is_dev で判定可
- LOG_LEVEL によるログの閾値設定（設定値は Settings.log_level で検証されます）

ディレクトリ構成（主要ファイル）
-----------------------------
以下はパッケージ内の主要ファイルとモジュール概要（与えられたコードベースに基づく）:

- src/kabusys/
  - __init__.py  (パッケージ定義, __version__ = "0.1.0")
  - config.py    (環境変数の自動読み込み、Settings クラス)
  - data/
    - __init__.py
    - jquants_client.py      (J‑Quants API クライアント、取得/保存ロジック)
    - news_collector.py      (RSS 収集・前処理・保存・銘柄抽出)
    - schema.py              (DuckDB スキーマ定義と init_schema)
    - stats.py               (zscore_normalize 等統計ユーティリティ)
    - pipeline.py            (ETL パイプライン、run_daily_etl 等)
    - features.py            (公開インターフェース)
    - calendar_management.py (市場カレンダー管理 / 更新ジョブ)
    - audit.py               (監査ログ用スキーマ初期化)
    - etl.py                 (ETLResult の再エクスポート)
    - quality.py             (データ品質チェック)
  - research/
    - __init__.py            (研究用 API のエクスポート)
    - factor_research.py     (mom/value/volatility 計算)
    - feature_exploration.py (将来リターン / IC / summary / rank)
  - strategy/
    - __init__.py            (戦略関連のプレースホルダ)
  - execution/
    - __init__.py            (発注関連のプレースホルダ)
  - monitoring/
    - __init__.py            (監視・モニタリング関連のプレースホルダ)

設計上の注意点
--------------
- J‑Quants API のレート制限（120 req/min）を守るため内部で RateLimiter を採用
- トークン期限切れ時の自動リフレッシュを実装（401 を受けたら 1 回リフレッシュして再試行）
- DuckDB への保存は ON CONFLICT（冪等）で行い、二重登録を防止
- ニュース収集では SSRF 対策・XML 脆弱性対策（defusedxml）・受信サイズ制限を実装
- 研究用関数は DuckDB の prices_daily / raw_financials のみ参照し、本番発注 API にはアクセスしない設計

貢献
----
改善・バグ修正・機能追加は歓迎します。プルリクエストの際は、関連するモジュールの動作に影響がないか、特にデータ保存（DDL/ON CONFLICT）や ETL の冪等性に注意して下さい。

ライセンス
----------
（リポジトリに記載されているライセンスファイルを参照してください。ここでは指定無し）

補足
----
この README は与えられたコードベースの内容を元にしたドキュメントです。実運用する際は各種シークレット（API トークン等）管理、Slack 連携・kabu ステーション連携の実装・テスト、監視・異常対応フローの設計を行ってください。必要であればサンプル .env.example や CLI ラッパー、Unit テストの導入を提案できます。