KabuSys — 日本株 自動売買 / データプラットフォーム
=================================================

概要
----
KabuSys は日本株のデータ収集・品質管理・ファクター計算・AI ベースのニュースセンチメント評価・監査ログを備えた
研究/運用向けの自動売買プラットフォーム向けライブラリ群です。
主に以下を提供します。

- J-Quants API からの差分 ETL（株価・財務・マーケットカレンダー）
- ニュース収集（RSS）と LLM を用いた銘柄別ニュースセンチメント付与
- 市場レジーム判定（ETF + マクロニュースの合成）
- ファクター（モメンタム・バリュー・ボラティリティ等）計算と研究用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution）のための DuckDB スキーマ初期化

主な機能一覧
--------------
- データ取得 / ETL
  - J-Quants API 用クライアント（認証・ページネーション・レート制御・リトライ）
  - run_daily_etl による日次差分 ETL（prices / financials / calendar）
- データ品質管理
  - quality.run_all_checks による欠損・スパイク・重複・日付不整合の検出
- データ操作ユーティリティ
  - calendar_management による営業日判定・次営業日/前営業日の取得
  - audit.init_audit_db / init_audit_schema による監査テーブル初期化（DuckDB）
- AI（OpenAI）統合
  - news_nlp.score_news: ニュース記事を LLM に送信して銘柄別 ai_score を ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF 1321 の MA を使ったテクニカル寄与とマクロニュースの LLM センチメントを合成して market_regime に保存
- 研究用ユーティリティ
  - research.calc_momentum / calc_value / calc_volatility
  - research.feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー
- ニュース収集
  - news_collector.fetch_rss: RSS フィードの安全な取得と前処理（SSRF 対策・トラッキング除去・サイズ制限等）

セットアップ手順
----------------

1. Python (3.10+) と仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 推奨の主要依存:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトで requirements.txt を用意している場合は pip install -r requirements.txt を使用してください）

3. 環境変数 / .env の準備
   - プロジェクトルートに .env を作成してください（.env.example を参考に）。
   - 自動的に .env と .env.local（存在する場合）を読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば無効化可能）。
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN  (必須) — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD      (必須) — kabu ステーション API パスワード（発注機能を使う場合）
     - OPENAI_API_KEY         — OpenAI API キー（AI 関連関数呼び出しで必要、引数で上書き可能）
     - KABU_API_BASE_URL      — kabu API のベース URL（省略時 http://localhost:18080/kabusapi）
     - DUCKDB_PATH            — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - その他: LINE_*（通知用）, PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEM thresholds, KABUSYS_ENV, LOG_LEVEL

   - .env の自動読み込み仕様:
     - 優先度: OS 環境変数 > .env.local > .env
     - プロジェクトルートは .git または pyproject.toml を探索して決定
     - 自動読み込みを無効にする場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

例: .env（最小例）
-----------------
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-xxxx...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

使い方（簡単な例）
-----------------

以下はライブラリ API を直接呼ぶ際の例です。実運用では CLI やワーカーから呼ぶことを想定しています。

- DuckDB 接続の作成
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行
  - from datetime import date
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニュースのスコアリング（LLM）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数に設定しておく
  - print(f"scored {n} symbols")

  - api_key を引数で明示的に渡すことも可能:
    - score_news(conn, date(2026,3,20), api_key="sk-...")

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY が必要

- 監査 DB 初期化（監査テーブルを新規に作る）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/monitoring.duckdb")

- カレンダー更新バッチ（単体）
  - from kabusys.data.calendar_management import calendar_update_job
  - saved = calendar_update_job(conn)
  - print(f"saved {saved} calendar records")

注意点 / 設計方針（要点）
-----------------------
- Look-ahead バイアス対策:
  - 多くの関数は内部で datetime.today() / date.today() を直接参照せず、呼び出し側が target_date を渡す設計です（バックテストで過去日時のみを使うため）。
- LLM 呼び出し:
  - OpenAI のレスポンスパース失敗や API 障害時には安全側（ゼロやスキップ）で継続する設計です。重大な例外は呼び出し側に伝播します。
- ETL の堅牢性:
  - 差分取得・バックフィル・品質チェックを組み合わせ、各ステップは独立してエラーハンドリングされます。
- セキュリティ:
  - API キー・パスワードなどのシークレットは .env や環境変数で管理し、リポジトリにコミットしないでください。
  - news_collector は SSRF 対策（リダイレクト検証 / プライベートアドレス拒否）や受信サイズ制限を実装しています。

主要モジュールとディレクトリ構成
-------------------------------

src/kabusys/
- __init__.py
- config.py                    — 環境変数/設定管理（.env 自動読み込み）
- ai/
  - __init__.py
  - news_nlp.py                 — ニュース NLP（LLM で銘柄別スコア化）
  - regime_detector.py         — 市場レジーム判定（ETF + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py          — J-Quants API クライアント（fetch/save）
  - pipeline.py                — ETL パイプライン（run_daily_etl 等）
  - etl.py                     — ETL 公開インターフェース（ETLResult）
  - quality.py                 — データ品質チェック
  - stats.py                   — 統計ユーティリティ（zscore_normalize）
  - calendar_management.py     — マーケットカレンダー管理（is_trading_day 等）
  - news_collector.py          — RSS によるニュース収集（SSRF 対策等）
  - audit.py                   — 監査ログスキーマ初期化（signal/order_requests/executions）
- research/
  - __init__.py
  - factor_research.py         — モメンタム/バリュー/ボラティリティ計算
  - feature_exploration.py     — 将来リターン / IC / 統計サマリー
- research/他モジュール ...     — 研究用ユーティリティ群
- その他モジュール（strategy, execution, monitoring 等）はパッケージ公開を想定

（上記は提供されたコードベースの主要ファイルを抜粋した構成です）

コントリビュート / テスト
------------------------
- 開発環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env ロードを無効化できます（ユニットテストなどで便利）。
- OpenAI や J-Quants の外部 API 呼び出しはモック（unittest.mock.patch）してテストしてください。ソース中でも _call_openai_api 等を差し替え可能な実装にしています。

よくある質問
-------------
- Q: OpenAI のキーはどの環境変数を使いますか？
  - A: OPENAI_API_KEY を使用します。個々の関数は api_key 引数で明示的に渡すこともできます。

- Q: .env の上書き順序は？
  - A: OS環境 > .env.local > .env の順で優先されます。

- Q: J-Quants の認証方法は？
  - A: JQUANTS_REFRESH_TOKEN を設定し、内部で get_id_token により id_token を取得します。

ライセンス / 注意
-----------------
この README はコードの説明を目的としたものであり、実運用では各種 API の利用規約やレート制限、取引リスク管理（注文制御・二重発注防止・監査）の適切な実装を行ってください。また、API キーや認証情報は厳重に管理し、公開リポジトリには含めないでください。

お問い合わせ
------------
このドキュメントの改善点や追加説明が必要な箇所があればお知らせください。README の他、各モジュール内の docstring に詳細な設計意図と使用例が記載されています。