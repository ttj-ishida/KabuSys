# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
主にデータ ETL、ニュース NLP（LLM を用いたセンチメント評価）、ファクター計算、監査ログの初期化など、トレーディング基盤で必要となる共通処理を提供します。

## 概要
- データ取得・保存（J-Quants API 経由の株価・財務・カレンダー等）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース収集・NLP（OpenAI を用いた銘柄ごとのセンチメント算出）
- 市場レジーム判定（ETF とマクロニュースを組み合わせて daily レジーム評価）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティを保持するテーブル定義）
- 研究用ユーティリティ（ファクター計算・特徴量解析・Z スコア正規化 等）

設計方針として、バックテストでの look-ahead バイアスを避けることや、ETL の冪等性（ON CONFLICT / idempotent 保存）、外部 API 呼び出しに対するリトライとレート制御、失敗時のフェイルセーフ動作を重視しています。

## 主な機能一覧
- 環境設定読み込み（.env / .env.local／環境変数）
- J-Quants API クライアント（認証自動更新、ページネーション、レート制御、保存関数）
- 日次 ETL（run_daily_etl: calendar, prices, financials, 品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- ニュース収集（RSS、安全対策: SSRF 検出、XML 安全パース）
- ニュース NLP（gpt-4o-mini を用いた銘柄ごとのセンチメントスコア算出）
- レジーム判定（ETF 1321 の MA とマクロニュースを組み合わせたレジーム分類）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）と探索ツール（forward returns、IC、summary）
- 監査ログスキーマの初期化ユーティリティ（init_audit_schema / init_audit_db）

## セットアップ手順

1. リポジトリをクローン（またはパッケージをコピー）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール  
   最低限の依存（本コードベースで参照されている主要ライブラリ）:
   ```
   pip install duckdb openai defusedxml
   ```
   実運用では logging、その他ライブラリや開発用ツール（pytest など）を追加してください。プロジェクトに requirements.txt がある場合はそちらを使用します。

4. 環境変数の設定  
   プロジェクトルートに `.env`（※自動ロードされます）を置くか OS 環境変数として設定します。主な環境変数:

   - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（必須 for ETL）
   - OPENAI_API_KEY: OpenAI API キー（必須 for NLP / Regime）
   - KABU_API_PASSWORD: kabu API パスワード（発注等で使用）
   - KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU/MEM/DISK thresholds
   - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

   自動 .env 読み込みは config.py によりプロジェクトルート（.git または pyproject.toml を基準）から行われます。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

## 使い方（代表的な例）

以下は Python REPL やスクリプトから呼び出す例です。

- DuckDB 接続を作って日次 ETL を実行する:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- OpenAI を使ってニューススコアを生成する:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
  print("scored:", count)
  ```

- 市場レジームをスコアリングする:
  ```python
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB を初期化する:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を使って order_events / order_requests / executions テーブルにアクセス可能
  ```

- RSS 取得（ニュース収集の一部）:
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["title"], a["datetime"])
  ```

注意点:
- OpenAI/API キーはセキュアに管理してください。テスト時はモック化（unittest.mock.patch）できるよう設計されています。
- 各処理（ETL / LLM 呼び出し等）はネットワークエラーや API レート制限に対してリトライやフェイルセーフを備えていますが、運用時にはログ監視を行ってください。

## 簡単な API 参照（抜粋）
- kabusys.config.settings: アプリ設定（env から取得）
- kabusys.data.pipeline:
  - run_daily_etl(conn, target_date, ...)
  - run_prices_etl, run_financials_etl, run_calendar_etl
- kabusys.data.jquants_client:
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
- kabusys.data.quality:
  - run_all_checks, check_missing_data, check_spike, ...
- kabusys.data.news_collector:
  - fetch_rss, preprocess_text
- kabusys.ai.news_nlp:
  - score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector:
  - score_regime(conn, target_date, api_key=None)
- kabusys.research:
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank

## ディレクトリ構成

（主要ファイルのみ抜粋）

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
      - calendar_management.py
      - pipeline.py
      - etl.py
      - stats.py
      - quality.py
      - audit.py
      - jquants_client.py
      - news_collector.py
      - pipeline.py
      - etl.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - (その他: strategy/, execution/, monitoring/ などのパッケージを想定)

実際のリポジトリでは tests/ や docs/、pyproject.toml / setup.cfg 等が存在することが想定されます。

## 運用上の注意
- DuckDB ファイル（デフォルト data/kabusys.duckdb）は定期バックアップを推奨します。
- OpenAI の利用にはコストが発生します。バッチサイズやモデル（デフォルト gpt-4o-mini）を適宜調整してください。
- J-Quants の API レート制限（120 req/min）を守るため、jquants_client 内でレート制御とリトライを実装しています。運用でトラフィックが増える場合は注意してください。
- news_collector は外部 RSS を取得するため SSRF 対策や受信サイズ制限を実装していますが、追加の安全対策は運用方針に合わせて行ってください。

---

さらに詳しい使い方や運用フロー（cron による ETL スケジュール化、監視・アラートの設定、バックテスト環境での look-ahead 対策等）を README に追記したい場合は、運用想定やデプロイ手順（systemd / Docker / k8s）などの要件を教えてください。必要に応じてサンプル .env.example や docker-compose の雛形も作成します。