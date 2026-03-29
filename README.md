KabuSys — 日本株自動売買プラットフォーム（README）
=================================

概要
----
KabuSys は日本株向けのデータプラットフォーム／研究基盤／自動売買補助ライブラリ群です。主に以下を目的としています。

- J-Quants API からのデータ取得（株価日足、財務、マーケットカレンダー）
- ETL（差分取得・保存・品質チェック）パイプライン
- ニュース収集・NLP（LLM を使ったセンチメント）処理
- 市場レジーム判定（ETF MA とマクロニュースを統合）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- 監査ログ（signal → order → execution のトレーサビリティ）
- 各種ユーティリティ（カレンダー管理、データ品質チェック、統計関数）

このリポジトリは主にライブラリ群として実装されており、DuckDB を中心としたローカル DB をデータ格納に使用します。LLM は OpenAI（gpt-4o-mini）を想定しています。

主な機能
--------
- データ取得 / 保存
  - J-Quants API クライアント（fetch / save の idempotent 実装）
  - RSS からのニュース収集（SSRF 対策、トラッキングパラメータ除去、冪等保存）
  - 市場カレンダー更新ジョブ（差分取得・バックフィル）

- ETL
  - 差分取得（最後の取得日をもとに差分を自動算出）
  - 品質チェック（欠損、重複、スパイク、日付整合性）
  - 日次 ETL の統合実行（run_daily_etl）

- AI / NLP
  - ニュースの銘柄別センチメント付与（score_news）
  - 市場レジーム判定（1321 の MA200 とマクロニュースを統合して daily regime を判定）

- Research
  - ファクター計算（モメンタム、バリュ―、ボラティリティ）
  - 将来リターン、IC（Information Coefficient）、統計サマリー
  - Z スコア正規化ユーティリティ

- 監査（Audit）
  - signal_events / order_requests / executions テーブルとインデックスの初期化（init_audit_schema / init_audit_db）
  - 発注トレーサビリティを保証するスキーマと制約

セットアップ
----------
前提
- Python 3.10 以上（型アノテーションで | を使用）
- 必要な Python パッケージ: duckdb, openai, defusedxml（その他標準ライブラリ）

インストール例（仮）
1) 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate

2) 必要パッケージのインストール
   pip install duckdb openai defusedxml

   （パッケージを packaging にまとめている場合はリポジトリルートで）
   pip install -e .

環境変数
- 自動ロード:
  パッケージはプロジェクトルート（.git または pyproject.toml）を探索し、.env と .env.local を自動で読み込む仕組みがあります。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- 必須/主要な環境変数:
  - JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
  - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
  - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
  - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に使用）
  - DUCKDB_PATH: デフォルト DuckDB パス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - KABUSYS_ENV: 実行環境（development | paper_trading | live、デフォルト development）
  - LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト INFO）

例 (.env)
  JQUANTS_REFRESH_TOKEN=xxxxx
  OPENAI_API_KEY=sk-xxxxx
  KABU_API_PASSWORD=your_kabu_password
  SLACK_BOT_TOKEN=xoxb-xxxx
  SLACK_CHANNEL_ID=C01234567
  DUCKDB_PATH=data/kabusys.duckdb
  KABUSYS_ENV=development

初期化（DB / スキーマ）
- 監査ログ用 DB を作成する例:
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は DuckDB 接続オブジェクト（duckdb.DuckDBPyConnection）

- データ格納用 DuckDB のパスは設定（環境変数 DUCKDB_PATH）に従ってください。
  例:
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(settings.duckdb_path)

基本的な使い方（主要 API）
-------------------------

- 日次 ETL 実行（株価・財務・カレンダー取得＋品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  # ETLResult オブジェクト（取得件数やエラー・品質問題を含む）

- ニュースセンチメント（AI）スコア付与
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date
  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  # ai_scores テーブルへ書き込み。戻り値は書込み銘柄数。

  注意: OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡してください。

- 市場レジーム判定（MA200 とマクロニュースの統合）
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  # market_regime テーブルへ書き込まれます

  注意: OPENAI_API_KEY が必要（api_key 引数または環境変数）。

- 研究用ファクター計算
  from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize
  import duckdb
  from datetime import date
  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2026,3,20))
  vol = calc_volatility(conn, target_date=date(2026,3,20))
  value = calc_value(conn, target_date=date(2026,3,20))
  normed = zscore_normalize(momentum, columns=["mom_1m", "mom_3m"])

注意点 / 設計上の留意事項
-----------------------
- ルックアヘッドバイアス対策:
  多くのモジュールは内部で date.today() や datetime.now() を直接バックテストループに用いない設計になっており、target_date を明示的に与えることで過去時点で入手可能なデータのみを利用することを推奨します。

- 冪等性:
  J-Quants の保存関数や ETL の保存は ON CONFLICT DO UPDATE 等により冪等に作られています。

- フェイルセーフ:
  AI 呼び出しや API 呼び出しに失敗した場合、システムは例外投げっぱなしではなくフォールバック（例: macro_sentiment = 0.0）やスキップで継続する設計が多いです。ログを参照してください。

- テスト容易性:
  OpenAI など外部呼び出しは内部的に _call_openai_api 等で抽象化され、ユニットテスト時にはモック可能です。

ディレクトリ構成（主なファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - calendar_management.py
  - etl.py
  - pipeline.py
  - stats.py
  - quality.py
  - audit.py
  - jquants_client.py
  - news_collector.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring/ (パッケージに含まれる想定モジュール)
- strategy/, execution/ など（パッケージ __all__ に定義あり。リポジトリによっては別ファイルが存在）

補足: 上記は主要なファイル一覧です。各モジュールに詳細な docstring / 設計コメントが含まれていますので、実装の流れや SQL、パラメータの意味はソース内コメントを参照してください。

サポート・開発のヒント
--------------------
- ロギングは各モジュールで logger = logging.getLogger(__name__) を使用しています。LOG_LEVEL 環境変数で出力レベルを調整してください。
- DuckDB の接続はモジュール内で受け渡す形（duckdb.connect(... ) の戻り値）を想定しています。
- OpenAI の利用はコストが発生します。score_news はバッチで銘柄をまとめて送る工夫をしていますが、実運用ではキー管理とレート制御に注意してください。
- news_collector は RSS の取得・XML パース・URL 正規化等にセキュリティ対策（SSRF、XML Bomb）を組み込んでいます。RSS ソース追加や運用設定変更時は実装を確認してください。

ライセンス
---------
（このリポジトリにライセンスファイルがある場合はそれに従ってください。README には明示されていません。）

最後に
------
この README はコードベースの主要機能と利用手順の概要を示しています。詳細な API 引数や戻り値、エラー挙動については各モジュールの docstring を参照してください。質問や補足の希望があれば実行例やより詳細なセットアップ手順（Docker / CI 用の設定など）を追記します。