# KabuSys

日本株向けのデータプラットフォーム / 研究・自動売買補助ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を利用したセンチメント）、ファクター計算、監査ログ（発注/約定トレーサビリティ）などを備え、研究（research）と運用（execution / monitoring）で利用するためのユーティリティ群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の主要機能を提供します。

- J-Quants API を用いた差分 ETL（株価 / 財務 / マーケットカレンダー）
- ニュース収集（RSS）・前処理・銘柄紐付け
- OpenAI（gpt-4o-mini 等）を利用したニュースセンチメント評価（銘柄別 ai_score、マクロセンチメント）
- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントの合成）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ（Zスコア、IC 等）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログスキーマの初期化（signal → order_request → execution の完全トレーサビリティ）
- 設定管理（.env 自動読み込み、環境変数ベース）

設計上の特徴:
- ルックアヘッドバイアスを避けるため、内部で date.today() 等に依存しない設計（一貫して target_date を引数で受ける）
- DuckDB をデータ格納先として想定
- OpenAI / J-Quants / RSS など外部接続に対する堅牢なリトライ・フェイルセーフロジック
- 冪等的な DB 保存（ON CONFLICT / upsert パターン）

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数、ID トークン自動更新、レートリミット管理）
  - カレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュース収集（RSS を安全に取得、前処理、raw_news への保存）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログ初期化ユーティリティ（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news(conn, target_date, api_key=None): 銘柄ごとニュースセンチメントを ai_scores に書き込み
  - regime_detector.score_regime(conn, target_date, api_key=None): ETF 200日 MA とマクロセンチメントから市場レジームを判定、market_regime に書き込み
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索・評価（calc_forward_returns, calc_ic, factor_summary, rank）

---

## セットアップ手順（開発用・最小）

以下はローカル開発 / 実行のための基本手順です。プロジェクトに依存するパッケージは実際の pyproject.toml / requirements.txt を参照してください。ここでは最低限必要な外部ライブラリを例示します。

1. Python 環境を作成（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   ※ 実際の依存関係はプロジェクト設定に合わせてください。

3. リポジトリ配置後、.env ファイルを作成
   - プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます（config.py の自動読み込み機能）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 必須環境変数（例）
   以下は config.Settings で参照される主要なキーです。必須のものは README のように明示します。

   必須:
   - JQUANTS_REFRESH_TOKEN       （J-Quants 認証用リフレッシュトークン）
   - SLACK_BOT_TOKEN             （Slack 通知に使用）
   - SLACK_CHANNEL_ID            （通知先チャンネル）
   - KABU_API_PASSWORD           （kabuステーション API 用パスワード）

   任意 / デフォルトあり:
   - KABUSYS_ENV                 (development | paper_trading | live) 既定: development
   - LOG_LEVEL                   (DEBUG/INFO/...)
   - KABU_API_BASE_URL           既定: http://localhost:18080/kabusapi
   - DUCKDB_PATH                 既定: data/kabusys.duckdb
   - SQLITE_PATH                 既定: data/monitoring.db
   - PID_FILE_PATH               既定: data/execution.pid
   - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

   OpenAI:
   - OPENAI_API_KEY              （news_nlp / regime_detector が使用。score_news/score_regime に api_key を直接渡すことも可）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_kabu_password
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. データディレクトリを作成（必要に応じて）
   - mkdir -p data

---

## 使い方（簡易ガイド）

以下は主要機能を Python REPL またはスクリプトから利用する例です。DuckDB 接続を渡して操作します。

- DuckDB 接続（既定のパスを使用）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（run_daily_etl）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- 単体の株価 ETL（差分）
  ```python
  from kabusys.data.pipeline import run_prices_etl
  fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
  ```

- ニュースのスコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY、または引数で指定）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  count = score_news(conn, target_date=date(2026,3,20))
  print("scored", count)
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログ DB の初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # conn_audit を用いて監査テーブルにアクセス可能
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, target_date=date(2026,3,20))
  ```

注意点:
- OpenAI 呼び出しは外部 API に依存するため、API キーとネットワークが必要です。失敗時はフェイルセーフ（多くの箇所で 0.0 やスキップ）になっていますが、ログを確認してください。
- J-Quants API 呼び出しはレート制限に従ってスロットリングされます。

---

## ディレクトリ構成

主要なファイル・モジュール構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                          -- 環境変数・設定管理（.env 自動読み込み）
    - ai/
      - __init__.py
      - news_nlp.py                      -- ニュース NLP（score_news）
      - regime_detector.py               -- 市場レジーム判定（score_regime）
    - data/
      - __init__.py
      - pipeline.py                      -- ETL パイプライン（run_daily_etl 等）
      - jquants_client.py                -- J-Quants REST クライアント + 保存ロジック
      - news_collector.py                -- RSS ニュース収集・前処理
      - calendar_management.py           -- マーケットカレンダー管理（営業日判定等）
      - quality.py                       -- データ品質チェック
      - stats.py                         -- 統計ユーティリティ（zscore_normalize）
      - audit.py                         -- 監査ログスキーマ初期化
      - etl.py                           -- ETLResult 再エクスポート
    - research/
      - __init__.py
      - factor_research.py               -- 各種ファクター計算
      - feature_exploration.py           -- 将来リターン・IC・サマリー等
    - research/*

その他、execution / monitoring / strategy 等のパッケージは __all__ に含める前提ですが、ここでは data/ ai/ research が中心です。

---

## 設定・運用上の注意

- .env の自動読み込み
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）から .env/.env.local を読み込みます。
  - 優先順位: OS 環境変数 > .env.local > .env
  - テスト等で自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- セキュリティ
  - news_collector は SSRF 対策やレスポンスサイズ制限を実装していますが、運用時は RSS ソースの管理に注意してください。
  - OpenAI・J-Quants・kabu ステーションの秘密情報は .env に保存せず安全な秘匿方法（KMS/シークレットストア等）を推奨します。

- ログ
  - config.Settings.log_level でログレベルを制御できます（LOG_LEVEL 環境変数）。

- テスト
  - OpenAI 呼び出し等はテスト時にモック化できる設計（モジュール内の _call_openai_api 等を patch する）。

---

## 貢献・開発

- バグ報告・機能提案は Issue を立ててください。
- コードを変更する際はユニットテストと簡単な統合テストを追加してください（外部 API 呼び出しはモック推奨）。

---

以上が README の概要です。実行時の具体的なコマンドや CI 設定、依存パッケージの固定などはプロジェクトの pyproject.toml / requirements.txt、CI 設定ファイルに合わせて補足してください。必要であれば README に含める具体的な .env.example や起動スクリプト（systemd / supervisor / cron の例）も作成しますので指示ください。