# KabuSys

日本株向け自動売買・データプラットフォームライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL、データ品質チェック、特徴量計算、ニュースNLP（OpenAIを利用したセンチメント解析）、市場レジーム判定、監査ログなどを備えたモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下の目的で設計された Python モジュール群です。

- J-Quants API から株価・財務・マーケットカレンダーを差分取得して DuckDB に保存する ETL パイプライン
- 生データに対する品質チェック（欠損、日付不整合、スパイク、重複）
- ニュース収集（RSS）と OpenAI を用いたニュースセンチメント（ai_scores）算出
- 市場レジーム判定（ETF とマクロニュースの組合せ）
- 研究用途のファクター計算（Momentum / Value / Volatility 等）と特徴量探索ユーティリティ
- 監査ログ（signal → order_request → executions）のスキーマ定義と初期化ユーティリティ
- 環境設定管理（.env 自動読み込み、環境変数アクセスのラッパ）

設計上の特徴として、バックテスト時のルックアヘッドバイアスを避ける取り回し、API 呼び出しのリトライとレート制御、DuckDB を使った高速なローカルDB保存・冪等性を重視しています。

---

## 主な機能一覧

- 環境設定
  - .env / .env.local の自動読み込み（プロジェクトルートを .git / pyproject.toml から探索）
  - 必須設定の取得ラッパ（settings）

- データ（kabusys.data）
  - J-Quants クライアント（fetch / save）
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - データ品質チェック（missing / spike / duplicates / date consistency）
  - マーケットカレンダー管理（営業日判定・次営業日/前営業日取得）
  - ニュース収集（RSS → raw_news, SSRF/サイズ/トラッキング対策あり）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）

- 研究（kabusys.research）
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算、IC 計算、ファクター統計サマリ
  - z-score 正規化ユーティリティ

- AI（kabusys.ai）
  - ニュース NLP スコアリング（score_news: gpt-4o-mini を JSON mode で利用）
  - 市場レジーム判定（score_regime: ETF 200日MA乖離 + マクロセンチメントを合成）

- その他ユーティリティ
  - 統計ユーティリティ（zscore_normalize）
  - DUCKDB / SQLite パス設定（settings）

---

## セットアップ手順（概略）

※ 本リポジトリに requirements.txt / pyproject.toml がある前提で、環境に応じて適宜読み替えてください。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージのインストール
   - pyproject.toml / requirements.txt がある想定:
     ```
     pip install -e .
     ```
     または
     ```
     pip install -r requirements.txt
     ```
   - 必要な外部パッケージ（例）:
     - duckdb
     - openai (OpenAI Python SDK)
     - defusedxml
     - その他プロジェクト依存パッケージ

4. 環境変数設定 (.env)
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）から `.env` / `.env.local` を自動読み込みします。
   - 必須（機能利用時に要求される）環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - SLACK_BOT_TOKEN — Slack 通知を使う場合
     - SLACK_CHANNEL_ID — Slack 通知先チャンネルID
     - KABU_API_PASSWORD — kabuステーション API を使う場合
   - 任意:
     - OPENAI_API_KEY — OpenAI を使う場合（score_news / score_regime）
     - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
     - LOG_LEVEL — DEBUG/INFO/…（デフォルト INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
   - 自動 .env ロードを無効化したいとき:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（代表的な例）

以下はライブラリを直接呼び出すサンプルです。実運用ではジョブスケジューラ（cron 等）またはワークフローで定期実行してください。

- DuckDB に接続して日次 ETL を実行する
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # target_date を指定しないと今日の日付が使われます（内部で営業日に調整されます）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコアを算出（OpenAI APIキーが必要）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡す
  n = score_news(conn, target_date=date(2026, 3, 20))
  print("scored:", n)
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  r = score_regime(conn, target_date=date(2026, 3, 20))
  print("regime scored:", r)
  ```

- 監査ログ用 DuckDB を初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # :memory: も可
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026, 3, 20))
  ```

注意点:
- OpenAI を使う機能（news_nlp, regime_detector）は API 呼び出しのリトライロジックを持ちますが、利用には OPENAI_API_KEY が必要です。API 呼び出しはコストが発生します。
- J-Quants 関連機能は J-Quants の認証（リフレッシュトークン）を必要とします。get_id_token および fetch_* 関数は内部でトークンを取得・キャッシュします。
- DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, raw_news, ai_scores, market_regime, etc.）は ETL 実行時に前提となるため、初期スキーマ提供スクリプトがある場合は先に実行してください（本 README のコードベースにスキーマ初期化ユーティリティがある場合はそれを使用）。

---

## 主要設定（settings）

kabusys.config.Settings 経由でアクセスします。主なプロパティ:

- jquants_refresh_token: JQUANTS_REFRESH_TOKEN（必須）
- kabu_api_password: KABU_API_PASSWORD（必須 if 使用）
- kabu_api_base_url: KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
- slack_bot_token: SLACK_BOT_TOKEN（必須 if Slack 通知を使う）
- slack_channel_id: SLACK_CHANNEL_ID（必須 if Slack 通知を使う）
- duckdb_path: DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- sqlite_path: SQLITE_PATH（デフォルト data/monitoring.db）
- env: KABUSYS_ENV（development / paper_trading / live）
- log_level: LOG_LEVEL（DEBUG/INFO/...）

必須設定が欠けている場合、Settings の該当プロパティアクセスで ValueError が送出されます。

---

## ディレクトリ構成（主要ファイル）

（この README は src/kabusys 配下の主要モジュールに基づいています）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数/設定読み込みユーティリティ
  - ai/
    - __init__.py
    - news_nlp.py              — ニュースセンチメント（OpenAI 呼び出し・バッチ処理）
    - regime_detector.py       — 市場レジーム判定（MA + マクロセンチメント合成）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（fetch / save / rate limit）
    - pipeline.py              — ETL パイプラインと run_daily_etl 等
    - etl.py                   — ETLResult の再エクスポート
    - news_collector.py        — RSS 取得・前処理・保存
    - calendar_management.py   — マーケットカレンダー管理（営業日判定 等）
    - quality.py               — 品質チェック（欠損/スパイク/重複/日付不整合）
    - stats.py                 — zscore 等汎用統計ユーティリティ
    - audit.py                 — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py       — Momentum/Value/Volatility 計算
    - feature_exploration.py   — forward returns / IC / rank / summary
  - monitoring/ (該当実装があれば監視周り)
  - strategy/, execution/, monitoring/ (トップレベル __all__ で参照される可能性あり)

---

## 開発・テスト時のヒント

- 自動 .env 読み込みはデフォルトで有効。テストで明示的に環境を操作する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化できます。
- OpenAI API 呼び出しはテストでモックしやすい設計（各モジュールごとに _call_openai_api を内部で呼ぶ）。unittest.mock.patch で差し替え可能です。
- network/IO 周りはモジュールごとに差し替えポイント（_urlopen など）がありテストしやすくなっています。
- DuckDB への executemany は空リストを受け付けないバージョン制約を意識してガードがあります（空チェックを行っている箇所がある）。

---

## ライセンス・貢献

（ここにライセンス／Contributing ガイドラインを記載してください）

---

質問や README の追加要望（例：具体的な schema 初期化 SQL、CI 実行方法、デプロイ手順など）があれば教えてください。必要に応じてサンプルスクリプトやテンプレート .env.example も作成します。