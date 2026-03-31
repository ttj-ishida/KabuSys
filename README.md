# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。ETL（J-Quants からのデータ取り込み）、ニュースセンチメント分析（OpenAI）、市場レジーム判定、研究用ファクター計算、データ品質チェック、監査ログ（発注→約定のトレーサビリティ）などを提供します。

---

## プロジェクト概要

KabuSys は日本株運用のための内部ライブラリ群です。主に以下を目的としています。

- J-Quants API からの株価・財務・カレンダーの差分 ETL と DuckDB への保存（冪等）
- RSS ニュース収集と OpenAI を用いた銘柄別センチメント算出（ai_scores への保存）
- マクロニュース + ETF（1321）200日移動平均乖離を用いた日次市場レジーム判定（bull/neutral/bear）
- ファクター計算・特徴量探索（リサーチ用途）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注〜約定までの監査ログテーブル初期化ユーティリティ（DuckDB）
- 環境変数管理（.env の自動読み込み等）

設計方針として、バックテストにおけるルックアヘッドバイアスを避けるため「現在時刻を直接参照しない」「DB クエリで date < target_date のように排他条件を付ける」等の配慮がなされています。

---

## 主な機能一覧

- データ取得 / ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）：fetch/save 関数、認証（get_id_token）、ページネーション、レート制御、リトライ
- ニュース関連（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、前処理、raw_news へ冪等保存
- ニュース NLP（kabusys.ai.news_nlp）
  - calc_news_window, score_news（OpenAI を使った銘柄別センチメント）
- 市場レジーム判定（kabusys.ai.regime_detector）
  - score_regime（ETF 1321 の MA とマクロニュースの LLM 評価を合成）
- 研究用（kabusys.research）
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / zscore_normalize 等
- データ品質（kabusys.data.quality）
  - 欠損チェック、スパイク検出、重複検査、日付整合性チェック、run_all_checks
- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- 監査ログ（kabusys.data.audit）
  - init_audit_schema / init_audit_db（発注・約定の監査テーブルを初期化）

---

## セットアップ手順

以下は開発マシンでのローカルセットアップ例です。

1. Python 環境準備（推奨: venv）

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

2. 依存ライブラリをインストール

   必要な主要パッケージ（プロジェクトの setup.py/pyproject.toml がある場合はそれを利用してください）。最低限必要なものの例:

   ```bash
   pip install duckdb openai defusedxml
   ```

   （実運用では HTTP クライアントや監視用パッケージ等が追加で必要になる場合があります）

3. 開発中に editable install（任意）

   プロジェクトルートで:

   ```bash
   pip install -e .
   ```

4. 環境変数の設定

   プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただしテスト等で無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`）。

   必須環境変数（主要）:

   - JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
   - KABU_API_PASSWORD — kabuステーション API パスワード
   - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID — Slack チャネル ID
   - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 実行時に必要）
   - （任意）DUCKDB_PATH / SQLITE_PATH / KABUSYS_ENV / LOG_LEVEL

   例: .env（簡易）

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡単な例）

以下はライブラリ関数を直接呼び出す簡易例です。DuckDB 接続は duckdb.connect(<path>) で取得します。

- 日次 ETL の実行

  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア付与（score_news）

  score_news は OpenAI API キーが必要です（api_key 引数または環境変数 OPENAI_API_KEY）。

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {n_written}")
  ```

- 市場レジーム判定（score_regime）

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化

  監査用 DB（DuckDB ファイル）を初期化して接続を得る:

  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/monitoring_audit.duckdb")
  # conn を使って order_requests / signal_events / executions を操作できます
  ```

- カレンダーの夜間更新ジョブ（calendar_update_job）

  ```python
  from kabusys.data.calendar_management import calendar_update_job
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  saved = calendar_update_job(conn, lookahead_days=90)
  print("saved:", saved)
  ```

---

## 環境変数（主な一覧）

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須: ETL 実行時）
- OPENAI_API_KEY — OpenAI API キー（必須: LLM を呼ぶ処理）
- KABU_API_PASSWORD — kabuAPI パスワード（注文実行等）
- KABU_API_BASE_URL — (任意) kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite path（デフォルト: data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動読み込みを無効化

設定値は kabusys.config.settings からプロパティとして参照できます。

---

## ディレクトリ構成

主要ファイル・モジュール構成（抜粋）:

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
      - jquants_client.py
      - pipeline.py
      - etl.py
      - news_collector.py
      - calendar_management.py
      - stats.py
      - quality.py
      - audit.py
      - audit_db 初期化ユーティリティ等
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - (その他: strategy, execution, monitoring 等のパッケージ名が __all__ に列挙されていますが、ここに含まれるコードベースに依存します)

上記のファイルは主な公開 API と内部ユーティリティを含みます。詳細は各モジュール内の docstring を参照してください。

---

## 注意事項 / 運用上の注意

- OpenAI API 呼び出し・外部 API 呼び出しは課金やレート制限の対象になります。テストではモック化（unittest.mock.patch）することを推奨します。
- ETL や LLM 処理は外部サービス依存のためエラーが発生し得ます。ライブラリはフェイルセーフ（API 失敗時はスコア 0.0 など）を備えていますが、運用では監視・アラートを設定してください。
- データベーススキーマの変更や DuckDB バージョン差異で executemany の挙動等が影響を受ける可能性があります。運用前にバックアップとスキーマ初期化手順を確認してください。
- 監査ログは削除を想定していません（永続化してトレーサビリティを担保）。

---

必要であれば、セットアップの自動化（docker-compose、Makefile、CI 設定）や .env.example のテンプレート、実運用向けのログ設定・監視ドキュメントも作成できます。どの情報を追加したいか教えてください。