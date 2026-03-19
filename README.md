KabuSys
======

日本株向けの自動売買／データ基盤ライブラリ（DuckDB ベース）。  
市場データ取得、ETL、ファクター計算、特徴量エンジニアリング、シグナル生成、ニュース収集、監査ログ等の機能をモジュール化して提供します。

概要
----
KabuSys は以下を目的とした内部ライブラリ群です。

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存
- データ品質チェック・差分 ETL（バックフィル対応）
- ファクター計算（Momentum / Value / Volatility / Liquidity）
- クロスセクション Z スコア正規化・特徴量生成
- AI スコアと統合したシグナル生成（BUY / SELL）
- RSS ベースのニュース収集と銘柄紐付け（SSRF 対策、トラッキング除去）
- 発注／約定／ポジション等の監査ログスキーマ（トレーサビリティ）

主な機能一覧
--------------
- データ取得・保存
  - J-Quants クライアント（rate limit、リトライ、トークン自動更新）
  - raw_prices / raw_financials / market_calendar への冪等保存
- ETL
  - 日次 ETL（calendar / prices / financials）: 差分取得、backfill、品質チェック
  - calendar_update_job（JPX カレンダーの夜間更新）
- データスキーマ
  - DuckDB 用のスキーマ初期化（init_schema）
  - 各層（raw / processed / feature / execution）のテーブル定義
- 研究・戦略
  - factor_research: calc_momentum, calc_volatility, calc_value
  - feature_engineering: build_features（Zスコア正規化・ユニバースフィルタ・features テーブルへ UPSERT）
  - signal_generator: generate_signals（final_score 計算、BUY/SELL 生成、signals テーブルへ UPSERT）
  - research utilities: IC 計算、forward returns、factor summary
- ニュース収集
  - RSS フィード取得（XML パース安全化、gzip 上限、SSRF 防止）
  - raw_news / news_symbols への冪等保存
  - 銘柄コード抽出（4 桁コードの抽出・既知コードフィルタ）
- ユーティリティ
  - 統計補助（zscore_normalize）
  - 設定管理（.env 自動ロード、必須環境変数の検証）
  - 監査ログ（signal_events / order_requests / executions 等）

前提／依存
-----------
- Python 3.10 以上（型ヒントに | を使用しているため）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリの urllib、json 等を使用

セットアップ手順
----------------

1. リポジトリをクローンして仮想環境を作成・有効化（例: venv, pyenv 等）

   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows (PowerShell)

2. 必要パッケージをインストール

   python -m pip install --upgrade pip
   python -m pip install duckdb defusedxml

   （プロジェクトに setup.cfg / pyproject.toml / requirements.txt がある場合はそちらに従ってください。）

3. 環境変数設定
   プロジェクトルートに .env / .env.local を置くことで自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   README に示す主な必須環境変数:
   - JQUANTS_REFRESH_TOKEN  (必須) — J-Quants API のリフレッシュトークン
   - KABU_API_PASSWORD      (必須) — kabuステーション API パスワード（execution 層利用時）
   - SLACK_BOT_TOKEN        (必須) — Slack 通知用（必要時）
   - SLACK_CHANNEL_ID       (必須) — Slack チャンネル ID

   オプション:
   - KABUSYS_ENV (development|paper_trading|live) デフォルト: development
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) デフォルト: INFO
   - KABU_API_BASE_URL デフォルト: http://localhost:18080/kabusapi
   - DUCKDB_PATH デフォルト: data/kabusys.duckdb
   - SQLITE_PATH デフォルト: data/monitoring.db

   ※ settings に不足があると起動時に ValueError が発生します。

4. データベース初期化（DuckDB）
   Python REPL またはスクリプトから:

   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   # conn は duckdb.DuckDBPyConnection

使い方（主要ワークフロー例）
-------------------------

1) 日次 ETL を実行（市場カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック）

from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

2) 特徴量構築（features テーブル作成）

from datetime import date
from kabusys.strategy import build_features
build_count = build_features(conn, date(2024, 1, 1))
print(f"features upserted: {build_count}")

3) シグナル生成（ai_scores を併用可能）

from datetime import date
from kabusys.strategy import generate_signals

total_signals = generate_signals(conn, date(2024, 1, 1))
print(f"signals generated: {total_signals}")

- 重みや閾値をカスタム指定することも可能:
  generate_signals(conn, target_date, threshold=0.65, weights={"momentum":0.5, "value":0.2, ...})

4) ニュース収集（RSS → raw_news / news_symbols）

from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は既知の銘柄コードセット（抽出用）
# conn は DuckDB 接続
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(results)

5) J-Quants からのデータ取得（低レベル）

from kabusys.data import jquants_client as jq
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
jq.save_daily_quotes(conn, records)

設定管理
--------
- kabusys.config.Settings クラスを通して環境変数から設定値を取得します。
- .env / .env.local はプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から自動読み込みされます。
- 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主なファイル）
------------------------------

src/kabusys/
- __init__.py
- config.py                — 環境変数／設定のロードと検証
- data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント（取得・保存機能）
  - news_collector.py      — RSS ニュース収集・保存
  - schema.py              — DuckDB スキーマ定義と init_schema
  - stats.py               — zscore_normalize 等の統計ユーティリティ
  - pipeline.py            — ETL パイプライン（run_daily_etl 等）
  - features.py            — features API (再エクスポート)
  - calendar_management.py — market_calendar 管理・営業日判定
  - audit.py               — 監査ログ用 DDL
- research/
  - __init__.py
  - factor_research.py     — モメンタム／バリュー／ボラティリティ計算
  - feature_exploration.py — IC / forward returns / summary
- strategy/
  - __init__.py
  - feature_engineering.py — build_features（正規化・フィルタ）
  - signal_generator.py    — generate_signals（最終スコア計算・BUY/SELL判定）
- execution/                — 発注・execution 層（雛形）
- monitoring/               — 監視・モニタリング用（DBやSlack連携等を想定）

設計上の注意点
--------------
- ルックアヘッドバイアス回避: 計算やシグナル生成は target_date 時点で利用可能なデータのみを使用するよう設計されています。
- 冪等性: DB への保存は可能な限り ON CONFLICT / UPSERT を使い冪等に設計しています。
- エラー／品質チェック: ETL や収集処理はソース単位でエラーハンドリングし、可能な限り処理を継続します。品質チェックは run_daily_etl 内でオプション実行されます。
- セキュリティ: RSS の取得では SSRF 対策、XML パースの安全化（defusedxml）、レスポンス上限（メモリ DoS 防止）などの保護が実装されています。

開発・貢献
-----------
- 新しい機能の追加やバグ修正はモジュール単位で行ってください。
- ユニットテストは DuckDB のインメモリ接続(":memory:") を使うと容易です（schema.init_schema(":memory:")）。
- 設定の変更は config.Settings を通して行い、直接 os.environ を参照しないでください。

ライセンス
----------
（ライセンス情報がリポジトリに含まれていればここに記載してください）

補足
----
ここに記載した例は主要なワークフローの最小構成です。実運用する際はログ設定、例外監視、Slack 通知、証券会社 API（kabuステーション）との連携処理やリスク管理ロジックを実装・検証してください。