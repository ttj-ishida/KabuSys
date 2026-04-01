KabuSys — 日本株向けデータ基盤＆自動売買ユーティリティ
================================================================

概要
----
KabuSys は日本株のデータ取得 / ETL / 品質チェック / 研究用ファクター計算 / ニュース NLP / 市場レジーム判定 / 監査ログなどを提供するライブラリ群です。J-Quants API と連携して DuckDB にデータを蓄積し、OpenAI（gpt-4o-mini）を利用したニュースセンチメント分析やレジーム判定、研究用途のファクター計算を行えます。発注・約定の監査トレース用スキーマも含まれます。

主な機能
--------
- J-Quants からの差分 ETL（株価日足 / 財務 / 市場カレンダー）
- ETL の品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集（RSS）と NLP による銘柄別センチメントスコア生成（OpenAI）
- 市場レジーム判定（ETF 1321 の MA とマクロ記事の LLM スコアを合成）
- 研究向けファクター計算（モメンタム / ボラティリティ / バリュー）と特徴量解析（前方リターン / IC / サマリー）
- 監査ログスキーマ（signal_events, order_requests, executions）と初期化ユーティリティ
- DuckDB を中心とした冪等保存（ON CONFLICT での更新）と堅牢な API リクエスト制御（レート管理・リトライ・トークンリフレッシュ）
- セットアップしやすい環境変数ベースの設定読み込み（.env / .env.local の自動ロード）

必要要件（主な依存）
-------------------
- Python 3.9+
- duckdb
- openai
- defusedxml
- （その他標準ライブラリのみで多くを実装）

セットアップ手順
----------------
1. リポジトリをクローン（またはパッケージとしてインストール）
   - 開発環境例:
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install -e .

   あるいは要件ファイルがある場合:
     - pip install -r requirements.txt

2. 環境変数の設定
   - プロジェクトルートに .env（および .env.local）を置くと自動で読み込まれます（config モジュールによる）。
   - 自動ロードを無効にする場合:
     - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト時など）。

主要な環境変数（.env に設定する例）
----------------------------------
- JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン（必須：ETL）
- OPENAI_API_KEY         — OpenAI API キー（必須：ニュース NLP / レジーム判定）
- KABU_API_PASSWORD      — kabu ステーション API パスワード（発注連携がある場合）
- KABU_API_BASE_URL      — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN        — Slack 通知に使用（必須なら）
- SLACK_CHANNEL_ID       — Slack のチャンネル ID
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH            — 監視用 SQLite パス（デフォルト data/monitoring.db）
- PID_FILE_PATH          — 実行監視用 PID ファイルパス（デフォルト data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV            — environment: development / paper_trading / live（デフォルト development）
- LOG_LEVEL              — ログレベル: DEBUG/INFO/…（デフォルト INFO）

使い方（よく使う API の例）
-------------------------

基本：DuckDB 接続の作成
- Python REPL 例:
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

ETL（日次パイプライン）を実行する
- from datetime import date
- from kabusys.data.pipeline import run_daily_etl
- result = run_daily_etl(conn, target_date=date(2026,3,20))
- print(result.to_dict())

個別 ETL（株価 / 財務 / カレンダー）
- from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
- run_prices_etl(conn, target_date, id_token=None)
- run_financials_etl(conn, target_date)
- run_calendar_etl(conn, target_date)

ニュース NLP スコア（OpenAI 必須）
- from kabusys.ai.news_nlp import score_news
- from datetime import date
- n = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
- 返り値は書き込み銘柄数（int）。OPENAI_API_KEY を環境に設定すれば api_key は省略可。

市場レジーム判定（OpenAI 必須）
- from kabusys.ai.regime_detector import score_regime
- score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

監査ログ DB の初期化
- from kabusys.data.audit import init_audit_db
- conn_audit = init_audit_db("data/audit.duckdb")
- これで signal_events / order_requests / executions 等のテーブルとインデックスが作成されます。

研究機能（ファクター計算等）
- from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize
- mom = calc_momentum(conn, target_date)
- vol = calc_volatility(conn, target_date)
- val = calc_value(conn, target_date)
- normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])

ニュース収集（RSS）
- from kabusys.data.news_collector import fetch_rss, preprocess_text
- articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
- preprocess_text を使ってタイトル/本文の前処理が可能

設定ファイルの自動読み込みについて
----------------------------------
- config.Settings モジュールはプロジェクトルート（.git または pyproject.toml を探索）から .env と .env.local を自動読み込みします。
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- .env.local は .env を上書きする想定（ローカル秘密情報や上書き用）
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト等で利用）

運用上の注意
-----------
- J-Quants API はレート制限があり、本実装では固定間隔スロットリング（120 req/min）とリトライを行います。大量一括実行の際は設定の確認をしてください。
- OpenAI 呼び出しはコストがかかります。ニュース NLP やレジーム判定をバッチ実行する際はリクエスト数とモデル利用料に注意してください。
- DuckDB の executemany に空リストを渡すとバージョン依存でエラーになる可能性があるため、内部で空チェックが行われています。直接 SQL を叩く場合は留意してください。
- ローカルテストで .env の自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

ディレクトリ構成（概要）
----------------------
src/kabusys/
- __init__.py                      — パッケージ定義（version 等）
- config.py                        — 環境変数 / 設定読み込みロジック（.env 自動読み込み含む）
- ai/
  - __init__.py
  - news_nlp.py                    — ニュース NLP（銘柄別スコア化、OpenAI 連携）
  - regime_detector.py             — 市場レジーム判定（MA + マクロ記事 LLM 合成）
- data/
  - __init__.py
  - jquants_client.py              — J-Quants API クライアント（取得 + 保存ユーティリティ）
  - pipeline.py                    — ETL パイプライン（差分取得・品質チェック）
  - etl.py                         — ETL の公開インターフェース（ETLResult 再エクスポート）
  - news_collector.py              — RSS 収集・前処理・保存ユーティリティ
  - calendar_management.py         — 市場カレンダー管理（営業日判定等）
  - quality.py                     — データ品質チェック
  - stats.py                       — 汎用統計ユーティリティ（z-score）
  - audit.py                       — 監査ログスキーマ初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py             — Momentum/Value/Volatility 等のファクター計算
  - feature_exploration.py         — 将来リターン / IC / 統計サマリー 等
- research/...（その他研究ユーティリティ）
- その他（strategy / execution / monitoring などは __all__ に想定されているが、ここに含まれないコンポーネントは将来的に追加予定）

開発者向け補足
---------------
- コードはルックアヘッドバイアス対策のため、内部で datetime.today()/date.today() を直接参照しない設計になっています（引数で target_date を渡す）。
- OpenAI 呼び出し部分はテスト容易性を考慮して差し替え可能（ユニットテストでは patch で _call_openai_api をモックしてください）。
- DuckDB とのやり取りは埋め込み SQL を多用しています。SQL の互換性・バージョン差に注意してください（特に executemany の挙動など）。

ライセンス、貢献
---------------
- この README にはライセンス情報は含みません。実プロジェクトに合わせて LICENSE を追加してください。
- バグ修正・機能追加の PR は歓迎します。テストとリントを付けていただけると助かります。

以上。必要であれば、README に実行例（より詳細なスクリプト例）や .env.example のテンプレートを追加します。どの項目を詳しく追記しましょうか？