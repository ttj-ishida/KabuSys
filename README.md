KabuSys — 日本株自動売買プラットフォーム
======================================

概要
----
KabuSys は日本株を対象としたデータ基盤・リサーチ・監視・自動売買のためのライブラリ群です。  
主な目的は以下です。

- J-Quants API から市場データ（株価、財務、カレンダー等）を差分取得して DuckDB に格納する ETL パイプライン
- ニュース収集・NLP による銘柄センチメント算出（OpenAI を利用）
- 市場レジーム判定（ETF + マクロニュースの合成）
- ファクター計算・特徴量解析（リサーチ）
- データ品質チェック、マーケットカレンダー管理、監査（発注から約定までのトレーサビリティ）

この README はリポジトリ内の主要モジュール設計に基づく基本的な使い方・セットアップ手順を記載しています。

主な機能
--------
- ETL（data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl：J-Quants から差分取得・保存
  - ETL 実行結果は ETLResult オブジェクトで取得
- ニュース収集・NLP（data.news_collector, ai.news_nlp）
  - RSS 取得、前処理、raw_news への冪等保存
  - OpenAI（gpt-4o-mini）の JSON Mode を使った銘柄ごとのセンチメントスコア化（score_news）
- 市場レジーム判定（ai.regime_detector）
  - ETF 1321 の 200日 MA 乖離とマクロニュースの LLM センチメントを合成して日次レジーム判定（score_regime）
- リサーチ（research）
  - ファクター計算: momentum, value, volatility
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - zscore_normalize 等の統計ユーティリティ
- データ品質チェック（data.quality）
  - 欠損・スパイク・重複・日付不整合チェック（run_all_checks）
- 監査ログ（data.audit）
  - signal_events / order_requests / executions テーブルの初期化と監査 DB の作成（init_audit_schema / init_audit_db）
- J-Quants クライアント（data.jquants_client）
  - rate limiting、リトライ、トークン自動リフレッシュ、ページネーション対応での取得・保存関数

前提（推奨）
------------
- Python >= 3.10（型ヒントに | 演算子を使用）
- インターネット接続（J-Quants / OpenAI 等の外部 API）
- 推奨ライブラリ（以下をインストールしてください）
  - duckdb
  - openai
  - defusedxml
  - （必要に応じて）その他ネットワーク・HTTP 標準ライブラリで対応可能な依存

環境変数 / 設定
----------------
設定は環境変数またはプロジェクトルートの .env / .env.local から読み込まれます。
自動読み込みはデフォルト有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。読み込み優先度は
OS 環境 > .env.local > .env です。

主に使われる環境変数（最低限）：
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime のデフォルト）
- KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
- KABU_API_BASE_URL     : kabuステーションベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV           : 実行環境 ("development","paper_trading","live")（デフォルト: development）
- LOG_LEVEL             : ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")

設定アクセス方法例:
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)

セットアップ手順
---------------
1. リポジトリをクローンして仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

3. （任意）パッケージとして開発インストール
   - pip install -e .

4. 環境変数を設定
   - プロジェクトルートに .env を作成するか、環境変数として設定してください。
   - 例 (.env):
       JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
       OPENAI_API_KEY=your_openai_api_key
       KABU_API_PASSWORD=your_kabu_password
       SLACK_BOT_TOKEN=xoxb-...
       SLACK_CHANNEL_ID=C01234567
       DUCKDB_PATH=data/kabusys.duckdb
       KABUSYS_ENV=development
   - 自動ロードを一時的に無効にする場合:
       export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方（簡単な例）
-----------------

1) DuckDB 接続を作成する
import duckdb
from kabusys.config import settings
conn = duckdb.connect(str(settings.duckdb_path))

2) 日次 ETL を実行する（J-Quants から差分取得して保存・品質チェック）
from datetime import date
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

3) ニュースセンチメントの算出（OpenAI API キーは環境変数か api_key 引数で）
from kabusys.ai.news_nlp import score_news
from datetime import date
n_written = score_news(conn, target_date=date(2026,3,20))
print(f"scored {n_written} codes")

4) 市場レジーム判定（ETF 1321 の ma200 + マクロニュース）
from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026,3,20))

5) 監査テーブルを初期化する（監査専用 DB を作る例）
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events/order_requests/executions テーブルが初期化されます

6) 研究用ファクター計算例
from kabusys.research.factor_research import calc_momentum
from datetime import date
res = calc_momentum(conn, target_date=date(2026,3,20))
# res は各銘柄ごとの辞書リスト

注意事項 / 設計上のポイント
--------------------------
- Look-ahead バイアス排除:
  - 内部処理は基本的に datetime.today()/date.today() を無作為に参照しない設計になっており、
    target_date 引数で明示的に日付を与えることが推奨されます（特に research / ai モジュール）。
- OpenAI 呼び出し:
  - news_nlp と regime_detector は OpenAI を利用します。API 失敗時はフェイルセーフ（スコア 0.0）で継続する実装になっていますが、API キー・課金に注意してください。
- ETL の堅牢性:
  - J-Quants クライアントはレート制限・リトライ・401 リフレッシュを備えています。
  - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で行います。
- ニュース収集の安全対策:
  - RSS 取得時に SSRF 対策、Content-Length / サイズ制限、XML パースの安全ライブラリ（defusedxml）を使用しています。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

src/kabusys/
- __init__.py
- config.py                      -- 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                  -- ニュース NLP / score_news
  - regime_detector.py           -- 市場レジーム判定 / score_regime
- data/
  - __init__.py
  - jquants_client.py            -- J-Quants API クライアント & 保存関数
  - pipeline.py                  -- ETL パイプライン（run_daily_etl 等）
  - etl.py                       -- ETLResult 再エクスポート
  - news_collector.py            -- RSS 取得・正規化・raw_news 保存
  - calendar_management.py       -- マーケットカレンダー管理（is_trading_day 等）
  - stats.py                     -- 統計ユーティリティ（zscore_normalize）
  - quality.py                   -- データ品質チェック
  - audit.py                     -- 監査ログテーブル初期化 / init_audit_db
- research/
  - __init__.py
  - factor_research.py           -- momentum/value/volatility
  - feature_exploration.py       -- 将来リターン / IC / summary / rank

（上記以外に strategy / execution / monitoring 等のトップレベル API が想定されています）

開発／貢献
----------
- 静的型チェック・ユニットテストの追加を歓迎します。
- OpenAI / J-Quants 依存のある機能は外部 API をモックして単体テストを作成してください（モジュール内で _call_openai_api の差し替えを想定しています）。

ライセンス
---------
（本 README では省略 — リポジトリの LICENSE ファイルを参照してください）

補足
----
- ここに示したコード利用例は最小限の呼び出し例です。実運用ではログ設定・例外処理・シークレット管理（Vault 等）を導入してください。