# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（読み取り専用のリサーチ・データパイプライン・AIスコアリング・監査ログ等を含む）。  
このリポジトリはデータ取得（J-Quants）、ニュース収集とNLU（OpenAI）、ファクター計算、ETLパイプライン、監査テーブル初期化などを提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買基盤のうち、データ取り込み・品質管理・研究（ファクター）・AI ベースのニュースセンチメント評価・市場レジーム判定・監査ログ（トレーサビリティ）などを担う共通ライブラリです。  
主に次の用途を想定しています。

- J-Quants API からの差分 ETL（株価・財務・カレンダー）
- RSS からのニュース収集と銘柄紐付け
- OpenAI を用いたニュースのセンチメント評価（銘柄別 / マクロ）
- 日次 ETL や品質チェックの自動化ジョブ
- 監査ログ（signal → order → execution）テーブルの初期化と操作ユーティリティ
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ）と統計ユーティリティ

---

## 主な機能一覧

- 環境変数・設定管理（kabusys.config.Settings）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数取得ヘルパ
  - KABUSYS_ENV（development / paper_trading / live）, LOG_LEVEL 指定

- データ取得（kabusys.data.jquants_client）
  - J-Quants からの株価、財務、マーケットカレンダー取得（ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - レート制御・リトライ・トークン自動刷新対応

- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - 品質チェック（kabusys.data.quality）と結果を ETLResult で集約

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、SSRF 対策、トラッキングパラメータ除去、前処理
  - raw_news / news_symbols への冪等保存

- ニュース NLP（kabusys.ai.news_nlp）
  - 銘柄ごとのニュースをまとめて OpenAI に投げ、ai_scores に保存
  - バッチ処理・リトライ・レスポンス検証あり

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）の 200 日 MA 乖離とマクロニュースセンチメントを合成して (bull / neutral / bear) 判定
  - LLM 呼び出し・バックオフ処理・DB への冪等書き込み

- 研究ツール（kabusys.research）
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / zscore_normalize など

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - init_audit_schema / init_audit_db（DuckDB 用）

---

## セットアップ手順

1. Python 環境の作成（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（代表的なもの）
   - pip install duckdb openai defusedxml

   （実プロジェクトでは requirements.txt / pyproject.toml を参照してください。上記は主要依存の例です。）

3. パッケージをインストール（開発モード）
   - pip install -e .

4. 環境変数を設定
   必須（各モジュールで _require を使っているもの）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabu ステーション API のパスワード（実行環境で使用する場合）
   - SLACK_BOT_TOKEN: Slack 通知を使う場合
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

   任意:
   - OPENAI_API_KEY: OpenAI 呼び出しを行う場合（関数呼び出し時に api_key 引数で上書き可能）
   - DUCKDB_PATH: デフォルト DuckDB ファイルパス（data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

   .env / .env.local ファイルについて:
   - package の起点 (__file__ の親) から .git または pyproject.toml を探索してプロジェクトルートを判定し、
     自動的に .env → .env.local を読み込みます。
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. データディレクトリ作成
   - デフォルトの DuckDB 等の親ディレクトリを作成（例: mkdir -p data）

---

## 使い方（主要例）

以下は最小の実行例です。必要な環境変数（特に OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN）がセットされている前提です。

- DuckDB 接続の生成（デフォルトパスを利用）
  ```
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行（市場カレンダー・株価・財務を取得し品質チェック）
  ```
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのスコアリング（ai_scores テーブルへ書き込む）
  ```
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written scores: {written}")
  ```

- 市場レジーム判定（market_regime テーブルへ書き込む）
  ```
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（専用ファイル）
  ```
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- カレンダー・営業日ユーティリティ
  ```
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

- 設定の参照
  ```
  from kabusys.config import settings
  print(settings.env, settings.log_level)
  print(settings.jquants_refresh_token)  # 未設定なら例外
  ```

注意点:
- OpenAI 呼び出しは api_key を引数で渡すこともできます（テスト時の差し替えや複数キー運用に便利）。
- DuckDB に対する書き込みは関数内で BEGIN/COMMIT/ROLLBACK を適切に使用していますが、必要に応じて上位でトランザクション管理してください。
- LLM 呼び出し・外部 API 呼び出しに失敗した場合、多くの処理はフェイルセーフ（スコア 0 やスキップ）で継続する設計です。

---

## ディレクトリ構成（主要ファイル）

（root: pyproject.toml/.git があると自動的にプロジェクトルートと判断されます）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数／設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（銘柄別）
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult の再エクスポート
    - news_collector.py      — RSS 収集＆前処理
    - calendar_management.py — マーケットカレンダー・営業日判定
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize 等）
    - audit.py               — 監査ログ（スキーマ定義・初期化）
  - research/
    - __init__.py
    - factor_research.py     — モメンタム/バリュー/ボラティリティ
    - feature_exploration.py — 将来リターン・IC・統計サマリー

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN — 必須: J-Quants リフレッシュトークン
- OPENAI_API_KEY — OpenAI を利用する機能で使用（関数引数で上書き可能）
- KABUS_API_PASSWORD — kabu API パスワード
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — Slack 通知に使用
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — ログレベル（INFO 等）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットすると .env 自動読込を抑止

---

## ログとエラー処理

- 多くの操作は内部で try/except を持ち、致命的でない失敗はログ（warning/error）を出して継続する設計です（外部 API や LLM の不安定性に対処するため）。
- 実稼働では LOG_LEVEL を調整し、監視・アラート（Slack 等）を併用することを推奨します。

---

## 開発・テストに関するメモ

- LLM や外部 API 呼び出しはモジュール毎にラッパー関数を通しており、ユニットテスト時はそれらをモック（patch）して挙動を制御できます（例: kabusys.ai.news_nlp._call_openai_api を差し替え）。
- DuckDB の挙動を利用しているため、テストでは in-memory DB (":memory:") を利用することでファイル I/O を避けて高速にテストできます。
- .env 自動読み込みはプロジェクトルート検出に依存するため、テスト環境で意図せず読み込まれる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

もし README に載せてほしい追加の使い方（具体的な ETL スケジュール例、cron / Airflow 用の実行例、Slack 通知の統合方法など）があれば教えてください。README をその要望に合わせて拡張します。