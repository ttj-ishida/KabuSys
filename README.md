# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ。データ収集（J-Quants / RSS）、ETL、データ品質チェック、ファクター・リサーチ、ニュースNLP（OpenAI）、市場レジーム判定、監査ログ（発注→約定トレース）など運用に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的をもつモジュール群から構成されます。

- データ取得（J-Quants API）と ETL（DuckDB に保存）
- RSS によるニュース収集と前処理
- OpenAI を用いたニュースセンチメント解析（銘柄別 ai_score、マクロセンチメント）
- 市場レジーム判定（ETF MA200 とマクロセンチメントの複合）
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 設定管理（.env / 環境変数自動読み込み）

設計上の特徴:
- ルックアヘッドバイアス回避（内部で datetime.now()/date.today() を不要にする設計）
- 冪等性を重視した DB 操作（ON CONFLICT / 個別 DELETE → INSERT）
- ネットワーク呼び出しはリトライ・バックオフ実装
- テスト容易性（API 呼び出し箇所の差し替えを想定）

---

## 主な機能一覧

- 環境変数/設定管理: kabusys.config.Settings（.env / .env.local を自動ロード、無効化可能）
- J-Quants クライアント: data.jquants_client
  - 株価日足、財務、上場情報、JPX カレンダーの取得・保存
  - レートリミッタ・トークン自動リフレッシュ・リトライ対応
- ETL パイプライン: data.pipeline.run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- データ品質チェック: data.quality（欠損、重複、スパイク、日付不整合）
- ニュース収集: data.news_collector.fetch_rss（RSS 取得、SSRF 対策、前処理）
- ニュースNLP: ai.news_nlp.score_news（銘柄ごとセンチメント -> ai_scores へ書き込み）
- 市場レジーム判定: ai.regime_detector.score_regime（ETF 1321 MA200 とマクロセンチメントの合成）
- 研究用ユーティリティ: research.factor_research, research.feature_exploration（ファクター計算、IC、統計）
- 監査ログ初期化: data.audit.init_audit_db / init_audit_schema（監査テーブル群の作成）
- 汎用統計: data.stats.zscore_normalize

---

## セットアップ

前提
- Python 3.10+（型ヒントに union 型等を使用）
- 必要パッケージ（一例）
  - duckdb
  - openai
  - defusedxml

インストール例（プロジェクトルートで）:
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）
3. 開発インストール（任意）
   - pip install -e .

環境変数:
- プロジェクトルート（.git または pyproject.toml を含む）にある `.env` / `.env.local` が自動で読み込まれます（優先度: OS 環境 > .env.local > .env）。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

主に使う環境変数（必須は後述）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime を実行する際に使用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment: development | paper_trading | live
- LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL

サンプル .env (プロジェクトルート/.env):
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXXX
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（主要なエントリポイント例）

以下は Python REPL やスクリプトから実行する簡易例です。実際の運用ではログやスケジューラ（cron / systemd / Airflow など）で定期実行してください。

- DuckDB 接続を作る:
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))  # settings は kabusys.config.settings

- 日次 ETL を実行:
  - from kabusys.data.pipeline import run_daily_etl
  - from kabusys.config import settings
  - import duckdb, datetime
  - conn = duckdb.connect(str(settings.duckdb_path))
  - res = run_daily_etl(conn, target_date=datetime.date(2026, 3, 20))
  - print(res.to_dict())

- ニュースセンチメント（銘柄別 ai_scores）を算出:
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date=datetime.date(2026,3,20), api_key="sk-...")  # api_key optional（環境変数で指定可）

- 市場レジームをスコアリング:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=datetime.date(2026,3,20), api_key="sk-...")

- 監査ログ DB を初期化:
  - from kabusys.data.audit import init_audit_db
  - conn_audit = init_audit_db("data/audit.duckdb")
  - これで signal_events / order_requests / executions などのテーブルが作成されます。

- 研究用ファクターを計算:
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - results = calc_momentum(conn, datetime.date(2026,3,20))

- 設定参照:
  - from kabusys.config import settings
  - print(settings.duckdb_path, settings.is_live, settings.log_level)

注意:
- OpenAI 呼び出しや J-Quants 呼び出しはネットワークアクセス・API キーが必要です。テスト時は該当関数をモックしてください（コード内でも差し替え容易に設計されています）。
- score_news / score_regime は API 呼び出しに失敗した場合でもフェイルセーフ（部分的にスキップ・0 値フォールバック）となるよう設計されていますが、結果の確認は必ず行ってください。

---

## ディレクトリ構成（主要ファイルと説明）

src/kabusys/
- __init__.py
  - パッケージ公開情報（__version__ 等）
- config.py
  - .env/環境変数の自動読み込み、Settings クラス（各種パラメータ取得・検証）
- ai/
  - __init__.py
  - news_nlp.py
    - 銘柄ごとのニュースセンチメントを OpenAI で解析し ai_scores テーブルへ書込む
  - regime_detector.py
    - ETF(1321) の MA200 乖離 + マクロセンチメントで market_regime を算出
- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（取得・保存ロジック、レート制御、リトライ）
  - pipeline.py
    - ETL パイプラインの主要フロー（run_daily_etl 等）
  - etl.py
    - ETLResult の再エクスポート
  - news_collector.py
    - RSS 取得・前処理・SSRF 対策・raw_news 保存
  - calendar_management.py
    - JPX カレンダー管理、営業日判定、calendar_update_job
  - stats.py
    - zscore_normalize 等の共通統計ユーティリティ
  - quality.py
    - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py
    - 監査ログ（signal/order_request/executions）DDL と初期化ロジック
- research/
  - __init__.py
  - factor_research.py
    - モメンタム・バリュー・ボラティリティなどのファクター計算
  - feature_exploration.py
    - 将来リターン計算 / IC / 統計サマリー / ランク関数

---

## 運用・開発上の注意点

- 環境: KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかを指定。live の場合は特に外部 API キーや発注設定を厳重に管理すること。
- DB: DuckDB をデータプラットフォームの中心に利用。バックアップやディスク容量管理に注意。
- API リクエスト: J-Quants のレート制限（120 req/min）に従う。jquants_client は内部でレート制御を行いますが、運用上の多数同時処理は避ける。
- OpenAI: 金銭的コストとレイテンシを考慮し、バッチ処理（score_news は銘柄をチャンク）を採用。
- テスト: OpenAI や J-Quants 呼び出し箇所は関数単位で差し替え可能。ユニットテストでは外部 API をモックして実行すること。

---

## 参考（トラブルシュート）

- 環境変数が読み込まれない
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認。手動で環境変数をエクスポートするか、.env をプロジェクトルートに配置してください。
- OpenAI で JSON 解析エラーが発生する
  - LLM レスポンスのフォーマットを検証するログが出力され、失敗時はフォールバックでスコア 0.0 になります。テスト時は _call_openai_api をモックして安定したレスポンスを返すと良いです。
- DuckDB に書き込めない
  - パスの親ディレクトリが存在するか確認。audit.init_audit_db は自動で親ディレクトリを作成しますが、他のケースでは明示的に作成が必要です。

---

この README はコードベースの主要な使い方と設計意図を簡潔にまとめたものです。追加の運用手順や API キーの発行方法、CI/CD、詳細なテーブルスキーマなどを別途ドキュメント化することを推奨します。