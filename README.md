KabuSys
=======

日本株向けのデータパイプライン・リサーチ・AI支援レジーム判定・監査ログを備えた
投資システム用ライブラリ群です。DuckDB をデータストアとして用い、
J-Quants / JAX（kabu）や OpenAI を組み合わせてデータ取得・品質管理・
ニュースセンチメント解析・市場レジーム判定・監査ログを提供します。

プロジェクト概要
---------------
KabuSys は以下を主目的とするモジュール群です。

- J-Quants API からの株価・財務・市場カレンダーの差分取得（ETL）
- raw_news の収集・前処理と OpenAI を用いたニュースセンチメント解析（AI）
- ETF 指数の移動平均等とマクロニュースの LLM スコアを合成した市場レジーム判定
- リサーチ向けファクター計算、将来リターン・IC 計算などの統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレース可能なスキーマ）
- 環境変数管理（.env 自動読み込み、設定クラス）

主要機能（機能一覧）
-------------------
- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl: 市場カレンダー→株価→財務→品質チェックの一連処理
  - run_prices_etl / run_financials_etl / run_calendar_etl：個別 ETL
- J-Quants クライアント（kabusys.data.jquants_client）
  - fetch/保存処理（raw_prices, raw_financials, market_calendar 等）
  - トークン自動リフレッシュ、レートリミット、リトライ処理
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、SSRF 対策、前処理、raw_news への冪等保存設計
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）で銘柄毎のセンチメントを算出し ai_scores テーブルへ保存
  - バッチ・トリム・リトライ・レスポンス検証など堅牢な実装
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF(1321) の 200 日 MA 乖離（重み 70%）＋マクロニュース LLM スコア（重み 30%）
  - 日次で regime_score/regime_label を market_regime に記録
- データ品質（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合を検出し QualityIssue を返却
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
- リサーチ（kabusys.research）
  - ファクター計算（momentum / value / volatility）、forward returns、IC、統計要約
- 設定管理（kabusys.config）
  - .env/.env.local の自動読み込み（プロジェクトルート検出）、Settings クラスで型安全に取得

セットアップ手順
----------------

前提
- Python 3.10+（typing の Union | 演算子等に依存）
- DuckDB（Python パッケージとして duckdb を使用）
- OpenAI Python SDK（openai、または SDK の互換クライアント）
- defusedxml（RSS パースの安全対策）

1. リポジトリをクローン
   git clone <リポジトリURL>
   cd <repo>

2. 仮想環境を作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

3. 必要なパッケージをインストール
   （プロジェクトに requirements.txt が無い場合は下記を一例としてインストール）
   pip install duckdb openai defusedxml

   ※プロジェクトで setuptools の editable install を提供していれば：
   pip install -e .

4. 環境変数設定 (.env)
   プロジェクトルート（.git または pyproject.toml のある場所）に .env / .env.local を配置すると自動読み込みされます（OS 環境変数が優先、.env.local が .env を上書き）。

主要な環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須: ETL 実行で使用）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD: kabu API パスワード（発注等を実装する際）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite（デフォルト data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START などの監視設定

.env 自動読み込みを無効にする（テスト等）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化します。

使い方（サンプル）
------------------

基本的な DuckDB 接続と日次 ETL 実行例：

from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

# DuckDB 接続（デフォルトパスは settings.duckdb_path を参照）
conn = duckdb.connect("data/kabusys.duckdb")

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

ニュースセンチメント（ai_scores）を生成する例：

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# 環境変数 OPENAI_API_KEY が設定されていれば api_key を省略可
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxxx")
print(f"書き込み銘柄数: {n_written}")

市場レジーム判定を実行する例：

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-xxxx")

監査ログ用 DB の初期化：

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使用して監査ログの CRUD を行う

設定の参照例（code 内で利用）：

from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)

テスト時のヒント
- OpenAI 呼び出しは内部で _call_openai_api を使っているため、unittest.mock.patch で差し替えてテスト可能です。
  例: patch("kabusys.ai.news_nlp._call_openai_api", mock_fn)
- .env 自動読み込みを抑制するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成
----------------

主要なソース配置（src/kabusys 以下の抜粋）:

- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数・.env 自動読み込み・Settings クラス
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py        : ニュースセンチメント解析（OpenAI 経由）
  - regime_detector.py : マクロセンチメント＋MA 乖離で市場レジーム判定
- src/kabusys/data/
  - __init__.py
  - jquants_client.py  : J-Quants API クライアント（取得・保存ロジック）
  - pipeline.py        : ETL パイプライン・run_daily_etl 等
  - etl.py             : ETLResult の再エクスポート
  - news_collector.py  : RSS 収集・前処理・冪等保存
  - quality.py         : データ品質チェック
  - stats.py           : zscore_normalize 等統計ユーティリティ
  - calendar_management.py : 市場カレンダー管理・営業日判定
  - audit.py           : 監査ログスキーマ定義と初期化ユーティリティ
- src/kabusys/research/
  - __init__.py
  - factor_research.py : momentum/value/volatility 等ファクター計算
  - feature_exploration.py : forward returns / IC / factor summary
- src/kabusys/ai/regime_detector.py
- ほかユーティリティ・補助モジュール群

設計上の注意点 / 動作方針
------------------------
- ルックアヘッドバイアスを避けるため、内部ロジックは date.today()/datetime.today() を直接参照しない設計となっている関数が多く、target_date を明示的に渡すことが推奨されます。
- OpenAI / J-Quants など外部 API 呼び出しは冗長性・リトライ・バックオフを組み込み、失敗時はフェイルセーフ（無理に例外を投げず継続）する方針の箇所が多いです。
- DuckDB への書き込みは基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）で実装されています。
- RSS の取得には SSRF 対策、XML の安全パース（defusedxml）、受信サイズ制限などセキュリティ対策が導入されています。

追加情報
--------
- .env のパースルールは POSIX ライクな export KEY=val、シングル/ダブルクォート、コメント取り扱いに対応しています。
- settings クラスにより各種パス・閾値・環境種別（development/paper_trading/live）を集中管理します。
- 監査ログ初期化時はタイムゾーンを UTC に固定します（SET TimeZone='UTC'）。

問題報告・貢献
---------------
バグや改善提案は issue を立ててください。貢献は歓迎します（コードのスタイル、テスト、ドキュメント改善など）。

以上が KabuSys の簡易 README です。必要であれば README に含める具体的な .env.example、requirements.txt の候補、あるいはよくある操作（ETL の定期実行 cron 例、systemd ユニット例、CI 設定サンプル）を追記できます。必要なら教えてください。