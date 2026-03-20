KabuSys — 日本株自動売買プラットフォーム
====================================

概要
----
KabuSys は日本株向けのデータ基盤・特徴量処理・シグナル生成・監査用スキーマを備えた自動売買プラットフォームのライブラリ群です。  
主に次の役割を持つコンポーネントで構成されています。

- データ取得・保存（J-Quants API 経由で株価・財務・カレンダーを取得し DuckDB に保存）
- データ品質チェック・ETL パイプライン（差分取得・バックフィル・品質検査）
- 研究モジュール（ファクター計算・特徴量探索）
- 特徴量構築・シグナル生成（Z スコア正規化、重み付け統合、BUY/SELL 生成）
- ニュース収集（RSS → raw_news、銘柄抽出）
- DuckDB スキーマ定義（Raw / Processed / Feature / Execution 層）
- 監査ログ（signal → order → execution のトレーサビリティ）

設計方針として、ルックアヘッドバイアス回避、冪等性（ON CONFLICT 等）、外部 API の rate limit およびリトライ、テスト可能性（ID トークン注入など）を重視しています。

主な機能一覧
------------
- data:
  - jquants_client: J-Quants API クライアント（ページネーション、トークン自動リフレッシュ、レート制御、retry）
  - schema: DuckDB スキーマの作成・初期化（init_schema）
  - pipeline: 日次 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS 取得・前処理・DB 保存・銘柄抽出（run_news_collection）
  - calendar_management: JPX カレンダー管理（is_trading_day / next_trading_day / calendar_update_job）
  - stats: Z スコア正規化などの統計ユーティリティ
- research:
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration: 将来リターン計算・IC 計算・統計サマリー
- strategy:
  - feature_engineering.build_features: 生ファクターの正規化と features テーブルへの保存
  - signal_generator.generate_signals: features + ai_scores を統合して BUY/SELL シグナルを生成
- audit（監査）/execution（発注/約定のスキーマ）: トレーサビリティ用テーブル群
- config:
  - Settings オブジェクトで環境変数管理（自動 .env ロード機能あり）

セットアップ手順
---------------
1. Python バージョン
   - Python 3.10 以上を推奨（型注釈に 3.10 構文を使用）

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - 最低限の依存: duckdb, defusedxml
   - 例:
     - pip install duckdb defusedxml
   - プロジェクトをパッケージ化している場合:
     - pip install -e .

4. 環境変数 / .env
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数（必須のもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants の refresh token（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用（必須）
     - SLACK_CHANNEL_ID — Slack チャネルID（必須）
   - オプション・デフォルト:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化するには 1 を設定
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
   - .env.example 相当のファイルをプロジェクトルートに置いておくことを想定しています。

使い方（簡易サンプル）
--------------------

※ 下記は Python REPL / スクリプトでの使用例です。実行前に環境変数（JQUANTS_REFRESH_TOKEN など）を設定してください。

1) DuckDB スキーマ初期化
- 初回は init_schema() で DB とテーブルを作成します。

from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # data/kabusys.duckdb（デフォルト）を作成して接続を返す

2) 日次 ETL を実行（データ取得 → 保存 → 品質チェック）
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())

3) 特徴量構築
from datetime import date
from kabusys.strategy import build_features

n = build_features(conn, date(2024, 1, 31))
print(f"features upserted: {n}")

4) シグナル生成
from kabusys.strategy import generate_signals

count = generate_signals(conn, date(2024, 1, 31))
print(f"signals written: {count}")

5) ニュース収集と銘柄紐付け
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄コード集合(例: {'7203','6758',...})
res = run_news_collection(conn, known_codes={'7203','6758'})
print(res)

6) カレンダー更新ジョブ（夜間バッチ）
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")

注意点 / 動作設計
-----------------
- 全ての ETL / 保存関数は基本的に冪等性を意識して実装されています（ON CONFLICT や RETURNING を活用）。
- J-Quants API へのアクセスは RateLimiter（120 req / min）を守るよう実装されています。get_id_token（リフレッシュ）、リトライ、指数バックオフを実装。
- 研究・戦略ロジックはルックアヘッドバイアスを避けるため、target_date 時点の利用可能データのみで計算するよう設計されています。
- DuckDB スキーマは Raw / Processed / Feature / Execution 層に分離されています。
- RSS ニュース収集は SSRF 対策・サイズ上限・XML の安全パーサ（defusedxml）を使用しています。

ディレクトリ構成（抜粋）
-----------------------
src/
  kabusys/
    __init__.py
    config.py                       # 環境変数・設定管理
    data/
      __init__.py
      jquants_client.py             # J-Quants API クライアント
      schema.py                     # DuckDB スキーマ初期化
      pipeline.py                   # ETL パイプライン（run_daily_etl 等）
      news_collector.py             # RSS ニュース収集/保存
      calendar_management.py        # 市場カレンダー管理
      features.py                   # 公開統計ユーティリティ（zscore）
      stats.py                      # 統計ユーティリティ（zscore_normalize）
      audit.py                      # 監査ログ DDL（signal/order/execution）
      pipeline.py
    research/
      __init__.py
      factor_research.py            # モメンタム/ボラティリティ/バリュー計算
      feature_exploration.py        # 将来リターン/IC/summary
    strategy/
      __init__.py
      feature_engineering.py        # build_features
      signal_generator.py           # generate_signals
    execution/                       # 発注・実行関連（モジュール空間あり）
      __init__.py
    monitoring/                      # 監視系（将来的な監視・通知処理）
      __init__.py

開発 / テスト
--------------
- 自動 .env 読み込みは config モジュールがプロジェクトルート（.git または pyproject.toml）を基準に探索して行います。テスト時に自動読み込みを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- モジュールは外部副作用（ネットワーク、DB）を伴うため、ユニットテストでは jquants_client の _request や network 呼び出し、news_collector の _urlopen などをモックすることを推奨します。

依存関係（主なもの）
-------------------
- duckdb
- defusedxml
- (標準ライブラリ: urllib, json, datetime, logging, etc.)

ライセンスやその他
------------------
本 README はコードベースのドキュメントから作成しています。実稼働での利用前に .env.example を作成し、API トークンや Slack 情報などの機密情報を安全に管理してください。セキュリティ（トークン管理・ネットワークアクセス制限）や取引リスクについては別途運用ルールを策定のうえご利用ください。

質問や README に追加してほしい具体的な利用シナリオ（例: バックフィル手順、cron の例、Slack 通知フローなど）があれば教えてください。必要に応じて実行コマンドやサンプルスクリプトを追記します。