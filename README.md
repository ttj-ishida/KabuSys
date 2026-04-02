KabuSys
======

概要
----
KabuSys は日本株のデータ基盤・リサーチ・自動売買支援のための Python ライブラリ群です。  
J-Quants（市場データ）の ETL、ニュース収集・NLP による銘柄センチメント評価、マーケットレジーム判定、各種ファクター計算、データ品質チェック、監査ログ（発注→約定のトレーサビリティ）などを提供します。  
主要設計方針として「ルックアヘッドバイアスを防ぐ」「DuckDB ベースのローカル DB」「外部 API 呼び出しはリトライ・フェイルセーフ」「冪等性を確保」を採用しています。

主な機能
-------
- ETL（J-Quants からの差分取得・DuckDB への保存）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- ニュース収集と NLP（OpenAI を用いた銘柄毎センチメント）
  - RSS 取得（SSRF 対策、トラッキング除去）: news_collector.fetch_rss
  - 銘柄別スコアリング（ai/news_nlp.score_news）
- 市場レジーム判定（ETF 1321 の MA とマクロ記事の LLM センチメント合成）
  - ai/regime_detector.score_regime
- リサーチ用ファクター計算
  - research/factor_research.calc_momentum / calc_value / calc_volatility
  - research/feature_exploration.calc_forward_returns, calc_ic, factor_summary, rank
- データ品質チェック（欠損・スパイク・重複・日付不整合）
  - data/quality.run_all_checks 等
- マーケットカレンダー管理（営業日判定、next/prev/get_trading_days）
  - data/calendar_management
- 監査ログ（signal → order_request → execution のトレーサビリティ）
  - data/audit.init_audit_db / init_audit_schema
- J-Quants クライアント（レート制限・リトライ・トークン自動リフレッシュ）
  - data/jquants_client

セットアップ手順
--------------
前提: Python 3.10+（typing | スタイルに合わせて適宜）を想定しています。

1. リポジトリをクローン（またはソースを配置）:
   - git clone ... （プロジェクトルートに pyproject.toml/.git がある想定）

2. 仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（例）:
   - pip install duckdb openai defusedxml
   - 追加で必要なパッケージがあれば pyproject.toml / requirements.txt を参照してください。

4. 環境変数（.env）を準備:
   - プロジェクトルートに .env（および任意で .env.local）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=xxxxx
     - OPENAI_API_KEY=sk-...
     - KABU_API_PASSWORD=xxxx
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C0123456
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PID_FILE_PATH=data/execution.pid
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...
   - 注意: Settings のプロパティは未設定時に例外を投げるものがあります（必須項目は README の例や .env.example を参照）。

使い方（簡単な例）
-----------------

共通準備:
- DuckDB 接続を取得して各種関数に渡します。

例: 日次 ETL を実行する
-----------------------
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は Path を返します
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

例: ニューススコアリング（OpenAI API を使用）
--------------------------------------------
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY が環境変数に設定されていれば api_key 引数は不要
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} symbols")

例: 市場レジーム判定
--------------------
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))

例: 監査 DB の初期化
--------------------
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# 監査用 DB を別ファイルに持つことを推奨
audit_conn = init_audit_db(settings.duckdb_path)

例: カレンダー判定ユーティリティ
-------------------------------
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect(str(settings.duckdb_path))
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))

注意点 / 運用メモ
-----------------
- 環境変数自動読み込み: .env / .env.local はプロジェクトルート（.git もしくは pyproject.toml があるディレクトリ）を基準に自動ロードされます。テストから自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しはモデル gpt-4o-mini を想定し、JSON Mode（厳密 JSON 出力）を使用しています。API 失敗時はフェイルセーフとしてスコアを 0.0 にする等の設計が組み込まれています。
- J-Quants API にはレート制限とトークンリフレッシュロジックが組み込まれています。認証は JQUANTS_REFRESH_TOKEN を用いた get_id_token により取得します。
- DuckDB へ保存する処理は冪等（ON CONFLICT DO UPDATE など）を意識しています。ETL は部分失敗が起きても他の処理は継続する設計です。
- LLM 呼び出しおよび外部 API 呼び出し部分はテスト時に容易にモックしやすく実装されています（関数差し替え、patch 指定など）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                       - 環境変数 / 設定管理（.env 自動ロード含む）
- ai/
  - __init__.py
  - news_nlp.py                    - ニュースセンチメントスコアリング（OpenAI）
  - regime_detector.py             - 市場レジーム判定（MA + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py              - J-Quants API クライアント（取得 + DuckDB 保存）
  - pipeline.py                    - ETL パイプライン（run_daily_etl など）
  - etl.py                         - ETL 結果の公開インターフェース（ETLResult）
  - news_collector.py              - RSS ニュース収集（SSRF 対策・正規化）
  - calendar_management.py         - マーケットカレンダー管理（営業日判定等）
  - quality.py                     - データ品質チェック
  - stats.py                       - 汎用統計ユーティリティ（zscore_normalize 等）
  - audit.py                       - 監査ログスキーマ / 初期化
- research/
  - __init__.py
  - factor_research.py             - モメンタム・バリュー・ボラティリティ等の計算
  - feature_exploration.py         - 将来リターン計算 / IC / サマリー
- research/*（上記モジュール群）
- その他（strategy / execution / monitoring などのパッケージが __all__ に含まれるが本一覧の主要モジュールが中心）

ライセンス / 貢献
-----------------
この README はコードベースのドキュメント用サマリです。実際のライセンスや貢献ルールはリポジトリの LICENSE / CONTRIBUTING を参照してください。

おわりに
--------
本 README はコード内ドキュメント（docstring）を元に主要機能と使い方をまとめたものです。各モジュール内に詳細な使用例や注意点が記載されているため、実運用前に該当モジュールの docstring を参照してください。質問や補足が必要であれば、使いたいユースケース（例: バックテストでの ETL 再現、OpenAI レート制御等）を教えてください。