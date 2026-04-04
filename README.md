# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。  
J-Quants からのデータ取得（ETL）、ニュース収集・NLP スコアリング、研究用ファクター計算、監査ログスキーマ、カレンダー管理、そして OpenAI を使った市場レジーム判定などの機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を主な目的とする Python モジュール群です。

- J-Quants API からのデータ取得（株価日足・財務・上場銘柄情報・市場カレンダー）
- データの ETL（差分取得・保存・品質チェック）
- RSS からのニュース収集と前処理、ニュース→銘柄マッピング
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント / マクロセンチメントのスコアリング
- リサーチ用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- 市場カレンダー管理（営業日判定、next/prev/trading days）
- 監査ログ（signal → order_request → executions）のスキーマと初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計方針として、バックテストでのルックアヘッドバイアスを避けるために「現在日時」を直接参照しない実装、API 呼び出しに対する堅牢なリトライやフォールバック、DuckDB を中心とした冪等保存ロジックが組み込まれています。

---

## 機能一覧（抜粋）

- 環境設定読み込み・管理（.env, .env.local 自動読み込み、環境変数保護）
- J-Quants クライアント（認証、ページネーション、レート制御、保存用ユーティリティ）
- ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
- ニュース収集（RSS→raw_news、URL 正規化・SSRF 防護）
- ニュース NLP（score_news: 各銘柄ごとのニュースセンチメントを ai_scores へ保存）
- 市場レジーム判定（score_regime: ETF 1321 の MA200 とマクロニュースを合成）
- 研究用モジュール（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank 等）
- 監査ログスキーマの初期化（init_audit_schema / init_audit_db）

---

## セットアップ手順

以下は開発／実行環境の準備例です。

1. Python 仮想環境（推奨）
   - Python 3.9+ を想定（コードは typing の新構文やライブラリを使用）
   - 例:
     - Unix/macOS:
       - python -m venv .venv
       - source .venv/bin/activate
     - Windows (PowerShell):
       - python -m venv .venv
       - .\.venv\Scripts\Activate.ps1

2. 依存ライブラリのインストール
   - 必要な主なパッケージ（例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   ※ 実際の requirements.txt がある場合はそれを使用してください（pip install -r requirements.txt）。

3. 環境変数の設定
   - 簡易的にはプロジェクトルートに `.env` または `.env.local` を作成できます。
   - 自動読み込みはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主な環境変数（必須／任意）:
     - 必須（使用する機能に応じて必須となる）:
       - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL 実行に必須）
       - OPENAI_API_KEY : OpenAI API キー（ニュース / レジーム判定で必須）
     - kabu ステーション（発注連携等を行う場合）:
       - KABU_API_PASSWORD
       - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - LINE 通知（任意）:
       - LINE_CHANNEL_ACCESS_TOKEN
       - LINE_USER_ID
     - データ格納先:
       - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
       - SQLITE_PATH (デフォルト: data/monitoring.db)
     - 実行監視 / PID / kill フラグ:
       - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
     - 閾値 / 環境設定:
       - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
       - KABUSYS_ENV (development | paper_trading | live) — default は development
       - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

   - 簡易 .env 例:
     - JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
     - OPENAI_API_KEY="sk-..."
     - DUCKDB_PATH="data/kabusys.duckdb"
     - KABUSYS_ENV=development

4. データベース用ディレクトリ作成
   - DUCKDB_PATH の親ディレクトリを作成しておく:
     - mkdir -p data

5. 監査ログ DB 初期化（任意）
   - 監査ログ専用 DB を初期化するユーティリティがあり、Python API から呼べます（下記 使い方参照）。

---

## 使い方（抜粋とサンプル）

以下は代表的な利用例です。すべての API は DuckDB 接続（duckdb.connect(...)）を受け取ることが多いです。

- DuckDB 接続の作成例:
  - Python:
    - import duckdb
    - from kabusys.config import settings
    - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行:
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=None)  # target_date を省略すると今日
  - print(result.to_dict())

- 個別 ETL（株価 / 財務 / カレンダー）:
  - from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
  - run_prices_etl(conn, target_date=some_date)
  - run_financials_etl(conn, target_date=some_date)
  - run_calendar_etl(conn, target_date=some_date)

