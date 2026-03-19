KabuSys
=======

バージョン: 0.1.0

概要
----
KabuSys は日本株向けのデータプラットフォーム兼自動売買フレームワークです。  
J-Quants API から市場データ／財務データを取得して DuckDB に保存し、研究環境で計算した生ファクターを正規化・合成して特徴量（features）を構築、戦略シグナル（buy / sell）を生成することを主な目的としています。  
設計上、発注・ブローカー連携などの execution 層は分離され、各モジュールは冪等性・ロギング・ルックアヘッドバイアス回避を重視して実装されています。

主な特徴
--------
- データ取得（J-Quants）:
  - 日足（OHLCV）、四半期財務、マーケットカレンダーをページネーション対応で取得
  - レート制限、リトライ、トークン自動リフレッシュ対応
- データ格納（DuckDB）:
  - Raw / Processed / Feature / Execution の多層スキーマを用意（init_schema で初期化）
  - 保存処理は冪等（ON CONFLICT / UPDATE）で再実行可能
- ETL パイプライン:
  - 差分取得・バックフィル・品質チェックを備えた日次 ETL（run_daily_etl）
- 特徴量作成:
  - Research モジュールで算出した生ファクターを Z スコア正規化・クリップし features テーブルへ UPSERT（build_features）
- シグナル生成:
  - features と ai_scores を統合して final_score を算出、BUY / SELL シグナルを生成・保存（generate_signals）
  - Bear レジーム判定やエグジット（ストップロス等）ロジックを実装
- ニュース収集:
  - RSS フィードを安全に取得・前処理して raw_news に保存、記事⇄銘柄の紐付け機能
- マーケットカレンダー管理:
  - 営業日判定・次/前の営業日取得・期間の営業日リスト化・夜間バッチ更新ジョブをサポート
- ネットワーク／セキュリティ対策:
  - SSRF 対策、XML の安全パース、受信サイズ制限、プライベートIPブロック等

必須環境変数（代表例）
---------------------
最低限設定が必要な環境変数（README では代表的なものを記載）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token で使用）
- KABU_API_PASSWORD: kabuステーション等の発注 API パスワード（execution モジュールで使用）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
- KABUSYS_ENV: 環境（development / paper_trading / live）。デフォルトは development
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）。デフォルト INFO
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）

注意: 自動で .env / .env.local をプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

セットアップ
----------
前提:
- Python 3.9+（typing 拡張を用いているため推奨）
- pip/env ツール

1. リポジトリをクローン
   - git clone ... && cd your-repo

2. 仮想環境を作成して有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   必要なパッケージ（代表例）:
   - duckdb
   - defusedxml

   例:
   - pip install duckdb defusedxml

   （プロジェクトに pyproject.toml/requirements.txt があればそれに従ってください）
   開発インストール（package が用意されている場合）:
   - pip install -e .

4. 環境変数設定
   プロジェクトルートに .env または .env.local を作成して必要な環境変数を設定してください。例（.env）:
   JQUANTS_REFRESH_TOKEN=あなたのトークン
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development

5. DuckDB スキーマ初期化
   Python から init_schema を呼び出すことで DB ファイルを作成し、テーブルを初期化できます（data ディレクトリは自動作成されます）。

使い方（簡単な例）
-----------------

1) DuckDB スキーマの初期化
- Python REPL またはスクリプトで:

from kabusys.data.schema import init_schema, get_connection
conn = init_schema("data/kabusys.duckdb")
# あるいは既存 DB に接続するだけなら:
# conn = get_connection("data/kabusys.duckdb")

2) 日次 ETL の実行
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定しなければ今日が対象
print(result.to_dict())

3) 特徴量の構築（ETL 後に）
from datetime import date
from kabusys.strategy import build_features
cnt = build_features(conn, date.today())
print(f"features upserted: {cnt}")

4) シグナル生成
from kabusys.strategy import generate_signals
total = generate_signals(conn, date.today(), threshold=0.6)
print(f"signals generated: {total}")

5) ニュース収集（RSS）
from kabusys.data.news_collector import run_news_collection
results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(results)

6) カレンダー関係ユーティリティ
from kabusys.data.calendar_management import is_trading_day, next_trading_day
import datetime
d = datetime.date(2024, 1, 1)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))

設定参照
-------
環境変数は kabusys.config.settings から安全に参照できます:

from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
if settings.is_live:
    print("live モードです")

主要モジュール概要
-----------------
- kabusys.config
  - .env 自動読み込み（プロジェクトルートを基準）、必須変数チェック、環境判定。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを抑制可能。

- kabusys.data
  - jquants_client: J-Quants API クライアント（トークン管理、リトライ、ページング、保存用ユーティリティ）
  - schema: DuckDB スキーマ定義と init_schema/get_connection
  - pipeline: run_daily_etl / 個別 ETL ジョブ（prices / financials / calendar）
  - news_collector: RSS 収集、正規化、保存、銘柄抽出
  - calendar_management: 営業日判定やカレンダー更新ジョブ
  - stats: zscore_normalize 等の統計ユーティリティ
  - features: zscore_normalize のエクスポート

- kabusys.research
  - factor_research: Momentum / Volatility / Value 等の生ファクター計算（prices_daily / raw_financials のみ参照）
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー

- kabusys.strategy
  - feature_engineering.build_features: raw factor を統合 → features テーブルへ UPSERT
  - signal_generator.generate_signals: features + ai_scores により final_score を算出 → signals テーブルへ書き込み

- kabusys.data.jquants_client の注意点
  - API レートは 120 req/min、内部で固定間隔スロットリングを実装
  - 401 受信時はリフレッシュトークンで自動更新して再試行
  - 408/429/5xx に対して指数バックオフでリトライ

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py
  - news_collector.py
  - schema.py
  - stats.py
  - pipeline.py
  - features.py
  - calendar_management.py
  - audit.py
  - calendar_management.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- strategy/
  - __init__.py
  - feature_engineering.py
  - signal_generator.py
- execution/
  - __init__.py
（上記は本リポジトリに含まれる主要ファイルを抜粋しています）

運用上の注意
------------
- DuckDB のファイルパス（DUCKDB_PATH）は settings.duckdb_path で参照されます。複数プロセスからの同一ファイル書き込みには注意してください（プロセス設計を検討）。
- ETL は外部 API に依存するため一時的な失敗が発生します。run_daily_etl は個々のステップを独立してエラーハンドリングし、結果を ETLResult で返します。
- シグナル→発注→注文管理のフローを本番運用する場合は execution 層でブローカー特有の冪等・確認ロジックを適切に実装してください（本コードは戦略側のシグナル生成と監査ログ設計を提供します）。
- ニュース収集は RSS のレイアウト差異や未標準のフィードに対して寛容に作られていますが、外部ソースの変更でパースが失敗することがあります。エラーはログで確認してください。

貢献・開発
-----------
- 開発環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env 読み込みを無効化できます（テスト等で便利）。
- 新しいテーブルを追加する場合は schema._ALL_DDL に DDL を追加し、init_schema のトランザクション内で実行してください。
- 単体テスト、モック（jquants_client の _request や news_collector の _urlopen を置き換える）を使ってネットワーク依存を切り離すことを推奨します。

ライセンス
--------
（ここにライセンス情報を記載してください。例: MIT 等）

問い合わせ
---------
不具合報告や設計相談はリポジトリの Issue を利用してください。README の改善提案も歓迎します。

-----  
この README はリポジトリ内の実装に基づいて作成しています。実際の運用前に .env の内容、DB バックアップ方針、発注ルール等を十分に検討してください。