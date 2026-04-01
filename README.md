KabuSys — 日本株自動売買 / データ基盤ライブラリ
====================================

概要
----
KabuSys は日本株向けのデータ基盤・リサーチ・自動売買のための内部ライブラリ群です。本リポジトリは主に以下を提供します。

- J-Quants API からの差分ETL（株価・財務・カレンダー）
- ニュースの収集・NLP スコアリング（OpenAI を利用）
- 市場レジーム判定（ETF とニュースを合成）
- 監査ログ（order / signal / execution）用スキーマ初期化ユーティリティ
- 研究用ファクター計算・統計ユーティリティ

設計方針のポイント
- Look‑ahead bias を避ける設計（関数は内部で date.today() を参照しないなど）
- DuckDB を主要な永続化層として利用
- 外部 API 呼び出しはリトライ／レート制御・フェイルセーフ実装
- 冪等性（ETL 保存や監査テーブル初期化は冪等）

主な機能一覧
----------------
- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - 差分取得、バックフィル、品質チェック（kabusys.data.quality）
- データ取得・保存（J-Quants クライアント）
  - fetch_daily_quotes / save_daily_quotes
  - fetch_financial_statements / save_financial_statements
  - fetch_market_calendar / save_market_calendar
- ニュース
  - RSS 取得・前処理（kabusys.data.news_collector）
  - ニュース NLT スコアリング（kabusys.ai.news_nlp.score_news）
- AI 系
  - ニュースを用いた銘柄ごとのスコアリング（news_nlp）
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- 研究（kabusys.research）
  - ファクター計算: calc_momentum / calc_value / calc_volatility
  - 将来リターン・IC・統計要約：calc_forward_returns / calc_ic / factor_summary / rank
- 監査ログ
  - 監査テーブル作成・初期化（kabusys.data.audit.init_audit_db / init_audit_schema）
- 設定管理
  - .env / 環境変数の自動ロード・検証（kabusys.config.settings）

動作環境 / 依存
----------------
（実際の requirements.txt は本 README に含まれていませんが、少なくとも以下が必要です）
- Python 3.9+（型注釈での union 表記等に依存）
- duckdb
- openai（OpenAI の新 SDK）
- defusedxml
- その他標準ライブラリ（urllib, json, datetime, logging 等）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml

   （必要に応じて requirements.txt を用意して pip install -r requirements.txt）

4. 環境変数 / .env を用意
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env または .env.local を配置すると自動で読み込まれます。
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

重要な環境変数（設定キー）
----------------
kabusys.config.Settings で参照される主なキー：

- JQUANTS_REFRESH_TOKEN （必須）: J-Quants リフレッシュトークン
- KABU_API_PASSWORD （必須）: kabuステーション API パスワード
- KABU_API_BASE_URL （任意）: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN （必須）: Slack 通知用ボットトークン
- SLACK_CHANNEL_ID （必須）: 通知先チャネル ID
- DUCKDB_PATH （任意）: デフォルト DB パス（data/kabusys.duckdb）
- SQLITE_PATH （任意）: 監視用 SQLite（data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視関連）
- KABUSYS_ENV（任意）: development / paper_trading / live のいずれか（デフォルト development）
- LOG_LEVEL（任意）: DEBUG/INFO/…（デフォルト INFO）
- OPENAI_API_KEY: OpenAI 呼び出しに使用（news_nlp/regime_detector で必要）

使い方（代表的な例）
-------------------

準備: DuckDB 接続を作る
- Python REPL やスクリプトで
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

日次 ETL 実行（価格・財務・カレンダー・品質チェック）
- from kabusys.data.pipeline import run_daily_etl
- from datetime import date
- result = run_daily_etl(conn, target_date=date(2026,3,20))
- print(result.to_dict())

ニュースのスコアリング（OpenAI が必要）
- from kabusys.ai.news_nlp import score_news
- from datetime import date
- n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
- ※ api_key を渡さない場合は環境変数 OPENAI_API_KEY を参照します

市場レジーム判定（ETF 1321 の MA とマクロニュースの組み合わせ）
- from kabusys.ai.regime_detector import score_regime
- from datetime import date
- score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

監査ログ DB を初期化（監査用 DuckDB）
- from kabusys.data.audit import init_audit_db
- audit_conn = init_audit_db("data/audit.duckdb")
- これにより監査テーブル(signal_events, order_requests, executions)が作成されます

ライブラリ内部の注意点
- news_nlp や regime_detector は OpenAI を呼ぶため APIキーが必須（もしくは api_key 引数で注入）
- 多くの関数はルックアヘッドバイアスを避ける設計（関数に target_date を明示的に渡す）
- J-Quants クライアントは rate limiting と retry 処理を含む
- .env パーサはシェル形式の export 文やクォート、コメントを理解する堅牢な実装

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                              — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                           — ニュース NLP スコアリング
  - regime_detector.py                    — 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py                     — J-Quants API クライアント & DuckDB 保存
  - pipeline.py                           — ETL パイプライン / run_daily_etl 等
  - etl.py                                — ETLResult の再エクスポート
  - quality.py                            — データ品質チェック
  - stats.py                              — zscore_normalize 等
  - news_collector.py                      — RSS 収集 / 前処理
  - calendar_management.py                — マーケットカレンダー管理
  - audit.py                              — 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py                    — calc_momentum / calc_value / calc_volatility
  - feature_exploration.py                — calc_forward_returns / calc_ic / factor_summary / rank
- research などはバックテスト・研究用ユーティリティを提供

よくある運用上の注意
- OpenAI 呼び出しはコストとレート制限があるため、実行は制御して下さい（テストではモック推奨）。
- J-Quants トークンは settings.jquants_refresh_token に設定しておく必要があります。
- DuckDB ファイルのバックアップ／バージョニングを検討してください（ETL により上書きされることあり）。
- .env の自動ロードはプロジェクトルート検出に基づくため、パッケージ配布後やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です。

サポート / 追加情報
-------------------
- 各モジュール内に詳細な docstring（日本語）が含まれており、関数の引数・戻り値や設計方針が記載されています。まずは docstring を参照してください。
- 実運用ではログ（LOG_LEVEL）設定、監視（PID ファイル、リソース閾値）や Slack 通知などを組み合わせることを推奨します。

以上がこのコードベースの概要と使い方です。README に追加したい実行例や CI/テスト手順、requirements.txt をご希望であれば追記します。