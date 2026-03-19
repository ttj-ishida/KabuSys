KabuSys
=======

バージョン: 0.1.0

概要
----
KabuSys は日本株向けの自動売買プラットフォーム用ライブラリです。  
J-Quants API からのデータ取得（株価・財務・市場カレンダー）、DuckDB によるデータ管理、特徴量作成、シグナル生成、ニュース収集、監査ログ／実行レイヤのスキーマ定義など、データプラットフォームから戦略実行までの基本的な機能群を提供します。

主な特徴
--------
- J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
- DuckDB ベースのデータスキーマ（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ファクター計算（Momentum / Volatility / Value 等）
- 特徴量エンジニアリング（Zスコア正規化・ユニバースフィルタ）
- シグナル生成（最終スコア計算、BUY/SELL ロジック、Bear レジーム抑制）
- ニュース収集（RSS 取得・トラッキングパラメータ除去・SSRF 対策）
- 監査ログ（シグナル→オーダー→約定までのトレーサビリティ）
- 自動的な .env 読み込み（プロジェクトルートの .env / .env.local）

セットアップ
---------

前提
- Python 3.10 以上（型注釈に PEP 604 の | 記法等を使用）
- duckdb
- defusedxml

インストール（開発・ローカル）
1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

3. パッケージとしてインストールする場合（プロジェクトルートに pyproject.toml/ setup がある想定）
   - pip install -e .

環境変数 / .env
- プロジェクトルートに .env または .env.local を置くと自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能）。
- 主要な必須環境変数:
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
  - KABU_API_PASSWORD     : kabuステーション API パスワード（実行環境で使用）
  - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（通知機能使用時）
  - SLACK_CHANNEL_ID      : Slack チャネル ID
- 任意 / デフォルト:
  - KABUSYS_ENV (development | paper_trading | live) デフォルト: development
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) デフォルト: INFO
  - DUCKDB_PATH デフォルト: data/kabusys.duckdb
  - SQLITE_PATH デフォルト: data/monitoring.db

使い方（簡易ガイド）
------------------

1) データベース初期化
- DuckDB スキーマを作成するには init_schema を使います。

例:
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # ファイルがなければ親ディレクトリを作成して初期化

テストや一時実行では ":memory:" を渡すとインメモリ DB が使えます:
conn = init_schema(":memory:")

2) 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定しなければ今日を対象
print(result.to_dict())

3) 市場カレンダー更新ジョブ
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"saved calendar rows: {saved}")

4) ニュース収集（RSS）
from kabusys.data.news_collector import run_news_collection

# known_codes は銘柄抽出時に利用する valid code の集合（optional）
res = run_news_collection(conn, known_codes=set(["7203", "6758"]))
print(res)  # ソース毎の新規保存数

5) 特徴量作成（feature engineering）
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, date(2025, 1, 15))
print(f"features upserted: {n}")

6) シグナル生成
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, date(2025, 1, 15))
print(f"signals generated: {count}")

7) 研究用ユーティリティ
- ファクターの計算（research）や forward returns / IC 計算などは kabusys.research 以下にまとめられています。
  例: calc_forward_returns, calc_ic, factor_summary, rank

API の設計上の注意
- build_features / generate_signals は DuckDB の接続オブジェクトを受け取り、該当日付のみのデータで処理を行います（ルックアヘッドバイアス対策）。
- jquants_client は内部でトークンキャッシュ・レートリミッタ・リトライを実装しています。必要に応じて id_token を注入してテスト可能です。
- NewsCollector は SSRF 対策・XML 疑似攻撃対策（defusedxml）・受信サイズ制限などを実施しています。
- ETL は差分更新（バックフィル）を行い、ON CONFLICT を使って冪等保存します。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py                  : パッケージのエントリ（__version__ = "0.1.0"）
- config.py                    : 環境変数 / 設定管理（自動 .env ロード・設定オブジェクト）
- data/
  - __init__.py
  - jquants_client.py          : J-Quants API クライアント + 保存ユーティリティ
  - news_collector.py         : RSS ニュース収集 / 保存ロジック
  - schema.py                 : DuckDB スキーマ定義と init_schema / get_connection
  - pipeline.py               : ETL パイプライン（run_daily_etl 等）
  - features.py               : features 用のユーティリティ再エクスポート
  - stats.py                  : zscore_normalize などの統計ユーティリティ
  - calendar_management.py    : market_calendar 管理と営業日ユーティリティ
  - audit.py                  : 監査ログ用 DDL（signal_events, order_requests, executions）
  - ...（その他の data 関連モジュール）
- research/
  - __init__.py
  - factor_research.py        : momentum/volatility/value ファクター計算
  - feature_exploration.py    : calc_forward_returns / calc_ic / factor_summary / rank
- strategy/
  - __init__.py
  - feature_engineering.py    : build_features（正規化・ユニバースフィルタ等）
  - signal_generator.py       : generate_signals（final_score 計算 / BUY/SELL 判定）
- execution/                   : 発注 / execution 関連（未実装箇所あり）
- monitoring/                  : 監視/モニタリング関連（DB: sqlite 等を想定）

設定例（.env）
--------------
# .env (プロジェクトルート)
JQUANTS_REFRESH_TOKEN=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb

開発・テストのヒント
-------------------
- 自動 .env 読み込みを無効にする:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- テストや簡易実行には DuckDB のインメモリ ":memory:" を利用すると便利:
  conn = init_schema(":memory:")
- jquants_client の外部呼び出しは urllib を使っているため、テストでは _request / _urlopen 等をモックして HTTP を切り替えてください。
- news_collector._urlopen をモックすることで RSS フェッチをローカルテスト可能です。

ライセンス・貢献
----------------
（このリポジトリのライセンス情報や貢献方法をここに記載してください）

お問い合わせ
----------
不具合報告や質問があれば issue を作成してください。README に含める連絡先や Slack ワークスペース等を適宜追加してください。

以上。