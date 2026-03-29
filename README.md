# KabuSys

日本株向けのデータ基盤・研究・自動売買補助ライブラリです。  
DuckDB を用いたデータストア、J-Quants/API クライアント、ニュース収集・NLP 統合、ファクター計算、ETL パイプライン、監査ログスキーマなどを提供します。

---

## プロジェクト概要

KabuSys は以下の機能を組み合わせて、日本株の自動売買システムの土台を提供します。

- J-Quants API からの株価・財務・カレンダー取得（レートリミット・リトライ・トークンリフレッシュ対応）
- DuckDB を用いた永続化（冪等保存）
- ニュース収集（RSS）と前処理、記事の銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄別 ai_score、マクロセンチメント）
- 市場レジーム判定（ETF MA + マクロセンチメントを合成）
- 研究系ユーティリティ（ファクター算出、将来リターン、IC、Zスコア正規化 等）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレース可能なスキーマ）

設計上のキーワードは「冪等性」「ルックアヘッドバイアス防止」「フェイルセーフ（API 失敗時はスキップして継続）」です。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API の取得・保存（daily_quotes, financials, market_calendar, listed info）
  - rate limiter、リトライ、id_token 自動リフレッシュ

- data/pipeline.py
  - run_daily_etl：市場カレンダー → 株価 → 財務 → 品質チェックの包括的 ETL

- data/news_collector.py
  - RSS フィード取得、URL 正規化、記事ID生成、raw_news へ冪等保存

- ai/news_nlp.py
  - 銘柄単位のニュースをまとめて LLM に投げ、銘柄別センチメントを ai_scores テーブルへ書込

- ai/regime_detector.py
  - ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成して market_regime テーブルへ書込

- research/
  - calc_momentum, calc_value, calc_volatility: ファクター算出
  - calc_forward_returns, calc_ic, factor_summary, rank: 研究用ユーティリティ

- data/quality.py
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks

- data/audit.py
  - 監査ログテーブル定義／初期化（signal_events / order_requests / executions）

- config.py
  - .env 自動ロード（.env, .env.local）、必須環境変数のラッパー settings

---

## セットアップ手順

前提
- Python 3.10+（モジュール内で | 型ヒントを使用しているため）
- ネットワークアクセス（J-Quants, OpenAI, RSS 等）

1. リポジトリを取得し、開発環境へインストール（例: 仮想環境推奨）

   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install --upgrade pip
   pip install duckdb openai defusedxml
   # または開発用 requirements があればそれを使う
   ```

   ※ 必要に応じて他の依存（requests 等）がある場合は追加してください。

2. 環境変数を設定

   プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   必須環境変数の例（.env）:

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   OPENAI_API_KEY=sk-...
   ```

   data データベースのパス等は任意で指定できます（デフォルトは `data/kabusys.duckdb` 等）。`DUCKDB_PATH` / `SQLITE_PATH` を使えます。

3. データディレクトリ（必要なら）を作成

   ```
   mkdir -p data
   ```

4. DuckDB 用テーブル初期化や監査DB初期化はアプリケーション内で行います（次節 使い方 を参照）。

---

## 使い方（主要な API の例）

以下は簡単な Python スニペット例です。実行はプロジェクトをインストールした仮想環境内で行ってください。

- DuckDB に接続して日次 ETL を実行する

  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- OpenAI を使ってニューススコアを生成（ai/news_nlp）

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026,3,20))
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジームスコアを計算して保存（ai/regime_detector）

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログ DB を初期化する

  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/kabusys_audit.duckdb")
  # conn を使って order/signals の操作や照会が可能
  ```

- 設定の参照例

  ```python
  from kabusys.config import settings
  print(settings.duckdb_path, settings.env, settings.log_level)
  ```

注意点：
- LLM 系（score_news/score_regime）は OPENAI_API_KEY が必要です。引数で直接渡すこともできます（api_key=...）。
- J-Quants API 利用には JQUANTS_REFRESH_TOKEN を設定してください（get_id_token 内で使用）。
- ETL やニューススコアはルックアヘッドバイアス対策（target_date 未満のデータのみ使用）を実装していますので、バックテストで再現性を担保できます。

---

## .env / 環境変数

自動読み込みされる環境変数（主要なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 BOT トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（LLM 関連機能で必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 実行環境 ('development', 'paper_trading', 'live')（デフォルト 'development'）
- LOG_LEVEL: ログレベル ('DEBUG','INFO',...)（デフォルト 'INFO'）

.env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
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
    - etl.py
    - quality.py
    - stats.py
    - calendar_management.py
    - news_collector.py
    - audit.py
    - (その他: migration / schema 初期化 等を想定)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/  (プロジェクト内に監視関連モジュールが入る想定)
  - strategy/    (戦略ロジックやモデルが入る想定)
  - execution/   (発注・接続ラッパー等)
  - monitoring/  (監視用ユーティリティ)

ファイルごとの責務は上の「主な機能一覧」およびソース内ドキュメントコメントを参照してください。

---

## 運用メモ / トラブルシューティング

- DuckDB の接続は複数プロセスで同時書き込みすると競合する可能性があります。バッチ実行や CRON での定期処理時は排他やロック設計に注意してください。
- J-Quants API のレートリミットは 120 req/min に設定されています（モジュール内で制御）。大量データ取得時は注意。
- OpenAI 呼び出しはリトライロジックを備えていますが、API キーの制限やコストに注意してください。
- テスト時などで .env 自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- settings.env には 'development' / 'paper_trading' / 'live' のいずれかを設定し、フラグで挙動を切り替えます（is_live, is_paper, is_dev）。

---

## 開発・貢献

- ソース内に詳細ドキュメント（関数・設計方針コメント）が多く含まれています。新機能追加やバグ修正時は各モジュールの設計方針に従ってください（特に「ルックアヘッドバイアス防止」「冪等性」）。
- 単体テスト・統合テストを追加する際は、外部 API 呼び出し（OpenAI/J-Quants/HTTP）をモックして再現性を確保してください。

---

README に書かれている使い方は主要なエントリポイントの最小例です。実運用ではログ設定、エラーハンドリング、ジョブスケジューリング（cron / Airflow 等）、バックテスト・ポジション管理・リスク管理ロジックの実装が必要です。必要であれば、特定のモジュールの詳細ドキュメントやサンプルコード（ETL の定期実行、ニュース収集ジョブ、スコアの監視・Slack 通知等）を作成します。どういった例が必要か教えてください。