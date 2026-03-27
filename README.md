# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J‑Quants）→ データ品質チェック → 特徴量計算 → ニュースセンチメント（LLM） → 市場レジーム判定 → 監査ログ といった一連の処理を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータ取得、品質管理、リサーチ、AI ベースのニュース解析、レジーム判定、監査ログを含むモジュール群を提供するパッケージです。  
主に以下を目的としています。

- J‑Quants API からの差分 ETL（株価、財務、カレンダー）
- ニュース収集と LLM を使った銘柄ごとのセンチメント算出
- 市場レジーム判定（ETF とマクロニュースを組み合わせた手法）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ初期化ユーティリティ

---

## 主な機能一覧

- data
  - J‑Quants クライアント（取得・保存・認証・レート制御・リトライ）
  - ETL パイプライン（run_daily_etl 等）
  - 市場カレンダー管理（営業日判定、next/prev/trading days）
  - ニュース収集（RSS、SSRF 対策、前処理）
  - データ品質チェック（QualityIssue 集約）
  - 監査ログスキーマ初期化（DuckDB）
  - 汎用統計ユーティリティ（Z スコア正規化等）
- ai
  - ニュース NLP スコアリング（gpt-4o-mini を想定、JSON mode）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメント合成）
- research
  - ファクター計算（momentum, value, volatility）
  - 特徴量探索（forward returns, IC, summary, rank）
- config
  - .env / 環境変数の自動読み込み（.env, .env.local）
  - settings オブジェクト経由で各種設定参照

---

## セットアップ手順

前提:
- Python 3.10 以上（注: 型注釈で `|` 演算子を使用）
- Git

1. リポジトリをクローン
   - git clone <リポジトリ URL>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （開発向け）pip install -e .

   ※実プロジェクトでは requirements.txt / pyproject.toml を用意して依存を固定することを推奨します。

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml のある場所）に `.env` として下記の環境変数を設定します。  
     自動ロードはデフォルトで有効（.env → .env.local の順に読み込み）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   例 (.env):
   ```
   # J‑Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabuステーション API
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意

   # OpenAI
   OPENAI_API_KEY=sk-...

   # Slack (通知等)
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789

   # DB パス
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境
   KABUSYS_ENV=development  # development|paper_trading|live
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ等の初期化  
   - 監査ログ用 DB を初期化する例:
     - python -c "import duckdb, kabusys; from kabusys.data.audit import init_audit_db; init_audit_db('data/audit.duckdb')"

---

## 使い方（例）

以下は代表的なユースケースの一例です。各関数はモジュール内ドキュメントに詳細を記載しています。

- ETL（日次パイプライン）を実行する
  - Python 例:
    ```python
    import duckdb
    from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())
    ```

- ニュースセンチメント（銘柄別）を算出して ai_scores に保存
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  num_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
  print("written:", num_written)
  ```

- 市場レジーム判定を行う
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を使ってアプリケーション内の監査テーブルを利用できます
  ```

- 研究用ファクター計算
  ```python
  from kabusys.research import calc_momentum, calc_value, calc_volatility
  import duckdb
  from datetime import date
  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))
  ```

注意:
- OpenAI API 呼び出しを行う関数（news_nlp, regime_detector）は API キーを引数に渡すことが可能です。引数に None を渡すと環境変数 OPENAI_API_KEY を参照します。
- LLM の失敗時はフェイルセーフ（スコア 0.0 等）や部分スキップの挙動を取るよう設計されていますが、レート制限・コストに留意してください。

---

## 設定・環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知に使用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development|paper_trading|live)
- LOG_LEVEL: ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化します

---

## ディレクトリ構成

以下は主要なファイル・モジュールの概要です（パッケージルート: src/kabusys）。

- __init__.py
  - パッケージメタ情報（__version__）と主要サブパッケージのエクスポート

- config.py
  - .env / 環境変数読み込みロジック、Settings オブジェクト（settings）

- ai/
  - __init__.py
  - news_nlp.py
    - raw_news を集約して LLM に投げ、ai_scores テーブルへ書き込む
  - regime_detector.py
    - ETF 1321 の MA200 乖離 + マクロニュース（LLM）を合成して market_regime を算出

- data/
  - __init__.py
  - jquants_client.py
    - J‑Quants API 呼出し・認証・保存（raw_prices / raw_financials / market_calendar）
  - pipeline.py
    - ETL 実行ロジック（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
    - ETLResult 型
  - calendar_management.py
    - market_calendar 関連ユーティリティ（is_trading_day, next_trading_day, get_trading_days, calendar_update_job）
  - news_collector.py
    - RSS 取得・前処理・raw_news への保存ロジック（SSRF 対策、URL 正規化）
  - quality.py
    - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats.py
    - zscore_normalize 等の統計ユーティリティ
  - audit.py
    - 監査ログ（signal_events, order_requests, executions）DDL / 初期化ユーティリティ
  - etl.py
    - ETL の公開インターフェース（ETLResult の再エクスポート）

- research/
  - __init__.py
  - factor_research.py
    - calc_momentum, calc_value, calc_volatility
  - feature_exploration.py
    - calc_forward_returns, calc_ic, factor_summary, rank

---

## 運用上の注意・設計上のポイント

- Look‑ahead bias 対策
  - 多くの関数は target_date を明示的に受け取り、内部で date.today() を勝手に参照しないように設計されています。バックテスト用途では過去データのみを使うよう注意してください。
- 冪等性
  - J‑Quants から取得したデータ保存は ON CONFLICT DO UPDATE を使用して冪等性を確保しています。
- リトライ・レート制御
  - J‑Quants クライアントは固定間隔スロットリング（120 req/min）と指数バックオフを実装しています。
  - OpenAI 呼び出しもリトライとフェイルセーフ（スコア 0.0 等）を持ちます。
- セキュリティ対策
  - NewsCollector は SSRF 防止、XML の defusedxml 使用、受信サイズ制限などの防御策を含みます。

---

## 貢献・拡張のヒント

- 実運用での監視・通知（Slack 統合や監査ログの可視化）
- モデル・LLM の切替やプロンプト改善（news_nlp / regime_detector）
- ETL の並列化・スケジューリング（Airflow 等との統合）
- テスト: OpenAI 呼び出し等はモックしやすい設計になっているためユニットテストを追加しやすいです（モジュール内部の _call_openai_api をパッチ可能）。

---

必要であれば README に「インストール済み依存の固定方法」「実用的な .env.example ファイル」「使い方のワークフロー（cron / Airflow 例）」「よくあるトラブルシュート」を追加します。どれを追加しましょうか？