KabuSys
=======

KabuSys は日本株の自動売買プラットフォームのコアライブラリです。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなど、戦略実行に必要な主要コンポーネントを提供します。

主な設計方針
- ルックアヘッドバイアス防止：target_date 時点までのデータのみを使用するよう実装
- 冪等性：DB への INSERT は ON CONFLICT 等で上書き/排他を担保
- 外部依存を最小化：主要統計処理は標準ライブラリ + DuckDB ベースで実装
- 安全性：RSS の SSRF 対策、XML パース安全化（defusedxml）などを実装

機能一覧
---------
- 環境設定管理
  - .env / .env.local 自動読み込み（優先順位: OS 環境変数 > .env.local > .env）
  - 必須変数の検証（不足時は例外）
- データ取得（J-Quants）
  - 株価日足（OHLCV）、財務データ、マーケットカレンダーの取得（ページネーション対応）
  - レート制限、リトライ、トークン自動リフレッシュ
- ETL（data.pipeline）
  - 差分取得、保存（冪等）、品質チェック呼び出し
  - 日次 ETL 実行用の run_daily_etl
- スキーマ管理（DuckDB）
  - init_schema による全テーブル作成（raw/processed/feature/execution 層）
- 特徴量計算（research.factor_research / strategy.feature_engineering）
  - Momentum / Volatility / Value 等のファクター計算
  - Z スコア正規化・ユニバースフィルタ適用・features テーブルへの保存
- シグナル生成（strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを生成し signals テーブルへ保存
  - Bear レジーム抑制、エグジット（ストップロス等）判定
- ニュース収集（data.news_collector）
  - RSS フィード取得、前処理、raw_news 保存、銘柄コード抽出と紐付け
  - SSRF 対策、gzip サイズ検査、defusedxml による安全パース
- カレンダー管理（data.calendar_management）
  - market_calendar の取得・更新、営業日/前後営業日判定、範囲内営業日取得
- 監査ログ（data.audit）
  - signal → order → execution のトレーサビリティ用テーブル群

セットアップ手順
----------------

前提
- Python 3.10+（typing と構文に依存）
- DuckDB が Python 環境でインストールされていること

インストール（開発中想定）
1. このパッケージを開発インストール:
   pip install -e .

2. 必要パッケージをインストール（例）:
   pip install duckdb defusedxml

※ 実際のプロジェクトでは pyproject.toml / requirements.txt を参照してください。

環境変数
- 必須（Settings._require により未設定時は ValueError）:
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD : kabuステーション API のパスワード
  - SLACK_BOT_TOKEN : Slack 通知用ボットトークン
  - SLACK_CHANNEL_ID : Slack 通知先チャンネル ID
- 任意 / デフォルト:
  - KABUSYS_ENV : development / paper_trading / live （デフォルト development）
  - LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
  - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH : 監視用 SQLite（デフォルト data/monitoring.db）
- 自動 .env ロード:
  - プロジェクトルート（.git または pyproject.toml を探索）に .env, .env.local があれば自動読み込み
  - 自動読み込みを無効化する場合:
    export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

推奨 .env（例）
- .env.example を参照して作成してください（プロジェクトに例ファイルを置く想定）
- 最小例:
  JQUANTS_REFRESH_TOKEN=xxxx
  KABU_API_PASSWORD=yyyy
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C01234567
  KABUSYS_ENV=development
  LOG_LEVEL=INFO

使い方（簡単なワークフロー例）
-----------------------------

以下は基本的な起動手順の例（Python スクリプトまたは REPL）です。

1) DuckDB スキーマ初期化
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # デフォルト data/kabusys.duckdb にファイル作成

2) 日次 ETL 実行（市場カレンダー・株価・財務の差分取得）
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())

3) 特徴量作成（feature テーブルの構築）
from datetime import date
from kabusys.strategy import build_features

