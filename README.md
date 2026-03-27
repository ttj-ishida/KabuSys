# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants からのデータ取得（ETL）、ニュースの NLP スコアリング、LLM を使った市場レジーム判定、研究用ファクター計算、監査ログ（発注／約定トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買に必要なデータ基盤と分析・実行ヘルパーをまとめたライブラリです。主な目的は以下のとおりです。

- J-Quants API を用いた株価・財務・カレンダー等の差分 ETL
- RSS によるニュース収集と OpenAI を使ったニュースセンチメント・スコアリング
- ETF とマクロニュースを組み合わせた市場レジーム判定（LLM+価格指標）
- 研究（ファクター計算、将来リターン・IC・統計サマリー）
- 監査ログ（signal → order_request → execution）用の DuckDB スキーマ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の特徴として、ルックアヘッドバイアスに配慮した時刻扱い、外部 API 呼び出しの堅牢なリトライ・レート制御、DuckDB を用いた冪等保存などが挙げられます。

---

## 機能一覧

- ETL:
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（差分取得・保存・品質チェック）
  - jquants_client: fetch/save 関連の実装、トークン自動リフレッシュ、レート制限対応
- データ品質:
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- ニュース:
  - fetch_rss（RSS 取得・前処理・SSRF 対策）
  - news_nlp.score_news（OpenAI で銘柄ごとの sentiment を ai_scores に書き込み）
- マーケットレジーム:
  - regime_detector.score_regime（1321 の MA200 とマクロニュースを合成して regime を決定）
- 研究:
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / zscore_normalize
- 監査ログ:
  - init_audit_schema / init_audit_db（signal/order_request/executions テーブル定義と初期化）
- カレンダー管理:
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job

---

## 要件

- Python 3.10+
- 主な依存パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリのみで実装されている部分も多いですが、OpenAI / DuckDB を使う機能は上記が必要です。

（プロジェクトには requirements.txt があればそれを利用してください）

---

## セットアップ手順

1. リポジトリをクローン、あるいはパッケージを配置
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージのインストール
   例:
   ```
   pip install duckdb openai defusedxml
   ```
   プロジェクトに requirements.txt があれば:
   ```
   pip install -r requirements.txt
   ```

4. 環境変数の設定
   必須:
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用）
   - KABU_API_PASSWORD — kabuステーション API 用パスワード（実行系がある場合）
   - SLACK_BOT_TOKEN — Slack 通知を使う場合
   - SLACK_CHANNEL_ID — Slack 通知先
   - OPENAI_API_KEY — OpenAI 呼び出し（news_nlp / regime_detector）を行う場合

   オプション（デフォルト値あり）:
   - KABUSYS_ENV = development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL = DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）

   簡単な .env の例（プロジェクトルートに置く）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_password
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

   自動 .env ロード:
   - ライブラリはプロジェクトルートを .git または pyproject.toml を基準に探索し、.env / .env.local を自動読み込みします。
   - テストなどで自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DB 用ディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（サンプル）

以下は主要 API の利用例です。実行は Python スクリプトや REPL から行います。

- DuckDB 接続作成:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行:
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの NLP スコア（OpenAI 必須）:
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"wrote scores for {written} codes")
  ```

- 市場レジーム判定（OpenAI 必須）:
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算:
  ```python
  from kabusys.research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  m = calc_momentum(conn, date(2026, 3, 20))
  v = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

- 監査ログ DB 初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # conn_audit は監査テーブルが作成済みの DuckDB 接続
  ```

- カレンダー関連ユーティリティ:
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date

  print(is_trading_day(conn, date(2026,3,20)))
  print(next_trading_day(conn, date(2026,3,20)))
  ```

注意点:
- OpenAI を使う関数（score_news, score_regime 等）は API キーを引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- DuckDB のテーブルはプロジェクトに同梱のスキーマ初期化ロジックや ETL の実行によって作成される前提です。必要なテーブルがない場合は ETL 実行時に作成処理を呼ぶよう実装してください。

---

## 環境変数（まとめ）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- OPENAI_API_KEY（news/regime 機能を使う場合）

任意/デフォルト:
- KABUSYS_ENV (development|paper_trading|live) — default: development
- LOG_LEVEL (INFO 等) — default: INFO
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env 読み込みを無効化

---

## ディレクトリ構成

以下は主要モジュールを抜粋した構成です（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースセンチメント（OpenAI）
    - regime_detector.py         — 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（fetch/save）
    - pipeline.py                — ETL パイプライン / run_daily_etl
    - etl.py                     — ETLResult 再エクスポート
    - news_collector.py          — RSS 収集（SSRF 対策・前処理）
    - calendar_management.py     — JPX カレンダー管理 / 営業日判定
    - quality.py                 — データ品質チェック
    - stats.py                   — 統計ユーティリティ（zscore_normalize）
    - audit.py                   — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py         — モメンタム／ボラティリティ／バリュー計算
    - feature_exploration.py     — 将来リターン・IC・統計サマリー等
  - ai/, data/, research/ 等で提供される関数はモジュールとして利用可能です。

---

## 運用上の注意 / トラブルシューティング

- 自動 .env 読み込み:
  - パッケージはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から .env/.env.local を自動読込します。テストでこれを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- OpenAI の呼び出し:
  - レスポンスパース失敗や API エラーはフェイルセーフでデフォルト値にフォールバックする設計ですが、必要に応じてログを確認してください。
  - LLM 呼び出しはリトライロジックを実装していますが、API 制限や料金に注意してください。

- J-Quants API:
  - get_id_token でリフレッシュトークンを使って ID トークンを取得します。API の rate limit（120 req/min）を守る実装になっていますが、大量取得時は注意してください。

- DuckDB の executemany に関する互換性:
  - 一部の処理は DuckDB のバージョン依存の挙動（executemany の空リストなど）を考慮した実装になっています。問題が発生したら DuckDB のバージョンを確認してください。

---

## 貢献 / ライセンス

この README では省略します。貢献する場合は Pull Request と Issue を歓迎します。必要であればコーディング規約・テスト方針等を別途まとめてください。

---

以上がこのコードベースの概要と基本的な使い方です。README の内容をプロジェクトの実装状況や要件に合わせて適宜調整してください。必要であれば README の英訳や具体的な CLI 実行例（cron ジョブ / systemd / Airflow など）も追加します。