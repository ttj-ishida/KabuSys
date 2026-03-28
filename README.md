# KabuSys

KabuSys は日本株のデータプラットフォームと自動売買パイプラインを目的としたライブラリ群です。J-Quants からのデータ取得・ETL、ニュース収集と NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質検査、監査ログ（トレーサビリティ）など、運用・研究・発注に必要な機能群を含みます。

バージョン: 0.1.0

---

## 主要機能（抜粋）

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定の取得ユーティリティ
- データ ETL（J-Quants 連携）
  - 株価日足（OHLCV）取得・保存（差分更新・ページネーション対応）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - ETL パイプライン（差分取得・バックフィル・品質チェック含む）
- ニュース収集
  - RSS フィードからの記事収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - raw_news / news_symbols への冪等保存
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースセンチメント評価（gpt-4o-mini, JSON mode）
  - チャンクバッチング、リトライ、レスポンス検証、スコアクリップ
- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離とマクロニュース（LLM）を合成して日次レジーム判定
- 研究用ユーティリティ
  - ファクター計算（モメンタム・バリュー・ボラティリティ 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z-score 正規化
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合チェック
- 監査ログ（Audit）
  - signal → order_request → execution のトレーサビリティを担保する監査スキーマ初期化・DB 作成
- 外部連携
  - OpenAI（news_nlp / regime_detector）
  - J-Quants API クライアント（認証・レート制御・リトライ・保存）

---

## 前提（Prerequisites）

- Python 3.10 以上（型アノテーションに | を使用）
- ネットワークアクセス（J-Quants / OpenAI / RSS ソース）
- 推奨パッケージ（本リポジトリ内で使用）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリのみで動作する部分も多い）

---

## セットアップ手順

1. リポジトリをクローン / ソースを取得

   git clone <リポジトリURL>
   cd <repo>

2. 仮想環境作成（推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール

   pip install -e .
   pip install duckdb openai defusedxml

   （プロジェクトに extras_require が定義されていればそれを使うか、必要なパッケージを個別に追加してください）

4. 環境変数 / .env ファイルの準備

   プロジェクトルートに `.env`（および環境ごとの `.env.local`）を置くと、自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。

   必要な環境変数（代表例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / regime_detector を使う場合）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注連携を行う場合）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: SQLite モニタリング DB（デフォルト data/monitoring.db）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
   - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

   .env 例（簡易）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡単な例）

> ここでは Python REPL やスクリプトから各ユーティリティを呼び出す例を示します。

1. DuckDB 接続の作成

   from datetime import date
   import duckdb
   conn = duckdb.connect("data/kabusys.duckdb")  # デフォルトパスに合わせる

2. 日次 ETL を実行（J-Quants トークンは settings で取得するか id_token を渡す）

   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn, target_date=date(2026,3,20))
   print(result.to_dict())

3. ニュース NLP（銘柄別スコア）を生成

   from kabusys.ai.news_nlp import score_news
   from datetime import date
   n = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY が環境変数に必要
   print("scored:", n)

4. 市場レジーム判定を実行

   from kabusys.ai.regime_detector import score_regime
   from datetime import date
   score_regime(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY が必要

5. 研究用関数（例: モメンタム計算）

   from kabusys.research.factor_research import calc_momentum
   from datetime import date
   results = calc_momentum(conn, target_date=date(2026,3,20))
   # results は [{"date": ..., "code": "XXXX", "mom_1m": ..., ...}, ...]

6. 監査ログ用 DB 初期化

   from kabusys.data.audit import init_audit_db
   conn_audit = init_audit_db("data/audit.duckdb")

---

## 実運用上の注意点

- Look-ahead バイアス回避
  - 内部実装では datetime.today() / date.today() を直接参照する処理を避け、target_date を明示的に与えることでバックテストでも安全に使えるよう設計されています。
- API のレート制御 / リトライ
  - J-Quants クライアントは 120 req/min のレート制御とリトライを実装しています。OpenAI 呼び出しもリトライや 5xx 対応ロジックがありますが、料金・レートは利用者側で注意してください。
- フェイルセーフ
  - LLM 呼び出しや外部 API 失敗時は、スコアのフォールバック（0.0）や処理続行を行う箇所が多く設計されています（ログに注意）。
- 環境切替
  - KABUSYS_ENV により挙動を環境区分（development / paper_trading / live）で分けられます。実トレード時は is_live 等で安全チェックを実装してください。

---

## ディレクトリ構成（主なファイルと役割）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み・設定管理（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュース記事を OpenAI でスコアリングして ai_scores に書き込むロジック
    - regime_detector.py
      - ETF 1321 の MA とマクロニュース（LLM）を合成して市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py
      - JPX カレンダー管理・営業日判定ユーティリティ
    - etl.py
      - pipeline の再エクスポート（ETLResult）
    - pipeline.py
      - 日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
    - stats.py
      - z-score 正規化など統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付不整合）
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）スキーマ初期化
    - jquants_client.py
      - J-Quants API クライアント（取得・認証・保存関数）
    - news_collector.py
      - RSS 収集、前処理、raw_news へ保存
  - research/
    - __init__.py
    - factor_research.py
      - momentum, value, volatility 等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー、ランク関数

---

## よく使う API の一覧（短記）

- 設定
  - from kabusys.config import settings
    - settings.jquants_refresh_token, settings.env, settings.duckdb_path など
- ETL / データ
  - from kabusys.data.pipeline import run_daily_etl, ETLResult
  - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
- ニュース / NLP / LLM
  - from kabusys.ai.news_nlp import score_news
  - from kabusys.ai.regime_detector import score_regime
- 監査ログ
  - from kabusys.data.audit import init_audit_db, init_audit_schema
- 研究用
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary, rank

---

## 追加情報 / 貢献

- テストや CI、詳細な設定例（.env.example）や運用手順書は別途整備を推奨します。
- 機密情報（API キー等）は絶対に公開リポジトリに置かないでください。
- バグ報告・改善提案は Issue を立ててください。

---

README はここまでです。必要であれば以下を追記します：
- .env.example のサンプル
- より詳細な実行例（スクリプト / systemd / Airflow / cron などの運用例）
- 開発用ワークフロー（テスト・フォーマット・静的解析）