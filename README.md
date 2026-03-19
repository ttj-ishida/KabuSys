KabuSys
=======

日本株向けの自動売買／データ基盤ライブラリ（モジュール群）の README です。  
このリポジトリは、データ取得（J-Quants）、ETL、特徴量構築、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを含む一連の処理を提供します。

プロジェクト概要
---------------
KabuSys は日本株の自動売買システムを構成するためのライブラリ群です。主な責務は次の通りです。

- J-Quants API からの市場データ・財務データ・カレンダーの取得（レート制御、リトライ、トークン自動更新）
- DuckDB を用いたデータベーススキーマ定義と永続化（raw / processed / feature / execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）と特徴量（features）構築
- シグナル生成（ファクタースコアと AI スコア統合、BUY / SELL 判定）
- RSS ベースのニュース収集と銘柄抽出（SSRF 対策、トラッキングパラメータ除去）
- マーケットカレンダー管理（営業日判定・next/prev/trading_days）
- 発注／監査用スキーマ（信頼性の高いトレーサビリティ設計）

主な機能一覧
-------------
- data.jquants_client
  - J-Quants からのデータ取得（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）
  - レート制御、リトライ、トークン自動更新
- data.schema
  - DuckDB のスキーマ定義と初期化（init_schema）
- data.pipeline
  - 日次 ETL（run_daily_etl）や個別 ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
  - 差分更新・バックフィルのサポート・品質チェック連携
- data.news_collector
  - RSS フィードの安全な取得（SSRF 対策・gzip サイズ制限）
  - raw_news への冪等保存、記事→銘柄紐付け
- data.calendar_management
  - market_calendar の差分更新、営業日判定、next_trading_day / prev_trading_day / get_trading_days
- research
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- strategy
  - build_features: ファクターの正規化／合成 → features テーブルへ保存
  - generate_signals: features と ai_scores を統合して signals テーブルへ書き込み
- utils / 設定
  - config.Settings: 環境変数読み込み（.env 自動ロード）と必須設定の検査
  - zscore_normalize 等の統計ユーティリティ

セットアップ手順
----------------

前提
- Python 3.9+（typing の新機能を利用しているため、推奨は 3.10 以上）
- システムにネットワークアクセスが可能であること（J-Quants / RSS）

必要な Python パッケージ（代表例）
- duckdb
- defusedxml

例: pip でインストール（requirements.txt がない場合の最小セット）
pip install duckdb defusedxml

環境変数（必須）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD : kabu API（発注等）用パスワード
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID : Slack 通知先チャンネル ID

任意／デフォルト
- KABU_API_BASE_URL : kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視等で使用する SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV : 実行環境 (development / paper_trading / live)、デフォルト development
- LOG_LEVEL : ログレベル（DEBUG/INFO/...）、デフォルト INFO

.env の自動読み込み
- パッケージはプロジェクトルート（.git または pyproject.toml のある場所）を探索し、.env → .env.local の順で自動読み込みします。
- 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

初期 DB の作成
- DuckDB スキーマを作成するには以下を実行します:

from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)

使い方（主要なワークフロー）
-------------------------

1) 日次 ETL（データ取得・保存・品質チェック）
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# 初期化（初回のみ）
conn = init_schema(settings.duckdb_path)  # ファイルを作成してスキーマを構築
# または既存 DB に接続
# conn = get_connection(settings.duckdb_path)

# 当日分 ETL を実行
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

2) 特徴量構築（features テーブルへの書き込み）
from datetime import date
from kabusys.strategy import build_features
build_count = build_features(conn, target_date=date(2026, 3, 18))
print(f"features upserted: {build_count}")

3) シグナル生成（signals テーブルへの書き込み）
from kabusys.strategy import generate_signals
sig_count = generate_signals(conn, target_date=date.today())
print(f"signals written: {sig_count}")

- generate_signals は weights（ファクター重み）や閾値を引数で上書きできます。
- Bear レジーム（市場レジーム）検出により BUY シグナルを抑制します。

4) ニュース収集
from kabusys.data.news_collector import run_news_collection
# known_codes は有効な銘柄コード集合（抽出のため）
results = run_news_collection(conn, known_codes=set(["7203","6758"]))
print(results)

5) カレンダー更新ジョブ（夜間バッチなどで実行）
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"saved calendar rows: {saved}")

注意点 / 運用上のヒント
- 認証情報（トークン・パスワード等）は .env ファイルや環境変数で管理し、公開リポジトリに含めないでください。
- DUCKDB_PATH のバックアップや定期的な VACUUM（運用ポリシー）を検討してください（DuckDB はファイルベースです）。
- ETL は差分更新を行いますが、必要に応じて backfill_days を調整して API 側訂正を取り込めます。
- run_daily_etl は品質チェック（quality モジュール）を呼びます。品質エラーがあっても ETL は継続し、結果に問題を報告します。

ディレクトリ構成
----------------

主要なモジュールとファイル（src/kabusys 以下）:

- kabusys/
  - __init__.py              (# パッケージ初期化、__version__)
  - config.py                (# 環境変数・設定管理)
  - data/
    - __init__.py
    - jquants_client.py      (# J-Quants API クライアント、保存ユーティリティ)
    - news_collector.py      (# RSS 取得・前処理・保存・銘柄抽出)
    - schema.py              (# DuckDB スキーマ定義と init_schema/get_connection)
    - stats.py               (# zscore_normalize 等統計ユーティリティ)
    - pipeline.py            (# ETL パイプライン：run_daily_etl 等)
    - calendar_management.py (# calendar_update_job / 営業日判定ロジック）
    - audit.py               (# 監査ログ用スキーマ）
    - features.py            (# zscore_normalize の再エクスポート）
    - execution/             (# 発注関連のプレースホルダ、現状空)
  - research/
    - __init__.py
    - factor_research.py     (# モメンタム / ボラティリティ / バリュー計算)
    - feature_exploration.py (# 将来リターン / IC / 統計サマリー)
  - strategy/
    - __init__.py
    - feature_engineering.py (# build_features）
    - signal_generator.py    (# generate_signals）
  - monitoring/              (# 監視・モニタリング関連（コードベースに未実装部分あり））

ドキュメント参照
- DataSchema.md, DataPlatform.md, StrategyModel.md 等の設計文書に基づいて実装されています（リポジトリ内に別ファイルがあれば参照してください）。

開発／デバッグ
--------------
- ログレベルは LOG_LEVEL 環境変数で調整できます（DEBUG/INFO/...）。
- .env 自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してから起動してください（テスト時など）。
- unit tests は本 README 時点のソースには含まれていませんが、各モジュールは引数注入（conn / id_token 等）をサポートしているため、モックを使った単体テストが容易です。

ライセンス / 責任
----------------
この README はコードベースの概要と利用例を示すためのものであり、実運用に際しては十分な検証・テスト・セキュリティ対策（特に発注関連）を行ってください。実際の証券取引に使用する場合、法令遵守・運用監査・リスク管理を必ず整備してください。

お問い合わせ
------------
実装上の疑問や拡張要望があれば、コードの該当モジュール（例: data/jquants_client.py, strategy/signal_generator.py）を参照し、Issue を作成してください。