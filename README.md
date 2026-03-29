KabuSys — 日本株自動売買プラットフォーム
=================================

概要
----
KabuSys は日本株のデータ収集（ETL）・品質チェック・ファクター計算・ニュース/NLP スコアリング・市場レジーム判定・監査ログ管理を備えた研究／運用向けのライブラリ群です。  
設計上のポイントは以下の通りです。

- DuckDB を中心としたローカル DB（データレイク）運用
- J-Quants API を使った差分 ETL（レートリミット・リトライ・トークン自動更新対応）
- ニュースを LLM（OpenAI）でスコアリングして ai_scores に保存
- ファクター・特徴量解析（研究用途）と Z-score 正規化ユーティリティ
- 監査ログ（signal → order_request → execution のトレーサビリティ）スキーマ初期化機能
- 自動環境変数ロード（.env / .env.local）と Settings 抽象

主な機能
--------
- Data
  - ETL パイプライン（daily ETL / prices / financials / calendar）
  - J-Quants API クライアント（取得 + DuckDB 保存）
  - カレンダー管理（営業日判定、next/prev/get_trading_days、calendar update job）
  - ニュース収集（RSS 取得 / 前処理 / raw_news 挿入）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログスキーマ初期化（audit テーブル群、init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- AI
  - ニュース NLP スコアリング（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
  - LLM 呼び出しは OpenAI（gpt-4o-mini など）を利用、JSON モードで結果取得
- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー、ランク付け
- ETL / pipeline
  - run_daily_etl による一括 ETL 実行、品質チェックの統合
- 設定 / 環境
  - 環境変数読み込み（.env / .env.local の自動ロード。無効化可）

セットアップ
-----------

前提
- Python 3.10 以上（コード中で PEP 604 記法などを使用）
- DuckDB, openai, defusedxml 等の依存ライブラリ

推奨手順（プロジェクトルートに pyproject.toml/.git がある想定）
1. 仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 依存定義ファイル（requirements.txt / pyproject.toml）がある場合:
     - pip install -r requirements.txt
     - または pip install .
   - 主な必要パッケージ（例）:
     - pip install duckdb openai defusedxml

3. 環境変数設定（.env をプロジェクトルートに配置）
   - 自動ロード: パッケージ import 時にプロジェクトルートの .env → .env.local が順に読み込まれます（OS 環境変数が優先）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 必要なキー（最低限）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
   - オプション:
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live)（デフォルト development）
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)

サンプル .env（簡易）
- .env.example を参考に作成してください。例:
  JQUANTS_REFRESH_TOKEN=xxxxx
  OPENAI_API_KEY=sk-...
  KABU_API_PASSWORD=your_kabu_pass
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C0123456
  DUCKDB_PATH=data/kabusys.duckdb

使い方（概要）
------------

基本的な DB 接続
- DuckDB 接続を作成して各機能に渡します。
  - 例（Python REPL / スクリプト）:
    from datetime import date
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")  # デフォルト path を使用する場合
    # ETL 実行や AI スコアリングに conn を渡す

ETL（データ取得）実行
- 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）:
    from kabusys.data.pipeline import run_daily_etl
    from datetime import date
    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026,3,20))
    print(result.to_dict())

個別 ETL ジョブ
- run_prices_etl / run_financials_etl / run_calendar_etl を直接呼ぶことも可能。

ニュース収集（RSS）
- 関数 fetch_rss で RSS を取得して raw_news に保存する処理を組み立てます。
  - fetch_rss は URL の検証（SSRF 対策）、gzip サイズチェック、XML 脆弱性対策を行います。
  - 取得後は DB に対する保存処理（news_symbols 連携等）を実装してください（サンプルはモジュール内に沿った設計）。

ニュース NLP（LLM）
- 日付ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）内のニュースを銘柄ごとに統合して LLM に送信し、ai_scores に保存します。
  - 例:
    from kabusys.ai.news_nlp import score_news
    from datetime import date
    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
    print("written:", n_written)

市場レジーム判定
- ETF（1321）の MA200 とマクロニュースの LLM センチメントを合成して market_regime テーブルに保存します。
  - 例:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

ファクター計算 / 研究ユーティリティ
- モメンタム / ボラティリティ / バリューなどのファクターを計算し、forward returns / IC / summary を行えます。
  - 例:
    from kabusys.research.factor_research import calc_momentum
    records = calc_momentum(conn, target_date=date(2026,3,20))

監査ログ初期化（発注トレーサビリティ）
- 監査用 DB を初期化:
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")

設定（環境変数）について
-----------------------
- 自動ロード:
  - パッケージ import 時にプロジェクトルートを .git または pyproject.toml から探し、.env → .env.local を読み込みます。
  - 既存 OS 環境変数は保護され、.env の値は上書きされません（.env.local は override=True で上書き可）。
  - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で有用）。
- Settings API:
  - from kabusys.config import settings
  - settings.jquants_refresh_token 等のプロパティで値を取得できます。必須項目がないと ValueError が上がります。

ディレクトリ構成（要点）
---------------------
ここではソース内の主要モジュールを抜粋して説明します。

- src/kabusys/
  - __init__.py                 パッケージ定義（data, strategy, execution, monitoring を公開）
  - config.py                   環境変数 / .env ロード / Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py               ニュースの LLM スコアリング（score_news）
    - regime_detector.py        市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py         J-Quants API クライアント（fetch / save）
    - pipeline.py               ETL パイプライン（run_daily_etl 等）
    - etl.py                    ETLResult の再エクスポート
    - calendar_management.py    マーケットカレンダー管理（is_trading_day等）
    - news_collector.py         RSS 収集・前処理
    - quality.py                データ品質チェック
    - stats.py                  統計ユーティリティ（zscore_normalize）
    - audit.py                  監査ログ（DDL / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py        ファクター計算（momentum/value/volatility）
    - feature_exploration.py    将来リターン・IC・summary・rank 等
  - research/ 以下は研究用ユーティリティ群

開発・運用上の注意点
-------------------
- Look-ahead バイアス回避:
  - モジュールの多くが date 引数ベースで動作し、内部で datetime.today()/date.today() を直に参照しないように設計されています。バックテストでは target_date を明示的に渡してください。
- LLM 呼び出し:
  - OpenAI API を使います。API エラー時はフェイルセーフ（スコア=0 等）にフォールバックするロジックが組まれていますが、APIキーとレート・費用に注意してください。
- J-Quants:
  - レート制限（120 req/min）厳守のため内部でスロットリングが入ります。ID トークンの自動リフレッシュに対応しています。
- DuckDB: executemany の空パラメータに制約があるバージョンを考慮した実装が行われています。

貢献・テスト
-------------
- 新機能や修正を行う場合は、ユニットテストで外部 API 呼び出しをモックすること（例: OpenAI / urllib / jq クライアント）。news_nlp / regime_detector では _call_openai_api のモックが容易になるよう設計されています。
- 自動環境読み込みはテスト時に影響するため、KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して無効化してください。

ライセンス
---------
- 本リポジトリにはライセンスファイルが含まれていない場合があります。実運用・配布前に適切なライセンスを明記してください。

問い合わせ
----------
- 実装の詳細や使用方法で不明点があれば、該当モジュール（例: kabusys.data.pipeline, kabusys.ai.news_nlp）を参照してください。README に記載のない具体例や CLI スクリプトが必要であれば、用途に合わせたサンプルを提供します。