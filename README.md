# KabuSys

日本株向けの自動売買 / データプラットフォームコンポーネント群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を用いたセンチメント）、市場レジーム判定、リサーチ向けファクター計算、監査ログ（発注トレーサビリティ）などを含みます。

バージョン: 0.1.0

## 概要

KabuSys は、以下の用途に対応する Python モジュール群から構成されています。

- データ取得・ETL（J-Quants API 経由で株価・財務・カレンダーを取得し DuckDB に保存）
- ニュース収集・前処理（RSS）と LLM を用いたニュースセンチメント評価
- 市場レジーム判定（ETF とマクロニュースを組み合わせた日次判定）
- 研究（ファクター計算 / 将来リターン / IC 等の統計解析）
- 監査ログ（signal → order_request → execution のトレーサビリティスキーマ）
- 設定管理（.env / 環境変数の自動ロード、settings オブジェクト）

設計方針の例:
- ルックアヘッドバイアスに配慮（関数は内部で date.today() を直接参照しない等）
- DuckDB を永続ストレージとして利用、ETL は冪等的（ON CONFLICT）に保存
- 外部 API 呼び出しはリトライ / バックオフ等で堅牢化

## 主な機能一覧

- data/etl:
  - run_daily_etl: 市場カレンダー、株価、財務の差分 ETL と品質チェックを一括実行
  - run_prices_etl / run_financials_etl / run_calendar_etl: 個別 ETL ジョブ
  - jquants_client: J-Quants API 呼び出し（認証、ページネーション、保存関数）
  - news_collector: RSS 取得・前処理・DB 保存（SSRF 対策・トラッキング除去）
  - audit: 監査ログ用テーブル定義・初期化ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: 営業日判定ユーティリティ・夜間カレンダー更新ジョブ
  - stats: zscore_normalize 等の統計ユーティリティ

- ai:
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価して `ai_scores` に保存
  - regime_detector.score_regime: ETF の MA とマクロニュースセンチメントを合成して `market_regime` に保存

- research:
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

- config:
  - Settings: 環境変数から設定を取得する `settings` インスタンス（自動 .env ロードあり）

## セットアップ手順

前提:
- Python 3.10+（型アノテーションに | を使用）
- DuckDB を利用（pip パッケージ duckdb）
- OpenAI SDK（openai）を利用する機能あり
- defusedxml（RSS パース）
- （必要に応じて）requests 等の追加依存

1. 仮想環境を作成・有効化（例）

   - Unix/macOS:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```

   - Windows:
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 必要パッケージをインストール（代表例）

   ```bash
   pip install duckdb openai defusedxml
   ```

   ※ requirements.txt がある場合は `pip install -r requirements.txt` を使ってください。

3. 環境変数（.env）を用意する  
   プロジェクトルートに `.env` / `.env.local` を置くことで自動ロードされます（モジュール読み込み時に自動で読みます）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須（代表的なもの）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で利用）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（発注関連で使用）
   - SLACK_BOT_TOKEN: Slack 通知で使用する Bot トークン
   - SLACK_CHANNEL_ID: Slack 通知先チャネル ID

   任意:
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL（DEBUG/INFO/...）

4. データディレクトリ作成（例）

   ```bash
   mkdir -p data
   ```

## 使い方（代表的な例）

以下はライブラリ関数を直接呼ぶ簡単な例です。実運用ではスクリプト / ジョブ管理（cron / systemd / Airflow 等）から呼び出してください。

- DuckDB 接続を作成して ETL を実行

  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコア算出（OpenAI API キーが環境変数にある前提）

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
  print(f"書き込み件数: {written}")
  ```

- 市場レジーム判定（ETF 1321 の MA とマクロセンチメントを合成）

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))  # 環境変数 OPENAI_API_KEY を使用
  ```

- 監査ログ DB 初期化

  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn を使って監査テーブルへ書き込み可能
  ```

- 設定 (settings) の利用

  ```python
  from kabusys.config import settings

  print(settings.duckdb_path)         # Path オブジェクト
  print(settings.is_live)             # True/False
  token = settings.jquants_refresh_token  # 必須項目（未設定時は ValueError）
  ```

注意:
- OpenAI 呼び出しはネットワーク・API レート制限に依存するため、API キーや課金設定に注意してください。
- ETL / ニュース収集の実行は、DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, raw_news 等）が事前に初期化されていることを前提とする部分があります。スキーマ初期化用のスクリプトを用意しておくことを推奨します（本リポジトリの別スクリプトに実装されている想定）。

## ディレクトリ構成

主要ファイル・モジュールを抜粋した構成:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / settings 管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースセンチメント（OpenAI）
    - regime_detector.py          — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント（取得・保存）
    - pipeline.py                 — ETL パイプライン / run_daily_etl
    - etl.py                      — ETL の公開インターフェース（ETLResult）
    - news_collector.py           — RSS 収集・前処理
    - calendar_management.py      — 市場カレンダー管理 / 営業日判定
    - quality.py                  — データ品質チェック
    - stats.py                    — 統計ユーティリティ（zscore_normalize）
    - audit.py                    — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py          — Momentum / Value / Volatility 等
    - feature_exploration.py      — 将来リターン / IC / summary
  - research/*.py
  - その他（execution, monitoring, strategy などを含む想定）

この README は主要なモジュールと使い方の導入をまとめたものです。各モジュールの詳細な使い方（関数の引数や戻り値、期待される DB スキーマなど）はソースコード内の docstring を参照してください。

必要であれば、以下の追加情報を作成できます:
- 初期スキーマ作成スクリプト（DuckDB テーブル定義）
- .env.example（推奨環境変数のテンプレート）
- 運用 / デプロイ手順（systemd / cron / コンテナ化の例）
- テストの実行方法（モックや CI の設定例）