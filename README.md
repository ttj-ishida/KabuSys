KabuSys — 日本株自動売買基盤（README）
===================================

概要
----
KabuSys は日本株のデータ収集／ETL、ニュース NLP（LLM）によるセンチメント評価、マーケットレジーム判定、リサーチ（ファクター計算）、監査ログ（トレーサビリティ）などを含む自動売買基盤のコアライブラリ群です。  
主に DuckDB をデータレイヤに、J-Quants API・RSS フィード・OpenAI（gpt-4o-mini）を外部データソースとして利用する設計になっています。

主な特徴
--------
- データ:
  - J-Quants からの株価（OHLCV）・財務・上場銘柄情報・市場カレンダーの差分 ETL（ページネーション／リトライ／レート制御対応）
  - RSS 収集器（トラッキング除去／SSRF対策／XML安全パース）
  - DuckDB への冪等保存（ON CONFLICT で上書き）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
- AI:
  - ニュースの銘柄別センチメント算出（OpenAI JSON Mode を利用、バッチ処理、リトライ）
  - マクロニュース＋ETF(1321)の MA200 乖離を合成した市場レジーム判定（bull/neutral/bear）
- リサーチ:
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（スピアマン）や統計サマリー、Z スコア正規化
- 監査（Audit）:
  - シグナル→発注→約定までを UUID 連鎖でトレースする監査テーブルの初期化ユーティリティ
- 設定:
  - .env / .env.local / OS 環境変数からの自動読み込み（パッケージ内での安全なパス探索）
  - 必須設定は Settings オブジェクト経由で取得

必要条件（目安）
--------------
- Python 3.10+
- 必要パッケージ（抜粋）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外は requirements.txt / pyproject.toml を参照してください）

セットアップ手順
---------------
1. リポジトリをクローン:
   - git clone <repo-url>

2. 仮想環境を作成して有効化（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール:
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）
   - 例: pip install -r requirements.txt

4. 環境変数 / .env の準備:
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env を置くと自動で読み込まれます（.env.local は上書き）。
   - 自動読み込みを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する
   - 重要な環境変数（抜粋）:
     - JQUANTS_REFRESH_TOKEN（必須: J-Quants リフレッシュトークン）
     - KABU_API_PASSWORD（kabuステーション API パスワード）
     - OPENAI_API_KEY（OpenAI 呼び出しに使用）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - その他: KABUSYS_ENV（development/paper_trading/live）, LOG_LEVEL, LINE_CHANNEL_ACCESS_TOKEN 等
   - .env のパースはシェル風（export KEY=val / quoted values / inline コメント等）に対応します。

使い方（主要な利用例）
--------------------

共通準備: DuckDB 接続
- ほとんどの処理は DuckDB 接続（duckdb.connect(...)）を受け取ります。設定からパスを取得する例:

from kabusys.config import settings
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))

ETL（日次 ETL）
- 日次 ETL の実行（カレンダー・株価・財務・品質チェック）:

from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn, target_date=None)  # None -> 今日
print(result.to_dict())

個別 ETL ジョブ
- 株価差分 ETL:

from kabusys.data.pipeline import run_prices_etl
fetched, saved = run_prices_etl(conn, target_date, id_token=None)

ニューススコアリング（銘柄別）
- raw_news / news_symbols を元に OpenAI で銘柄ごとのスコアを ai_scores に書き込む:

from kabusys.ai.news_nlp import score_news
n_written = score_news(conn, target_date, api_key=None)  # api_key 省略時は OPENAI_API_KEY を使用

市場レジーム判定
- ETF 1321 の MA200 乖離と macro ニュースの LLM スコアを合成し market_regime に書き込む:

from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date, api_key=None)

監査スキーマ初期化
- 監査ログ用 DB を初期化（ファイル or :memory:）:

from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリは自動作成されます

RSS ニュース収集（単発取得）
- RSS を取得して記事リストを得る（保存ロジックは別途利用）:

from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")

設定取得（Settings）
- 環境変数は kabusys.config.settings 経由で取得できます。必須値未設定時は ValueError が発生します。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要モジュール（抜粋）です。

src/
  kabusys/
    __init__.py                # パッケージ定義、__version__
    config.py                  # 環境変数・.env ロード・Settings
    ai/
      __init__.py
      news_nlp.py              # ニュース NLP（score_news 等）
      regime_detector.py       # 市場レジーム判定（score_regime）
    data/
      __init__.py
      calendar_management.py   # 市場カレンダー管理（is_trading_day 等）
      etl.py                   # ETL の公開インターフェース
      pipeline.py              # 日次 / 個別 ETL ロジック（run_daily_etl 等）
      stats.py                 # 統計ユーティリティ（zscore_normalize）
      quality.py               # データ品質チェック
      audit.py                 # 監査ログテーブル初期化
      jquants_client.py        # J-Quants API クライアント + save_* 関数
      news_collector.py        # RSS 収集（SSRF対策・XML保護付き）
    research/
      __init__.py
      factor_research.py       # ファクター計算（momentum, value, volatility）
      feature_exploration.py   # forward returns, IC, summary, rank
    research/ (その他モジュール)
    execution/                  # （発注・約定処理などの想定モジュール）
    monitoring/                 # （実行監視関連：PID / kill flag / リソース閾値等）

注意事項・設計上のポイント
------------------------
- Look-ahead bias 防止:
  - 多くのモジュールで datetime.today() / date.today() を直接参照せず、target_date を明示的に渡す設計です。バックテストや再現性を考慮しています。
- 冪等性:
  - DuckDB への保存は ON CONFLICT / executemany による差分更新で冪等性を確保しています（ETL の再実行安全性）。
- フェイルセーフ:
  - OpenAI や HTTP API の失敗は多くの箇所でフェイルセーフ（0.0 スコアやスキップ）にしてシステム全体の停止を避ける設計です。
- 自動 .env ロード:
  - プロジェクトルートを .git または pyproject.toml を基準に探索し、.env/.env.local を自動読み込みします。テスト環境などで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 環境値検証:
  - Settings.env は development / paper_trading / live のいずれかに制限されます。LOG_LEVEL は標準的なログレベルに制約があります。

よくある操作例（短いスニペット）
--------------------------------
- DuckDB で ETL 実行（例）:

from kabusys.config import settings
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
res = run_daily_etl(conn)
print(res.to_dict())

- ニュースをスコアして ai_scores に書き込む:

from kabusys.ai.news_nlp import score_news
count = score_news(conn, target_date, api_key=None)
print(f"Wrote scores for {count} symbols")

サポート / 開発メモ
------------------
- 単体テストを実行する際は自動 .env ロードがテストに影響することがあるため KABUSYS_DISABLE_AUTO_ENV_LOAD を使って環境を固定してください。
- OpenAI 呼び出しはテスト時に _call_openai_api を patch してモックできます（各モジュールにそのための注記があります）。
- DuckDB の executemany は空リストを受け付けないバージョンの挙動（0.10 系）に配慮した実装箇所があります。空パラメータでの呼出しは避ける実装になっています。

ライセンス
----------
（プロジェクトに応じたライセンス情報をここに明記してください）

以上がこのコードベースの概要と基本的な利用方法です。追加で README に載せたいサンプルコマンドや設定例（.env.example 等）があれば提示してください。