target = date.today()  # または ETL の実行日（営業日に調整）
n_features = build_features(conn, target)
print("features upserted:", n_features)

4) シグナル生成
from kabusys.strategy import generate_signals

n_signals = generate_signals(conn, target)
print("signals written:", n_signals)

5) ニュース収集（RSS）
from kabusys.data.news_collector import run_news_collection
known = {"7203", "6758", "9984"}  # 既知銘柄セット（DB から取得して渡すのが理想）
res = run_news_collection(conn, known_codes=known)
print(res)

6) カレンダー夜間更新ジョブ（バッチ）
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("calendar saved:", saved)

注意点 / 実運用のヒント
- run_daily_etl は内部で market_calendar を先に取得し、target_date を営業日に調整します。
- ETL の差分ロジックは DB 内の最終取得日を基に backfill（デフォルト 3 日）します。必要なら引数で上書き可能です。
- DuckDB のパスは Settings.duckdb_path（デフォルト data/kabusys.duckdb）で指定されます。":memory:" を渡すとインメモリ DB で動作します（テスト向け）。
- J-Quants API のレート制限（120 req/min）に対応するため、API クライアントで間隔制御と retry を行っています。
- RSS フィード取得は外部ネットワークに依存するため、実運用ではタイムアウト・エラーハンドリングを監視してください。
- ai_scores 等の外部スコアは本 README の範囲外です。AI スコアを組み込む場合は ai_scores テーブルに日次で書き込むことでシグナル生成に反映されます。

ディレクトリ構成（主要ファイル）
-------------------------------

src/kabusys/
- __init__.py
- config.py                     -- 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py           -- J-Quants API クライアント（取得・保存）
  - schema.py                   -- DuckDB スキーマ定義と init_schema
  - pipeline.py                 -- ETL パイプライン（run_daily_etl など）
  - stats.py                    -- 統計ユーティリティ（zscore_normalize）
  - features.py                 -- data.stats の再エクスポート
  - news_collector.py           -- RSS ニュース収集・保存・銘柄抽出
  - calendar_management.py      -- market_calendar 管理、営業日判定
  - audit.py                    -- 発注・約定の監査ログ用テーブル定義
  - pipeline.py                 -- ETL フロー（同上）
- research/
  - __init__.py
  - factor_research.py          -- Momentum / Volatility / Value 等の計算
  - feature_exploration.py      -- IC, forward returns, factor summary
- strategy/
  - __init__.py
  - feature_engineering.py      -- features を作成して DB に保存
  - signal_generator.py         -- final_score 計算と signals 書き込み
- execution/                     -- 発注 / ブローカー連携用層（プレースホルダ）
- monitoring/                    -- 監視・メトリクス関連（プレースホルダ）

（注）上記はリポジトリの主要モジュール一覧です。細かい補助関数や内部実装は各ファイル内のドキュメント参照。

開発・テストについて
--------------------
- 設定読み込みは .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動で探して読み込みます。テスト時に自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB をインメモリで使うとテストが容易です: init_schema(":memory:")
- ネットワーク依存部分（jquants_client._request, _urlopen 等）はユニットテストでモックしてください。

ライセンス / 貢献
-----------------
この README にはライセンス情報は含まれていません。実際のリポジトリでは LICENSE ファイルを追加してください。  
バグ報告・機能提案は issue を立ててください。プルリクエスト歓迎。

補足
----
- 内部の実装や仕様（StrategyModel.md, DataPlatform.md 等）への言及がソース内にあります。実運用・チューニングを行う場合はそれらのドキュメントに従って設定・重み・閾値を調整してください。
- Slack 通知や実際の発注を有効にする際は、まず paper_trading 環境で十分に検証してください（KABUSYS_ENV=paper_trading）。

以上。必要であれば README に含めるサンプルスクリプトや詳細な環境変数一覧、実行時の CLI ラッパー例（cron / Airflow ジョブ化）などを追加します。どの情報を拡張しますか？