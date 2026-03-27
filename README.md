KabuSys
=======

日本株向けの自動売買 / データ基盤ライブラリ。  
DuckDB をデータレイヤーに用い、J-Quants や RSS、OpenAI（LLM）を組み合わせてデータ収集・品質管理・ファクター計算・ニュース NLP・市場レジーム判定・監査ログなどの機能を提供します。

主な用途
- 日次 ETL（株価・財務・市場カレンダー）の差分取得・品質チェック
- ニュース収集・前処理・LLM を用いた銘柄別センチメントスコアリング
- 市場（レジーム）判定（ETF MA とマクロニュースの合成）
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ 等）
- 監査ログ（signal → order_request → execution のトレース）スキーマ初期化

機能一覧
- 環境設定読み込み（.env / .env.local または環境変数）
- J-Quants API クライアント（レート制御・再試行・トークンリフレッシュ）
- ETL パイプライン（run_daily_etl を提供）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS、SSRF 対策、前処理、DB 保存用ユーティリティ）
- ニュース NLP（OpenAI を用いたバッチセンチメント、JSON Mode ハンドリング・リトライ）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを統合）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー、forward returns、IC、統計サマリ）
- 監査テーブルの初期化ユーティリティ（DuckDB）

要件（主な依存関係）
- Python 3.10+
- duckdb
- openai
- defusedxml

（その他標準ライブラリで完結する部分あり。実行環境に応じて追加パッケージをインストールしてください。）

セットアップ手順

1. リポジトリをクローン / コピー
   - 例: git clone <repo-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存関係のインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements.txt があればそちらを利用してください）
   - pip install -e . などパッケージ化されている場合は editable install。

4. 環境変数設定
   - プロジェクトルート（.git のある親ディレクトリ）に .env または .env.local を置くと、自動で読み込まれます。
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須環境変数（代表的なもの）
- JQUANTS_REFRESH_TOKEN  … J-Quants のリフレッシュトークン（jquants_client で使用）
- KABU_API_PASSWORD      … kabu ステーション API のパスワード（設定値として参照）
- SLACK_BOT_TOKEN        … Slack 通知用 Bot トークン（通知機能利用時）
- SLACK_CHANNEL_ID       … Slack チャンネル ID（通知機能利用時）
- OPENAI_API_KEY         … OpenAI API キー（news_nlp / regime_detector を直接 API 呼び出しする場合）

任意 / デフォルト設定
- KABUSYS_ENV          … development / paper_trading / live（デフォルト: development）
- LOG_LEVEL            … DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH          … DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH          … 監視 DB の SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD … 自動 .env 読み込みを無効化するフラグ（値は任意だが存在すれば無効化）

例: .env（簡易）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- OPENAI_API_KEY=sk-...
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- KABUSYS_ENV=development
- DUCKDB_PATH=data/kabusys.duckdb

使い方（代表的な例）

- DuckDB 接続の作成
  from pathlib import Path
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL の実行
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  # ETLResult オブジェクトを返す。result.to_dict() で内容を確認できます。

- ニュースのセンチメントスコア算出（LLM）
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20))
  # ai_scores テーブルに書き込まれた銘柄数を返す

- 市場レジーム判定
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  # market_regime テーブルに日次判定を冪等書き込み

- 研究用ファクター計算
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  moment = calc_momentum(conn, target_date=date(2026, 3, 20))
  vol = calc_volatility(conn, target_date=date(2026, 3, 20))
  val = calc_value(conn, target_date=date(2026, 3, 20))

- 監査ログ DB 初期化（監査専用 DB を作りたい場合）
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリ自動作成
  # テーブルとインデックスが作成されます

- ニュース RSS 取得（収集前の確認等）
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  # NewsArticle 型のリストを返す（id, datetime, source, title, content, url）

重要な設計方針（運用上の注意）
- ルックアヘッドバイアス防止: モジュール内の関数は datetime.today() や date.today() を内部で参照して結果が変わることを避けています。target_date を明示的に渡して使用してください。
- 冪等性: DB への保存は可能な限り ON CONFLICT / DELETE→INSERT で冪等化されています。ETL は再実行に耐える設計です。
- フェイルセーフ: LLM や外部 API 呼び出しの失敗時は例外を上位へ投げずフォールバックやスキップ（0.0 スコア化等）して処理継続する設計箇所があります（ただし DB 書き込み失敗など致命的な問題は例外伝播します）。
- リトライ/レート制御: J-Quants クライアントはレート制限と再試行を実装しています。OpenAI 呼び出しもリトライ処理を行います。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                … 環境変数 / .env 自動読み込み / settings
  - ai/
    - __init__.py
    - news_nlp.py            … ニュース NLP（OpenAI で銘柄ごとにスコア）
    - regime_detector.py     … 市場レジーム判定（ETF MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py      … J-Quants API クライアント（fetch/save）
    - pipeline.py            … ETL パイプライン（run_daily_etl 等）
    - calendar_management.py … 市場カレンダー管理（営業日判定、更新ジョブ）
    - news_collector.py      … RSS 収集・前処理・SSRF 対策
    - quality.py             … データ品質チェック
    - stats.py               … zscore_normalize 等統計ユーティリティ
    - audit.py               … 監査ログスキーマ初期化
    - etl.py                 … ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py     … モメンタム / ボラティリティ / バリュー 計算
    - feature_exploration.py … forward returns, IC, rank, factor_summary

テスト / 開発
- 関数単位で DuckDB のインメモリ接続（":memory:"）を使ってテストしやすいように設計されています。
- OpenAI / ネットワーク呼び出し部分はユニットテストでモックしやすいように分離実装されています（_call_openai_api の差し替えなど）。

トラブルシュート（よくある問題）
- .env が読み込まれない場合:
  - プロジェクトルートの判定は __file__ を起点に .git または pyproject.toml を探索します。ルートが検出できないと自動ロードはスキップされます。必要なら KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して手動で環境変数をセットしてください。
- OpenAI の JSON 解析エラー:
  - LLM の応答が厳密な JSON でない場合に復元処理を行っていますが、整形に失敗する場合は該当チャンクはスキップされます。ログを確認してプロンプトやモデル設定を見直してください。
- J-Quants API エラー（401 等）:
  - jquants_client は 401 を検出するとリフレッシュを試行します。refresh token が正しいか .env の JQUANTS_REFRESH_TOKEN を確認してください。

ライセンス / 責務
- 本リポジトリに含まれる実装は取引上の利用においてリスクが伴います。実運用・ライブ取引で使う場合は必ずコードレビュー・テスト・適切なリスク管理の上でご利用ください。外部 API 利用に伴う料金や制限は利用者の責任です。

補足
- ここに記載の使用例はライブラリの主要 API を示した最小限の例です。実際の運用ではログ設定、例外処理、認証トークンの安全管理、監査ログ保存、オーケストレーション（cron / Airflow / GitHub Actions 等）などが必要になります。

フィードバック / 追加機能
- README に書かれていない利用ケースや追加したい機能があればお知らせください。ドキュメントに反映します。