# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL、ニュース収集、ニュースNLP（LLM を用いたセンチメント評価）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）などを包括的に提供します。

概要
- 設計方針は「バックテストでのルックアヘッドバイアス防止」「DB（DuckDB）中心の冪等操作」「外部 API の堅牢なリトライ・フェイルセーフ」。
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント／レジーム判定機能や、J-Quants API を使った株価・財務・カレンダー ETL を提供します。
- DuckDB を主要な永続化ストアとして想定しています。監査ログ用に専用 DuckDB DB を初期化するユーティリティもあります。

主な機能一覧
- data（ETL / カレンダー / ニュース収集 / J-Quants クライアント）
  - 日次 ETL パイプライン run_daily_etl：市場カレンダー、株価日足、財務データの差分取得・保存・品質チェック
  - jquants_client：J-Quants API 呼び出し、ページネーション、トークン自動リフレッシュ、保存ユーティリティ（raw_prices / raw_financials / market_calendar 等）
  - news_collector：RSS 取得・前処理・SSRF 対策・raw_news 保存（冪等）
  - quality：欠損/スパイク/重複/日付不整合などのデータ品質チェック
  - audit：signal → order_request → execution の監査テーブル定義と初期化（冪等）
  - calendar_management：market_calendar を使った営業日判定、next/prev/get_trading_days、calendar_update_job
  - ETLResult（パイプライン実行結果の定型）
- ai（ニュースNLP / 市場レジーム判定）
  - news_nlp.score_news：銘柄ごとのニュースを集約して LLM に投げ、ai_scores に書き込む
  - regime_detector.score_regime：ETF（1321）の MA200 乖離とマクロニュース LLM スコアを合成して market_regime に書き込む
  - 両モジュールとも OpenAI API のリトライや失敗時のフォールバックを実装
- research（ファクター計算・特徴量解析）
  - calc_momentum / calc_volatility / calc_value：ファクター計算（prices_daily / raw_financials 参照）
  - calc_forward_returns / calc_ic / factor_summary / rank / zscore_normalize：特徴量評価・統計ユーティリティ
- utils / config
  - 環境変数読み込みと Settings（.env の自動ロード、優先順位、必須値チェック）
  - 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を起点
  - 環境での自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

セットアップ手順（開発向け・例）
1. Python 環境を用意
   - 推奨: Python 3.10+
2. リポジトリをクローン
   - git clone <repo>
3. 依存パッケージをインストール
   - requirements.txt がある場合:
     - python -m pip install -r requirements.txt
   - 主要な依存（例）:
     - duckdb, openai, defusedxml
   - 開発インストール:
     - python -m pip install -e .
4. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動読み込みされます（優先: OS > .env.local > .env）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. 必須の環境変数（代表）
   - JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（settings.jquants_refresh_token）
   - KABU_API_PASSWORD: kabuステーション API のパスワード
   - OPENAI_API_KEY: OpenAI を直接使う場合は環境変数または関数引数で指定
   - そのほか（任意）:
     - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視DB, デフォルト data/monitoring.db）
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
     - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV（development / paper_trading / live）
     - LOG_LEVEL（DEBUG / INFO / WARNING / ERROR / CRITICAL）
   - Settings は kabusys.config.settings から参照できます。必須値未設定時は ValueError が発生します。

.env の自動ロード仕様
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に .env と .env.local を読み込み
- 読み込みルール:
  - OS 環境変数の既存キーは上書きしない（.env は override=False）
  - .env.local は override=True（OS 環境変数以外は上書き）
  - export KEY=val の形式に対応、クォートやエスケープ、インラインコメント処理あり
- 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方（主要なユースケース例）

1) DuckDB 接続を作って ETL を実行する（例）
```
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str("data/kabusys.duckdb"))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントをスコアリングして ai_scores に保存
```
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("scored:", n_written)
```
- api_key を None にした場合は環境変数 OPENAI_API_KEY を参照します。
- API 失敗時は個別チャンクをスキップして処理を継続します（フェイルセーフ）。

3) 市場レジーム判定（daily）
```
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key=None)
```
- ETF 1321 の MA200 乖離（重み70%）とマクロニュースセンチメント（重み30%）を合成して market_regime に書き込みます。
- OpenAI 呼び出しが失敗した場合 macro_sentiment = 0.0 で継続します（フェイルセーフ）。

4) 監査ログ（audit）DB を初期化する
```
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンを設定します
```

5) RSS ニュース取得（news_collector）を直接呼ぶ（低レベル）
```
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
```
- 内部で SSRF 対策、リダイレクト先検査、最大受信サイズ制限、XML パースの安全化（defusedxml）を行っています。
- 収集した記事は raw_news テーブルに冪等で保存する処理が別に用意されています。

注意点 / 設計に基づく挙動
- ルックアヘッドバイアス対策:
  - 日付計算では datetime.today() / date.today() を直接使わない（呼び出し側で target_date を渡すことが推奨）。
  - 特に AI モジュールや research モジュールは target_date 未満のデータのみを参照するよう設計されています。
- 外部 API 呼び出し:
  - J-Quants: 固定レート制限（120 req/min）、リトライ、401 時はトークン自動リフレッシュ。
  - OpenAI: 429/ネットワーク/5xx 等はリトライ（指数バックオフ）し、最終的に失敗しても処理継続の設計（多くは 0.0 やスキップでフォールバック）。
- DuckDB への書き込みは可能な限り冪等（ON CONFLICT DO UPDATE / DO NOTHING）を採用。
- news_nlp / regime_detector では OpenAI の JSON Mode を想定した厳密な JSON 出力を期待していますが、パース失敗時の安全処理を備えています。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                      — .env 自動ロード、Settings
  - ai/
    - __init__.py (score_news をエクスポート)
    - news_nlp.py                   — ニュースセンチメント（score_news）
    - regime_detector.py            — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント + 保存関数
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETLResult 再エクスポート
    - news_collector.py             — RSS 収集・前処理
    - quality.py                    — 品質チェック
    - stats.py                      — zscore_normalize 等
    - calendar_management.py        — 市場カレンダー管理・営業日判定
    - audit.py                      — 監査ログ DDL と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py            — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py        — calc_forward_returns / calc_ic / factor_summary / rank

開発・運用上のヒント
- ログレベルは環境変数 LOG_LEVEL で制御（INFO デフォルト）。
- 本番運用時は KABUSYS_ENV=live / paper_trading を使い分け、Settings.is_live / is_paper を参照して振る舞いを分岐できます。
- テストや CI で .env 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセット。
- DuckDB ファイルのパス（DUCKDB_PATH）は settings.duckdb_path を通じて取得できます。親ディレクトリがない場合は init_audit_db 等が自動作成します。

その他
- README に書かれている以外の詳細（DB スキーマ全体、API の詳細仕様、Strategy の実行フローや実際の発注ロジック）は別ドキュメント（StrategyModel.md / DataPlatform.md 等）に従ってください（コード内ドキュメントに多くの設計メモが含まれています）。
- セキュリティ: API キーやトークンはソース管理しないでください。.env や環境変数で運用してください。

質問や README に追加したい使用例・運用手順があれば指定してください。README のサンプル .env 例や運用チェックリストも作成できます。