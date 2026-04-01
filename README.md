KabuSys
=======

日本株のデータ基盤・リサーチ・自動売買支援ライブラリ（モジュール群）の README です。  
このリポジトリは DuckDB を用いたデータ ETL、ニュース収集・NLP、研究用ファクター計算、監査ログ（トレーサビリティ）、J-Quants / OpenAI / kabu API との連携を想定したユーティリティ群を提供します。

プロジェクト概要
---------------
KabuSys は日本株向けの以下用途を想定した Python モジュール群です。

- データ収集（J-Quants 経由の株価／財務／カレンダー）
- ETL パイプライン（差分取得、保存、品質チェック）
- ニュース収集（RSS）と LLM を使った銘柄センチメント算出
- 市場レジーム判定（ETF の MA とマクロニュースの LLM センチメントの合成）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 監査ログ（signal → order_request → executions のトレーサビリティ用テーブル）
- 各種ユーティリティ（カレンダー管理、統計、品質チェック、J-Quants クライアント等）

主な機能一覧
-------------
- data.jquants_client: J-Quants API からの取得 / DuckDB への保存（差分、ページネーション、トークン自動更新、レート制御、リトライ）
- data.pipeline: 日次 ETL を統括する run_daily_etl / 個別 ETL ジョブ（prices/financials/calendar）と ETLResult
- data.quality: 欠損・スパイク・重複・日付不整合などの品質チェック
- data.news_collector: RSS 取得・前処理・raw_news への冪等保存（SSRF/サイズ制限/トラッキング除去等を考慮）
- ai.news_nlp: ニュースを銘柄ごとに集約し OpenAI（gpt-4o-mini）でセンチメントを算出し ai_scores に書き込む（score_news）
- ai.regime_detector: ETF 1321 の MA200 とマクロニュース LLM センチメントを合成して market_regime に書き込む（score_regime）
- research: ファクター計算（calc_momentum, calc_volatility, calc_value）や特徴量解析（calc_forward_returns, calc_ic, factor_summary, rank）
- data.audit: 監査ログ用テーブルの初期化 / 専用 DB の作成（init_audit_schema, init_audit_db）
- config: 環境変数 / .env 自動読込（プロジェクトルートを探索）と settings オブジェクト

セットアップ手順
----------------
前提:
- Python 3.10+（型注釈で Union | を使用しているため）
- DuckDB を使用するため duckdb パッケージが必要
- OpenAI Python SDK、defusedxml などが利用されます

推奨インストール（仮想環境を推奨）:
1. 仮想環境作成と有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（代表例）
   - pip install duckdb openai defusedxml

   （requirements.txt があれば pip install -r requirements.txt を使用してください）

3. ソースをインストール（開発モード）
   - pip install -e .

環境変数（必須・任意）
- 必須（モジュールを使う機能に応じて）:
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（jquants_client.get_id_token に使用）
  - OPENAI_API_KEY         : OpenAI API キー（score_news / score_regime で省略時に参照）
  - KABU_API_PASSWORD     : kabu API パスワード（kabu API 連携用）
  - SLACK_BOT_TOKEN       : Slack 通知に使用
  - SLACK_CHANNEL_ID      : Slack チャンネル ID

- 任意（デフォルト値あり）:
  - KABUSYS_ENV (development | paper_trading | live) — settings.env
  - LOG_LEVEL (DEBUG/INFO/...) — settings.log_level
  - DUCKDB_PATH — デフォルト data/kabusys.duckdb
  - SQLITE_PATH — デフォルト data/monitoring.db
  - PID_FILE_PATH / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT など監視設定

.env の自動ロード:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して .env, .env.local を自動で読み込みます。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（コード例）
-----------------

基本的な DuckDB 接続を作成して ETL を実行する例:

from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

ニュースセンチメント（LLM）スコアの算出:

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定済みであれば api_key 引数は省略可
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} symbols")

市場レジーム判定:

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数に設定するか api_key を渡す

監査ログ用 DB 初期化:

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリがなければ自動作成されます

J-Quants データ取得（直接呼び出す場合）:

from kabusys.data.jquants_client import fetch_daily_quotes
# settings.jquants_refresh_token が設定されている想定
records = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,19))
print(len(records))

ニュース RSS 取得（単体）:

from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["title"], a["datetime"])

研究用ファクター計算（例）:

from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2026,3,19))
vol = calc_volatility(conn, date(2026,3,19))
val = calc_value(conn, date(2026,3,19))

エラーハンドリングと注意点
- OpenAI API 呼び出しや J-Quants API 呼び出しにはリトライ / フェイルセーフのロジックが組み込まれていますが、APIキー未設定やネットワーク障害は例外となる場合があります。
- LLM レスポンスのパースに失敗した場合、score_news / score_regime は該当部分をスキップしつつ継続する設計です（フェイルセーフ）。
- run_daily_etl 等は内部でトランザクションや ROLLBACK を行いますが、外部環境の DB 状況により振る舞いが変わる可能性があります。実運用前に小規模テストを推奨します。
- Look-ahead バイアス防止: ライブラリの設計方針として内部で date.today()/datetime.today() を直接参照しない関数が多く、バックテスト用途でも扱いやすくなっています。ただし ETL の一部や calendar_update_job 等は date.today() を使います。バックテスト用途ではデータ収集時刻の管理に注意してください。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

src/
  kabusys/
    __init__.py
    config.py
    ai/
      __init__.py
      news_nlp.py
      regime_detector.py
    data/
      __init__.py
      jquants_client.py
      pipeline.py
      etl.py
      quality.py
      stats.py
      news_collector.py
      calendar_management.py
      audit.py
      etl.py
      pipeline.py
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
      (その他の研究ユーティリティ)
    research/
    (strategy/, execution/, monitoring/ を __all__ で想定していますが実装ファイルは該当コードベース参照)

主なモジュール概要
- kabusys.config: 環境変数と .env 自動ロード、settings オブジェクトを提供
- kabusys.data.jquants_client: J-Quants の取得 / DuckDB 保存（save_*）関数
- kabusys.data.pipeline: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl と ETLResult
- kabusys.data.news_collector: RSS の取得と前処理、安全対策（SSRF/サイズ/トラッキング除去等）
- kabusys.ai.news_nlp: score_news（OpenAI を使った銘柄ごとのニュースセンチメント）
- kabusys.ai.regime_detector: score_regime（ETF MA とマクロニュース合成による市場レジーム判定）
- kabusys.research.*: ファクター算出 / 将来リターン / IC / 統計サマリー

その他メモ
---------
- .env.example を用意して、必要なキーをプロジェクトルートの .env に記載してください（JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY 等）。
- テストや CI で自動読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env の自動読み込みを抑制できます。
- DuckDB による executemany の挙動やバージョン差異に対する注意（コード内に互換性対策あり）

問い合わせ・貢献
----------------
バグ報告・機能提案・プルリクエストは README と同じリポジトリの Issue / PR を通して行ってください。コードはできる限りユニットテストを用意してから PR を送ってください。

以上。README に記載してほしい追加情報（依存関係リスト、実行スクリプト、CI 設定など）があれば教えてください。