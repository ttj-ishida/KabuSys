# KabuSys

日本株向けの自動売買 / データプラットフォーム用 Python パッケージ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング（OpenAI）、リサーチ用ファクター計算、監査ログ（オーダー・約定トレース）などを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は次の目的を持つモジュール群です。

- J-Quants API から株価・財務・市場カレンダー等を差分取得して DuckDB に保存する ETL パイプライン
- RSS ニュース収集器（SSRF 対策・トラッキング除去・前処理）とニュース → LLM による銘柄センチメント算出
- 市場レジーム判定（ETF の MA とマクロニュースの LLM スコアを合成）
- リサーチ用ファクター計算（モメンタム・ボラティリティ・バリュー 等）と統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal → order_request → execution をトレースする DB スキーマ・初期化）

コードベースは DuckDB をデータ格納に利用し、OpenAI（gpt-4o-mini 想定）を NLP に用います。J-Quants API を通じて市場データを取得します。

---

## 主な機能一覧

- data
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（認証・ページネーション・レートリミット・保存関数）
  - カレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - ニュース収集（RSS の正規化・SSRF対策・raw_news への保存）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news：銘柄ごとのセンチメント算出、JSON Mode + バッチ）
  - 市場レジーム判定（score_regime：ETF MA とニュースセンチメント合成）
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索・IC・前方リターン（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - .env / 環境変数自動ロード（プロジェクトルート検出、.env / .env.local の読み込み）
  - Settings オブジェクトで設定値を取得（settings）

---

## セットアップ手順

※ 実行環境や CI に合わせて適宜調整してください。

1. 必要な Python（3.10+ 推奨）を用意する。

2. リポジトリをクローンしてインストール（ローカル開発向け）：

   - ソースルートに `pyproject.toml` がある想定で、editable インストールが可能です。
   - 依存パッケージ例（プロジェクト内で明示されているもの）:
     - duckdb
     - openai
     - defusedxml
     - （標準ライブラリ以外は pip でインストール）

   例:
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb openai defusedxml
   pip install -e .
   ```

   （実プロジェクトでは requirements.txt / pyproject.toml を参照してください。）

3. 環境変数の準備

   プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env` / `.env.local` を置くと、パッケージ読み込み時に自動でロードされます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時に有用）。

   必要な環境変数（主なもの）:

   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
   - SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
   - SLACK_CHANNEL_ID (必須) — Slack チャネル ID
   - OPENAI_API_KEY (推奨) — OpenAI 呼出し用（score_news / score_regime の引数でも渡せる）
   - KABUSYS_ENV (任意) — "development" / "paper_trading" / "live"（デフォルト "development"）
   - LOG_LEVEL (任意) — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト "INFO"）
   - DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト "data/kabusys.duckdb"）
   - SQLITE_PATH (任意) — SQLite（モニタリング用）パス（デフォルト "data/monitoring.db"）
   - KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト "http://localhost:18080/kabusapi"）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（基本例）

以下は主要 API の簡単な使用例です。DuckDB 接続 (duckdb.connect(...)) を渡して各関数を呼び出します。

- 日次 ETL を実行する（株価・財務・カレンダーの差分取得 + 品質チェック）:

  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを算出して ai_scores に書き込む:

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OpenAI API key は環境変数 OPENAI_API_KEY に設定するか、api_key 引数で渡せます
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"written: {n_written} codes")
  ```

- 市場レジームをスコアリングする（ETF 1321 の MA200 とマクロニュース LLM を合成）:

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ DB を初期化する（監査用 DuckDB）:

  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # テーブルが作成され、UTC タイムゾーンが設定されます
  ```

- 研究用ファクター計算:

  ```python
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  # conn: duckdb connection, target_date: datetime.date
  mom = calc_momentum(conn, target_date)
  vol = calc_volatility(conn, target_date)
  val = calc_value(conn, target_date)
  ```

注意:
- OpenAI 呼び出しはネットワーク/レート制限/エラー処理を含みます。関数は API 失敗時に安全なフォールバック（ゼロスコアやスキップ）を行う設計です。テスト時は内部の API 呼び出しをモック可能です（モジュール内の _call_openai_api 等を patch）。

---

## ディレクトリ構成（主なファイル）

以下はパッケージ内の主要モジュール一覧（src/kabusys/ 以下）：

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py (エイリアス / 抽象)
  - calendar_management.py
  - news_collector.py
  - quality.py
  - stats.py
  - audit.py
  - (その他: pipeline の ETLResult をエクスポートする etl.py)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/helpers: zscore_normalize は data.stats で提供

（上記はソースに含まれる主なファイルのみを抜粋しています。実装ファイルにさらに細分化されたモジュールが含まれます。）

---

## 設計上の注意点 / 重要な挙動

- 環境変数の自動ロード
  - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml）を探索し `.env` と `.env.local` を読み込みます。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

- Look-ahead bias（未来情報の漏洩）対策
  - AI / ETL / リサーチ関数は内部で `datetime.today()` / `date.today()` を直接参照しないよう配慮されています。`target_date` を明示的に渡すことを推奨します。
  - J-Quants からの取得データには `fetched_at` を記録し、いつデータを知り得たかをトレース可能にします。

- 冪等性
  - J-Quants 保存関数は ON CONFLICT DO UPDATE により冪等にデータを保存します。
  - 監査ログの order_request_id / broker_execution_id 等により発注の冪等性を担保します。

- エラー処理
  - 多くの外部 API 呼び出しはリトライ（指数バックオフ）やフォールバック（スコア=0 等）を実装し、単一の外部障害がパイプライン全体を停止させない設計です。
  - 品質チェックは Fail-Fast ではなく問題を集計して返すため、呼び出し元が停止基準を判断できます。

---

## よくある運用タスク（Tips）

- ETL の定期実行:
  - cron / Airflow / GitHub Actions 等で `run_daily_etl` を日次実行。
  - ETLResult の has_errors / has_quality_errors をチェックしてアラート判定。

- OpenAI 呼び出しのテスト:
  - 環境で実際の API を呼ばないテストは、内部の `_call_openai_api` を unittest.mock.patch で差し替えて行えます（news_nlp, regime_detector 両方で同様）。

- ローカルテスト用 DB:
  - DuckDB はファイルまたはインメモリ（":memory:"）で使用可能。テストではインメモリ DB を使うと便利です。

---

README はここまでです。より詳細な API リファレンスや運用ガイド（cron 設定例、監視・アラート設計、Slack 通知実装例など）が必要であれば用途に合わせたドキュメントを追記します。必要な章を指定してください。