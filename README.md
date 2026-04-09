# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
ETL、ニュース収集・NLP（OpenAI 経由）、市場レジーム判定、ファクター計算、監査ログなどをモジュール単位で提供します。

主な用途
- J-Quants からの株価・財務・カレンダーの差分ETL
- RSS ニュース収集と LLM による銘柄センチメント評価（ai_scores）
- ETF とマクロニュースを組み合わせた市場レジーム判定
- ファクター（モメンタム・バリュー・ボラティリティ等）の計算・解析
- 監査ログ（signal → order_request → execution）の DuckDB スキーマ初期化

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（代表的な呼び出し例）
- ディレクトリ構成（主要ファイル説明）
- 環境変数一覧（.env 例）

---

プロジェクト概要
- KabuSys は日本株向けに設計されたデータプラットフォーム兼リサーチ／自動売買ライブラリです。
- DuckDB を内部データストアとして利用し、J-Quants API からの差分取得・保存を行います。
- ニュースは RSS から収集し、OpenAI を用いて銘柄ごと／マクロのセンチメントを算出します。
- マーケットレジーム判定、ファクター生成、データ品質チェック、監査ログ（トレース）などを備えます。

---

機能一覧
- 環境設定管理（kabusys.config）
  - .env 自動ロード（OS環境変数優先、.env.local で上書き）
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN など）
- データ ETL（kabusys.data.pipeline / jquants_client）
  - 差分取得（株価・財務・カレンダー）、保存（冪等）
  - 日次パイプライン run_daily_etl
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、SSRF 対策、raw_news / news_symbols への保存（設計済）
- ニュース NLP（kabusys.ai.news_nlp）
  - 銘柄別に複数記事を統合して OpenAI でセンチメント評価、ai_scores に保存
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF(1321) の 200 日 MA 乖離 + マクロニュースの LLM スコアを合成して regime を判定
- リサーチ（kabusys.research）
  - ファクター計算（モメンタム・バリュー・ボラティリティ等）
  - 将来リターン計算、IC 計算、統計サマリー
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合チェック
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルおよびインデックスを初期化
- ユーティリティ（kabusys.data.stats 等）
  - Z スコア正規化など

---

セットアップ手順

前提
- Python 3.10+（型アノテーションで 3.10 構文を使用）
- システムに DuckDB をインストールする（pip で OK）
- OpenAI API キー（OpenAI を使用する機能を使う場合）
- J-Quants のリフレッシュトークン（ETL を実行する場合）

インストール（例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクト配布に pyproject.toml がある想定なら）
   - pip install -e .

3. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml がある階層）に .env または .env.local を配置すると自動読み込みされます（OS 環境変数が優先）。
   - テストなどで自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数（代表）
- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（ETL 実行に必須）
- OPENAI_API_KEY: OpenAI 呼び出しに使用（news_nlp / regime_detector）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（実売買機能利用時）
- そのほか（任意で設定可能）: KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, DUCKDB_PATH 等

---

使い方（代表的な呼び出し例）

まず基本的な準備例（Python REPL / スクリプト内で）:
- DuckDB 接続を作成し、日次 ETL を実行する例:

from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())

- OpenAI を用いたニューススコアリング（score_news）の例:

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY 環境変数が設定されていれば api_key 引数は不要
n = score_news(conn, target_date=date(2026,3,20))
print(f"scored {n} codes")

- 市場レジーム判定（score_regime）の例:

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
# market_regime テーブルへ書き込まれます

- 監査ログ DB を初期化する例:

from kabusys.data.audit import init_audit_db
from kabusys.config import settings

conn = init_audit_db(settings.duckdb_path)
# conn は初期化済みの DuckDB 接続

ログ設定（任意）
- 標準ライブラリ logging を利用してログレベルを設定してください。環境変数 LOG_LEVEL により設定が推奨されます。

注意点
- 多くの関数は DB 接続（duckdb.DuckDBPyConnection）を受け取り、テーブルが存在しない場合はエラーになります。初期スキーマ作成は呼び出し側で行ってください。
- OpenAI の呼び出しは外部 API の失敗に対してフォールバックする設計（失敗時はスコア 0.0 など）です。API キーは api_key 引数で明示的に渡すことも可能です。
- J-Quants API 呼び出しは内部でトークンリフレッシュ・レートリミット・リトライ処理を行います。JQUANTS_REFRESH_TOKEN を設定しておくと便利です。

---

ディレクトリ構成（主要ファイルの説明）

src/kabusys/
- __init__.py
  - パッケージ定義（バージョン、公開サブモジュール一覧）

- config.py
  - 環境変数 / .env ロード、settings オブジェクト（J-Quants トークン・DB パス等）

- ai/
  - __init__.py
  - news_nlp.py
    - ニュースの LLM スコアリング（ai_scores への書き込みロジック）
  - regime_detector.py
    - ETF(1321) の MA200 乖離とマクロニュース LLM を合成して market_regime を作成

- data/
  - __init__.py
  - pipeline.py
    - ETL の高レベルパイプライン（run_daily_etl, run_prices_etl 等）
  - jquants_client.py
    - J-Quants API クライアント（fetch / save / 認証・レート制御・リトライ）
  - news_collector.py
    - RSS 取得、前処理、raw_news への保存（SSRF 対策・XML 安全化）
  - calendar_management.py
    - 市場カレンダー取得 / 営業日判定ユーティリティ
  - quality.py
    - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - audit.py
    - 監査ログ（signal/order_request/execution）スキーマ初期化ユーティリティ
  - stats.py
    - 汎用統計ユーティリティ（zscore_normalize など）
  - etl.py
    - ETLResult 再エクスポート

- research/
  - __init__.py
  - factor_research.py
    - モメンタム / バリュー / ボラティリティ等のファクター計算
  - feature_exploration.py
    - 将来リターン計算、IC、統計サマリー、ランク変換

その他（参照される主要テーブル）
- raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime, signal_events, order_requests, executions など

---

代表的な環境変数（.env 例）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- OPENAI_API_KEY=sk-...
- KABU_API_PASSWORD=your_kabu_password
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN=
- LINE_USER_ID=
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_FILL_MODE=instant
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- KILL_FLAG_CLEAR_ON_START=0
- CPU_THRESHOLD_PCT=90.0
- MEMORY_THRESHOLD_PCT=85.0
- DISK_THRESHOLD_PCT=90.0
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

.env ロードの挙動
- 自動読み込み順: OS 環境変数 > .env.local > .env（.env.local は .env を上書き）
- OS 環境変数は保護され、自動ロードで上書きされません
- 自動ロードを無効にする場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

開発・テストについて
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env 自動ロードを抑止し、テスト用の環境を明示的に設定してください。
- news_nlp / regime_detector の OpenAI 呼び出し箇所は内部的に _call_openai_api を定義しており、unittest.mock.patch により差し替えてユニットテスト可能です。

---

補足
- 本 README はコードベースから抽出した説明です。実行前に DB スキーマや初期テーブル（raw_prices など）の準備、J-Quants／OpenAI の認証情報確認を行ってください。
- 実売買（kabu ステーション連携）を行う際は必ず paper_trading モード等で十分に試験を行ってから live 運用してください。

質問や追加したいサンプル（スクリプト/CLI ラッパー等）があれば教えてください。README に例スクリプトを追記します。