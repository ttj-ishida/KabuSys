# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants → DuckDB）、ニュースのNLPスコアリング（OpenAI）、市場レジーム判定、研究用ファクター計算、データ品質チェック、監査ログ機能などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買基盤を構成するためのモジュール群です。主要な責務は以下の通りです。

- J-Quants API からのデータ取得（株価日足、財務、カレンダー）
- DuckDB へ冪等に保存する ETL パイプライン
- ニュース収集と OpenAI によるセンチメント解析（銘柄別 ai_score）
- 市場レジーム判定（ETF の MA とマクロニュースの LLM センチメントを合成）
- 研究用ファクター計算・特徴量解析ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → executions のトレーサビリティ）用スキーマ初期化

設計上の特徴:
- ルックアヘッドバイアス防止（内部で date.today()/datetime.now() を不用意に参照しない）
- DuckDB を中核にしたオンプレ/ローカルのデータ管理
- API 呼び出しに対するリトライ・レートリミット・フェイルセーフ実装
- 冪等保存（ON CONFLICT / INSERT … DO UPDATE）を多用

---

## 機能一覧

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（取得・保存関数: fetch_*, save_*）
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSS fetch_rss、前処理）
  - データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news）
  - 市場レジーム判定（score_regime）
  - OpenAI 呼び出しは gpt-4o-mini を想定（JSON モードでの厳密な応答を期待）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数・設定管理（settings オブジェクト）
  - 自動でプロジェクトルートの .env / .env.local を読み込む（無効化可）

---

## セットアップ手順

前提
- Python >= 3.10
- Git リポジトリのルートにプロジェクトを配置（.env 自動読込のため .git または pyproject.toml に依存）

インストール（例）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクト外で Slack 等の実行機能を使う場合は slack-sdk 等が別途必要になることがあります）

3. 環境変数設定
   - プロジェクトルートに `.env`（および任意で `.env.local`）を配置します。
   - `.env.example` を参考に必要な変数を設定してください。主な環境変数:

     - J-Quants / データ
       - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - kabu API
       - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
       - KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
     - OpenAI
       - OPENAI_API_KEY: OpenAI API キー（score_news, score_regime に必要）
     - Slack
       - SLACK_BOT_TOKEN: Slack bot token（必須）
       - SLACK_CHANNEL_ID: 通知先 channel id（必須）
     - DB パス等
       - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
       - SQLITE_PATH: 監視等で使う sqlite パス（デフォルト data/monitoring.db）
     - 実行環境
       - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
       - LOG_LEVEL: DEBUG|INFO|WARNING|...（デフォルト INFO）
     - その他
       - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込む挙動を無効化できます（テスト時に便利）

4. プロジェクトルートに data ディレクトリを作成しておくと便利
   - mkdir -p data

---

## 使い方（主な例）

以下はライブラリ API を直接呼ぶ最小の例です。DuckDB 接続を渡して各ジョブを実行します。

- DuckDB 接続の生成例:
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL（市場カレンダー、株価、財務の差分取得）:
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026,3,20))
  - print(result.to_dict())

- ニュースの NLP スコア取得（OpenAI 必須）:
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n = score_news(conn, target_date=date(2026,3,20))  # returns 書き込んだ銘柄数

- 市場レジーム判定（OpenAI 必須）:
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - r = score_regime(conn, target_date=date(2026,3,20))  # returns 1 on success

- 監査ログスキーマ初期化:
  - from kabusys.data.audit import init_audit_db, init_audit_schema
  - audit_conn = init_audit_db("data/audit.duckdb")  # 必要なテーブルを作成して接続を返す
  - あるいは既存の conn に対して init_audit_schema(conn, transactional=True)

- 設定オブジェクト:
  - from kabusys.config import settings
  - print(settings.duckdb_path, settings.env)

ログレベルを変更したい場合は環境変数 LOG_LEVEL を適宜設定してください。

注意点:
- score_news / score_regime は OpenAI API の JSON mode を期待した応答を前提としています。API キー管理とレート制御を行ってください。
- J-Quants API の呼び出しはレート制限（120 req/min）・トークンリフレッシュ等の保護が入っています。get_id_token の呼び出しに注意してください。

---

## ディレクトリ構成

主要なモジュール・ファイル構成（src/kabusys 以下）:

- __init__.py
  - パッケージ定義、__version__、__all__

- config.py
  - 環境変数の自動読み込みロジック、settings オブジェクト

- ai/
  - __init__.py
  - news_nlp.py         : ニュースの収集・OpenAI でのスコアリング（score_news）
  - regime_detector.py  : マクロセンチメントと ETF MA に基づく市場レジーム判定（score_regime）

- data/
  - __init__.py
  - jquants_client.py         : J-Quants API クライアント（fetch_*/save_*）
  - pipeline.py               : ETL パイプライン（run_daily_etl 等）
  - etl.py                    : ETLResult の公開再エクスポート
  - calendar_management.py    : マーケットカレンダー管理（is_trading_day 等）
  - news_collector.py         : RSS 取得・前処理
  - quality.py                : データ品質チェック
  - stats.py                  : 汎用統計ユーティリティ（zscore_normalize）
  - audit.py                  : 監査ログスキーマ定義・初期化（init_audit_schema / init_audit_db）

- research/
  - __init__.py
  - factor_research.py        : ファクター計算（momentum/value/volatility）
  - feature_exploration.py    : 将来リターン計算、IC、統計サマリー等

その他:
- src/kabusys/ai/__init__.py、research/__init__.py 等で主要関数を再エクスポートしています。

---

## 補足・運用上の注意

- 環境変数管理:
  - config.py はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に .env/.env.local を自動読み込みします。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。
- OpenAI / J-Quants の API 呼び出しは課金やレートに影響するため、本番運用ではリトライポリシーやバックオフ、コスト管理を検討してください。
- DuckDB の executemany に空リストを渡すと失敗するバージョンの制約に配慮した実装になっています（空チェックが入っています）。
- news_collector は SSRF 対策、受信サイズ上限、XML の安全パース（defusedxml）などを備えています。

---

もし README に追加したいサンプル .env.example、利用時の注意（Slack 通知フロー、kabu ステーション連携手順）や CLI ラッパーの作成例が必要であればお知らせください。