# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI）、リサーチ用ファクター計算、監査ログなどを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能を備えた内部ライブラリ群です。

- J-Quants API を使った日次株価・財務・上場情報・カレンダー取得（レート制御・リトライ・トークン自動リフレッシュ）
- DuckDB を利用した ETL パイプライン（差分更新・バックフィル・品質チェック）
- RSS ベースのニュース収集と記事前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント / マクロセンチメント評価（JSON Mode を使用）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）および統計ユーティリティ（Zスコアなど）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）
- マーケットカレンダー管理（JPX カレンダー取得・営業日判定）

設計上の重要点:
- ルックアヘッドバイアスを避けるため、内部処理は `date` / `target_date` 等を明示的に受け取る設計です。
- API 呼び出しは堅牢性を重視（レート制御、指数バックオフ、リトライ、フェイルセーフ）しています。
- DuckDB に対する保存は冪等性を意識した実装（ON CONFLICT）です。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得 + DuckDB 保存関数）
  - pipeline / etl: 日次 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS 取得・前処理・raw_news への保存ロジック
  - calendar_management: 営業日判定／カレンダー更新ジョブ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマ初期化ユーティリティ
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: 銘柄毎のニュースセンチメントを計算して ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA200 とマクロセンチメントを合成して市場レジームを判定
- research/
  - factor_research: momentum / volatility / value の計算
  - feature_exploration: forward returns / IC / 統計サマリー 等
- config: 環境変数読み込み・設定ラッパー（.env 自動ロード機能あり）

---

## 必要環境 / 依存ライブラリ

（プロジェクトによって差異があるため、最終的には pyproject.toml / requirements を参照してください。ここでは本コードで明示的に使用している主要パッケージを列挙します）

- Python 3.9+
- duckdb
- openai (OpenAI の v1 SDK 想定)
- defusedxml
- その他標準ライブラリ（urllib, json, datetime, logging, typing 等）

インストール例（仮）:
pip install duckdb openai defusedxml

プロジェクトパッケージとして利用する場合:
pip install -e .

---

## 環境変数（必須 / 推奨）

config.Settings で参照される主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
- KABU_API_PASSWORD: kabuステーション連携用パスワード（API 呼び出し実装を行う場合）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネルID

OpenAI:
- OPENAI_API_KEY: OpenAI 呼び出しに使用（ai.score_* のデフォルト）

その他（デフォルトあり）:
- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト "development"）
- LOG_LEVEL: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト "INFO"）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）

.env 自動読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml）を探索し、.env → .env.local の順で自動ロードします。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env のパースは shell 風の形式をサポートしています（export プレフィックスやクォート処理など）。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ...

2. Python 環境を用意
   - python -m venv .venv
   - source .venv/bin/activate

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - もしくは必要パッケージを個別にインストール（duckdb, openai, defusedxml 等）

4. 環境変数を準備
   - プロジェクトルートに .env を作成し、上記必須変数を設定
     例（.env）:
       JQUANTS_REFRESH_TOKEN=xxx
       OPENAI_API_KEY=sk-...
       SLACK_BOT_TOKEN=xoxb-...
       SLACK_CHANNEL_ID=C01234567
       KABU_API_PASSWORD=secret
       DUCKDB_PATH=data/kabusys.duckdb

   - テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用して明示的に環境を設定できます。

5. DuckDB データベース / 監査 DB の初期化（必要に応じて）
   - 監査ログ専用 DB を作る例:
     python -c "from kabusys.data.audit import init_audit_db; init_audit_db('data/audit.duckdb')"

   - 必要なテーブルを作成する初期化処理が別途ある場合はそちらを実行してください（本コードは audit.init_audit_db を提供します）。

---

## 使い方（例）

ここではライブラリの主要な操作例を示します。実行はプロジェクトルートで行ってください。

- DuckDB に接続して日次 ETL を実行する:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())
  ```

- ニュースセンチメント（ai.score_news）を実行して ai_scores に書き込む:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n = score_news(conn, target_date=date(2026,3,20))
  print("scored:", n)
  ```

- 市場レジーム判定（ai.score_regime）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- RSS を取得する（news_collector.fetch_rss）:
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  ```

- 監査ログスキーマ初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算:
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026,3,20))
  ```

注意:
- OpenAI を使用する関数は API キーを環境変数 OPENAI_API_KEY から取得します。関数呼び出し時に api_key 引数でオーバーライド可能です。
- run_daily_etl 等は内部で日付を基準に処理を行うため、バックテスト用途での利用時は Look-ahead に注意してください（target_date を明示してください）。

---

## ディレクトリ構成（抜粋）

ソースは `src/kabusys` に配置されています。主要ファイル:

- src/kabusys/
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
    - pipeline.py
    - etl.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/
  - monitoring/ (存在する場合)
  - strategy/ (戦略実装を置く場所)
  - execution/ (注文処理・ブローカー連携用)

（上記はコードベースの主要モジュール抜粋です。プロジェクトの完全な構成はリポジトリ直下を参照してください。）

---

## 運用上の注意 / ベストプラクティス

- 環境設定: 秘密情報は .env ファイルまたは CI/CD シークレットで管理してください。`.env.local` は .env を上書きするため開発用のローカル設定に適しています。
- OpenAI 呼び出しはコストとレート制限があるため、バッチサイズやリトライ設定を運用に合わせて調整してください。
- ETL を cron / Airflow 等で定期実行する際は、run_daily_etl の返す ETLResult を監視して品質エラーや例外をアラートする運用が推奨されます。
- DuckDB のファイルパス（DUCKDB_PATH）や監査 DB の保存場所はバックアップ方針に従って管理してください。
- 本ライブラリの関数は「DuckDB 接続」を直接受け取る設計です。接続管理（接続プール・開始・終了）は呼び出し側で行ってください。

---

## 貢献 / 開発

- コードスタイルやテストはプロジェクトポリシーに従ってください（pytest 等の採用が想定されます）。
- .env.example を用意して主要な環境変数のテンプレートを示すことを推奨します。
- OpenAI 呼び出し部分はテスト時にモック可能なように内部関数を patch して検証できます（コード中にその旨の注記あり）。

---

## ライセンス / 免責

- 本ドキュメントはコード内のコメント・設計意図に基づいて作成されています。実際の商用運用時は、法令・規約の確認（証券会社 API 利用規約、OpenAI 利用規約等）を行ってください。
- 自動売買の利用は自己責任で行ってください。本リポジトリは金融リスクを保証するものではありません。

---

必要であれば README の英語版、セットアップスクリプトの例、.env.example のテンプレート、または各 API の使用例（より詳しいコードサンプル）を追加で作成します。どれを優先しますか？