- データ品質チェック:
  - from kabusys.data.quality import run_all_checks
  - issues = run_all_checks(conn, target_date=some_date)
  - for i in issues: print(i)

- ニュース収集（RSS）→ raw_news への保存フローは news_collector モジュールを使用（fetch_rss 等）。
  - 直接 RSS を取得して DB に保存するヘルパー関数群が含まれます。

- ニュース NLP（銘柄ごと ai_score を作成）:
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date=some_date, api_key=None)  # api_key 指定しない場合は OPENAI_API_KEY を参照

- 市場レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=some_date, api_key=None)

- 研究用ファクター計算:
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - momentum_records = calc_momentum(conn, target_date=some_date)

- 統計ユーティリティ:
  - from kabusys.data.stats import zscore_normalize
  - normalized = zscore_normalize(records, ["mom_1m", "mom_3m"])

- 監査ログスキーマ初期化:
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可

注意:
- OpenAI 呼び出しは API キー（OPENAI_API_KEY）を参照します。テスト時はモック可能です（内部呼び出し関数を unittest.mock.patch で差し替え）。
- DuckDB に対する INSERT は冪等設計（ON CONFLICT DO UPDATE）になっているため、再実行に耐えます。

---

## 環境変数自動読み込みについて

- モジュールはプロジェクトルート（.git または pyproject.toml を上位に持つ場所）から .env と .env.local を自動で読み込みます。
  - 優先順位: OS 環境変数 > .env.local > .env
  - OS 環境変数は保護され、.env.local の override による上書きから除外されます（ただし .env.local は基本的に上書き用）。
- 自動読み込みを無効化するには環境変数をセット:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成

リポジトリの主要なソースツリー（要点）:

- src/kabusys/
  - __init__.py
  - config.py                      - 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   - ニュースセンチメント（銘柄単位 ai_scores）
    - regime_detector.py            - 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py             - J-Quants API クライアント + 保存ユーティリティ
    - pipeline.py                   - ETL パイプライン（run_daily_etl 等）
    - etl.py                        - ETL 結果型の再エクスポート
    - news_collector.py             - RSS 収集・前処理・保存
    - calendar_management.py        - 市場カレンダー管理（営業日判定等）
    - quality.py                    - データ品質チェック
    - stats.py                      - 統計ユーティリティ（zscore_normalize 等）
    - audit.py                      - 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py            - ファクター計算（Momentum/Value/Volatility 等）
    - feature_exploration.py        - 将来リターン・IC・統計サマリー
  - (その他) modules: strategy, execution, monitoring が __all__ に含まれる想定

各モジュールは DuckDB 接続を受け取る設計になっており、実行環境次第で組み合わせて利用します。

---

## テスト・開発メモ / 実運用上の注意

- OpenAI / J-Quants の API 呼び出しにはコストやレート制限があるため、実運用ではキー管理・リトライ設定・課金監視を行ってください。
- ETL は差分取得および backfill を実装しているため、定期バッチ（cron / Airflow 等）での運用に適しています。
- ニュース収集の RSS 処理では SSRF 対策やレスポンスサイズ制限、XML パースの安全対策（defusedxml）を施していますが、RSS ソース追加時は該当ソースの挙動を観察してください。
- DuckDB のバージョン差異による executemany の挙動に注意（ライブラリ内で互換性ワークアラウンドを実装しています）。

---

## 参考（短いコードスニペット）

- ETL 実行（例）:
  - from datetime import date
  - import duckdb
  - from kabusys.config import settings
  - from kabusys.data.pipeline import run_daily_etl
  - conn = duckdb.connect(str(settings.duckdb_path))
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニューススコアリング:
  - from kabusys.ai.news_nlp import score_news
  - n = score_news(conn, target_date=date(2026,3,20))

- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026,3,20))

---

もし README に追加したい項目（API の詳細なドキュメント、requirements.txt、例となる .env.example、CI/CD 設定、実行スケジュール例など）があれば教えてください。必要に応じて追記・整形します。