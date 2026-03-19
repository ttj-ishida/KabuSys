# KabuSys

日本株向けの自動売買システム用ライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査・スキーマ管理などを含むモジュール群を提供します。

> 本リポジトリはライブラリ/内部ツール群を想定した実装であり、実際の発注や運用にあたっては十分な検証とリスク管理が必要です。

## 主な特徴
- J-Quants API クライアント（ページネーション、レート制御、リトライ、トークン自動リフレッシュ）
- DuckDB を用いたデータスキーマ（Raw / Processed / Feature / Execution 層）と初期化関数
- ETL パイプライン（差分取得・バックフィル・品質チェック統合）
- ファクター計算（Momentum / Volatility / Value 等）および Z スコア正規化ユーティリティ
- 戦略用特徴量ビルド（ユニバースフィルタ、正規化、日次 UPSERT）
- シグナル生成（最終スコア計算、買い/売りシグナル生成、売却ルール）
- ニュース収集（RSS 取得、前処理、記事保存、銘柄抽出、SSRF 対策）
- マーケットカレンダー管理（JPXカレンダー取り込み、営業日判定）
- 監査ログ（シグナル→発注→約定 のトレーサビリティ用スキーマ）

## 必要な環境変数
config.Settings から参照される主な環境変数（必須は README に明示）:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API パスワード（発注連携する場合）
- SLACK_BOT_TOKEN — Slack 通知を行う場合の Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャネル ID

任意（デフォルト値あり）:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）

自動 .env ロード:
- リポジトリのルート（.git または pyproject.toml が存在するディレクトリ）にある `.env` と `.env.local` を自動で読み込みます。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

## セットアップ手順（開発者向け）
1. リポジトリをクローン:
   git clone <repo-url>
2. Python 仮想環境を作成・有効化（例）:
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
3. 必要パッケージをインストール（例）:
   pip install duckdb defusedxml
   ※ requirements.txt がある場合は `pip install -r requirements.txt` を推奨します。
4. 環境変数を設定:
   - プロジェクトルートに `.env` を作成して上記必須変数を設定してください（.env.example を参照）。
   - 例:
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUS_API_PASSWORD=your_password
5. データベース初期化:
   - DuckDB スキーマを初期化するには Python REPL またはスクリプトで次を実行してください。

   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

## 使い方（主要ワークフロー例）
以下は典型的なデイリー処理の流れ例です。

1) DuckDB 接続作成 / スキーマ初期化
- 初回は init_schema() を使い、以後は get_connection() を利用できます。

from kabusys.data.schema import init_schema, get_connection
conn = init_schema("data/kabusys.duckdb")
# または既存 DB へ接続
# conn = get_connection("data/kabusys.duckdb")

2) 日次 ETL を実行（株価・財務・カレンダー取得 + 品質チェック）
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定することも可能
print(result.to_dict())

3) 特徴量（features）を構築
from datetime import date
from kabusys.strategy import build_features
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")

4) シグナル生成
from kabusys.strategy import generate_signals
num_signals = generate_signals(conn, target_date=date.today())
print(f"signals written: {num_signals}")

5) ニュース収集ジョブの実行
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
# known_codes は銘柄抽出に使う有効な銘柄コード集合
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(results)

6) カレンダー夜間更新
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")

7) 監査・発注フローや execution 層との連携は別モジュール（execution）を利用して実装します。

## 主なモジュール / API（抜粋）
- kabusys.config
  - settings: 環境変数ラッパー（JQUANTS_REFRESH_TOKEN 等）
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token（トークン取得）
- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
- kabusys.data.pipeline
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, run_news_collection
- kabusys.data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.strategy
  - build_features, generate_signals
- kabusys.data.stats
  - zscore_normalize

## ディレクトリ構成
（主要ファイルのみ抜粋）
- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - audit.py
    - stats.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/
    - __init__.py  (発注層の実装を収容)
  - monitoring/    (監視・運用関連モジュールを配置想定)

## 開発メモ / 設計方針の抜粋
- データの取り扱いは DuckDB を中核とし、「Raw → Processed → Feature → Execution」の層で管理。
- J-Quants クライアントはレート制限とリトライ・トークン更新を備え、取得時刻（fetched_at）を UTC で記録してルックアヘッドバイアスを可視化。
- ETL と戦略ロジックはルックアヘッドバイアスを避ける設計（target_date 時点のデータのみ参照）。
- ニュース収集は SSRF 対策 / XML の安全パーサ（defusedxml） / レスポンスサイズ上限のガードを実装。
- DB 操作は冪等性を重視（ON CONFLICT DO UPDATE / DO NOTHING）し、トランザクションで日付単位の置換を行う。

## テスト・デバッグ
- 自動 .env 読み込みを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 各関数は引数でトークンや接続を注入できるためユニットテストが容易です（モジュールレベルのネットワーク呼び出しはモック推奨）。

## ライセンス / 貢献
- ライセンス情報・貢献ルールはリポジトリのトップレベルファイル（LICENSE / CONTRIBUTING）を参照してください。

---

問題・改善提案や実運用に関する質問があれば、お知らせください。README の追加項目（例: example .env、CI/CD、デプロイ手順）を作成できます。