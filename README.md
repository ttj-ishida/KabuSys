# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ集です。DuckDB ベースのデータレイヤ、J-Quants からの ETL、ニュースの NLP スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログスキーマなどを提供します。

---

## 概要

KabuSys は以下の目的で設計された Python パッケージです。

- J-Quants API から株価・財務・マーケットカレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS ベースのニュース収集と記事前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント解析・銘柄別 AI スコア付与
- ETF（1321）200 日移動平均乖離＋マクロニュースで市場レジーム（bull / neutral / bear）判定
- 研究用のファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 発注〜約定までのトレースを可能にする監査ログスキーマ（DuckDB）

設計上、バックテスト等でのルックアヘッドバイアスを避けるために `date.today()` や `datetime.today()` を無差別に参照せず、ETL/スコアは明示的なターゲット日を受け取る形になっています。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（認証・ページネーション・リトライ・保存関数）
  - カレンダー管理（営業日判定・next/prev_trading_day 等）
  - ニュース収集（RSS 正規化・SSRF 対策・raw_news 保存）
  - データ品質チェック（missing / duplicates / spike / date consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize 等）
- ai/
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores に書き込む
  - regime_detector.score_regime: ETF + マクロニュースで日次市場レジームを判定
  - OpenAI API 呼び出しは retry / backoff / JSON mode を用いた堅牢な実装
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（forward returns, IC, summary, rank）
- config.py
  - .env 自動読み込み（プロジェクトルート検出、.env / .env.local）
  - 必須環境変数の集約（settings オブジェクト）

---

## セットアップ手順（開発環境向け）

前提: Python 3.9+ を想定（typing 機能を利用）。プロジェクトはソースが `src/` 配下にある構成です。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存ライブラリをインストール（最小セット）
   ```
   pip install duckdb openai defusedxml
   ```
   ※ 実際のプロジェクトでは追加の依存（例: slack SDK 等）が必要になる場合があります。パッケージ化済みなら `pip install -e .` や `requirements.txt` を利用してください。

4. 環境変数の準備
   - プロジェクトルートに `.env`（および任意で `.env.local`）を配置すると、パッケージ読み込み時に自動で取り込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化できます）。
   - 必須環境変数（少なくともローカルで実行する場合）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注機能を使う場合）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知を使う場合
     - OPENAI_API_KEY: OpenAI を使う AI 処理を行う場合
   - データベースパス（任意・デフォルトあり）:
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
   - システム設定:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. データベース初期化（監査スキーマ）
   Python REPL / スクリプトで:
   ```python
   import duckdb
   from kabusys.data.audit import init_audit_schema, init_audit_db
   conn = duckdb.connect("data/kabusys.duckdb")
   init_audit_schema(conn)  # 既存接続へテーブルを追加する場合
   # または監査専用DBを作る:
   # conn2 = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（簡単な例）

以下は代表的な操作例です。実運用ではログ・例外処理・ジョブスケジューラ（cron/airflow 等）と組み合わせてください。

- ETL（1日分）を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの AI スコア付け（OpenAI API が必要）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # api_key を明示するか環境変数 OPENAI_API_KEY を設定
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("written:", n_written)
  ```

- 市場レジーム判定（1321 + マクロニュース）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（研究用途）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  ```

- 監査 DB の初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

---

## 主要モジュールとディレクトリ構成

パッケージは `src/kabusys` 配下に配置されています。代表的な構成:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースの AI スコアリング（score_news）
    - regime_detector.py      — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（fetch / save）
    - pipeline.py             — ETL パイプライン（run_daily_etl など）
    - etl.py                  — ETLResult の再エクスポート
    - news_collector.py       — RSS 収集 / 前処理 / raw_news 保存
    - calendar_management.py  — 市場カレンダーと営業日ユーティリティ
    - quality.py              — データ品質チェック
    - stats.py                — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                — 監査ログスキーマ初期化・監査DBヘルパー
  - research/
    - __init__.py
    - factor_research.py      — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー
  - (その他)                  — strategy / execution / monitoring 等の名前は __all__ に含まれるが、このコードベースでは data/research/ai を中心に実装

各モジュールは DuckDB 接続オブジェクトを受け取り SQL と Python を組み合わせて処理します。外部 API 呼び出し（J-Quants / OpenAI）やファイル I/O は明示的に行われ、エラーハンドリングやリトライ、フェイルセーフが組み込まれています。

---

## 環境変数（主要なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須 for kabu APIs) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI 呼び出しに利用（score_news / regime_detector）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — development | paper_trading | live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

設定は `kabusys.config.settings` 経由で参照できます（プロパティでバリデーション済み）。

自動 .env ロードはパッケージ読み込み時にプロジェクトルート（.git または pyproject.toml の存在）を探索して `.env` / `.env.local` を取り込みます。テスト等で自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 運用 / トラブルシューティング

- OpenAI / J-Quants の API 呼び出しにはそれぞれ API キーが必要です。エラー時はログに WARN/ERROR が出力され、AI スコア処理は失敗してもシステム全体の実行を止めないように設計されています（フェイルセーフとしてスコア 0 やスキップで継続）。
- DuckDB の executemany におけるバージョン差異（空リスト不可等）に配慮しているため、古い DuckDB でも動作するよう設計していますが、可能であれば最新安定版を利用してください。
- RSS 取得は SSRF 対策やレスポンスサイズ制限、gzip 解凍後のサイズ検査等を行っています。外部フィードを追加する際は `DEFAULT_RSS_SOURCES` を参照のうえ安全な URL を指定してください。
- データ品質チェック結果は `kabusys.data.quality.QualityIssue` のリストとして返ります。ETL 実行結果（ETLResult）は `to_dict()` で監査ログに適した形式に変換できます。

---

## 開発・テスト

- モジュール単位で外部 API 呼び出し関数（例: news_nlp._call_openai_api や news_collector._urlopen）をモック可能なように設計されています。単体テスト時はモックして外部依存を切り離してください。
- 自動 .env ロードを無効化したいテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

必要があれば README に含める実行例（systemd / cron / Airflow ジョブ定義）、より詳しい設定例、スキーマ定義一覧、依存パッケージの pinned requirements 等を追加できます。どの情報を優先的に追記しますか？