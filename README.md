KabuSys
=======

KabuSys は日本株向けのデータプラットフォームと自動売買（リサーチ / ETL / AI / 監査ログ）補助ライブラリです。本リポジトリは DuckDB を用いたデータ格納・品質チェック、J-Quants からの差分 ETL、RSS ニュース収集、OpenAI を用いたニュース NLP / 市場レジーム判定、監査ログスキーマなどを提供します。

主な特徴
--------
- データ ETL
  - J-Quants API から株価（日次 OHLCV）、財務、マーケットカレンダーを差分取得・保存する ETL パイプライン（run_daily_etl）。
  - 差分更新・バックフィル対応、冪等保存（ON CONFLICT DO UPDATE）。
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合などを検出する品質チェック群（data.quality）。
- ニュース収集と NLP
  - RSS 収集（SSRF 対策、トラッキングパラメータ除去）と raw_news への保存ロジック（news_collector）。
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント算出（news_nlp.score_news）。
- 市場レジーム判定
  - ETF（1321）の 200 日 MA 乖離とマクロニュースセンチメントを合成して日次レジームを算出・保存（ai.regime_detector.score_regime）。
- 研究用ファクター計算
  - モメンタム/バリュー/ボラティリティ等のファクター計算（research）。
- 監査ログ（トレーサビリティ）
  - signal → order_request → execution に至る監査テーブル定義と初期化ユーティリティ（data.audit）。
- 環境設定管理
  - .env/.env.local の自動読み込み、環境変数保護、設定クラス（config.Settings）。

セットアップ手順
---------------

前提
- Python 3.10+（ソース内で型ヒントに | を用いているため）
- DuckDB (Python パッケージ)
- OpenAI SDK（openai パッケージ）
- defusedxml（RSS パース用）
- その他：urllib, typing 等の標準ライブラリ

推奨仮想環境作成とインストール（例）
1. 仮想環境を作成・有効化:
   python -m venv .venv
   source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール（プロジェクトに requirements.txt が無い場合の例）:
   pip install duckdb openai defusedxml

3. 開発インストール（パッケージとして使う場合）:
   pip install -e .

環境変数
- .env 自動読み込み:
  - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml がある親ディレクトリ）を探索し、
    .env → .env.local（.env.local は .env を上書き）を自動的に読み込みます。
  - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- 主な環境変数（Settings で参照されるもの）
  - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
  - KABU_API_PASSWORD : kabuステーション API パスワード（必須）
  - KABU_API_BASE_URL : デフォルト http://localhost:18080/kabusapi
  - OPENAI_API_KEY : OpenAI API キー（score_news/score_regime 実行時に使用）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : 通知用途（任意）
  - DUCKDB_PATH : デフォルト data/kabusys.duckdb
  - SQLITE_PATH : 監視用 SQLite デフォルト data/monitoring.db
  - PID_FILE_PATH / KILL_FLAG_PATH : 監視関連
  - KILL_FLAG_CLEAR_ON_START : "1" にすると起動時にキルフラグをクリア
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT : 監視閾値
  - KABUSYS_ENV : development / paper_trading / live（デフォルト development）
  - LOG_LEVEL : DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）

使い方（主要 API / 例）
---------------------

基本的な DuckDB 接続
- DuckDB ファイルを使用する例:
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")

ETL（デイリー）
- 日次 ETL を実行して prices/financials/calendar を取得・保存し品質チェックを実行:
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())

- 個別ジョブ:
  from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
  run_prices_etl(conn, target_date=date(2026,3,20))
  run_calendar_etl(conn, target_date=date(2026,3,20))

ニュース NLP（OpenAI）
- 指定日のニュースウィンドウ（前日15:00 JST〜当日08:30 JST）をスコアリングして ai_scores に保存:
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")

- 注意: api_key が None の場合は環境変数 OPENAI_API_KEY が利用されます。API 呼び出しに失敗したチャンクはスキップして継続する設計です。

市場レジーム判定（Regime）
- ETF(1321) の ma200 乖離とマクロニュースセンチメントを合成して market_regime テーブルへ書き込み:
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026,3,20), api_key=None)

監査ログ初期化
- 監査用 DuckDB を初期化して接続を取得:
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # 既存接続へスキーマのみ追加する場合:
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

設定値の参照
- アプリ設定を参照:
  from kabusys.config import settings
  print(settings.duckdb_path, settings.env, settings.is_live)

ログ設定
- 環境変数 LOG_LEVEL でログレベルを制御できます。アプリ起動時に logging.basicConfig 等を設定してください。

設計上の注意点 / 実装上のポイント
--------------------------------
- ルックアヘッドバイアス回避:
  - news_nlp / regime_detector / research 等の関数は内部で date.today() を参照せず、必ず引数の target_date に基づいて処理します。バックテストでの使用では重要です。
- 冪等性:
  - J-Quants データ保存や ai_scores 書き込みなどは冪等に設計されています（ON CONFLICT DO UPDATE / DELETE→INSERT）。
- フェイルセーフ:
  - OpenAI API 等の外部 API 呼び出しはリトライやフォールバック（失敗時は 0.0 またはスキップ）で継続する設計です。
- セキュリティ:
  - RSS 収集は SSRF 対策、XML の安全なパース（defusedxml）を採用しています。
- テスト容易性:
  - OpenAI 呼び出し等はモジュール内の _call_openai_api をモックしてテスト可能です。
  - 自動 .env ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を利用可能。

ディレクトリ構成（主要ファイル）
-----------------------------
リポジトリの主要なパスは以下の通り（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュース NLP スコアリング
    - regime_detector.py          — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
    - etl.py                      — ETLResult エクスポート
    - calendar_management.py      — マーケットカレンダー管理（is_trading_day 等）
    - news_collector.py           — RSS ニュース収集
    - quality.py                  — データ品質チェック
    - stats.py                    — 汎用統計ユーティリティ（zscore）
    - audit.py                    — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py          — Momentum/Value/Volatility 等
    - feature_exploration.py      — 将来リターン / IC / 統計要約 等

挙動・動作上の注意
-----------------
- .env パーサはシェル風の export KEY=val やクォート・エスケープ・行末コメントを取り扱いますが、
  .env.example を参考に必要な環境変数を設定してください。
- J-Quants API レートリミット（120 req/min）を尊重するため内部でスロットリングとリトライを行います。
- OpenAI モデルは gpt-4o-mini を想定しています（レスポンスを JSON モードで受け取る設計）。
- DuckDB のバージョン依存の注意点（executemany の空リスト等）に配慮した実装があるため、
  DuckDB は比較的新しい安定版を使うことを推奨します。

開発・テスト
-------------
- OpenAI 呼び出しをモックする際は、kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api を patch してください。
- .env の自動ロードを抑止するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してテストを実行してください。

ライセンス / 貢献
-----------------
- （本 README はコードベースの説明用テンプレートです。実際のライセンスや貢献ルールはリポジトリの LICENSE / CONTRIBUTING を参照してください。）

補足
----
この README はソース内のドキュメント文字列と公開 API を元に要点をまとめたものです。各関数・モジュールの詳細な使い方やパラメータの振る舞いはソースコード内の docstring を参照してください。必要であれば、特定モジュール（例: ETL の実行フロー、news_nlp のプロンプト定義、jquants_client の認証フロー等）に関する詳しいセクションを追加します。