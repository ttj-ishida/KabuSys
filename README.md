# KabuSys

日本株向けのデータプラットフォーム＋自動売買/リサーチ基盤（モジュール群）の軽量実装です。本リポジトリは以下の機能を想定しています：J-Quants からのデータ取得・ETL、ニュース収集と LLM によるニュース/マクロセンチメント評価、ファクター計算・特徴量解析、監査ログ（発注/約定トレース）など。

---

## プロジェクト概要

KabuSys は以下を主目的とした Python モジュール群です。

- J-Quants API を用いた株価（OHLCV）・財務・市場カレンダーの差分 ETL
- RSS ニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュース／マクロセンチメント評価（JSON Mode）
- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントの合成）
- リサーチ用のファクター計算（モメンタム、ボラティリティ、バリュー等）、将来リターン・IC・統計要約
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- 監査ログ（signal → order_request → execution のトレース）用の DuckDB スキーマ初期化ユーティリティ

設計上の特徴は「ルックアヘッドバイアス対策」「冪等性」「API リトライ／レート制御」「フェイルセーフ（API 失敗時は無害にフォールバック）」などです。

---

## 主な機能一覧

- 環境設定自動読み込み（.env / .env.local、トップレベルに .git または pyproject.toml を想定）
- J-Quants API クライアント（レートリミット・トークン自動リフレッシュ・ページネーション対応）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ冪等保存）
- ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
- データ品質チェック（missing_data / spike / duplicates / date_consistency / run_all_checks）
- ニュース収集（RSS → raw_news、SSRF 対策・サイズ上限・トラッキング除去）
- LLM ベースのニュース NLP（score_news: 銘柄別センチメント、JSON Mode、バッチ処理・リトライ）
- 市場レジーム判定（score_regime: MA200 とマクロセンチメント合成）
- リサーチ用ファクター（calc_momentum, calc_volatility, calc_value）と解析ツール（calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize）
- 監査ログスキーマ初期化（init_audit_schema / init_audit_db）

---

## セットアップ手順

前提
- Python 3.9+（ソースは型注釈に 3.10 以降の構文を含む可能性があるため 3.10 推奨）
- DuckDB、OpenAI SDK、defusedxml 等の依存

例: 仮想環境を作って依存をインストールする
- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージ（最低限）
  - pip install duckdb openai defusedxml

（プロジェクト化されている場合は pyproject.toml / requirements.txt を参照してください）

環境変数
- 本ライブラリは多数の環境変数を使用します。主な必須変数:
  - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（jquants_client 用）
  - KABU_API_PASSWORD — kabuステーション API のパスワード（発注連携等）
  - SLACK_BOT_TOKEN — Slack 通知用ボットトークン
  - SLACK_CHANNEL_ID — Slack 送信先チャンネル ID
  - OPENAI_API_KEY — OpenAI 呼び出し用（score_news / score_regime で使用可能）
- 任意 / デフォルト:
  - KABUSYS_ENV (development | paper_trading | live) — 環境フラグ（default: development）
  - LOG_LEVEL (DEBUG|INFO|...) — ログレベル
  - DUCKDB_PATH — デフォルト data/kabusys.duckdb
  - SQLITE_PATH — 監視用 SQLite path data/monitoring.db

.env 自動読み込み
- パッケージ import 時にプロジェクトルート（.git か pyproject.toml を上位に探索）を探索し、.env を自動読み込みします。
- 読み込み順: OS 環境 > .env > .env.local（.env.local は override=True）
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 使い方（簡易例）

基本的な DuckDB 接続を使う例

- ETL を日次実行（例: Python スクリプト）

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアリング（ai.news_nlp.score_news）

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で提供
  print(f"書き込んだ銘柄数: {written}")

- 市場レジーム判定（ai.regime_detector.score_regime）

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーを環境変数 OPENAI_API_KEY で指定

- 監査 DB 初期化（監査ログ専用 DuckDB）

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # :memory: も可

注意点
- OpenAI 呼び出しは外部 API に依存するため、適切な API キーとレート制限の考慮が必要です。
- ETL/ニュース収集はネットワーク I/O を含むのでジョブスケジューラ（cron / Airflow 等）で実行することを想定しています。
- DuckDB にスキーマが事前に存在することを前提とする関数が多くあります（ETL 実行前にスキーマ定義を適用してください）。

---

## ディレクトリ構成

以下は主要ファイルのツリー（抜粋）です。実際のリポジトリは src/kabusys 下にモジュールを配置します。

- src/
  - kabusys/
    - __init__.py
    - config.py                         # 環境変数・設定管理（.env 自動読み込み）
    - ai/
      - __init__.py
      - news_nlp.py                     # ニュース NLP（score_news）
      - regime_detector.py              # 市場レジーム判定（score_regime）
    - data/
      - __init__.py
      - jquants_client.py               # J-Quants API クライアント + DuckDB 保存
      - pipeline.py                     # ETL パイプライン（run_daily_etl 等）
      - etl.py                          # ETL 型／再エクスポート (ETLResult)
      - calendar_management.py          # 市場カレンダー管理 / calendar_update_job
      - news_collector.py               # RSS ニュース収集・前処理（SSRF 対策）
      - stats.py                        # 汎用統計ユーティリティ（zscore_normalize）
      - quality.py                      # データ品質チェック（run_all_checks 等）
      - audit.py                        # 監査ログスキーマ初期化（init_audit_schema/db）
    - research/
      - __init__.py
      - factor_research.py              # ファクター計算（momentum, volatility, value）
      - feature_exploration.py          # 将来リターン / IC / summary / rank
    - research/... (その他ユーティリティ)

備考
- README に記載の機能はソースドキュメント（各ファイル冒頭の docstring）に詳細設計が記載されています。
- strategy / execution / monitoring といった名前空間はパッケージ公開面では __all__ に含まれていることがありますが、本ツリーに含まれているコードの範囲は data / ai / research を中心としています（戦略・約定連携部分は別パッケージや拡張を想定しています）。

---

## 運用上のポイント・注意事項

- ルックアヘッドバイアス防止:
  - 日付計算で datetime.today()/date.today() を不用意に使用せず、target_date を明示して処理する実装を心がけています。バックテスト等では ETL 実行タイミングとデータの取得日時（fetched_at）に注意してください。
- 冪等性:
  - DuckDB への保存は基本的に ON CONFLICT DO UPDATE / INSERT ... DO NOTHING を用いて冪等性を保ちます。ETL は差分取得とバックフィルを併用して API の後出し修正を吸収します。
- API リトライ / レート制御:
  - J-Quants は固定間隔スロットリング、OpenAI 呼び出しにはリトライと指数バックオフ実装が含まれます。
- セキュリティ:
  - news_collector には SSRF 対策、XML の defusedxml を利用したパース、受信サイズ上限などが実装されています。

---

## 参考: 主要な公開 API（抜粋）

- kabusys.config.settings — アプリケーション設定アクセス
- kabusys.data.pipeline.run_daily_etl(conn, target_date, ...)
- kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes
- kabusys.data.news_collector.fetch_rss(...)
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- kabusys.data.audit.init_audit_db(path) / init_audit_schema(conn)

---

もし README に追加したいサンプルコード、CI（テスト）手順、パッケージ公開手順、あるいは戦略レイヤー（strategy / execution / monitoring）のテンプレートを含めたい場合は要望を教えてください。