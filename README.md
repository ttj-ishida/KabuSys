KabuSys
=======

日本株向けのデータ基盤・研究・自動売買支援ライブラリです。本リポジトリは以下の主要機能群を提供します。

- データ取得・ETL（J-Quants API 連携、DuckDB 保存、品質チェック）
- ニュース収集・前処理（RSS → raw_news）
- ニュースの NLP（OpenAI を用いたセンチメント／銘柄別スコアリング）
- 市場レジーム判定（ETF MA とマクロニュースを統合）
- 研究用ファクター/特徴量計算（モメンタム、バリュー、ボラティリティ、将来リターン、IC 等）
- 監査ログ（signal → order → execution をトレースする監査 DB スキーマ）
- 設定管理（.env 自動ロード、環境変数読み取りユーティリティ）

以下、導入・使い方・ディレクトリ構成をまとめます。

プロジェクト概要
---------------

KabuSys は日本株のデータパイプライン／リサーチ／戦略運用を支援するための Python ライブラリです。J-Quants API からデータを差分取得し DuckDB に保存、データ品質チェック、ニュース収集と LLM を用いたニュース解析、ファクター計算、レジーム判定や監査ログスキーマ初期化などを一貫して扱えます。

主な特徴
--------

- ETL（run_daily_etl）で市場カレンダー・日足・財務を差分取得して DuckDB に保存
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- RSS ベースのニュース収集（SSRF 対策、トラッキング除去、前処理）
- OpenAI（gpt-4o-mini）を利用したニュース NLP（銘柄別 ai_score、マクロセンチメント）
- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントの合成）
- 監査ログ（signal_events / order_requests / executions）の初期化ユーティリティ
- 環境変数 / .env 自動ロード（プロジェクトルート基準、.env.local 上書き）

セットアップ手順
---------------

前提
- Python 3.10+（型アノテーションで | を使用しているため）
- ネットワークアクセス（J-Quants, OpenAI など）

1. レポジトリをクローン（任意）:
   git clone <repo-url>

2. 仮想環境を作成して有効化:
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール（例）:
   pip install duckdb openai defusedxml

   ※ 実プロジェクトでは requirements.txt / pyproject.toml を用意している想定です。
   pip install -e . などで開発インストールするケースもあります。

4. 環境変数設定:
   プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（デフォルト）。
   自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD     : kabuステーション連携用パスワード（発注等）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : Slack チャンネル ID
- OPENAI_API_KEY        : OpenAI 呼び出し（news_nlp / regime_detector を直接呼ぶ場合）

オプション（デフォルトあり）
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト INFO
- DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, CPU_THRESHOLD_PCT 等（config.Settings 参照）

.env の書式
- export FOO=bar 形式もサポート
- シングル／ダブルクォート、インラインコメント等の扱いに柔軟に対応
- .env.local は .env を上書き（OS 環境変数は保護）

使い方（コード例）
-----------------

基本的な DuckDB 接続と日次 ETL 実行例:

from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

ニューススコアリング（OpenAI 必須）:

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY が環境変数にあれば api_key を省略可
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote {n_written} ai_scores")

市場レジーム判定（1321 MA200 + マクロセンチメント）:

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API key は env または api_key 引数で渡す

監査ログ DB 初期化（監査専用 DuckDB を作る）:

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions 等のテーブルが作成されます

研究用ファクター計算（例: momentum）:

from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{'date': ..., 'code': 'XXXX', 'mom_1m': ..., ...}, ...]

主要な公開 API
- kabusys.data.pipeline.run_daily_etl(...) — 日次 ETL（calendar/prices/financials + 品質チェック）
- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
- kabusys.data.jquants_client.save_... — DuckDB への保存ユーティリティ
- kabusys.data.news_collector.fetch_rss(...) — RSS 取得ユーティリティ
- kabusys.ai.news_nlp.score_news(...) — 銘柄別ニューススコア作成
- kabusys.ai.regime_detector.score_regime(...) — 市場レジームスコア計算
- kabusys.data.audit.init_audit_db(...) / init_audit_schema(...) — 監査ログ初期化
- kabusys.research.* — ファクター計算・特徴量探索ユーティリティ

注意点 / 設計上の要点
--------------------
- Look-ahead bias を避けるため、多くの関数は内部で datetime.today() / date.today() を直接参照せず、target_date を引数で受け取る設計です。
- OpenAI / J-Quants API 呼び出しはリトライ・バックオフやフェイルセーフ（部分失敗の継続）を備えています。
- ニュース収集は SSRF 対策・レスポンスサイズ制限・トラッキング除去などセキュリティ面を配慮しています。
- ETL 処理は冪等性を重視（DuckDB 側の ON CONFLICT を利用）しています。
- .env はプロジェクトルート（.git や pyproject.toml の親）を起点に自動読み込みされます。

ディレクトリ構成（主要ファイル）
------------------------------

src/kabusys/
- __init__.py
- config.py                      - 環境変数/設定管理（.env 自動ロード）
- ai/
  - __init__.py
  - news_nlp.py                   - ニュース NLP（銘柄別 ai_score）
  - regime_detector.py            - 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py             - J-Quants API クライアント（fetch/save）
  - pipeline.py                   - ETL パイプライン（run_daily_etl 等）
  - etl.py                        - ETLResult のエクスポート
  - quality.py                    - データ品質チェック
  - news_collector.py             - RSS ニュース収集器
  - calendar_management.py        - 市場カレンダー管理・営業日判定
  - stats.py                      - 汎用統計ユーティリティ（zscore 正規化）
  - audit.py                      - 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py            - モメンタム/バリュー/ボラティリティ計算
  - feature_exploration.py        - 将来リターン / IC / 統計サマリー 等
- monitoring/ (存在する場合: 監視/実行制御関連モジュール等)
- strategy/, execution/, monitoring（パッケージ化用 __all__ 指定あり）

依存関係（主なもの）
- duckdb
- openai
- defusedxml
- 標準ライブラリ（urllib, json, datetime, logging など）

よくある質問
-------------
Q. OpenAI のキーはどこに置くべきですか？
A. 環境変数 OPENAI_API_KEY を設定するか、score_news / score_regime の api_key 引数に渡してください。.env に記述しておけば自動で読み込まれます。

Q. .env の自動読み込みを無効にできますか？
A. はい。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動ロードは行われません（テスト用途など）。

Q. DuckDB のファイルパスはどこで設定しますか？
A. 環境変数 DUCKDB_PATH で指定できます。指定なしの場合は data/kabusys.duckdb がデフォルトです。

最後に
------
この README はコードベースの主要な機能と典型的な使い方をまとめたものです。各モジュールの詳細（引数や返り値、例外挙動）はソース内ドキュメント（docstring）を参照してください。必要であれば README にサンプル .env.example、CI 実行例、より詳細な API 仕様を追加できます。必要があれば追記します。