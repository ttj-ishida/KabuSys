# KabuSys

日本株向けの自動売買システムのライブラリ群。データの取得・ETL、ニュースの NLP（LLM ベース）による銘柄スコアリング、マーケットレジーム判定、リサーチ用ファクター計算、監査ログ（発注→約定のトレーサビリティ）などを提供します。

主な目的は「データプラットフォーム + 研究（リサーチ） + AI 補助による意思決定 + 監査・実行管理」を一貫して行うための共通ユーティリティ群の提供です。

---

## 機能一覧（概要）

- データ取得・ETL
  - J-Quants API から株価（日足）、財務、カレンダーを差分取得・保存（duckdb 保存、冪等）
  - ETL パイプライン（run_daily_etl）でカレンダー→株価→財務→品質チェックを連続実行
- データ品質チェック
  - 欠損（OHLC）、重複、将来日付、スパイク（急騰/急落）などの検出
- ニュース収集・前処理
  - RSS フィードの取得（SSRF 対策、トラッキング除去）、raw_news への保存補助
- ニュース NLP（LLM）
  - 銘柄ごとのニュースを統合して gpt-4o-mini（JSON mode）でセンチメントを算出し ai_scores へ保存（score_news）
  - マクロニュース + ETF（1321）の MA200 乖離を合成して市場レジームを判定（score_regime）
- リサーチ用ファクター
  - Momentum / Volatility / Value 系ファクター計算（prices_daily / raw_financials 参照）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブル初期化・管理（init_audit_schema / init_audit_db）
- J-Quants クライアント
  - レート制御・再試行・トークン自動リフレッシュ付きの HTTP クライアント
- 設定管理
  - .env（.env.local）や OS 環境変数から設定をロード（自動ロードは無効化可）

---

## 必要条件

- Python 3.10+
  - （ソース内で PEP 604 の型注釈（A | B）や型ヒントを使用）
- 主な依存パッケージ
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリ: urllib, logging, datetime, json など

（プロジェクトに requirements.txt がない場合は上記を個別にインストールしてください）

---

## セットアップ手順

1. リポジトリを取得
   - git clone などでソースを取得

2. 仮想環境（任意）
   - python -m venv .venv
   - source .venv/bin/activate

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （パッケージはプロジェクト運用ポリシーに合わせて requirements.txt / constraints を用意してください）

4. パッケージをインストール（開発用）
   - pip install -e .

5. 環境変数の準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数 > .env.local > .env の優先順）
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）

6. 必要な環境変数（主要）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 等で使用）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注連携がある場合）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知設定（必要に応じて）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視関連
   - KABUSYS_ENV: 環境 ("development", "paper_trading", "live")
   - LOG_LEVEL: "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（代表的な利用例）

以下はライブラリ関数を使う最小限の例です。実行は Python スクリプトや管理用ジョブ（cron / Airflow 等）から行います。

- DuckDB 接続の例
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # conn は上で作成した DuckDB 接続
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（score_news）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY が環境にある前提。api_key 引数で明示も可。
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定（score_regime）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # conn_audit を使って監査テーブルへ書き込み可能
  ```

注意点:
- score_news / score_regime は OpenAI API キー（OPENAI_API_KEY）を必要とします。api_key を関数引数で渡すことも可能です。
- これら AI 関連関数は外部 API 呼び出しを伴うためエラーやレート制限が発生し得ます。ログやリトライ実装が組み込まれていますが、実運用では追加の監視やエラーハンドリングを検討してください。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの `src/kabusys` 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み & Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py
      - score_news(conn, target_date, api_key=None)
      - RSS 時間ウィンドウ計算など
    - regime_detector.py
      - score_regime(conn, target_date, api_key=None)
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント、fetch_* / save_* 関数
    - pipeline.py
      - ETL の主要エントリ: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
      - ETLResult データクラス
    - quality.py
      - データ品質チェック（missing_data / spike / duplicates / date_consistency / run_all_checks）
    - news_collector.py
      - RSS 取得・前処理・記事ID生成（SSRF 対策等）
    - calendar_management.py
      - market_calendar 管理、営業日判定、calendar_update_job
    - stats.py
      - zscore_normalize 等汎用統計ユーティリティ
    - audit.py
      - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
    - etl.py
      - ETLResult を再エクスポート
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum, calc_volatility, calc_value
    - feature_exploration.py
      - calc_forward_returns, calc_ic, factor_summary, rank

---

## 運用上の注意・開発者向けメモ

- 環境ロード:
  - プロジェクトルート上の `.env` と `.env.local` を自動で読み込みます（OS 環境変数を保護するための保護ロジックあり）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し:
  - news_nlp / regime_detector は gpt-4o-mini の JSON mode を想定しています。API レスポンスのパース失敗や API エラー時はフォールバック（スコア 0.0 等）するよう設計されていますが、API の仕様変更に注意してください。
  - テスト時は内部の _call_openai_api をモックして外部呼び出しを避けられるように設計されています。
- J-Quants クライアント:
  - レート制御や 401 リフレッシュ、再試行ロジックが組み込まれています。大量データ取得時のページネーション処理に対応しています。
- DuckDB:
  - 多くの処理が DuckDB 接続を前提としています。DB スキーマは ETL や audit.init で初期化可能。運用時は DB のバックアップや VACUUM などの管理を検討してください。
- テスト:
  - 環境変数の自動ロードを無効にしてからテストを実行する、OpenAI / HTTP 呼び出しをモックする等の方針を推奨します。

---

もし README に入れてほしい追加情報（例: 実行用 CLI、CI 設定、デプロイ手順、サンプル .env.example の全キー一覧、テーブルスキーマ定義の詳細）や、特定モジュールの詳細なドキュメントが必要であれば教えてください。