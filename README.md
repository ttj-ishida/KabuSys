# KabuSys — 日本株自動売買システム

簡潔な日本語 README を作成します。以下はこのリポジトリの概要、機能、セットアップ手順、主な使い方とディレクトリ構成です。

---

## プロジェクト概要

KabuSys は日本株向けのデータプラットフォームと自動売買基盤のライブラリ群です。J-Quants API からのデータ取得（株価・財務・マーケットカレンダー）や、ニュースの NLP によるセンチメントスコアリング、ファクター計算、ETL パイプライン、監査ログ（トレーサビリティ）等、アルゴリズム取引やリサーチに必要な機能を提供します。

設計方針の例:
- DuckDB を用いたローカルデータストア
- J-Quants / OpenAI 等外部 API との堅牢な接続（リトライ・レート制御等）
- ルックアヘッドバイアスを避ける設計
- ETL とデータ品質チェックの分離
- 冪等（idempotent）なデータ保存

---

## 主な機能一覧

- 環境設定管理（.env 自動ロード / 必須変数チェック）
- J-Quants クライアント
  - 株価日足（OHLCV）取得 / 保存
  - 財務データ取得 / 保存
  - JPX マーケットカレンダー取得 / 保存
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース収集（RSS）と前処理（SSRF 対策、追跡パラメータ除去）
- ニュース NLP（OpenAI）による銘柄別センチメント -> `ai_score` 保存
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメント合成）
- 研究用ユーティリティ（モメンタム / バリュー / ボラティリティ等のファクター計算）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）
- マーケットカレンダー管理（営業日判定 / next/prev_trading_day 等）

---

## 要求環境 / 依存パッケージ

- Python 3.10 以上（typing の | 型ヒントを使用）
- 主要依存（例）:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ：urllib, json, logging, datetime, hashlib, socket, ipaddress など

実際のプロジェクトでは requirements.txt または pyproject.toml に依存関係を明記してください。

---

## セットアップ手順

1. Python 仮想環境作成（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```

   （実際はプロジェクトの requirements.txt や pyproject.toml を参照してください）

3. 環境変数を設定
   - プロジェクトルートに `.env`（および `.env.local`）を置くと自動で読み込まれます。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な必須環境変数（例）
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=...

   # OpenAI
   OPENAI_API_KEY=...

   # kabuステーション (注文系がある場合)
   KABU_API_PASSWORD=...
   KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意

   # Slack (通知等に利用)
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...

   # DB パス（任意、省略時はデフォルトを使用）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境
   KABUSYS_ENV=development   # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要 API の例）

以下は最小限の利用例です。実行前に必要な環境変数（特に認証トークン）を設定してください。

- DuckDB 接続の作成（例）
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行する（差分取得＋品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（銘柄別スコア）を生成する
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY が環境変数に必要
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込んだ銘柄数:", n_written)
  ```

- 市場レジームスコアを計算して保存する
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  # OPENAI_API_KEY が環境変数に必要
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # これで監査テーブルが作成されます
  ```

- マーケットカレンダー関連ユーティリティ
  ```python
  from datetime import date
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

注意点:
- OpenAI 呼び出し（news_nlp / regime_detector）は API 料金が発生します。テストではモック化することを推奨します。
- ETL / データ取得は J-Quants の認証トークン（refresh token）とレート制限に従います。
- 内部関数はルックアヘッドバイアスに配慮した作りになっています（多くの処理が target_date を明示的引数とする）。

---

## 設定と起動に関するヒント

- .env 自動読み込み
  - パッケージの config モジュールはリポジトリルート（.git または pyproject.toml を探索）にある `.env` / `.env.local` を起動時に自動で読み込みます。
  - テスト等で自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

- 実行環境フラグ
  - 環境は `KABUSYS_ENV` で `development` / `paper_trading` / `live` を切り替えられます。
  - `settings.is_live` / `is_paper` / `is_dev` で判定できます。

- ログ
  - 環境変数 `LOG_LEVEL`（DEBUG/INFO/WARNING/ERROR/CRITICAL）で制御します。

---

## ディレクトリ構成（主要ファイル）

以下はコードベースの主要ファイルとディレクトリの抜粋（提供されたコードに基づく）です。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py                (re-export)
    - pipeline.py
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/... (ファクター・解析ユーティリティ)
  - (その他: strategy/, execution/, monitoring/ が __all__ に含まれる場合あり。実装が別ディレクトリにある可能性があります)

実際のリポジトリではさらにテスト、スクリプト、ドキュメント、設定ファイル（pyproject.toml 等）が含まれる想定です。

---

## 開発・運用上の注意点

- 外部 API キー（J-Quants / OpenAI / Slack 等）は安全に管理してください。リポジトリにハードコーディングしないでください。
- OpenAI 呼び出しは課金対象です。テストではモック化するか `OPENAI_API_KEY` を設定せずにテスト用の差し替え関数を用いることを推奨します。
- ETL はレート制限・リトライを実装していますが、大量実行や並列実行時の挙動は注意してください。
- DuckDB のバージョンや SQL 方言の違いにより一部バインド挙動が影響を受ける可能性があります（コード内にも注意コメントあり）。

---

## サンプル .env.example

プロジェクトルートに `.env.example` を置くとユーザがコピーして編集しやすくなります（例）:

```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# OpenAI
OPENAI_API_KEY=your_openai_api_key_here

# kabuステーション API (注文を行う場合)
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB paths (任意)
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

必要があれば README に「コマンド例」「詳細 API リファレンス」「テスト手順」「CI 設定」などの追加セクションも作成できます。どの情報を優先して追記しますか？