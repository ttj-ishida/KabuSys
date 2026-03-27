# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。  
データ収集（J-Quants）、ETL、データ品質チェック、ニュースセンチメント解析（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログなどの機能を含みます。

バージョン: 0.1.0

---

## 概要

本プロジェクトは以下の機能群を提供します。

- J-Quants API からの株価・財務・マーケットカレンダーの差分取得と DuckDB への保存（ETL）
- RSS ベースのニュース収集と前処理（SSRF 対策、トラッキング除去、記事ID生成）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント解析（銘柄別・マクロ）
- マーケットレジーム判定（ETF 1321 の MA200 とマクロセンチメントの合成）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量探索ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査（audit）テーブルの初期化および監査ログ操作ユーティリティ
- 設定管理（.env 自動読み込み、環境変数保護）

設計上の重要点:
- ルックアヘッドバイアス対策（内部で datetime.today()/date.today() を直接参照しない等）
- 冪等性（DB 保存は ON CONFLICT による上書き）
- フェイルセーフ（外部 API 失敗時は最低限のフォールバックで継続）
- 依存を最小化（標準ライブラリ中心、DuckDB を採用）

---

## 機能一覧（主要モジュール）

- kabusys.config
  - 環境変数 / .env 自動読み込み、必須変数の検証
- kabusys.data
  - jquants_client: J-Quants API ラッパー（取得・保存・認証・リトライ・レート制御）
  - pipeline / etl: 日次 ETL（prices, financials, calendar）を差分実行
  - news_collector: RSS 収集、トリミング、DB への保存
  - quality: データ品質チェック群（欠損・スパイク・重複・日付不整合）
  - calendar_management: 市場カレンダー管理と営業日ロジック（next/prev/is_trading_day 等）
  - audit: 監査ログ（signal_events, order_requests, executions）テーブルの初期化
  - stats: z-score 正規化等の統計ユーティリティ
- kabusys.ai
  - news_nlp: ニュースを銘柄ごとに集計して OpenAI に渡し ai_scores に保存するロジック
  - regime_detector: ETF 1321 の MA200 とマクロセンチメントを合成して market_regime を作る
- kabusys.research
  - factor_research: momentum/volatility/value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー、ランク関数

---

## 前提（推奨環境）

- Python 3.10+（typing の一部表記に union 型が使用されています）
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI API）

※ requirements.txt は本リポジトリには含まれていないため、プロジェクトに合わせて環境を整備してください。

---

## セットアップ手順

1. リポジトリをクローン／展開する

   git clone <repo-url>
   cd <repo-dir>

2. Python 仮想環境を作成・有効化（推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール（例）

   pip install duckdb openai defusedxml

   ※ 実際には使用する環境・オプションに応じて追加パッケージをインストールしてください。

4. 環境変数を設定する（.env をプロジェクトルートに置くと自動読み込みされます）
   - 自動読み込みはデフォルトで有効。無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   例 (.env):

   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
     （これらはコード上で _require によって必須扱いされるプロパティがあります。用途によっては不要なものもあるため、必要なサービスに応じて設定してください。）
   - OPENAI_API_KEY は ai モジュールを使う場合に必須です（関数引数で渡すことも可能）。

5. データディレクトリを作成（必要に応じて）

   mkdir -p data

---

## 使い方（主要 API の例）

以下はライブラリを直接インポートして使う簡単な例です。DuckDB 接続には duckdb パッケージを使います。

- DuckDB 接続を作成（デフォルトパスは .env の DUCKDB_PATH、指定しない場合は data/kabusys.duckdb）

  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行（市場カレンダー、株価、財務を差分で取得）

  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- ニュースのセンチメントを算出して ai_scores に保存

  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n_written = score_news(conn, target_date=date(2026,3,20))
  print("written:", n_written)

  - OPENAI_API_KEY を環境変数に設定しておくか、api_key 引数で明示的に渡してください。

- 市場レジームをスコアリングして market_regime に保存

  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026,3,20))

- 監査用 DuckDB を初期化（order/signal/execution ログ用）

  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # init_audit_db はトランザクションでスキーマを作成します

- 研究用ファクター計算の例

  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  from datetime import date
  mom = calc_momentum(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))

- 市場カレンダーのユーティリティ

  from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
  from datetime import date
  d = date(2026,3,20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))

注意点:
- OpenAI 呼び出しは外部 API に依存します。API Key の設定や利用料に注意してください。
- J-Quants API 呼び出しではレート制御と自動リフレッシュが組み込まれていますが、認証情報（refresh token）は .env に置かないなどセキュリティに留意してください。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API 用パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須 if Slack 機能を使う）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須 if Slack 機能を使う）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite path for monitoring DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development, paper_trading, live）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動ロードを無効化

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - pipeline.py (ETLResult 再エクスポート)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/__init__.py は研究用ユーティリティをまとめてエクスポート
- その他（strategy, execution, monitoring）はパッケージレベルで公開される想定（実装ファイルはこのツリーにより追加される想定）

各ファイルの役割（簡易）:
- config.py: .env 自動ロード／環境変数取得のラッパー（Settings クラス）
- jquants_client.py: J-Quants API の取得・保存ロジック（レート制御・リトライ・認証）
- pipeline.py / etl.py: ETL の Orchestrator（run_daily_etl など）
- news_collector.py: RSS 取得 → raw_news への保存（SSRF 対策や前処理含む）
- news_nlp.py: OpenAI で銘柄ごとのニュースセンチメントを算出して ai_scores に保存
- regime_detector.py: ETF の MA200 とマクロセンチメントを合成して市場レジームを保存
- quality.py: raw_prices 等のデータ品質チェック
- audit.py: 監査用テーブル定義と初期化ユーティリティ
- research/*: 研究用ファクター計算と統計解析ユーティリティ

---

## 開発・運用上の注意

- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、パラメータが空でないことを確認してから呼び出しています。ETL 実行時にも注意してください。
- OpenAI のレスポンスは JSON mode を利用していますが、時折前後に余計なテキストが混ざるためパース時に耐性を持たせています。
- RSS の取得では SSRF/内部アドレスアクセスや大容量レスポンス（Gzip bomb 等）を防ぐために複数の防御ロジックを入れています。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行います。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## よくある利用フロー（例）

1. .env を用意して認証情報を設定する
2. DuckDB（data/kabusys.duckdb）を用意して接続する
3. run_daily_etl() を定期実行してデータを蓄積（Cron / Airflow 等）
4. news_collector を定期実行して raw_news を蓄積
5. score_news を ETL 後に実行して ai_scores を更新
6. score_regime を実行して market_regime を更新
7. 研究・バックテスト用に kabusys.research の関数を利用

---

もし README に追加したいサンプルスクリプト、CI 設定、requirements.txt、あるいは具体的なデプロイ手順（Dockerfile / systemd / Airflow ジョブなど）があれば、提供された情報に基づいて追記できます。必要な箇所を教えてください。