KabuSys — 日本株 自動売買 / データプラットフォーム
================================================

概要
----
KabuSys は日本株のデータ収集・品質管理・特徴量計算・AI ベースのニュースセンチメント、
マーケットレジーム判定、監査ログ（トレーサビリティ）を備えた研究・自動売買プラットフォームのコアライブラリです。
主に DuckDB を使ったデータレイヤ、J-Quants API クライアント、ニュース収集・NLP、リサーチ用のファクター計算、
監査テーブルの初期化・管理、ETL パイプラインなどの機能を提供します。

主な機能
--------
- データ取得 / ETL
  - J-Quants からの株価日足、財務データ、マーケットカレンダー取得（jquants_client）
  - 差分更新・バックフィルを考慮した日次 ETL（data.pipeline.run_daily_etl）
- データ品質チェック（data.quality）
  - 欠損、スパイク、重複、日付不整合などの検出
- マーケットカレンダー管理（data.calendar_management）
  - 営業日判定、次/前営業日取得、カレンダーの夜間更新ジョブ
- ニュース収集（data.news_collector）
  - RSS からの収集、前処理、SSRF 対策、トラッキングパラメータ除去
- AI ベース NLP（kabusys.ai）
  - ニュース記事の銘柄ごとのセンチメントスコア化（score_news）
  - マクロニュース + ETF MA200 乖離を組み合わせた市場レジーム判定（score_regime）
- リサーチ（kabusys.research）
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- 監査ログ（data.audit）
  - signal_events / order_requests / executions を含む監査テーブルの初期化（冪等）
  - 監査用 DuckDB の初期化ユーティリティ
- 共通ユーティリティ
  - 設定管理（kabusys.config）: .env 自動読み込み、必須環境変数チェック
  - 統計ユーティリティ（data.stats）

セットアップ手順
----------------

1. リポジトリをクローン（例）
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - 最低限の依存例:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

4. 環境変数 / .env
   - プロジェクトルート（pyproject.toml または .git のあるディレクトリ）に .env を置くと自動読み込みされます。
   - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト用）。

   主な環境変数（必須 / デフォルト）
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須、jquants_client.get_id_token に使用）
   - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で使用、関数引数でオーバーライド可）
   - KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
   - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用（必須）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
   - KABUSYS_ENV — 実行環境 (development | paper_trading | live)、デフォルト development
   - LOG_LEVEL — ログレベル（DEBUG/INFO/...）、デフォルト INFO

   tip: .env のフォーマットは Bash 風（export 句・コメント・クォート等に対応）でパースされます。

使い方（簡単なサンプル）
----------------------

Python REPL / スクリプトから主要ユースケースを呼ぶ例を示します。

1) DuckDB に接続して日次 ETL を実行する
- 例:
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

2) ニュース NLP スコアを生成する（OpenAI API 必須）
- 例:
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 19), api_key=None)  # api_key None -> 環境変数 OPENAI_API_KEY を参照

  # 戻り値は書き込んだ銘柄数（int）

3) 市場レジーム判定
- 例:
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 19), api_key=None)

4) 監査ログ用 DB 初期化
- 例:
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # または :memory: でインメモリ DB を生成
  # conn = init_audit_db(":memory:")

主な API / 関数
----------------
（抜粋）
- kabusys.config.settings — 環境変数にアクセスするユーティリティ
- kabusys.data.pipeline.run_daily_etl(conn, target_date=..., id_token=...) — 日次 ETL（prices/financials/calendar + 品質チェック）
- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar — J-Quants API 取得
- kabusys.data.jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar — DuckDB へ保存（冪等）
- kabusys.data.news_collector.fetch_rss — RSS フェッチ（SSRF 対策・サイズ制限）
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None) — ニュース NLP スコアリング（ai_scores テーブルへ書込）
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — 市場レジーム判定（market_regime テーブルへ書込）
- kabusys.data.audit.init_audit_db(path) / init_audit_schema(conn) — 監査テーブル初期化
- kabusys.research.calc_momentum / calc_volatility / calc_value — ファクター計算
- kabusys.data.quality.run_all_checks(conn, target_date=..., reference_date=...) — 品質チェック群の実行

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                     — 環境変数・設定管理（.env 自動読み込み等）
- ai/
  - __init__.py
  - news_nlp.py                 — ニュース NLP（score_news）
  - regime_detector.py          — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py           — J-Quants API クライアント / DuckDB 保存
  - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
  - etl.py                      — ETL 型の公開インターフェース（ETLResult 等）
  - news_collector.py           — RSS ニュース収集（SSRF 対策含む）
  - calendar_management.py      — マーケットカレンダー管理
  - quality.py                  — データ品質チェック
  - stats.py                    — 統計ユーティリティ（zscore_normalize 等）
  - audit.py                    — 監査ログ（監査テーブル定義・初期化）
- research/
  - __init__.py
  - factor_research.py          — モメンタム/バリュー/ボラティリティ等
  - feature_exploration.py      — 将来リターン/IC/統計サマリー

設計上の注意点 / 運用メモ
-----------------------
- Look-ahead bias に配慮して、内部ロジックは datetime.today()/date.today() の無条件使用を避け、関数の引数で日付を受け取る設計が基本です。
- OpenAI 呼び出しはリトライやフォールバック（API 失敗時はスコア 0）を取り入れており、例外による全停止を避けます。ただし API レートや料金に注意してください。
- jquants_client は API レート制限（120 req/min）を守るよう設計されています。ID トークンの自動リフレッシュ、ページング処理、冪等保存（ON CONFLICT）に対応しています。
- news_collector は SSRF 対策、XML の安全パース（defusedxml）、受信サイズ制限などセキュリティ面に配慮しています。
- DuckDB への executemany に空リストを渡すとエラーになるバージョンがあるためコード中で空チェック等がされています。

トラブルシュート
-----------------
- .env 自動読み込みが不要／テストで邪魔な場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI や J-Quants の認証エラー:
  - 環境変数（OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN）が正しいか確認してください。
  - jquants_client.get_id_token() は内部でリフレッシュ処理を行いますが、環境変数が未設定だと例外になります。

貢献・拡張
----------
- 新しい ETL ソース、ニュースソース追加、AI モデル・プロンプト改善、リサーチ指標の追加などを歓迎します。
- テスト: API 呼び出し部分はモック化が容易な作りになっています（内部の _call_openai_api や _urlopen 等をパッチ可能）。

ライセンス・連絡
----------------
- 本リポジトリのライセンス / 連絡先はリポジトリルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

以上が KabuSys の概要と使い方の要点です。必要であれば、具体的な .env.example のテンプレートや実行スクリプト例（cron 用、Dockerfile、systemd ユニットなど）も作成します。どの形式が必要か教えてください。