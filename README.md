# KabuSys

KabuSys は日本株のデータプラットフォームと自動売買基盤向けユーティリティ群です。  
J-Quants / kabuステーション / OpenAI 等と連携し、データ収集（ETL）、品質チェック、ニュースセンチメント評価、研究用ファクター計算、監査ログ管理などを提供します。

バージョン: 0.1.0

---

## 概要

主な目的は以下です。

- J-Quants API から株価・財務・カレンダー等を差分取得して DuckDB に保存する ETL。
- ニュース収集（RSS）と LLM/OpenAI を用いたニュースセンチメント評価（銘柄別 ai_score）。
- 市場レジーム判定（ETF MA とマクロニュースの LLM センチメント混合）。
- 研究向けファクター計算（Momentum / Value / Volatility 等）と特徴量解析ユーティリティ。
- 監査ログ（シグナル→発注→約定のトレーサビリティ）を管理するスキーマの初期化・ユーティリティ。
- データ品質チェック（欠損、重複、スパイク、日付不整合など）。

設計上の方針として、バックテスト等でのルックアヘッドバイアスを防ぐために
日時参照や DB クエリの境界（排他）に配慮した実装がされています。

---

## 機能一覧（抜粋）

- データ（kabusys.data）
  - ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - ニュース収集: fetch_rss, preprocess_text, news → raw_news テーブル保存ロジック
  - カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
  - 品質チェック: run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
  - 監査ログ: init_audit_schema, init_audit_db
  - 汎用統計: zscore_normalize

- AI（kabusys.ai）
  - ニュース NLP: score_news（OpenAI を利用して銘柄ごとのセンチメントを ai_scores に保存）
  - レジーム判定: score_regime（ETF 1321 の MA200 乖離 + マクロニュース LLM による混合判定）

- 研究（kabusys.research）
  - ファクター計算: calc_momentum / calc_value / calc_volatility
  - 特徴量探索: calc_forward_returns / calc_ic / factor_summary / rank

- 設定管理（kabusys.config）
  - .env 自動ロード（プロジェクトルート検出）、環境変数取得ラッパー（Settings）

---

## セットアップ手順

前提:
- Python 3.10 以上（`|` 型注釈を使用しているため）
- DuckDB, OpenAI SDK, defusedxml などが必要

1. リポジトリをクローン（例）
   ```bash
   git clone <このリポジトリ>
   cd <リポジトリ>
   ```

2. 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   （プロジェクトに requirements.txt がない場合、最低限これらを入れてください）
   ```bash
   pip install duckdb openai defusedxml
   ```
   必要に応じて追加パッケージ（例: pytest 等）をインストールしてください。

4. 環境変数を設定
   - プロジェクトルートに `.env` と `.env.local` を置くと、自動で読み込まれます（優先度: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主な必須環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API 用パスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime の呼び出しで使用）

   追加の設定:
   - DUCKDB_PATH: デフォルト data/kabusys.duckdb
   - SQLITE_PATH: デフォルト data/monitoring.db
   - KABUSYS_ENV: development / paper_trading / live （デフォルト development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

5. データベースの初期化（監査ログ用）
   監査ログ専用の DB を作成する例:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")  # ディレクトリは自動作成されます
   ```

---

## 使い方（代表的な例）

以下は簡単な実行例の抜粋です。実運用ではログ設定・例外処理・環境変数管理を合わせて行ってください。

- DuckDB 接続を作って日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")  # settings.duckdb_path を参照しても良い
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- OpenAI を使ってニュースの AI スコアを生成し ai_scores テーブルへ書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定（ETF 1321 の MA200 + マクロニュース）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  ```

- 監査ログスキーマを既存接続に追加（冪等）
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

注意:
- OpenAI 呼び出しは API キーを必要とします。`api_key` 引数で直接渡すか、環境変数 `OPENAI_API_KEY` を設定してください。
- DuckDB のクエリや ETL は外部 API 呼び出し・ファイルアクセスを伴うため、ネットワーク接続や権限に注意してください。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime などで使用）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン（通知に使用）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する（任意）

.env ファイル読み込みルール:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます。
- 読み込み順: OS 環境変数 > .env.local > .env
- テスト等で自動ロードを抑止するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセット。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys の主要モジュール構成（実際のファイルツリーの抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - calendar_management.py
      - etl.py
      - pipeline.py
      - stats.py
      - quality.py
      - audit.py
      - jquants_client.py
      - news_collector.py
      - (その他 jquants_client で使われるユーティリティ等)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/__init__.py
    - (strategy/, execution/, monitoring/ などのパッケージは __all__ に含められていますが、ここには抜粋されていません)

各モジュールは責務ごとに分離されており、ETL、品質管理、AI（LLM）処理、研究用分析、監査ログ管理などが別ファイルに分かれています。

---

## 運用上の注意

- OpenAI コールは外部ネットワークかつ有料 API 呼び出しです。API 利用量とレート制限に注意してください。retry/backoff ロジックは実装されていますが、運用時はコスト管理が必要です。
- J-Quants の API レート制御（120 req/min）を尊重するよう RateLimiter が実装されています。長時間の大量リクエストを投げる場合は考慮してください。
- ETL は差分取得とバックフィルを組み合わせており、データの一貫性を保つために DB のスキーマ・インデックスが前提になります。初期セットアップではスキーマ作成手順（別途の schema 初期化スクリプト等）が必要です（このリポジトリの他モジュールでスキーマ初期化を提供していることが想定されます）。
- DuckDB の executemany 等はバージョン差分に注意（このコードは互換性を考慮した実装になっています）。

---

## 貢献・開発

- 新しい機能追加／バグ修正の際は、ユニットテストを追加してください。特に ETL・品質チェック・AI レスポンスのパース部分は外部 API に依存するため、モックを用いたテストが推奨されます。
- .env.example を用意して環境変数のサンプルを共有すると導入が楽になります。
- ライブラリ依存の固定や CI（テスト用 DB の初期化、OpenAI 呼び出しのモック）を整備すると安定した開発が行えます。

---

README の内容やサンプルコードについて、追加で補足すべき点や実際の初期データロード手順（スキーマ作成スクリプトなど）を記載してほしい場合は教えてください。