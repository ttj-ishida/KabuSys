# KabuSys

日本株向けのデータプラットフォーム & 自動売買基盤ライブラリ（モジュール群）。  
ETL（J-Quants 連携による市場データ収集）、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注/約定トレーサビリティ）などを提供します。

---

## 概要

KabuSys は日本株の自動売買システムやリサーチ環境向けに設計された Python モジュール群です。主な目的は以下です。

- J-Quants API から市場データ（株価日足・財務・カレンダー）を安全に取得して DuckDB に保存する ETL。
- RSS ニュースの収集と、OpenAI を用いた銘柄別ニュースセンチメントのスコアリング。
- ETF の移動平均乖離とマクロニュースから市場レジーム（bull / neutral / bear）を判定。
- ファクター計算（モメンタム・ボラティリティ・バリュー）や特徴量探索（将来リターン・IC・統計サマリー）。
- データ品質チェック（欠損・スパイク・重複・日付不整合）。
- 監査ログ（signal → order_request → executions のトレーサビリティ）用テーブル／初期化ユーティリティ。

設計上の共通方針として、バックテストでのルックアヘッドバイアスを避けるために日時の参照に注意し、API 呼び出しはリトライやレート制御を備えています。

---

## 機能一覧

- data
  - J-Quants クライアント（fetch / save 機能、トークン自動リフレッシュ、レート制御、リトライ）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 市場カレンダー管理（営業日判定、next/prev trading day、calendar_update_job）
  - ニュース収集（RSS → raw_news）
  - 監査ログ（監査用テーブル定義と初期化 init_audit_schema / init_audit_db）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news: 銘柄ごとにニュースセンチメントを ai_scores に保存）
  - 市場レジーム判定（score_regime: ETF 1321 の MA 乖離とマクロセンチメントから判定）
- research
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数読み込み・管理（.env/.env.local の自動ロード、Settings クラス）
- audit / execution / strategy / monitoring
  - 監査・発注・戦略・監視のための命名空間（主要ユーティリティは data / ai / research に含まれる）

---

## セットアップ手順

前提: Python 3.10+（コードでは型ヒントに Union 演算子や型注釈を使用しています）を想定します。

1. リポジトリをクローンしてインストール（開発モード例）

   ```bash
   git clone <repo-url>
   cd <repo-root>
   pip install -e .
   ```

2. 必要な依存パッケージ（代表例）
   - duckdb
   - openai
   - defusedxml

   上記は setup.cfg / pyproject.toml にまとめられている想定です。手動でインストールする場合:

   ```bash
   pip install duckdb openai defusedxml
   ```

3. 環境変数の設定
   - プロジェクトルートの `.env` / `.env.local` を作成すると自動的に読み込まれます（config.py による自動ロード）。
   - 自動ロードを無効化するには環境変数を設定:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   代表的な環境変数（例）:

   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # OpenAI
   OPENAI_API_KEY=sk-...

   # kabuステーション API（発注等で使用）
   KABU_API_PASSWORD=...
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack（通知用）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # データベースパス
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境
   KABUSYS_ENV=development  # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

   Settings（kabusys.config.settings）でアクセス可能です。

4. データベースの準備
   - DuckDB を使用するため、指定したパスにファイルが作成されます。
   - 監査DB専用に初期化する場合:

     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（例）

以下は主要なユースケースの簡単な Python サンプルです。実運用ではログ設定やエラーハンドリングを追加してください。

1. 日次 ETL を実行（J-Quants からデータ取得）

   ```python
   import duckdb
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

2. ニュースセンチメントを計算して ai_scores に保存

   - OpenAI API キーは環境変数 OPENAI_API_KEY で渡すか、関数引数に指定できます。

   ```python
   import duckdb
   from datetime import date
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect("data/kabusys.duckdb")
   written = score_news(conn, target_date=date(2026, 3, 20))
   print(f"書き込み銘柄数: {written}")
   ```

3. 市場レジームを判定して market_regime に保存

   ```python
   import duckdb
   from datetime import date
   from kabusys.ai.regime_detector import score_regime

   conn = duckdb.connect("data/kabusys.duckdb")
   score_regime(conn, target_date=date(2026, 3, 20))
   ```

4. ファクター計算 / 研究用ユーティリティ

   ```python
   from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
   conn = duckdb.connect("data/kabusys.duckdb")
   recs = calc_momentum(conn, target_date=date(2026, 3, 20))
   # 正規化
   from kabusys.data.stats import zscore_normalize
   normalized = zscore_normalize(recs, ["mom_1m", "mom_3m", "mom_6m"])
   ```

5. 監査スキーマの初期化（既存 DB に監査テーブルを追加）

   ```python
   from kabusys.data.audit import init_audit_schema
   conn = duckdb.connect("data/kabusys.duckdb")
   init_audit_schema(conn, transactional=True)
   ```

注意点:
- OpenAI 呼び出しを行う関数（score_news, score_regime）は API リトライやフェイルセーフを備えていますが、API キーの設定は必須です（引数で上書き可能）。
- ETL や API 呼び出しはネットワークや外部サービスに依存します。運用ではリトライや監視を組み合わせてください。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN：J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY：OpenAI API キー（score_news / score_regime）
- KABU_API_PASSWORD：kabu API パスワード（発注関連）
- KABU_API_BASE_URL：kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID：通知用
- DUCKDB_PATH：DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH：SQLite（監視等）ファイルパス（デフォルト data/monitoring.db）
- KABUSYS_ENV：development | paper_trading | live
- LOG_LEVEL：DEBUG | INFO | WARNING | ERROR | CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD：1 にすると .env の自動読み込みを無効化

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主なファイル・モジュールです（抜粋）。

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
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py
    - etl.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*（factor / feature utilities）
  - (その他) strategy, execution, monitoring 名前空間（パッケージ公開用）

---

## 運用上の注意

- Look-ahead バイアス防止: 多くの関数は date 引数に依存し、内部で date.today() を安易に参照しないよう設計されています。バックテスト時は必ず使用日を明示してください。
- OpenAI や J-Quants への呼び出しはコスト・レート制限があるため、バッチ化・レート制御を意識してください（ライブラリ内で制御あり）。
- ニュース収集では SSRF 対策や XML パースの安全化（defusedxml）を行っていますが、外部入力の扱いには注意してください。
- 本リポジトリ内に「実際の発注ロジック（kabuステーションとのやり取りなど）」が含まれる場合、live 環境でのテストは注意して行ってください。KABUSYS_ENV により paper_trading / live を区別し、実運用前にリスク対策を必ず行ってください。

---

## 参考・拡張

- 新しい ETL ジョブやデータソースを追加する場合は data.jquants_client の設計（レート制御・リトライ・リフレッシュ）を踏襲してください。
- AI 関連は OpenAI のレスポンス形式に依存するため、モデルやプロンプトを変更する際はレスポンスバリデーション部分（news_nlp._validate_and_extract 等）を更新してください。

---

必要であれば、README にインストール手順（pyproject / setup.cfg に基づく）や CI・デプロイ方法、具体的な運用手順（cron / Airflow などでの ETL スケジューリング例）を追記できます。どの情報を優先して追加しましょうか？