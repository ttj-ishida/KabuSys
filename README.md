KabuSys — 日本株向けデータ基盤・自動売買補助ライブラリ
=================================================

概要
----
KabuSys は日本株向けのデータ収集（J-Quants）、品質チェック、特徴量計算、ニュースNLP（OpenAI）を用いたセンチメント評価、そして自動売買の監査ログ設計を支援する Python モジュール群です。DuckDB をデータ層に用い、ETL パイプラインやニュース収集、ファクター計算、マーケットレジーム判定など、バックテスト／研究／実運用の基礎処理を提供します。

設計上のポイント
- Look-ahead bias を意図的に避ける設計（target_date 引数を明示的に扱う）
- DuckDB を中心とした idempotent（冪等）な DB 保存ロジック
- OpenAI（gpt-4o-mini）を用いたニュース集約・スコアリング（JSON mode 利用想定）
- J-Quants API 用の頑健な HTTP/認証・レート制御・リトライ処理
- ニュース収集での SSRF / XML 攻撃対策（URL 検証・defusedxml 利用）
- 監査ログ（signal → order_request → executions）を冪等に残すスキーマ

主な機能
--------
- データ ETL
  - J-Quants からの株価日足（raw_prices）、財務データ（raw_financials）、市場カレンダー（market_calendar）取得・保存
  - 差分取得・バックフィル・品質チェックの一括実行（run_daily_etl）
- データ品質チェック
  - 欠損（OHLC）・重複・スパイク（急変）・日付不整合チェック
- ニュース収集・処理
  - RSS 取得、テキスト前処理、記事ID 正規化、raw_news / news_symbols への保存支援
  - SSRF 保護・サイズ制限・XML 安全対策搭載
- ニュースNLP（OpenAI）
  - 銘柄ごとのニュース集約と LLM によるセンチメントスコア付与（score_news）
  - マクロ記事を用いた市場レジーム判定（score_regime）
- ファクター計算・研究用ユーティリティ
  - Momentum / Volatility / Value 等の計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ、Zスコア正規化
- 監査ログ（audit）
  - signal_events, order_requests, executions のテーブル定義・初期化（init_audit_schema / init_audit_db）
- J-Quants クライアント
  - 認証（リフレッシュトークン→id_token）、ページネーション、レート制御、リトライ、データ保存関数

セットアップ手順
----------------
前提
- Python 3.10 以上（PEP 604 の union 型記法などを使用）
- DuckDB（Python パッケージ）、openai、defusedxml などの外部パッケージ

推奨手順（例）
1. 仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトで requirements.txt / pyproject.toml があればそれに従ってください。）

3. 環境変数設定
   - プロジェクトルートに .env（および開発用 .env.local）を置くと自動ロードされます。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注連携がある場合）
- KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知設定（必要に応じて）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV: environment ('development'|'paper_trading'|'live')
- LOG_LEVEL: 'DEBUG'|'INFO'|'WARNING'|'ERROR'|'CRITICAL'

（.env の読み込み挙動）
- 自動で .env → .env.local の順で読み込み（OS 環境変数は優先）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード停止

使い方（簡易例）
---------------

共通: DuckDB 接続の作成
- Python から直接利用する場合の基本
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")  # ":memory:" も可

ETL（日次 ETL 実行）
- from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

株価データのみ差分 ETL
- from kabusys.data.pipeline import run_prices_etl
  fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))

ニュース NLP スコア付与（OpenAI 必須）
- from datetime import date
  from kabusys.ai.news_nlp import score_news
  # api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定
  n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
  print("書き込んだ銘柄数:", n_written)

市場レジーム判定（ETF 1321 の MA200 + マクロニュース）
- from datetime import date
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,3,20), api_key=None)

監査 DB 初期化（監査専用 DuckDB を作る）
- from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions 等が作成されます

ファクター計算（研究用）
- from kabusys.research.factor_research import calc_momentum
  records = calc_momentum(conn, target_date=date(2026,3,20))
- 正規化ユーティリティ:
  - from kabusys.data.stats import zscore_normalize

注意事項（運用・開発）
- OpenAI API 呼び出しはコスト・レート制限に注意。retry/backoff を備えていますが、実行頻度やモデルは運用方針に合わせてください。
- J-Quants API はレート制限（120 req/min）に従います。get_id_token や fetch 系は自動で調整しますが、用途によっては注意してください。
- ETL は idempotent であることを目指していますが、DB スキーマや外部 API の仕様変更時は注意が必要です。
- news_collector は SSRF 対策や response サイズ制限を入れていますが、RSS ソースの信頼性と規模を考慮して運用して下さい。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                     — 環境変数 / 設定管理（.env 自動ロード）
- ai/
  - __init__.py
  - news_nlp.py                 — ニュースセンチメント（score_news）
  - regime_detector.py          — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
  - etl.py                      — ETLResult の再エクスポート
  - jquants_client.py           — J-Quants API クライアント（取得・保存）
  - news_collector.py           — RSS ニュース収集
  - quality.py                  — データ品質チェック
  - stats.py                    — 統計ユーティリティ（zscore_normalize）
  - calendar_management.py      — 市場カレンダー管理（is_trading_day 等）
  - audit.py                    — 監査ログテーブル定義・初期化
- research/
  - __init__.py
  - factor_research.py          — Momentum/Volatility/Value 計算
  - feature_exploration.py      — 将来リターン計算・IC・統計要約
- ai/__init__.py
- research/__init__.py

開発上のポイント
- テスト時は OpenAI や HTTP クライアント呼び出しをモックする設計（各モジュール内で差し替えしやすい実装）。
- DuckDB の executemany に空リストを渡すとエラーになるバージョン対策（コード内でチェック済み）。
- 日付関連の処理はすべて timezone-naive な UTC もしくは date オブジェクトで扱う設計方針（Look-ahead 防止）。

ライセンス / 貢献
-----------------
（本リポジトリにライセンス記載がある場合はそちらに従ってください。開発・バグ報告・機能リクエストは issue / PR を通じて受け付けてください。）

付録: 最小 .env テンプレート例
-----------------------------
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=your_slack_token
SLACK_CHANNEL_ID=your_slack_channel_id
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

以上。何か特定の使用例（ETL の実行スクリプト、監査テーブルの利用例、CI 設定など）を README に追加したい場合は用途を教えてください。