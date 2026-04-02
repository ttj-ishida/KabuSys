# KabuSys

日本株向けのデータプラットフォームと自動売買補助ライブラリ群です。J-Quants / kabuステーション / OpenAI 等と連携して、データのETL、ニュースのセンチメント解析、ファクター計算、監査ログ管理、マーケットカレンダー管理などを提供します。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- J-Quants API を用いた株価・財務・カレンダーの差分取得と DuckDB への保存（ETL）
- RSS ベースのニュース収集と前処理
- OpenAI（gpt-4o-mini）を用いたニュースのセンチメント解析（銘柄別）とマクロセンチメントを用いた市場レジーム判定
- 各種ファクター（モメンタム、バリュー、ボラティリティ等）の計算、統計ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ用テーブル（signal → order_request → execution のトレーサビリティ）と初期化ユーティリティ
- マーケットカレンダーの管理（営業日の判定・前後営業日の取得等）

設計方針としては「Look-ahead bias を避ける」「API 呼び出しはリトライ・フェイルセーフ」「DuckDB をメインの永続化先」「モジュール間の過度な結合を避ける」等に配慮しています。

---

## 機能一覧

主要な機能（モジュール）:

- kabusys.config
  - .env / .env.local 自動読み込み（プロジェクトルート検出）・設定取得
- kabusys.data.jquants_client
  - J-Quants API からのデータ取得（株価、財務、カレンダー）
  - DuckDB への冪等保存関数
- kabusys.data.pipeline
  - 日次 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック
  - 個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
- kabusys.data.news_collector
  - RSS 取得、テキスト前処理、raw_news への保存（冪等）
- kabusys.ai.news_nlp
  - ニュースを銘柄ごとにまとめて OpenAI でセンチメントを評価し ai_scores へ保存（score_news）
- kabusys.ai.regime_detector
  - ETF(1321) の MA200 乖離とマクロニュースの LLM センチメントを合成して市場レジームを判定（score_regime）
- kabusys.research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー等
- kabusys.data.quality
  - データ品質チェック群（欠損、重複、スパイク、日付不整合）
- kabusys.data.audit
  - 監査ログ用スキーマ定義と初期化ユーティリティ（init_audit_schema / init_audit_db）
- kabusys.data.calendar_management
  - 営業日判定、前後営業日の取得、カレンダー夜間更新ジョブ

---

## 必要条件

- Python 3.10 以上（タイプヒントの union 型（|）等を使用）
- 推奨パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml

サードパーティライブラリは要件に応じて追加してください。CLI / 実運用ではさらに Slack 連携用や kabu API クライアント等が必要になる可能性があります。

---

## セットアップ手順

1. リポジトリをクローン:
   git clone <リポジトリURL>
   cd <repo>

2. 仮想環境を作成・有効化（例）:
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .\.venv\Scripts\activate   # Windows (PowerShell)

3. 必要パッケージをインストール（簡易）:
   pip install duckdb openai defusedxml

   実運用では requirements.txt を用意している場合はそれを使用してください。

4. 環境変数の設定:
   プロジェクトルート（.git または pyproject.toml がある場所）に `.env` / `.env.local` を置けます。config モジュールが自動で読み込みます（自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   主要な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - SLACK_BOT_TOKEN: Slack Bot トークン（通知等を使う場合）
   - SLACK_CHANNEL_ID: Slack 通知先 チャネル ID
   - KABU_API_PASSWORD: kabu ステーション API のパスワード（使用時）

   任意 / デフォルトあり
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/...
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
   - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
   - SQLITE_PATH: data/monitoring.db（デフォルト）
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABU_API_PASSWORD=secret
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（主要例）

下記はライブラリ API を直接呼び出す最小例です。DuckDB 接続はライブラリ側で使われます。

- 日次 ETL を実行する:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）を評価して ai_scores に書き込む:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY が環境変数にあるなら api_key=None で動作します
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"written: {written}")
  ```

- 市場レジーム判定（MA200 + マクロニュース）を実行:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ用 DB を初期化:
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # 必要なら conn を使って監査テーブルへアクセス可能
  ```

- 設定を参照する例:
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

注意点:
- AI 機能を使用する関数は `api_key` 引数を受け取ります。引数を渡さない場合は環境変数 `OPENAI_API_KEY` を参照します。未設定だと ValueError が発生します。
- DuckDB 側のスキーマ（raw_prices / raw_financials / market_calendar / raw_news / news_symbols / ai_scores / market_regime 等）は別途初期化（DDL実行）しておく必要があります。ETL や保存関数は既存のテーブル構造に従って動作します。

---

## 自動 .env ロードについて

- kabusys.config モジュールはプロジェクトルート（.git または pyproject.toml）を起点に `.env` と `.env.local` を自動読み込みします。
- 読み込み順は: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時などに便利です）。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル／モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント解析（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント＋DuckDB 保存ロジック
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult の再エクスポート
    - news_collector.py      — RSS ニュース収集／前処理
    - quality.py             — データ品質チェック
    - calendar_management.py — マーケットカレンダー管理
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ等

---

## 注意・運用上のポイント

- Look-ahead bias を避けるため、各種関数は内部で date.today() を参照せず、明示的な target_date を受け取る設計です。バックテストや再現性に注意してください。
- OpenAI / J-Quants など外部 API 呼び出しはリトライ・バックオフの考慮がありますが、API キーやレート制限の取り扱いに注意してください。
- DuckDB に対する executemany の空リストバグやバージョン差分に配慮して実装していますが、使用する DuckDB バージョン・環境によって挙動が異なる場合があるため運用前に検証してください。
- ニュース収集では SSRF 対策・受信サイズ上限・XML の安全パース（defusedxml）などセキュリティ考慮が施されています。外部ソース追加時も同様の配慮を行ってください。

---

## 貢献・拡張

- 新しい ETL ソースやニュースソースの追加、Strategy 実行・注文送信層の実装はモジュール分割の方針に従って追加してください。
- テストは各モジュールで外部呼び出しをモックして行うことを推奨します（OpenAI 呼び出しやネットワーク I/O をテストで直接叩かない）。

---

この README はコードベースの現状（主に src/kabusys 以下）を元に作成しています。運用や実行には環境依存のセットアップ（API キーや DB スキーマ作成等）が必要です。追加で具体的な起動スクリプトや Docker コンテナ化、CI 設定が必要であればその目的に合わせたドキュメントを作成します。