KabuSys — 日本株自動売買 / データプラットフォーム
======================================

概要
----
KabuSys は日本株向けのデータプラットフォーム兼自動売買基盤のライブラリ群です。本リポジトリには以下の主要機能が含まれます。

- J-Quants API からの株価・財務・カレンダー等の差分取得（ETL）
- RSS ベースのニュース収集と前処理（raw_news）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント & 市場レジーム判定
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions）のためのスキーマ初期化ユーティリティ
- DuckDB を用いたローカルデータ保存、監視用 SQLite パス指定

対象読者: データエンジニア / クオンツリサーチ / 自動売買システム開発者

主な機能一覧
--------------
- data/
  - ETL パイプライン（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
  - J-Quants API クライアント（認証、自動リトライ、レートリミット、保存関数）
  - 市場カレンダー管理（営業日判定、next/prev trading day、calendar_update_job）
  - ニュース収集（RSS 取得、安全対策、前処理、冪等保存）
  - データ品質チェック（missing_data, spike, duplicates, date_consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: ニュースを集約し OpenAI で銘柄ごとセンチメントを算出して ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime に保存
- research/
  - factor 計算（calc_momentum, calc_volatility, calc_value）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）

動作要件
---------
- Python 3.10 以上（型記法 `X | Y` を使用）
- 主要依存（抜粋）:
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- 標準ライブラリの urllib 等を利用（追加で slack 等を用いる場合は別途インストール）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / poetry 等がある場合はそれに従ってください）
4. パッケージを編集可能モードでインストール（任意）
   - pip install -e .
5. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のある場所）に .env, .env.local を置くと自動で読み込まれます。
   - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

重要な環境変数（一覧）
--------------------
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン（ETL 認証に使用）
- KABU_API_PASSWORD (必須) — kabu ステーション API のパスワード（実行モジュールで使用）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン（通知を使う場合）
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- OPENAI_API_KEY (必須 for ai.score_news/score_regime) — OpenAI API キー（関数引数でも渡せます）
- KABUSYS_ENV (任意) — 実行環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意) — ログレベル: DEBUG, INFO, WARNING, ERROR, CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 (任意) — .env 自動読み込みを抑止
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH (任意) — SQLite 監視 DB パス（デフォルト data/monitoring.db）
- KABU_API_BASE_URL (任意) — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）

簡単な .env 例
--------------
例（プロジェクトルート/.env）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb

使い方（主な API と実行例）
--------------------------

- DuckDB に接続して ETL を起動する（Python REPL / スクリプト）:
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  conn = duckdb.connect("data/kabusys.duckdb")
  # 日次 ETL 実行（target_date を指定しない場合は今日）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- J-Quants トークンを手動で取得する:
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を使用

- ニュースセンチメントをスコアリングして ai_scores に保存:
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY が環境変数にあるか、api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", n_written)

- 市場レジームを判定して market_regime に保存:
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ用 DB を初期化:
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")

- 研究用関数（例: momentum 計算）:
  from kabusys.research.factor_research import calc_momentum
  from datetime import date
  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))

実行に関する注意点
------------------
- Look-ahead bias に配慮した設計が多くの関数に組み込まれています（関数は内部で date.today() に依存しない等）。
- OpenAI への呼び出しは gpt-4o-mini を想定しており、JSON Mode レスポンスをパースする実装です。API 呼び出しにはレート制御・リトライロジックがあります。
- J-Quants API はレート制限（120 req/min）を考慮して実装されています。get_id_token(), fetch_daily_quotes などは自動リトライとレート制御を備えます。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml の位置）を基準に行います。テスト等で自動読み込みを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany に空リストを渡すと失敗するバージョンがあるため、モジュール側で空判定を行っています。ローカルの duckdb バージョンに注意してください。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                    — 環境変数 / 設定管理（.env 自動ロード含む）
- ai/
  - __init__.py
  - news_nlp.py                — ニュースセンチメントの取得・ai_scores 書き込み
  - regime_detector.py         — マクロ + MA200 による市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py          — J-Quants API クライアント（取得・保存）
  - pipeline.py                — ETL パイプライン（run_daily_etl 等）
  - etl.py                     — ETLResult のエクスポート
  - news_collector.py          — RSS 収集と前処理
  - calendar_management.py     — 市場カレンダー管理（is_trading_day 等）
  - quality.py                 — データ品質チェック
  - audit.py                   — 監査ログスキーマ初期化
  - stats.py                   — zscore_normalize 等の統計ユーティリティ
- research/
  - __init__.py
  - factor_research.py         — モメンタム / ボラ / バリュー等
  - feature_exploration.py     — 将来リターン, IC, summary, rank
- research/*、その他モジュール…

貢献・拡張
----------
- 新しい ETL 対象やニュースソースの追加、OpenAI の出力フォーマット変更への対応、kabu（発注）連携の実装などが今後の拡張候補です。
- コードを変更する際は Look-ahead bias に留意してください（特に研究用関数・ETL）。

ライセンス
---------
（本 README ではライセンス情報を明記していません。リポジトリに LICENSE ファイルがあればそちらを参照してください。）

補足
----
何か不明点・追加で README に載せてほしい内容（テスト手順、CI、より詳しい環境変数説明など）があれば教えてください。README を追記・改善します。