# KabuSys

日本株向けの自動売買／データプラットフォーム用 Python ライブラリ群です。  
データ ETL、ニュース NLP（LLM を用いたセンチメント）、市場レジーム判定、監査ログ（トレーサビリティ）、研究用ファクター計算などを提供します。

## プロジェクト概要
KabuSys は以下を目的としたモジュール群です。

- J-Quants からの市場データ（株価・財務・カレンダー）を取得して DuckDB に差分保存する ETL パイプライン
- RSS ベースのニュース収集と前処理
- OpenAI（gpt-4o-mini 等）を利用したニュースセンチメント／銘柄ごとの AI スコアリング
- ETF（1321）の MA とマクロニュースの組合せによる日次市場レジーム判定
- 監査ログ（signal → order_request → execution）用スキーマ初期化・ユーティリティ
- 研究用途のファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ

設計方針としては、Look-ahead bias を防ぐために日付の扱いを厳格化し、DuckDB を中心に冪等性／トランザクションを考慮した処理を行います。

## 主な機能一覧
- データ ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants API クライアント（kabusys.data.jquants_client）：取得・リトライ・レート制御・保存ロジック
- ニュース処理・NLP
  - RSS 収集・前処理（kabusys.data.news_collector）
  - LLM を使った銘柄ごとのニューススコアリング（kabusys.ai.news_nlp）
  - マクロニュース + ETF MA を用いた市場レジーム判定（kabusys.ai.regime_detector）
- 研究支援
  - ファクター計算（momentum / value / volatility）（kabusys.research.factor_research）
  - 将来リターン計算、IC 計算、統計サマリ（kabusys.research.feature_exploration）
  - Z スコア正規化（kabusys.data.stats）
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合などを検出
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions のスキーマ定義、初期化ユーティリティ
- 設定管理（kabusys.config）
  - .env 自動ロード（プロジェクトルート基準）、環境変数ラッパー（settings）

## セットアップ手順（ローカル開発向け）
1. Python 仮想環境を作成・有効化
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows PowerShell:
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 必要パッケージをインストール
   - 最低限必要なパッケージ（例）:
     ```
     pip install --upgrade pip
     pip install duckdb openai defusedxml
     ```
   - （プロジェクト配布用に requirements.txt がある場合は `pip install -r requirements.txt` を推奨）

3. パッケージを開発モードでインストール（任意）
   ```
   pip install -e .
   ```

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと、自動でロードされます（デフォルト）。自動ロードを無効化するには環境変数を設定:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主要な環境変数（抜粋）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabu API パスワード（発注連携がある場合）
     - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
     - OPENAI_API_KEY: OpenAI API キー（AI スコアリングに必要）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

## 使い方（簡単なサンプル）
以下はライブラリの主要機能を呼ぶ最小例です。実行前に OpenAI / J-Quants のキー設定と DuckDB の初期スキーマが整っていることを確認してください。

- DuckDB 接続を作って日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI 必須）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY が環境変数で必要
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY が必要
  ```

- 監査データベース（監査ログ専用）を初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を使って以降の監査テーブルにアクセスできます
  ```

- 研究用ファクター計算（例：モメンタム）
  ```python
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026,3,20))
  ```

注意: 上記はライブラリ関数の呼び出し例です。実運用ではログ設定・例外処理・トランザクションの管理・スケジューリング（cron/airflow など）を整備してください。

## 主要モジュール説明（簡潔）
- kabusys.config
  - 環境変数と .env の自動読み込み、settings オブジェクトでアクセス
- kabusys.data.jquants_client
  - J-Quants API とやり取りする関数群（fetch_*/save_*、認証・リトライ・レート制御）
- kabusys.data.pipeline
  - run_daily_etl 等の ETL ワークフローと ETLResult
- kabusys.data.news_collector
  - RSS 収集・前処理・SSRF 対策・記事保存ヘルパー
- kabusys.data.quality
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
- kabusys.data.audit
  - 監査ログ用テーブル定義と初期化ユーティリティ
- kabusys.ai.news_nlp
  - 銘柄ごとのニュースセンチメントを LLM で評価し ai_scores に書き込む
- kabusys.ai.regime_detector
  - ETF MA とマクロニュースを合成し市場レジーム（bull/neutral/bear）を判定
- kabusys.research.*
  - ファクター計算と特徴量解析（バックテスト・研究用）

## ディレクトリ構成
（抜粋）

src/
  kabusys/
    __init__.py
    config.py
    ai/
      __init__.py
      news_nlp.py
      regime_detector.py
    data/
      __init__.py
      jquants_client.py
      pipeline.py
      etl.py
      news_collector.py
      calendar_management.py
      quality.py
      stats.py
      audit.py
      # ...（他の data 関連モジュール）
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
    research/（...）
    # strategy/, execution/, monitoring/ はパッケージ公開対象だが実装は別ファイル群

## 注意点 / 運用上のヒント
- OpenAI を利用する機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）が必要です。API コストとレート制限に注意してください。
- J-Quants は API レート制限があり、jquants_client にレート制御・リトライが組み込まれています。認証トークンは JQUANTS_REFRESH_TOKEN を .env に設定してください。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml の存在するディレクトリ）基準で行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- DuckDB の SQL 実行はモジュール内で多用されます。スキーマ初期化やマイグレーションは別途整備してください（本コードは保存関数や init_audit_schema を提供します）。

---

この README はコードベース（src/kabusys）から主要機能をまとめたものです。より詳細な API 仕様や運用手順（スキーマ定義、スケジューリング、監視）は別ドキュメントにまとめることを推奨します。必要であれば README に追記する内容（例: サンプル .env.example、SQL スキーマ、デプロイ手順など）を指定してください。