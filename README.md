KabuSys — 日本株向け自動売買／データプラットフォーム
================================

概要
----
KabuSys は日本株のデータ収集・品質管理・ファクター算出・AI（ニュース）スコアリング・市場レジーム判定・監査ログなどを含む、バックテスト / リサーチ / 自動売買のためのユーティリティ群です。DuckDB を内部データストアとして利用し、J-Quants API や RSS、OpenAI を組み合わせて運用・研究ワークフローを実現します。

主な特徴（機能一覧）
-----------------
- データ取得（J-Quants）
  - 日足（OHLCV）、財務データ、上場銘柄情報、JPX マーケットカレンダーの差分取得・保存（ETL）
  - レート制限／リトライ／トークン自動リフレッシュ対応
- データ品質管理
  - 欠損、重複、スパイク、日付不整合などのチェック
- ニュース収集 / 前処理
  - RSS 収集、URL 正規化、SSRF 防御、記事の冪等保存
- AI（ニュース NLP）
  - OpenAI を用いた銘柄単位のニュースセンチメント算出（gpt-4o-mini, JSON mode）
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA200 乖離 + LLM）
- リサーチユーティリティ
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - 将来リターン、IC（Information Coefficient）、統計サマリー
- 監査ログ（トレーサビリティ）
  - signal → order_request → execution をたどれる監査テーブル群の初期化
- 汎用ユーティリティ
  - Zスコア正規化、ニュース時間ウィンドウ計算 など

前提・依存関係
---------------
（実行環境により変わりますが、主に以下パッケージを想定）
- Python 3.10+
- duckdb
- openai
- defusedxml
- （標準ライブラリ以外の依存は setup / requirements を参照してください）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. インストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - pip install -e .   （パッケージ化されている場合）
   またはプロジェクトに requirements.txt があれば pip install -r requirements.txt
4. 環境変数の設定
   - プロジェクトルートに .env を置くと自動読込（優先度: OS 環境 > .env.local > .env）。
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

推奨される .env（例）
--------------------
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
LINE_CHANNEL_ACCESS_TOKEN=your_line_token
LINE_USER_ID=your_line_user_id
DUCKDB_PATH=./data/kabusys.duckdb
SQLITE_PATH=./data/monitoring.db
PID_FILE_PATH=./data/execution.pid
KILL_FLAG_PATH=./data/kill.flag
KILL_FLAG_CLEAR_ON_START=0
CPU_THRESHOLD_PCT=90.0
MEMORY_THRESHOLD_PCT=85.0
DISK_THRESHOLD_PCT=90.0
KABUSYS_ENV=development
LOG_LEVEL=INFO

設定の注意:
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN（J-Quants 用）
  - KABU_API_PASSWORD（kabuステーション API を利用する場合）
  - OPENAI_API_KEY（AI スコアリングを行う場合）
- 設定は kabusys.config.settings から参照できます（例: settings.duckdb_path）。

基本的な使い方（Python API 例）
-------------------------------

共通: DuckDB 接続を作成
- import duckdb
- conn = duckdb.connect(str(settings.duckdb_path))

ETL（日次パイプライン）の実行
- from kabusys.data.pipeline import run_daily_etl
- from datetime import date
- result = run_daily_etl(conn, target_date=date(2026, 3, 20))
- print(result.to_dict())

ニューススコアリング（銘柄別 ai_scores 生成）
- from kabusys.ai.news_nlp import score_news
- from datetime import date
- n_written = score_news(conn, target_date=date(2026, 3, 20))
- print(f"書き込み件数: {n_written}")

市場レジーム判定（market_regime テーブルへ書込）
- from kabusys.ai.regime_detector import score_regime
- from datetime import date
- score_regime(conn, target_date=date(2026, 3, 20))

監査ログ DB 初期化（独立 DB を用いる場合）
- from kabusys.data.audit import init_audit_db
- audit_conn = init_audit_db("./data/audit.duckdb")
- # これで監査テーブル群が作成されます

ニュース RSS の収集（単体）
- from kabusys.data.news_collector import fetch_rss
- articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
- # 取得した articles は NewsArticle リスト（dictionary 準拠）

設定参照（コード内）
- from kabusys.config import settings
- settings.jquants_refresh_token, settings.duckdb_path, settings.env など

運用に関するヒント
-----------------
- OpenAI 呼び出しはリトライ・フェイルセーフ設計になっていますが、APIキーとレートには注意してください（コスト・速度）。
- ETL は各ステップで例外を捕捉して継続するため、result.errors や quality_issues を確認して問題を把握してください。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本コードはルックアヘッドバイアスを避ける設計（内部で date.today() を直接参照しない等）になっています。バックテスト用途でもその設計原則に従って利用してください。

主要モジュール・ディレクトリ構成
-------------------------------
（src/kabusys 以下の主要ファイルを抜粋）

- kabusys/
  - __init__.py                      - パッケージ定義（バージョン）
  - config.py                        - 環境変数／設定管理（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py                     - ニュース NLP スコアリング（score_news）
    - regime_detector.py              - 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py               - J-Quants API クライアント（fetch / save）
    - pipeline.py                     - ETL パイプライン（run_daily_etl 他）
    - etl.py                          - ETLResult の再エクスポート
    - calendar_management.py          - 市場カレンダー管理 / 営業日判定
    - news_collector.py               - RSS 収集・前処理
    - stats.py                        - 統計ユーティリティ（zscore_normalize）
    - quality.py                      - データ品質チェック
    - audit.py                        - 監査ログテーブル定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py              - ファクター計算（momentum/value/volatility）
    - feature_exploration.py          - 将来リターン / IC / 統計サマリー

主な公開 API（抜粋）
- kabusys.config.settings
- kabusys.data.pipeline.run_daily_etl, ETLResult
- kabusys.ai.news_nlp.score_news
- kabusys.ai.regime_detector.score_regime
- kabusys.data.jquants_client.get_id_token / fetch_* / save_*
- kabusys.data.audit.init_audit_db / init_audit_schema
- kabusys.data.news_collector.fetch_rss

ログとデバッグ
----------------
- log レベルは環境変数 LOG_LEVEL で制御（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- KABUSYS_ENV は development / paper_trading / live のいずれかに設定可能（settings.env）。
- 監視用の閾値（CPU/MEM/DISK など）は環境変数で調整可能。

貢献・開発
----------
- コードを変更する場合はユニットテストを追加してください（モジュールの多くは外部依存呼び出しを内部関数でラップしておりモックしやすく設計されています）。
- OpenAI 呼び出しや外部 HTTP 呼び出しはテスト時に差し替え可能な内部ヘルパー関数が用意されています（unittest.mock を推奨）。

免責
----
- 本リポジトリはあくまで研究・運用支援ツールであり、実際の売買に用いる場合は十分な検証・リスク管理を行ってください。
- 実際の発注系ロジック（ブローカー接続・注文管理）の実装・テストは慎重に行ってください。

---

必要であれば README にサンプル .env.example、requirements.txt、具体的な CLI／ジョブスケジュール例（systemd / cron / Airflow など）を追加します。どの情報を優先して追加しますか？