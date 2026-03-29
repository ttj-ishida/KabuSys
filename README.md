# KabuSys

日本株向け自動売買／データプラットフォーム用ライブラリ KabuSys の README。  
このリポジトリはデータ収集（J-Quants）、品質チェック、特徴量生成、ニュースNLP（OpenAI）、市場レジーム判定、監査ログなどの機能を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムの内製ユーティリティ群を集めた Python モジュール群です。主に以下を目的としています。

- J-Quants API からのデータ取得（株価・財務・マーケットカレンダー）
- DuckDB を使ったデータ保存と ETL パイプライン
- データ品質チェック（欠損、重複、スパイク、日付整合性）
- ニュース収集と LLM を用いたニュースセンチメント評価（gpt-4o-mini 等）
- マクロ情報とテクニカル指標を組み合わせた市場レジーム判定
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- 発注・約定を追跡する監査ログスキーマ（DuckDB）

設計上の特徴は、ルックアヘッドバイアスを避ける実装（内部で date.today() を不用意に参照しない）、API 呼び出しに対する堅牢なリトライとフェイルセーフ、DuckDB を用いた冪等的な保存操作です。

---

## 機能一覧

- data/jquants_client.py
  - J-Quants API からのデータ取得・保存（fetch / save）
  - RateLimiter、401 自動リフレッシュ、ページネーション処理
- data/pipeline.py / data/etl.py
  - 日次 ETL 実行（run_daily_etl）: カレンダー・株価・財務の差分取得・保存・品質チェック
  - ETL 結果を ETLResult として返却
- data/quality.py
  - 欠損・重複・スパイク・日付不整合チェック（run_all_checks）
- data/news_collector.py
  - RSS 収集、前処理、SSRF 対策、冪等保存ロジック
- data/calendar_management.py
  - 営業日判定、前後営業日探索、カレンダー更新ジョブ
- data/audit.py
  - 監査ログ・トレーサビリティ用スキーマの初期化（init_audit_schema / init_audit_db）
- ai/news_nlp.py
  - ニュースを銘柄ごとにまとめて LLM に投げ、ai_scores にスコアを保存（score_news）
- ai/regime_detector.py
  - ETF(1321) の 200日 MA 乖離とマクロニュースの LLM センチメントを合成して市場レジームを判定（score_regime）
- research/
  - ファクター計算・特徴量探索（calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic 等）
- config.py
  - 環境変数・.env ロード、アプリ設定取得（settings オブジェクト）

---

## セットアップ手順

1. Python 環境を作成（推奨: venv/virtualenv）
   - 例:
     ```
     python -m venv .venv
     source .venv/bin/activate
     pip install --upgrade pip
     ```

2. 依存パッケージをインストール  
   ※リポジトリに requirements.txt が無い想定のため、主要依存を例示します（プロジェクト環境に合わせて調整してください）:
   ```
   pip install duckdb openai defusedxml
   ```
   - 必要に応じて他パッケージ（requests 等）を追加してください。

3. パッケージを開発モードでインストール（任意）
   ```
   pip install -e .
   ```

4. 環境変数を設定
   - 推奨: プロジェクトルートに `.env`（および `.env.local` を開発用）を置くと自動で読み込まれます（ただし、パッケージ初期化時にプロジェクトルートが判定できる場合のみ）。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. 必須環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - SLACK_BOT_TOKEN: Slack 通知用ボットトークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - OPENAI_API_KEY: OpenAI を利用する機能（news/regime）で必要
   - （任意）KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - （任意）LOG_LEVEL: DEBUG/INFO/...
   - ファイルパス設定（省略時デフォルトを使用）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   ```

---

## 使い方（主要な API とサンプル）

以下は Python スクリプト/REPL からの利用例です。DuckDB 接続は duckdb.connect(path) を使用します。

- 設定値参照
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

- ETL（日次パイプライン）の実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコア（OpenAI を使用）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None で env の OPENAI_API_KEY を使用
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査専用 DuckDB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # テーブルが作成され、UTC タイムゾーンが設定されます
  ```

- 市場カレンダー確認ユーティリティ例
  ```python
  from kabusys.data.calendar_management import is_trading_day
  import duckdb, datetime
  conn = duckdb.connect(str(settings.duckdb_path))
  print(is_trading_day(conn, datetime.date(2026, 3, 20)))
  ```

注意:
- OpenAI 呼び出し部は retries とフェイルセーフを持ちますが、API キーとクォータに注意してください。
- run_daily_etl や score_news / score_regime は DB の既存スキーマ（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, market_regime 等）を前提とします。適切なスキーマ初期化や ETL の順序を確認してください。

---

## .env の自動読み込みについて

- config.py はパッケージ初期化時にプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索し、`.env` と `.env.local` を自動で読み込みます。
  - 読み込み優先度: OS 環境 > .env.local > .env
  - OS 環境変数を上書きしない（ただし .env.local は override=True の挙動で .env より優先的に読み込まれます）
- 自動ロードを無効にする場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## ディレクトリ構成

主要ファイル・モジュール構成（src/kabusys/ 以下）:

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント算出（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETL 結果の再公開（ETLResult）
    - news_collector.py      — RSS 収集と前処理
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - quality.py             — データ品質チェック
    - stats.py               — 共通統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum, value, volatility）
    - feature_exploration.py — 将来リターン、IC、統計サマリー等

（上記は主要サブモジュールの抜粋です。詳しい実装は各モジュール内の docstring 参照）

---

## 注意点 / 運用上のヒント

- DuckDB スキーマおよびテーブルの初期化はプロジェクト側で行う必要があります（スキーマ生成ユーティリティ等を別途用意することを想定）。
- OpenAI の利用は API キーの保護、コスト管理に注意してください。テスト時はモックを使えるよう内部で分離設計されています。
- J-Quants API のレート制限やトークン有効期間に注意。jquants_client はトークン自動リフレッシュと固定間隔レート制御を実装しています。
- ETL は各ステップで個別にエラーハンドリングされ、部分失敗しても他のステップは継続する設計です。ETLResult で問題を収集して呼び出し元で判断してください。

---

必要であれば、README にサンプルの DB スキーマ、具体的な ETL 実行スケジュール（cron / Airflow の例）、または Docker / CI セットアップ手順を追加できます。どの情報が欲しいか教えてください。