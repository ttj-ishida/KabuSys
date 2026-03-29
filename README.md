# KabuSys

日本株向けのデータプラットフォーム兼自動売買基盤のライブラリ的コードベースです。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、AI（ニュースセンチメント・市場レジーム判定）、リサーチ用ファクター計算、監査ログ/発注トレーサビリティなどの機能を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュール群を提供します。

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分取得 & DuckDB への永続化（ETL）
- RSS ベースのニュース収集（raw_news テーブル）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント分析と市場レジーム判定
- ファクター計算（モメンタム・ボラティリティ・バリュー等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal / order_request / executions）テーブルと初期化ユーティリティ
- 環境変数管理（.env 自動読み込みの仕組み）

設計上の重要な方針:
- ルックアヘッドバイアスを避ける（date 引数ベース、date.today() を内部で参照しない設計が多い）
- API 呼び出しはリトライ/バックオフやフェイルセーフ（失敗時はスキップまたはデフォルト値）を備える
- DuckDB を中心に SQL を用いた効率的な処理
- API キーや外部接続情報は環境変数で管理

---

## 機能一覧

主要な機能（モジュール別）

- kabusys.config
  - .env 自動ロード（プロジェクトルート検出） / 設定ラッパー（settings）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存関数、認証・レート制御）
  - pipeline: 日次 ETL 実行（run_daily_etl）と個別 ETL（prices / financials / calendar）
  - news_collector: RSS 取得・前処理・raw_news への保存ロジック
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: 市場カレンダー管理 / 営業日判定 / calendar_update_job
  - audit: 監査ログテーブル初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを作成し ai_scores に保存
  - regime_detector.score_regime: ETF(1321) MA とニュースセンチメントを合成して market_regime に保存
- kabusys.research
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- その他
  - ETL 結果データクラス（ETLResult）等

---

## セットアップ手順

前提:
- Python 3.10 以上（型注釈で `X | Y` を使用しているため）
- Git 等でプロジェクトをクローンした状態を想定

1. リポジトリをクローン（省略可）
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・アクティベート（任意だが推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - 最小限の例:
     ```
     pip install duckdb openai defusedxml
     ```
   - もしプロジェクトに `pyproject.toml` / `requirements.txt` があればそれに従ってください。

4. 開発インストール（ソースを編集して使う場合）
   ```
   pip install -e .
   ```

5. 環境変数を用意
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
     - SLACK_BOT_TOKEN=<your_slack_bot_token>
     - SLACK_CHANNEL_ID=<slack_channel_id>
     - KABU_API_PASSWORD=<kabu_api_password>
   - 推奨 / 任意:
     - OPENAI_API_KEY=<your_openai_api_key>  （AI モジュールを使う場合）
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（代表的なユースケース）

以下は Python REPL / スクリプトでの簡単な利用例です。

- DuckDB に接続して日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（AI）を計算して ai_scores に保存
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数か api_key 引数で指定
  n = score_news(conn, target_date=date(2026, 3, 20))
  print("scored:", n)
  ```

- 市場レジームスコアを算出して market_regime に保存
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB を初期化する（別 DB を使う場合）
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")  # 必要なディレクトリは自動作成
  ```

- カレンダー更新ジョブを実行する（JPX カレンダーを取得）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import calendar_update_job

  conn = duckdb.connect("data/kabusys.duckdb")
  saved = calendar_update_job(conn, lookahead_days=90)
  print("saved:", saved)
  ```

ログレベルは環境変数 `LOG_LEVEL` やアプリ側で標準 logging 設定を行って調整してください。

注意:
- AI 系関数は OpenAI API キー（OPENAI_API_KEY）を必要とします。未設定時は ValueError を投げます。
- ETL / 保存処理は DuckDB スキーマ（該当テーブル）存在を前提とします。スキーマ初期化ロジックは別に用意してください（本リポジトリに schema 作成スクリプトがある想定）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                         -- 環境変数 / .env 自動ロード & Settings
    - ai/
      - __init__.py
      - news_nlp.py                     -- ニュースセンチメント計算（score_news）
      - regime_detector.py              -- 市場レジーム判定（score_regime）
    - data/
      - __init__.py
      - jquants_client.py               -- J-Quants API クライアント（fetch / save）
      - pipeline.py                     -- ETL パイプライン（run_daily_etl 等）
      - etl.py                          -- ETLResult の公開
      - news_collector.py               -- RSS 収集・前処理
      - quality.py                      -- 品質チェック
      - calendar_management.py          -- 市場カレンダー管理
      - stats.py                        -- zscore_normalize 等
      - audit.py                        -- 監査ログテーブル定義 / 初期化
    - research/
      - __init__.py
      - factor_research.py              -- calc_momentum / calc_value / calc_volatility
      - feature_exploration.py          -- calc_forward_returns / calc_ic / factor_summary / rank

補足:
- DuckDB をメイン DB として想定（settings.duckdb_path）。監査ログ用に別 DB を切ることも可能。
- OpenAI 呼び出しは gpt-4o-mini を利用する想定（response_format に JSON mode を使用）。

---

## 注意点・運用上のヒント

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テスト時は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化できます。
- J-Quants API はレート制限（120 req/min）を守る実装になっています。複数プロセスで同時に叩く場合は注意してください。
- AI 呼び出し部分は外部 API に依存するため、テストでは該当内部関数をモックする設計になっています（各モジュールに _call_openai_api を設ける等）。
- ETL の処理は部分失敗に耐えるように設計されています。結果は ETLResult に蓄積され、品質チェック結果やエラーは呼び出し元で参照できます。
- DuckDB executemany に関する互換性（空リスト不可等）に配慮した実装が含まれます。

---

必要であれば以下も作成できます:
- .env.example（推奨環境変数のテンプレート）
- スキーマ初期化スクリプト（raw_prices / ai_scores / market_regime 等の DDL）
- サンプルジョブスクリプト（cron / Airflow 用のラッパー）

ご希望があれば README に追記・整形します。