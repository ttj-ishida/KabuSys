# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
市場データの ETL、ニュース収集・NLP、ファクター計算、監査ログ（オーディット）、および市場レジーム判定などを提供します。

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から株価（日足）、財務データ、JPX カレンダーを差分取得して DuckDB に保存
  - 差分更新・バックフィル・品質チェックを含む日次 ETL パイプライン（run_daily_etl）
- ニュース収集・NLP
  - RSS からニュースを収集して raw_news に保存（SSRF / コンテンツ長対策あり）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント（score_news）
- 市場レジーム判定
  - ETF（1321）の 200 日移動平均乖離とマクロニュースセンチメントを合成して日次レジーム判定（score_regime）
- リサーチ・ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー等のユーティリティ
- データ品質チェック
  - 欠損、スパイク（急変）、重複、日付不整合の検出（run_all_checks）
- 監査ログ（Audit）
  - シグナル → 注文要求 → 約定 のトレーサビリティを担保する監査テーブル定義と初期化（init_audit_schema / init_audit_db）
- 設定管理
  - .env / .env.local / OS 環境変数から自動ロード（優先順位あり）。自動ロードは環境変数で無効化可能。

---

## セットアップ手順

1. Python と仮想環境の作成（推奨: Python 3.9+）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell)
   ```

2. 依存ライブラリをインストール（例）
   - 必須パッケージ（代表例）
     - duckdb
     - openai
     - defusedxml
   - requirements.txt がある場合:
     ```bash
     pip install -r requirements.txt
     ```
   - ない場合は個別に:
     ```bash
     pip install duckdb openai defusedxml
     ```

3. リポジトリルートに .env ファイルを作成
   - 自動読み込みの優先順位: OS 環境変数 > .env.local > .env
   - 自動読み込みを無効にする場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必要な環境変数（例）
     ```
     # J-Quants
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

     # OpenAI (score_news / regime_detector 用)
     OPENAI_API_KEY=your_openai_api_key

     # kabu API (証券接続)
     KABU_API_PASSWORD=your_kabu_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi

     # Slack (通知など)
     SLACK_BOT_TOKEN=your_slack_token
     SLACK_CHANNEL_ID=your_slack_channel_id

     # DB パス（任意）
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db

     # 実行環境
     KABUSYS_ENV=development  # development|paper_trading|live
     LOG_LEVEL=INFO
     ```

4. データベース用ディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（簡易例）

※ ここでは Python REPL／スクリプト内での呼び出し例を示します。アプリ／ジョブ化は用途に応じてラップしてください。

- DuckDB 接続の例
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（run_daily_etl）
  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn)  # target_date を指定しなければ今日
  print(result.to_dict())
  ```

- ニューススコア（OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("scored:", n_written)
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB（独立ファイル）を初期化
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- ファクター計算・リサーチユーティリティ
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  recs = calc_momentum(conn, target_date=date(2026,3,20))
  ```

---

## 設定（環境変数の詳細）

主要な必須値:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 利用時に必要）
- KABU_API_PASSWORD: kabuステーション API パスワード（注文連携がある場合）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知を使う場合

任意・デフォルト:
- KABU_API_BASE_URL: デフォルト "http://localhost:18080/kabusapi"
- DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
- SQLITE_PATH: デフォルト "data/monitoring.db"
- KABUSYS_ENV: "development" / "paper_trading" / "live"（デフォルト "development"）
- LOG_LEVEL: "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト "INFO"）

自動 .env ロード:
- リポジトリルート（.git または pyproject.toml を基準）から .env/.env.local を自動読み込みします。
- 無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主要ファイル説明）

（src/kabusys 以下）

- __init__.py
  - パッケージのエクスポート設定（data, strategy, execution, monitoring 等）

- config.py
  - 環境変数の読み込み・設定管理（Settings クラス）

- ai/
  - news_nlp.py: ニュースを OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py: ETF MA とマクロニュースで市場レジーム判定
  - __init__.py: score_news を公開

- data/
  - jquants_client.py: J-Quants API クライアント（取得・保存関数を提供）
  - pipeline.py: ETL パイプライン（run_daily_etl など）
  - etl.py: ETLResult の再エクスポート
  - calendar_management.py: 市場カレンダー管理（営業日判定等）
  - news_collector.py: RSS 取得・前処理・raw_news 保存
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py: 汎用統計ユーティリティ（zscore_normalize 等）
  - audit.py: 監査ログテーブル定義と初期化
  - __init__.py

- research/
  - factor_research.py: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py: 将来リターン・IC・統計サマリー
  - __init__.py: 便利関数の再エクスポート

- research/* / ai/* / data/* は DuckDB 接続経由でデータにアクセスする設計です。  
  本番の注文処理や外部発注は execution / strategy 等の別モジュールで実装される想定です（今回のコード群はデータ処理・解析・ログ基盤が中心）。

---

## 運用上の注意

- 機密情報（API トークン・パスワード）は .env ファイルやシークレット管理で厳重に管理してください。
- OpenAI や J-Quants の API 呼び出しは課金・レート制限があるためローカルでのテスト時も注意してください。
- DuckDB による書き込みは一部トランザクション制御を行っていますが、実行環境でのバックアップ戦略を検討してください。
- 自動 .env 読み込みを無効にするフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1（テスト時に便利）

---

README はここまでです。必要であれば次を追加します:
- requirements.txt の推奨内容（バージョン固定）
- 具体的なワークフロー（cron / Airflow / GitHub Actions による ETL の定期実行例）
- テーブルスキーマ（raw_prices / ai_scores / market_calendar 等）の抜粋

追加希望があれば教えてください。