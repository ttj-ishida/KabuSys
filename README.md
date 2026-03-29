# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ（KabuSys）。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP スコアリング、ファクター計算、監査ログ（オーディット）、市場レジーム判定などの機能を備えた内部ライブラリ群です。

---

## 概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API を用いた日次データの差分取得・保存（DuckDB）
- ニュース収集（RSS）と LLM によるセンチメント評価（OpenAI）
- ファクター / リサーチ用ユーティリティ（モメンタム、バリュー、ボラティリティ、将来リターン、IC 等）
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- 監査ログ（signal → order_request → executions のトレーサビリティ）
- 市場レジーム判定（ETF MA と LLM マクロセンチメントの合成）

設計上の重要点:
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を直接参照しない設計や、クエリの排他条件等）
- DuckDB を主要なローカル DB として使用
- 冪等性（ETL 保存は ON CONFLICT DO UPDATE など）
- API 呼び出しはリトライ/バックオフ/レート制限を実装
- OpenAI 呼び出しは JSON mode を期待し、パースの堅牢化を行う

---

## 主な機能一覧

- data:
  - J-Quants クライアント（fetch / save）：prices, financials, market calendar, listed info
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - ニュース収集（RSS）と記事前処理（news_collector）
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - 品質チェック（missing_data, spike, duplicates, date_consistency）
  - 監査ログ初期化（init_audit_schema, init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai:
  - ニュース NLP スコアリング（score_news）
  - 市場レジーム判定（score_regime; ETF 1321 の MA200 とマクロセンチメントの合成）
- research:
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索 / IC / forward returns / 統計サマリー
- config:
  - 環境変数読み込み（.env / .env.local 自動ロード）、必須環境変数取得ユーティリティ（settings）

---

## セットアップ手順

前提:
- Python 3.10+（typing | union 型表記などを利用）
- ネットワーク接続（J-Quants / OpenAI / RSS）

1. リポジトリをクローン／配置（src 配下のパッケージ構成を想定）
2. 必要パッケージをインストール（例）:

   pip install duckdb openai defusedxml

   ※ 実際のプロジェクトでは requirements.txt / pyproject.toml を用意して管理してください。

3. 環境変数を設定
   - プロジェクトルートに `.env`（および `.env.local`）を置くと、kabusys.config モジュールが自動で読み込みます（CWD ではなくパッケージファイル位置からプロジェクトルートを探索: .git または pyproject.toml を基準）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 必須の環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必要時）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必要時）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必要時）
   - OPENAI_API_KEY: OpenAI API キー（ai.score_news / score_regime で使用）
   - DUCKDB_PATH / SQLITE_PATH（任意、デフォルトは data/kabusys.duckdb / data/monitoring.db）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（簡易ガイド）

以下は主要ユーティリティの利用例です。実行は Python スクリプト / REPL で行います。

- DuckDB 接続を作成して ETL を実行する:

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str("data/kabusys.duckdb"))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースの NLP スコアを生成して ai_scores テーブルへ書き込む:

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数または引数で指定
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"wrote {written} scores")

- 市場レジームスコアを計算して market_regime テーブルへ保存する:

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査ログ DB を初期化する:

  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn は初期化済みの DuckDB 接続

- 設定値の取得（コード内で）:

  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.env)

注意点:
- OpenAI を呼ぶ関数は api_key 引数で上書き可能（テスト時に差し替えや DI がしやすい）。
- ETL / AI 関数は内部で日付のルックアヘッドを避けるように設計されています（target_date を明示することを推奨）。
- J-Quants の API 呼び出しはレート制御・リトライ・トークン自動リフレッシュを備えています。

---

## ディレクトリ構成（主要ファイル）

リポジトリは src パッケージ構成を想定しています。主要モジュール:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定読み込み
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP スコアリング（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult の再エクスポート
    - news_collector.py      — RSS 収集・前処理
    - calendar_management.py — マーケットカレンダー管理
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py     — calc_momentum, calc_value, calc_volatility
    - feature_exploration.py — calc_forward_returns, calc_ic, factor_summary, rank
  - ai/（既出）など

各モジュールには docstring に詳細な設計・処理フローが記載されています。実運用ではこれらの関数を組み合わせてバッチジョブやワーカーを作成してください。

---

## 実運用上の注意 / ベストプラクティス

- 環境ごと（development / paper_trading / live）に KABUSYS_ENV を設定し、settings.is_live / is_paper / is_dev を使って挙動を分岐させる。
- 機密情報（API キー）は OS 環境変数か安全なシークレットストアで管理する。`.env` は開発用に使うが公開リポジトリには含めない。
- ETL / AI 呼び出しはリトライやログを踏まえて監視する（Slack 経由で通知する仕組みを組み込むと便利）。
- OpenAI 呼び出しはコストが発生するのでバッチ化・バッチサイズ調整を行う（news_nlp はバッチ処理を実装済み）。
- 単体テスト・統合テストでは環境変数の自動ロードを無効化するために `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使うとテストの副作用を避けられる。

---

必要であれば README にサンプル .env.example、CI ワークフロー、より詳細な実行例（cron / systemd / Airflow 等での運用方法）を追記できます。どの部分をより詳しく書きたいか教えてください。