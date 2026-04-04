KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買／データプラットフォーム向けライブラリ群です。  
主に以下を目的としたモジュールを含みます。

- J-Quants API 経由のデータ取得（株価・財務・カレンダー）
- DuckDB を用いたデータ格納・ETL パイプライン
- ニュース収集・前処理（RSS）
- LLM を使ったニュース NLP（銘柄センチメント）および市場レジーム判定
- ファクター計算・特徴量探索（リサーチ用ユーティリティ）
- データ品質チェック
- 監査ログ（注文→約定のトレーサビリティ）スキーマ初期化

重要な設計方針は「ルックアヘッドバイアスの排除」「冪等性」「フェイルセーフ（API失敗時は継続）」です。

主な機能
--------
- ETL: daily_etl を含む差分取得／保存／品質チェック（kabusys.data.pipeline）
- J-Quants クライアント: レート制限・リトライ・トークン自動リフレッシュを備えた API クライアント（kabusys.data.jquants_client）
- ニュース収集: RSS から記事収集・前処理・SSRF 対策（kabusys.data.news_collector）
- ニュース NLP: OpenAI を使った銘柄センチメント算出（kabusys.ai.news_nlp）
- 市場レジーム判定: ETF (1321) の MA200乖離 と マクロニュースセンチメントの合成（kabusys.ai.regime_detector）
- 研究用ファクター: モメンタム／ボラティリティ／バリュー等の計算（kabusys.research）
- データ品質チェック: 欠損・重複・スパイク・日付不整合検出（kabusys.data.quality）
- マーケットカレンダー管理: 営業日判定やカレンダーの夜間更新ジョブ（kabusys.data.calendar_management）
- 監査ログ: signal → order_request → execution の監査スキーマ生成（kabusys.data.audit）

セットアップ
------------
前提
- Python 3.10 以上（型注釈に 3.10 の構文を使用）
- 必要パッケージ（例）: duckdb, openai, defusedxml

推奨手順（開発環境）
1. リポジトリを取得:
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境作成・有効化:
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. インストール:
   pip install -U pip setuptools
   pip install -e ".[dev]"  # setup が extras を提供している場合
   # 必要最低限:
   pip install duckdb openai defusedxml

4. 環境変数 (.env)
   プロジェクトルート（.git または pyproject.toml と同じ階層）に .env を置くと自動で読み込まれます。
   自動読み込みを無効にする場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（Settings から抜粋）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite（デフォルト data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV: environment ("development" / "paper_trading" / "live")
- LOG_LEVEL: "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"

例 (.env)
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

使い方（サンプル）
-----------------

基本的な DuckDB 接続例
from datetime import date
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))

1) 日次 ETL 実行（差分取得 → 保存 → 品質チェック）
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())

2) ニュースセンチメント（OpenAI 必須）
from kabusys.ai.news_nlp import score_news
from datetime import date
# conn: DuckDB 接続、target_date: スコア生成対象日
count = score_news(conn, date(2026,3,20))  # OpenAI APIキーは env または api_key 引数で指定
print(f"scored {count} codes")

3) 市場レジーム判定
from kabusys.ai.regime_detector import score_regime
from datetime import date
score_regime(conn, date(2026,3,20))

4) ファクター計算（研究用）
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from datetime import date
mom = calc_momentum(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
val = calc_value(conn, date(2026,3,20))

5) 監査データベース初期化
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")

6) RSS フィード取得（ニュース収集）
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
# 取得した articles は id, datetime, source, title, content, url を持つ

注意点
- OpenAI を利用する処理は API 呼び出しのため料金とレイテンシが発生します。API キーの管理に注意してください。
- J-Quants API の呼び出しはレート制限 (120 req/min) を守るため RateLimiter が動作します。
- ETL / API 呼び出しはネットワーク障害や API サーバの不具合を考慮してリトライやフォールバック処理を実装していますが、運用環境ではログ監視を併用してください。
- DuckDB の executemany はバージョン差による制約があるため、コード中で空リストの渡し方などに注意があります（ライブラリ側で既に考慮済みです）。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                      # 環境変数・設定管理
- ai/
  - __init__.py
  - news_nlp.py                  # ニュース NLP（OpenAI）
  - regime_detector.py           # 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py            # J-Quants API クライアント（取得・保存）
  - pipeline.py                  # ETL パイプライン（run_daily_etl 等）
  - etl.py                       # ETLResult の再エクスポート
  - news_collector.py            # RSS ニュース収集
  - calendar_management.py       # マーケットカレンダー管理
  - quality.py                   # データ品質チェック
  - stats.py                     # 汎用統計ユーティリティ（zscore_normalize 等）
  - audit.py                     # 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py           # モメンタム・ボラティリティ・バリュー計算
  - feature_exploration.py       # 将来リターン・IC・統計サマリ等
- ai, research, data 以下にある各モジュールは unit-test フレンドリーに設計されています（API 呼び出し部分はモック可能）。

テストとデバッグ
----------------
- config の自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト時に便利）。
- OpenAI / J-Quants 呼び出しはそれぞれ _call_openai_api / _request 等で抽象化されており、unittest.mock.patch で差し替えて単体テストが可能です。
- DuckDB を ":memory:" にしてユニットテスト用の一時 DB を作成できます（例: init_audit_db(":memory:")）。

ライセンス・コントリビュート
----------------------------
（この項目はリポジトリ固有の LICENSE / CONTRIBUTING を参照してください）

最後に
------
この README はコードベースの主要な構成・利用方法をまとめたものです。各モジュールの詳細はソース内の docstring とコメントに設計方針・制約が明記されています。具体的な使い方や運用手順はプロジェクトの運用ドキュメントに従ってください。