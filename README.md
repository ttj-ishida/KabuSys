KabuSys — 日本株自動売買基盤（README）
=================================

概要
----
KabuSys は日本株向けのデータ基盤・戦略実行レイヤーを備えた自動売買システム向けライブラリ群です。  
主に以下を提供します。

- J-Quants API からのデータ取得クライアント（株価・財務・カレンダー）
- DuckDB を用いたローカルデータベーススキーマと初期化ロジック
- ETL パイプライン（差分取得、保存、品質チェック）
- ニュース収集（RSS）と記事→銘柄紐付け
- 研究（research）向けのファクター計算・特徴量探索ツール
- 戦略用の特徴量生成（features）とシグナル生成（signals）
- 発注／監査用のスキーマ（Execution / audit）

設計方針のハイライト
- ルックアヘッドバイアスを避けるため、target_date 時点のデータのみで計算
- DuckDB へは冪等的（ON CONFLICT）に保存
- ネットワーク操作はレート制御・リトライ・トークン自動リフレッシュ等を考慮
- 外部依存を最小化（pandas 等に依存しない純 Python 実装）

主な機能一覧
----------------
- data:
  - jquants_client: J-Quants API の取得・保存（fetch_* / save_*）
  - schema: DuckDB スキーマ定義と init_schema()/get_connection()
  - pipeline: 日次 ETL（run_daily_etl）、個別 ETL（run_prices_etl 等）
  - news_collector: RSS 収集、テキスト前処理、raw_news 保存、銘柄抽出
  - calendar_management: market_calendar の更新と営業日ユーティリティ
  - stats: zscore_normalize（クロスセクション正規化）
- research:
  - calc_momentum / calc_volatility / calc_value（ファクター計算）
  - calc_forward_returns / calc_ic / factor_summary（探索解析用）
- strategy:
  - build_features: raw ファクターを統合・正規化して features テーブルへ格納
  - generate_signals: features と ai_scores を統合して BUY/SELL シグナル作成
- config:
  - 環境変数・.env 読み込み（自動ロード機能付き。無効化可）
- execution, monitoring, audit:
  - データベース上の実行・監査用スキーマを含む（orders/trades/positions 等）

前提 / 要求環境
---------------
- Python 3.10+
  - 型ヒントで PEP 604（X | Y）等を使用しているため 3.10 以上を推奨します。
- 推奨パッケージ（例）
  - duckdb
  - defusedxml
- ネットワーク API 利用には J-Quants のリフレッシュトークンが必要

セットアップ手順
----------------
1. リポジトリをクローンする
   - 例: git clone <repo-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージをパッケージとして使う場合）pip install -e .

4. 環境変数を設定
   - プロジェクトルートに .env または .env.local を置くと自動でロードされます（自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須環境変数（config.Settings 参照）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD : kabuステーション API のパスワード（発注を行う場合）
     - SLACK_BOT_TOKEN : Slack 通知用トークン（必要に応じて）
     - SLACK_CHANNEL_ID : Slack チャネルID
   - 任意/デフォルト:
     - KABUSYS_ENV : development / paper_trading / live（デフォルト development）
     - LOG_LEVEL : DEBUG/INFO/etc（デフォルト INFO）
     - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH : モニタリング用 SQLite（デフォルト data/monitoring.db）

サンプル .env（参考）
-------------------
例:
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

使い方（代表的なワークフロー）
----------------------------

1) DuckDB スキーマ初期化
- Python REPL / スクリプト例:

from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")

- ":memory:" を渡すとインメモリ DB を使用します。

2) 日次 ETL の実行（株価/財務/カレンダー取得 + 品質チェック）
- run_daily_etl を呼ぶ例:

from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

3) ニュース収集ジョブ
- RSS フィードから収集して DB に保存し、既知銘柄に紐付ける:

from kabusys.data.news_collector import run_news_collection
# conn は init_schema あるいは get_connection で取得
known_codes = {"7203", "6758", "9984"}  # 例
res = run_news_collection(conn, sources=None, known_codes=known_codes)
print(res)

4) 特徴量の作成（strategy.build_features）
- DuckDB 接続と target_date を渡すだけで features テーブルを作成（置換）します:

from datetime import date
from kabusys.strategy import build_features
count = build_features(conn, date(2024, 1, 5))
print(f"features upserted: {count}")

5) シグナル生成（strategy.generate_signals）
- features / ai_scores / positions を参照し signals テーブルへ書き込みます:

from kabusys.strategy import generate_signals
num = generate_signals(conn, date(2024, 1, 5))
print(f"signals written: {num}")

6) J-Quants の直接利用（データ取得 / DB 保存）
- jquants_client は fetch_* / save_* を分離しており、テスト用に id_token を注入できます:

from kabusys.data import jquants_client as jq
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,5))
saved = jq.save_daily_quotes(conn, records)

注意点 / 運用上のポイント
------------------------
- 環境変数は必須チェックを行います（config.Settings._require）。.env.example を参考にセットしてください。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です。
- J-Quants API のレート制限やエラーに対してはクライアントにリトライ・レートリミットが組み込まれていますが、APIキーの管理・モニタリングは運用者で行ってください。
- DuckDB のデータ永続化先は DUCKDB_PATH で指定。バックアップやローテーションを適切に行ってください。

ディレクトリ構成（主要ファイル）
-----------------------------
src/kabusys/
- __init__.py
- config.py  — 環境変数管理・自動 .env 読込み
- data/
  - __init__.py
  - jquants_client.py  — J-Quants API クライアント（fetch/save）
  - schema.py          — DuckDB スキーマ定義と init_schema()
  - pipeline.py        — ETL パイプライン（run_daily_etl 等）
  - news_collector.py  — RSS 収集 / テキスト処理 / DB 保存
  - stats.py           — zscore_normalize 等の統計ユーティリティ
  - calendar_management.py — market_calendar 管理ユーティリティ
  - audit.py           — 監査ログスキーマ（signal_events / order_requests / executions）
  - features.py        — data.stats の再エクスポート
- research/
  - __init__.py
  - factor_research.py — calc_momentum / calc_value / calc_volatility
  - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank
- strategy/
  - __init__.py
  - feature_engineering.py — build_features
  - signal_generator.py    — generate_signals
- execution/             — 発注周り（プレースホルダ）
- monitoring/            — 監視用モジュール（プレースホルダ）

開発・テスト
------------
- 単体関数は外部依存（ネットワーク）を注入可能な設計です（例: id_token を渡せる、_urlopen をモックできる等）。ユニットテストは外部呼び出しをモックして実行してください。

ライセンス / 貢献
-----------------
- （リポジトリの LICENSE に従ってください）
- バグ報告・プルリクエストは issue/PR にてお願いします。

補足
----
- README に書かれている関数名や挙動はコード中の docstring に基づきます。実運用前には小さな範囲での試験運用（paper_trading 環境）を強く推奨します。
- 本 README はコードベースの概要と使い方の導入を目的としています。詳細な API 仕様やデータモデル（DataSchema.md / StrategyModel.md 等）については別ドキュメントを参照してください。