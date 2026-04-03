# KabuSys

日本株向け自動売買 / データプラットフォームライブラリ

概要
----
KabuSys は、日本株のデータ取得（J-Quants）、ETL、ニュース収集、AI によるニュースセンチメント評価、因子計算、監査ログなどを備えた内部ライブラリです。DuckDB をデータストアとして利用し、OpenAI（gpt-4o-mini）を用いたセンチメント推定や市場レジーム判定、日次 ETL パイプラインなどを提供します。

主な特徴
--------
- J-Quants API 経由での株価・財務・カレンダー取得（レートリミット・リトライ対応）
- DuckDB への冪等保存（ON CONFLICT / UPDATE）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース収集（RSS、SSRF 対策、前処理）と銘柄紐付け
- OpenAI を用いたニュース NLP（銘柄ごとのセンチメントスコア化）
- 市場レジーム判定（ETF MA と LLM センチメントの合成）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、Zスコア正規化）
- データ品質チェック（欠損、スパイク、重複、日付不整合）

動作環境
--------
- Python 3.10 以上（型注釈・Union 表記の使用に対応したバージョン）
- 推奨パッケージ（抜粋）:
  - duckdb
  - openai
  - defusedxml
  - （その他：標準ライブラリを多用。ネットワーク・HTTP関連は標準 urllib を使用）

簡単なインストール例
--------------------
（プロジェクトルートに pyproject.toml / setup.cfg がある前提）

1. 仮想環境作成・有効化（例）
   python -m venv .venv
   source .venv/bin/activate

2. 必要パッケージのインストール（例）
   pip install duckdb openai defusedxml

3. 開発インストール（プロジェクトで setup/pyproject がある場合）
   pip install -e .

環境変数（必須 / 任意）
----------------------
主要な環境変数（.env ファイルに記載することが想定されています）:

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL で使用）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必要時）

OpenAI（AI 機能使用時）:
- OPENAI_API_KEY: OpenAI の API キー（score_news / score_regime で参照）

任意 / デフォルトあり:
- KABUSYS_ENV: one of development / paper_trading / live （デフォルト development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知等で使用する場合
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START: 実行監視用フラグ

自動 .env ロード
- パッケージ起動時に、プロジェクトルート (.git または pyproject.toml を基準) を探索して .env を自動読込します。
- 読み込み順: OS 環境 > .env.local > .env
- 自動ロードを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

セットアップ手順（実運用向け簡易）
-------------------------------
1. リポジトリを取得
   git clone <repo>
   cd <repo>

2. 仮想環境作成、依存パッケージをインストール
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject があればそちらを使ってください）

3. .env を作成（例を参考）
   .env（プロジェクトルート）に必要なキーを記載します。例:

   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxx...
   KABU_API_PASSWORD=your_kabu_password
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb

4. データディレクトリ作成（デフォルトパスを使用する場合）
   mkdir -p data

使い方（代表的な例）
------------------

1) DuckDB 接続を開いて日次 ETL を実行する
- ETL は J-Quants から差分取得して DuckDB に保存し、品質チェックを実行します。

Python サンプル:
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

2) ニュースのセンチメントスコアを生成する（AI）
- OpenAI API キーは環境変数 OPENAI_API_KEY、または score_news に api_key を渡します。

Python サンプル:
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")

3) 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM 評価を合成）
Python サンプル:
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルへ書き込まれます

4) 監査ログデータベース初期化
- 取引監査用の DuckDB を初期化するユーティリティがあります。

Python サンプル:
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの DuckDB 接続

5) RSS ニュース取得（保存ロジックは ETL 側と組み合わせて使用）
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")

重要な実装上の注意点
-------------------
- Look-ahead bias（未来情報参照）対策:
  - AI スコアリング / レジーム判定 / ETL の各処理は target_date に対して未来データを参照しないよう設計されています（date 比較は排他的条件を使用）。
- OpenAI 呼び出し:
  - レスポンスの検証、リトライ、フェイルセーフ（API 失敗時は影響を極力限定）を実装しています。
- J-Quants API:
  - レートリミット（120 req/min）に合わせた固定間隔スロットリングを実装しています。
  - 401 が返った場合はリフレッシュトークンで自動更新を試みます。
- DuckDB の executemany に対する注意:
  - 一部関数は DuckDB のバージョン依存の挙動を回避するため executemany 前に空チェックを行っています。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                # 環境変数・設定読み込み
- ai/
  - __init__.py
  - news_nlp.py            # ニュースセンチメント（銘柄別）
  - regime_detector.py     # 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py      # J-Quants API クライアント、保存関数
  - pipeline.py            # ETL（run_daily_etl 等）
  - etl.py                 # ETLResult 再エクスポート
  - news_collector.py      # RSS 収集・前処理
  - calendar_management.py # マーケットカレンダー管理
  - quality.py             # データ品質チェック
  - stats.py               # 統計ユーティリティ（zscore_normalize 等）
  - audit.py               # 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py     # ファクター計算（momentum/value/volatility）
  - feature_exploration.py # forward returns, IC, summary, rank

開発・テスト時のヒント
---------------------
- 自動 .env ロードが邪魔な場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます（テスト用に便利）。
- OpenAI / J-Quants の外部 API 呼び出しはモック可能なように内部で関数を分離しているため、ユニットテストではパッチして依存を切り離してください（各モジュールにテスト用差替えポイントを用意）。
- DuckDB のスキーマ初期化やマイグレーションはプロジェクトにスキーマ初期化コードを追加して行ってください（audit.init_audit_schema 等を参照）。

最後に
-----
この README はコードベースの主要機能と使い方を概説したものです。実際の運用ではログ設定、監視、エラーハンドリング、権限管理（APIキーの安全な保管）、およびバックテスト/シミュレーション環境での厳密な検証が不可欠です。必要であれば、各モジュールの詳細使用例やスキーマ定義の抜粋を含めたより詳細なドキュメントを作成します。