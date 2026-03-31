KabuSys
=======

概要
----
KabuSys は日本株向けのデータプラットフォームと研究・自動売買基盤の骨組みを提供する Python パッケージです。J-Quants からのデータ取得（株価・財務・市場カレンダー）、RSS ニュース収集、AI（OpenAI）によるニュースセンチメント評価、ファクター計算、ETL パイプライン、監査ログ（発注/約定トレーサビリティ）などを含みます。DuckDB をデータレイクとして用いる設計です。

主な特徴
--------
- J-Quants API クライアント（取得・保存・リトライ・レート制御・トークン自動リフレッシュ）
- 日次 ETL パイプライン（価格・財務・カレンダーの差分取得、品質チェック）
- ニュース収集（RSS、SSRF 対策、トラッキングパラメータ除去、前処理）
- ニュースの AI スコアリング（OpenAI を用いた銘柄別センチメント、JSON Mode を利用）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）と初期化ユーティリティ
- 環境変数 / .env 自動読み込み（プロジェクトルート検出）と Settings API

セットアップ
-----------

前提
- Python 3.10 以上（コードは PEP 604 の union 型表記などを使用）
- DuckDB、openai、defusedxml などの外部ライブラリ

インストール（開発用）
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに setup.cfg/pyproject.toml がある場合は pip install -e . で開発インストール）

環境変数 / .env
- プロジェクトはルート（.git または pyproject.toml があるディレクトリ）を探索して .env/.env.local を自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- 主要な環境変数（少なくとも以下は設定が必要または使用されます）:

  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須：jquants_client.get_id_token で使用）
  - OPENAI_API_KEY         : OpenAI API キー（score_news / score_regime 等の AI 機能で使用）
  - KABU_API_PASSWORD     : kabuステーション API パスワード（実運用時）
  - KABU_API_BASE_URL     : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - SLACK_BOT_TOKEN       : Slack 通知用トークン（モニタリング用）
  - SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID
  - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH           : SQLite（監視DB）パス（デフォルト: data/monitoring.db）
  - PID_FILE_PATH         : 実行 PID ファイルパス（デフォルト: data/execution.pid）
  - KABUSYS_ENV           : 環境 ("development", "paper_trading", "live")（デフォルト "development"）
  - LOG_LEVEL             : ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト "INFO"）

  例 (.env)
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    OPENAI_API_KEY=sk-...
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=CXXXXXXX
    DUCKDB_PATH=data/kabusys.duckdb

使い方（簡単な例）
-----------------

DuckDB 接続を作り、ETL やスコア処理を呼び出す簡単な Python スクリプト例:

- 日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの AI スコアリング（指定日）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化（専用 DB）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って監査ログへ書き込みや参照が可能
```

主要 API / 呼び出し先
- ETL / データ
  - kabusys.data.pipeline.run_daily_etl(...)
  - run_prices_etl, run_financials_etl, run_calendar_etl
  - kabusys.data.jquants_client.*（fetch_*/save_*）
- ニュース / AI
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 研究
  - kabusys.research.calc_momentum / calc_value / calc_volatility
  - kabusys.research.calc_forward_returns, calc_ic, factor_summary, rank
- データ品質
  - kabusys.data.quality.run_all_checks(...)
- 監査ログ初期化
  - kabusys.data.audit.init_audit_db(path) / init_audit_schema(conn)

挙動・注意点
-------------
- AI 関連（score_news, score_regime）は OPENAI_API_KEY を参照します。API 呼び出しに失敗した場合はフェイルセーフとしてスコアに 0 を用いる設計（例外を投げずに継続する箇所がある）。
- J-Quants クライアントはレート制限（120 req/min）・リトライ・トークン自動リフレッシュを内蔵しています。
- ETL や AI スコアはルックアヘッドバイアスを避けるため、内部で date.today() / datetime.today() を直接参照しない設計がされています（target_date を明示的に渡すことを推奨）。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テストや一時的に無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany は空リストを受け付けないバージョンがあるため、コード側で空チェックを行っています。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                       -- 環境変数 / Settings 管理（.env 自動ロード含む）
- ai/
  - __init__.py
  - news_nlp.py                    -- ニュースの銘柄別センチメント生成（OpenAI）
  - regime_detector.py             -- 市場レジーム判定（MA200 + マクロセンチメント）
- data/
  - __init__.py
  - jquants_client.py              -- J-Quants API クライアント（fetch/save 等）
  - pipeline.py                    -- ETL パイプライン / run_daily_etl 等
  - etl.py                         -- ETLResult の再エクスポート
  - calendar_management.py         -- JPX カレンダー管理（market_calendar）
  - news_collector.py              -- RSS ニュース収集、前処理、SSRF 対策
  - quality.py                     -- データ品質チェック（欠損・スパイク・重複・日付整合性）
  - stats.py                       -- zscore_normalize 等の統計ユーティリティ
  - audit.py                        -- 監査ログスキーマ定義・初期化
- research/
  - __init__.py
  - factor_research.py             -- モメンタム/バリュー/ボラティリティ計算
  - feature_exploration.py         -- 将来リターン・IC・統計サマリー
- research/... (その他の分析ユーティリティ)
- その他（monitoring, execution, strategy 等の名前が __all__ に見えるが実装はこのコードベースにまとめられています）

開発・テストのヒント
--------------------
- テストでは OpenAI / ネットワーク呼び出しをモックしてください。news_nlp と regime_detector は内部で _call_openai_api をラップしているため、ユニットテストではこれを patch して応答を制御できます。
- .env の自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB を使うため、テストは ":memory:" を指定してインメモリ DB を利用できます（例: duckdb.connect(":memory:")）。
- audit.init_audit_db() は必要に応じて transactional=True/False を切替可能です（既存トランザクションとの兼ね合いに注意）。

ライセンス・貢献
----------------
（ここにライセンス情報やコントリビュート方法を記載してください。プロジェクトに LICENSE ファイルがある場合は参照してください。）

問い合わせ
----------
不具合や要望は Issue を立ててください。開発時の設計方針や安全性（SSRF、データ整合性、ルックアヘッド回避）を重視して実装されているため、新機能追加の際もこれらの観点を維持してください。