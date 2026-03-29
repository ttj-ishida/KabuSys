KabuSys — README (日本語)
========================

概要
----
KabuSys は日本株向けのデータプラットフォームと自動売買基盤のための Python パッケージ群です。  
データの ETL、ニュースの収集・NLP スコアリング、ファクター計算、マーケットカレンダー管理、監査ログ（トレーサビリティ）など、投資戦略の研究〜運用に必要な基盤機能を提供します。

主な特徴
--------
- データ取得（J-Quants API）と DuckDB への冪等保存（差分取得 / ON CONFLICT）
- 日次 ETL パイプライン（株価、財務、カレンダー）
- ニュース収集（RSS）と LLM によるニュースセンチメント評価（gpt-4o-mini を想定）
- 市場レジーム判定（ETF 1321 の MA + マクロニュースで判定）
- ファクター計算（モメンタム / ボラティリティ / バリュー等）と統計ユーティリティ
- データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）初期化ユーティリティ
- 環境設定管理（.env 自動ロード、Settings オブジェクト経由のアクセス）

必要な環境変数（代表）
--------------------
- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / regime_detector 実行時に必要）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)

※ 自動 .env ロードはパッケージ読み込み時にプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を読み込みます。自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

セットアップ（開発環境）
----------------------
1. Python と依存ライブラリを用意します（例）。
   - Python 3.10+ 推奨
   - 主要依存: duckdb, openai, defusedxml など（requirements.txt を用意している場合はそれを使用）
   例:
   pip install duckdb openai defusedxml

2. リポジトリルートに .env を配置（.env.example を参照することを推奨）
   - 必須変数を設定してください（上記参照）。

3. データディレクトリを作成（必要に応じて）
   mkdir -p data

使用方法（主要 API と例）
------------------------

共通: Settings の利用
from kabusys.config import settings
- settings.duckdb_path などで設定値を取得できます。

DuckDB 接続例
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))

日次 ETL 実行（run_daily_etl）
from datetime import date
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())

個別 ETL（例）
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
# 同様に run_financials_etl / run_calendar_etl

ニューススコアリング（LLM）
from kabusys.ai.news_nlp import score_news
from datetime import date
# OPENAI_API_KEY を環境変数で設定するか api_key に渡す
count = score_news(conn, target_date=date(2026,3,20), api_key=None)
print(f"scored {count} codes")

市場レジーム判定
from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026,3,20), api_key=None)

監査ログ DB 初期化
from kabusys.data.audit import init_audit_db, init_audit_schema
# 監査専用 db を作る場合
audit_conn = init_audit_db("data/audit.duckdb")
# または既存 conn にテーブル追加
init_audit_schema(conn, transactional=True)

マーケットカレンダー操作
from kabusys.data.calendar_management import (
    is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
)
is_open = is_trading_day(conn, date(2026,3,20))

データ品質チェック
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)

研究用ユーティリティ（ファクター計算など）
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.data.stats import zscore_normalize
momentum = calc_momentum(conn, target_date=date(2026,3,20))
normed = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])

環境変数の自動読み込みについて
-----------------------------
パッケージ import 時にプロジェクトルートを探索して .env (優先度低) と .env.local (優先度高) を自動読み込みします。  
- 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数 / Settings 管理（.env 自動読み込み）
- ai/
  - __init__.py
  - news_nlp.py             — ニュースの LLM スコアリング（score_news）
  - regime_detector.py      — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - calendar_management.py  — マーケットカレンダー管理（is_trading_day 等）
  - pipeline.py             — ETL パイプライン（run_daily_etl 等）
  - jquants_client.py       — J-Quants API クライアント + 保存関数
  - news_collector.py       — RSS ニュース収集ユーティリティ
  - quality.py              — データ品質チェック
  - stats.py                — 統計ユーティリティ（zscore_normalize 等）
  - audit.py                — 監査ログ（テーブル作成 / init）
  - etl.py                  — ETLResult の公開（pipeline.ETLResult を再エクスポート）
- research/
  - __init__.py
  - factor_research.py      — モメンタム / バリュー / ボラティリティ計算
  - feature_exploration.py  — 将来リターン・IC・統計サマリー等
- research/（その他ファイルは factor_research / feature_exploration 参照）
- （その他: strategy, execution, monitoring パッケージは __all__ に含まれる想定）

設計上の注意点
--------------
- ルックアヘッドバイアス対策が随所に実装されています（datetime.today() に直接依存しない設計や、ETL の date パラメータ指定等）。
- LLM 呼び出し（OpenAI）はリトライ・バックオフを行い、API 失敗時はフェイルセーフでスコア 0.0 を返す箇所があるため、部分的失敗がシステム全体を停止させにくい設計です。
- DuckDB をデータ層に使用し、ON CONFLICT で冪等性を保っています。
- news_collector は SSRF / XML インジェクション / gzip bomb 等への対策を含みます（defusedxml、ホスト検査、サイズ制限など）。

よくある質問
------------
- Q: OpenAI の API キーはどこで設定する？  
  A: 環境変数 OPENAI_API_KEY、もしくは score_news/score_regime の api_key 引数で直接渡せます。

- Q: J-Quants の認証は？  
  A: JQUANTS_REFRESH_TOKEN を環境変数に設定してください。jquants_client.get_id_token がこれを使用して id token を取得します。

- Q: .env を自動で読み込ませたくない場合は？  
  A: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

付録: 最小スクリプト例
---------------------
# ETL を実行する最小スクリプト例
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
res = run_daily_etl(conn, target_date=date.today())
print(res.to_dict())

以上がプロジェクトの概要と主要な使い方です。README に含めてほしい追加項目（例: CI / テスト実行手順、依存関係ファイルの位置、.env.example のテンプレートなど）があれば教えてください。