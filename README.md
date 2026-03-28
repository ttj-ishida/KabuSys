# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI）、リサーチ用ファクター計算、監査ログ（トレーサビリティ）、カレンダー管理など、自律売買システムのバックエンド処理群を提供します。

---

## 主な特徴（概要）

- J-Quants API を用いた差分 ETL（株価・財務・上場情報・市場カレンダー）
- DuckDB を中心としたローカルデータベース保存（冪等保存）
- ニュース収集（RSS）と前処理、銘柄紐付け
- OpenAI（gpt-4o-mini 等）によるニュースセンチメント評価（銘柄ごとの ai_score、マクロセンチメント）
- 市場レジーム判定（ETF 1321 の MA200 乖離とマクロセンチメントを合成）
- リサーチ用ファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ初期化ユーティリティ
- 自動環境変数読み込み（プロジェクトルートの .env / .env.local を参照、無効化可）

---

## 機能一覧（モジュール別）

- kabusys.config
  - 環境変数管理、.env 自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - settings オブジェクト（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_*, DUCKDB_PATH など）

- kabusys.data
  - pipeline: 日次 ETL 実行（run_daily_etl 等）
  - jquants_client: J-Quants API クライアント（取得・保存・認証・ページネーション・レート制御）
  - news_collector: RSS 取得・前処理・raw_news 保存（SSRF/圧縮/XML 脆弱性対策等）
  - calendar_management: JPX カレンダー管理、営業日判定・next/prev/get_trading_days、calendar_update_job
  - quality: データ品質チェック（missing_data, spike, duplicates, date_consistency）
  - stats: zscore_normalize 等の汎用統計ユーティリティ
  - audit: 監査ログスキーマ定義と初期化（init_audit_schema / init_audit_db）

- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント算出・ai_scores への書込
  - regime_detector.score_regime: ETF MA200 とマクロセンチメントを合成して market_regime を作成

- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize を利用して正規化など

---

## 必要な環境変数（主なもの）

最低限プロジェクトで使用される主要な環境変数（.env に記載する想定）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知に使用（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）
- OPENAI_API_KEY — OpenAI 呼び出し時の API キー（news_nlp / regime_detector の引数でも注入可）
- DUCKDB_PATH — デフォルト DB パス（例: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（例: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" / "paper_trading" / "live")
- LOG_LEVEL — ログレベル ("DEBUG" / "INFO" / ...)

参考: config.Settings にプロパティ定義があり、必須変数は取得時に例外を投げます。

---

## セットアップ手順（開発用）

1. リポジトリをクローン／チェックアウト
   - 例: git clone <repo-url>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. パッケージのインストール
   - pip install -e . 
     （プロジェクトが setuptools/pyproject を備えている前提。requirements.txt がある場合は pip install -r requirements.txt）
   - 主な依存例:
     - duckdb
     - openai (または openai の新 SDK を使用する場合はそれに合わせる)
     - defusedxml

   ※ 実際の requirements は配布パッケージに合わせてください。

4. 環境変数 / .env の準備
   - プロジェクトルートに .env を作成（.env.example を参考に）
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
     KABU_API_PASSWORD="your_kabu_password"
     SLACK_BOT_TOKEN="xoxb-..."
     SLACK_CHANNEL_ID="C01234567"
     OPENAI_API_KEY="sk-..."
     DUCKDB_PATH="data/kabusys.duckdb"
     KABUSYS_ENV="development"

   - 自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データベース用ディレクトリを作成（必要に応じて）
   - mkdir -p data

---

## 使い方（基本的なコード例）

以下の例は Python REPL やスクリプト内で利用する想定です。すべての操作は DuckDB 接続（duckdb.connect(...)）を渡して実行します。

- DuckDB 接続の作成（設定されたパスを使用）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定（省略時は today）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄ごと）取得
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境変数で設定しておく
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定（マクロ＋MA200）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログスキーマ初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # この接続を発注/監査処理で使用します
  ```

- 市場カレンダー更新ジョブ（夜間バッチ想定）
  ```python
  from kabusys.data.calendar_management import calendar_update_job

  saved = calendar_update_job(conn)
  print(f"saved calendar records: {saved}")
  ```

- リサーチ: モメンタム計算例
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # records: list[dict] with keys: date, code, mom_1m, mom_3m, mom_6m, ma200_dev
  ```

注意点:
- AI 関連関数（score_news, score_regime）は api_key を引数で受け取れます。None の場合は環境変数 OPENAI_API_KEY を参照します。
- DuckDB への書き込みは冪等設計（ON CONFLICT / DELETE→INSERT 戦略）になっています。
- 多くの関数はルックアヘッドバイアスを避ける設計になっており、target_date を明示的に渡すことを推奨します。

---

## ディレクトリ構成 （主要ファイル）

以下はソースツリー（src/kabusys）に含まれる主なファイル／モジュールの一覧です。

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
    - etl.py
    - pipeline.py
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
    - (その他: jquants クライアント周辺ユーティリティ)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/...（zscore_normalize は data.stats に依存）
  - (将来的に strategy, execution, monitoring パッケージが想定されています)

---

## 設計上の注意・運用メモ

- Look-ahead バイアス対策:
  - AI/ETL/リサーチモジュールは target_date を明示して、将来データを使わない設計になっています。
  - prices_daily 等のクエリでは date < target_date（排他条件）や LEAD/LAG を適切に使っています。

- 冪等性・トランザクション:
  - ETL の保存関数は ON CONFLICT DO UPDATE 等で冪等に実装。
  - 複数テーブルの更新は必要箇所で BEGIN/COMMIT/ROLLBACK を使い、エラー時は部分ロールバックを試みます。

- API レート制御・リトライ:
  - J-Quants クライアントは固定間隔のスロットリングと指数バックオフを実装。
  - OpenAI 呼び出しはリトライ（429/ネットワーク/5xx に対して）を備えます。

- セキュリティ:
  - news_collector は SSRF 対策、XML の defusedxml 使用、gzip 上限チェック、トラッキングパラメータ除去等を実装。
  - .env の取り扱い（機密情報）には注意してください。

---

## 追加情報・拡張

- strategy / execution / monitoring 等のパッケージは __all__ に想定されており、将来的に注文実行ロジックや監視アラート機能が追加される想定です。
- 実運用で本番口座を接続する場合は十分なバックテスト・リスク制御（注文の二重送信防止、発注上限、手動停止機構など）を実装してください。

---

もし README に追加したい具体的な内容（例: requirements.txt の正確な依存、CI/CD 手順、データスキーマ定義の詳細、運用 runbook など）があれば教えてください。必要に応じてサンプル .env.example や利用例スクリプトも作成します。