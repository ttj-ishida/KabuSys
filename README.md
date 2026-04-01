# KabuSys

日本株自動売買システム（ライブラリ）  
本リポジトリは、データ収集（J-Quants）、ETL、データ品質チェック、特徴量/リサーチ、ニュースNLP（OpenAI）、市場レジーム判定、監査ログ等を一通り備えた日本株向けのデータ・リサーチ・監視モジュール群を提供します。

---

## 概要

KabuSys はバックテスト／リサーチ／実運用のための基盤ライブラリです。主な責務は以下の通りです。

- J-Quants API からのデータ取得（株価日足・財務・マーケットカレンダー）と DuckDB への保存（ETL）
- 原始ニュースの収集と前処理、ニュースを銘柄ごとにまとめて LLM（OpenAI）でセンチメント評価
- 市場レジーム判定（ETF の MA200 乖離 + マクロニュースの LLM センチメント）
- ファクター算出（モメンタム / バリュー / ボラティリティ）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions のトレーサビリティ）用スキーマ初期化ユーティリティ
- 環境変数 / .env ファイルの読み込みユーティリティ（自動ロード機能あり）

設計方針としては、Look-ahead bias の排除、DuckDB を用いた効率的な SQL 処理、API 呼び出しのリトライ/レート制御、LLM 呼び出しのフォールバックを重視しています。

---

## 主な機能一覧

- データ取得 / ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）: fetch_* / save_* 関数
- データ品質チェック（kabusys.data.quality）
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- ニュース収集・前処理（kabusys.data.news_collector）
  - RSS フィード取得・正規化・SSRF 対策・raw_news 保存前処理
- ニュース NLP（kabusys.ai.news_nlp）
  - score_news: 銘柄ごとに LLM でセンチメントを算出して ai_scores に保存
- 市場レジーム判定（kabusys.ai.regime_detector）
  - score_regime: ETF(1321) の MA200 とマクロニュース LLM を合成して market_regime に保存
- 研究用ファクター計算（kabusys.research）
  - calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank
- 監査ログ / トレーサビリティ（kabusys.data.audit）
  - init_audit_schema / init_audit_db
- 環境設定（kabusys.config）
  - .env / .env.local の自動ロード（プロジェクトルート検出）と settings オブジェクト

---

## セットアップ手順

前提:
- Python 3.10 以上を推奨（型ヒントや union 型表記に基づく）
- DuckDB, OpenAI SDK, defusedxml 等が必要

1. リポジトリをクローン
   ```bash
   git clone <このリポジトリURL>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # POSIX
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   注: プロジェクトに requirements.txt が無い場合、下記を参考に最低限の依存を入れてください。
   ```bash
   pip install duckdb openai defusedxml
   ```
   実運用では logging / requests 等の補助ライブラリを追加してください。

4. ローカルパッケージ（開発モード）としてインストール（任意）
   ```bash
   pip install -e .
   ```
   （pip install -e . は setup/pyproject が用意されている場合に有効です。ない場合は上の直接インストールだけで利用可能です）

5. 環境変数設定
   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD をセットすると自動ロードを無効化できます）。

   代表的な環境変数（README 用の例）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（サンプル）

以下はライブラリの代表的な使い方例です。実行時は environment variables を適切に設定してください。

- 設定参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  ```

- DuckDB 接続を作成し日次 ETL を実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str("<任意の.duckdbファイルパス>"))  # または str(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント算出（target_date は評価対象日）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str("<db_path>"))
  # OPENAI_API_KEY は環境変数か api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026,3,20))
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str("<db_path>"))
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログ用 DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # schema が作成された DuckDB 接続が返る
  ```

- 監査スキーマだけ既存接続に適用
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

注意:
- LLM（OpenAI）呼び出しは料金・レート制限があるため、API キーの管理と呼び出し回数の制御に注意してください。
- J-Quants API 呼び出しにはリフレッシュトークン（JQUANTS_REFRESH_TOKEN）が必要です。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（LLM を利用する機能で必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: デフォルトの DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視関連
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を探し、.env → .env.local の順で読み込みます。
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で有用）。

---

## ディレクトリ構成

以下は src/kabusys 以下の主要ファイルとモジュールの一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / .env の管理（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP（score_news）
    - regime_detector.py         — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（fetch_*/save_*）
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - etl.py                     — ETLResult 再エクスポート
    - news_collector.py          — RSS ニュース収集・前処理
    - calendar_management.py     — 市場カレンダー管理（is_trading_day など）
    - quality.py                 — データ品質チェック
    - stats.py                   — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                   — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py         — Momentum / Value / Volatility 等の算出
    - feature_exploration.py     — 将来リターン / IC / 統計サマリー 等
  - ai, research 等の他モジュール

---

## 開発・運用上の注意点

- Look-ahead bias の防止:
  - 各関数は内部で date.today() の直接参照を避け、呼び出し側から target_date を渡す設計です。バックテストや再現性のため、常に明示的に日付を渡すことを推奨します。
- API リトライ・レート制御:
  - J-Quants クライアントは rate limiter とリトライ実装を内蔵しています。OpenAI 呼び出しも retry/backoff を含みます（実装上の制約に注意）。
- テスト:
  - 環境変数自動ロードが邪魔な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
  - LLM/API 呼び出し部分は内部で関数を分離しており、unittest.mock.patch によりモック化しやすく設計されています。

---

もし README に追加してほしい内容（例: pyproject.toml のサンプル、CI ワークフロー、より詳細な .env.example、具体的な SQL スキーマ一覧など）があれば教えてください。必要に応じて追記します。