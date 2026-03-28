KabuSys — 日本株自動売買プラットフォーム（README 日本語版）
====================================

概要
----
KabuSys は日本株向けのデータ基盤・研究・AI スコアリング・監査ログ・ETL を含む
自動売買システムのライブラリ群です。本リポジトリは以下の主要機能を提供します。

- J-Quants API からのデータ取得（株価日足・財務・カレンダー等）と DuckDB への冪等保存
- ニュース収集（RSS）とニュースベースの LLM センチメント評価（OpenAI）
- マーケットレジーム判定（ETF MA + マクロニュースによる合成）
- ファクター計算（モメンタム／バリュー／ボラティリティ等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）
- ETL の統合実行（差分取得・保存・品質チェック）

主な特徴（機能一覧）
-----------------
- data/jquants_client: J-Quants API クライアント（レート制御・トークン自動リフレッシュ・再試行ロジック付き）
- data/pipeline: 日次 ETL 実行（prices/financials/calendar の差分取得・保存・品質チェック）
- data/news_collector: RSS 収集（SSRF 対策・トラッキング除去・GZIP/サイズ制限）
- data/quality: データ品質チェック一式（欠損 / スパイク / 重複 / 日付整合性）
- data/audit: 監査ログ用 DuckDB スキーマ初期化・ユーティリティ
- ai/news_nlp: ニュースを銘柄毎にまとめて LLM に投げ、銘柄別 ai_score を ai_scores テーブルへ保存
- ai/regime_detector: ETF(1321) の MA200 乖離とマクロニュースの LLM スコアを合成して市場レジーム判定
- research: ファクター計算（momentum/value/volatility）と特徴量解析（forward returns / IC / summary）
- data/stats: z-score 正規化等の統計ユーティリティ
- 設定: 環境変数（.env 自動ロード対応）経由の設定管理（kabusys.config）

要件（簡易）
-------------
- Python 3.10+
- 依存（主なもの）:
  - duckdb
  - openai
  - defusedxml
  - 標準ライブラリ（urllib, json, datetime 等）

セットアップ手順
----------------

1. リポジトリをクローン / 取得し、開発パッケージとしてインストール（任意）:
   - 推奨: 仮想環境を作成して activate する
   - pip install -e . が可能な構成であればそれを利用

2. 必要なパッケージをインストール:
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があればそれを使用）

3. 環境変数の準備:
   - プロジェクトルートに .env（および任意で .env.local）を置くと自動でロードされます
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu API のパスワード（注文連携がある場合）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必要なら）
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意 / デフォルトあり:
     - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live)（default: development）
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)（default: INFO）
   - OpenAI を使う機能（news_nlp / regime_detector）を使う場合:
     - OPENAI_API_KEY 環境変数を設定するか、各関数に api_key 引数で渡す

使い方（主要な操作例）
--------------------

- DuckDB 接続の準備（デフォルト path を使う例）:

  from pathlib import Path
  import duckdb
  from kabusys.config import settings

  db_path = settings.duckdb_path  # Path オブジェクト
  conn = duckdb.connect(str(db_path))

- 日次 ETL の実行（run_daily_etl）:

  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

  - ETLResult には取得件数 / 保存件数 / 品質チェック結果 / エラーメッセージが含まれる

- ニュース収集（RSS）と保存（news_collector.fetch_rss を利用して raw_news へ保存するロジックは別途 ETL などで実装）:

  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  # 返り値は NewsArticle 型の list（id, datetime, source, title, content, url）

- News NLP スコア生成（銘柄別 ai_scores への書き込み）:

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None → OPENAI_API_KEY を参照
  print(f"書き込み銘柄数: {written}")

- 市場レジーム判定（regime_detector）:

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査ログスキーマの初期化（監査 DB を別ファイルで保つ場合）:

  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit_duckdb.db")
  # これで監査用テーブル（signal_events, order_requests, executions）とインデックスが作成される

- 研究用ユーティリティ（例: モメンタム計算）:

  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect(str(settings.duckdb_path))
  momentum_records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # 結果は dict のリストで返る

注意事項 / 設計上のポイント
-------------------------
- ルックアヘッドバイアス防止: 主要な処理（news_window, ma200, ETL など）は内部で date.today() を不用意に参照せず、
  呼び出し側が target_date を明示することでバックテストでの漏洩を防止する設計です。
- OpenAI 呼び出しは再試行・フェイルセーフを実装しており、API 失敗時はスコアを 0 にフォールバックする等の挙動があります。
- J-Quants クライアントはレート制限を守るための RateLimiter と、401 時のトークンリフレッシュを備えています。
- news_collector は SSRF 対策・Gzip サイズ上限・トラッキング除去などを実装しているため、安全に RSS を取り込めます。
- DuckDB への書き込みは基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING 等）です。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py                 - パッケージ初期化（version）
- config.py                   - 環境変数 / 設定管理（.env 自動ロード）
- ai/
  - __init__.py               - ai パッケージ公開関数
  - news_nlp.py               - ニュース NLP スコアリング（ai_scores へ書き込み）
  - regime_detector.py        - 市場レジーム判定ロジック
- data/
  - __init__.py
  - jquants_client.py         - J-Quants API クライアント（fetch/save）
  - pipeline.py               - ETL パイプライン（run_daily_etl 等）
  - etl.py                    - ETLResult の再エクスポート
  - news_collector.py         - RSS ニュース収集
  - calendar_management.py    - 市場カレンダー管理・営業日ユーティリティ
  - quality.py                - データ品質チェック
  - stats.py                  - 統計ユーティリティ（zscore_normalize）
  - audit.py                  - 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py        - ファクター計算（momentum/value/volatility）
  - feature_exploration.py    - 将来リターン・IC・summary・rank 等
- research/...                - その他の研究用ユーティリティ

開発 / テストのヒント
----------------------
- .env はプロジェクトルート（.git または pyproject.toml がある場所）から自動読み込みされます。テストで自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しをテストする場合、内部の _call_openai_api 関数を unittest.mock.patch で差し替えることで外部 API 依存を排除できます（news_nlp と regime_detector はそれぞれ独立した _call_openai_api 実装を持ちます）。
- DuckDB の一時 DB を使う場合は ":memory:" を渡せます（audit.init_audit_db など）。

ライセンス / 貢献
-----------------
本 README はコードベースの説明です。実運用・商用利用を行う際は依存ライブラリのライセンス・API 利用規約（J-Quants, OpenAI 等）を確認してください。バグ報告・プルリクエストは歓迎します。

以上。必要ならサンプル .env.example や、CLI ベースの実行スクリプト（run_etl.py 等）のテンプレートを追記できます。ご希望があれば追加で作成します。