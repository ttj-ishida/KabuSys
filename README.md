KabuSys — 日本株自動売買プラットフォーム
=================================

概要
----
KabuSys は日本株向けのデータパイプライン、ファクター研究、ニュースNLP、監査ログなどを備えた自動売買／リサーチ基盤用の Python ライブラリ群です。本コードベースは以下の主要機能群を含みます。

- J-Quants API からのデータ取得（株価日足・財務データ・市場カレンダー）
- ETL パイプライン（差分取得、保存、品質チェック）
- ニュース収集（RSS）とニュースの NLP（OpenAI）による銘柄別センチメント付与
- 市場レジーム判定（ETF の MA とマクロニュースの LLM センチメントを合成）
- ファクター計算（モメンタム／バリュー／ボラティリティ等）と探索的分析ユーティリティ
- 監査ログ（signal → order_request → execution のトレーサビリティ）用 DuckDB スキーマ
- マーケットカレンダー管理（営業日判定・更新ジョブ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

主な機能一覧
-------------
- data.jquants_client: J-Quants API クライアント（レートリミット、リトライ、トークンリフレッシュ、DuckDB への冪等保存）
- data.pipeline: 日次 ETL（run_daily_etl）と個別 ETL ジョブ（prices, financials, calendar）
- data.news_collector: RSS 取得・前処理・raw_news への保存（SSRF 対策・トラッキング除去・受信サイズ制限）
- data.quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
- data.calendar_management: JPX カレンダー管理と営業日計算ユーティリティ
- data.audit: 監査ログテーブル定義と初期化（init_audit_schema / init_audit_db）
- data.stats: zscore_normalize 等の共通統計ユーティリティ
- research.*: ファクター計算・特徴量探索（calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic など）
- ai.news_nlp: ニュースの LLM スコアリング（score_news）
- ai.regime_detector: ETF（1321）の MA200 乖離とマクロニュース LLM を合成して市場レジームを判定（score_regime）
- config: 環境変数・設定管理（自動 .env ロード、設定プロパティ）

前提（Prerequisites）
--------------------
- Python 3.10 以上（型記法や | 演算子を使用）
- 以下のパッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス: J-Quants API、OpenAI、RSS ソース など
- DuckDB ファイルの保存先（デフォルト: data/kabusys.duckdb）

セットアップ手順
----------------

1. リポジトリをクローンしてソースをインストール
   - 開発環境であれば editable install 推奨:
     pip install -e .

2. 必要パッケージをインストール（例）
   pip install duckdb openai defusedxml

   ※プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください。

3. 環境変数（または .env）を準備
   ルートに .env または .env.local を作成すると、kabusys.config が自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば無効化可）。

   最低限必要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_api_password
   - SLACK_BOT_TOKEN=your_slack_bot_token
   - SLACK_CHANNEL_ID=your_slack_channel_id
   - OPENAI_API_KEY=your_openai_api_key (score_news/score_regime 実行時に使用されます)

   その他:
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - KABUSYS_ENV: development / paper_trading / live
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

4. データディレクトリの作成（必要に応じて）
   デフォルトで data/ 以下に DB ファイルを作成します。必要であれば事前にディレクトリを作成してください。

基本的な使い方
--------------

以下は Python REPL / スクリプトからの簡単な利用例です。DuckDB の接続は duckdb.connect() を使用します。

- 日次 ETL の実行（例: 今日分の ETL）
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- ニュースの NLP スコア付与（score_news）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # target_date はスコア生成日（前日 15:00 JST ～ 当日 08:30 JST を対象）
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")

- 市場レジーム判定（score_regime）
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ DB 初期化
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # テーブルが作成され、UTC タイムゾーンが設定されます

- ETL をテストする際のヒント
  - OPENAI 呼び出しや RSS 取得はネットワークに依存するため、テストでは関数（_call_openai_api など）を unittest.mock.patch で差し替えてモックしてください。
  - 自動 .env ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

設定と環境変数
----------------
kabusys.config.Settings から以下プロパティでアクセス可能です:

- jquants_refresh_token (JQUANTS_REFRESH_TOKEN) — 必須
- kabu_api_password (KABU_API_PASSWORD) — 必須
- kabu_api_base_url (KABU_API_BASE_URL) — 既定: http://localhost:18080/kabusapi
- slack_bot_token (SLACK_BOT_TOKEN) — 必須
- slack_channel_id (SLACK_CHANNEL_ID) — 必須
- duckdb_path (DUCKDB_PATH) — 既定: data/kabusys.duckdb
- sqlite_path (SQLITE_PATH) — 既定: data/monitoring.db
- env (KABUSYS_ENV) — development / paper_trading / live
- log_level (LOG_LEVEL) — DEBUG/INFO/...

自動 .env ロードの挙動:
- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml を上位ディレクトリに持つディレクトリ）を探索して .env を自動的に読み込みます。
- 読み込み順: OS 環境 > .env.local（上書き） > .env（未設定キーのみセット）
- 無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主なファイル）
------------------------------
（抜粋。実際のリポジトリに合わせて追加してください）

- src/kabusys/
  - __init__.py                   パッケージエントリ（version 等）
  - config.py                     環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                 ニュース NLP（score_news）
    - regime_detector.py          市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py           J-Quants API クライアント（fetch/save 関連）
    - pipeline.py                 ETL パイプライン run_daily_etl 等
    - etl.py                      ETLResult の再エクスポート
    - news_collector.py           RSS 取得・前処理・保存
    - calendar_management.py      マーケットカレンダー管理（営業日判定 / update job）
    - quality.py                  データ品質チェック
    - stats.py                    統計ユーティリティ（zscore_normalize）
    - audit.py                    監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py          モジュール: calc_momentum / calc_value / calc_volatility
    - feature_exploration.py      calc_forward_returns / calc_ic / factor_summary / rank
  - ai、research、data の下にさらにユーティリティ関数や補助モジュールが含まれます。

運用上の注意点 / トラブルシューティング
-----------------------------------
- OpenAI / J-Quants といった外部 API 呼び出しはネットワーク障害やレート制限が起き得ます。各モジュールはリトライやフェイルセーフ（0.0 スコアにフォールバック等）を備えていますが、ログを監視してください。
- DuckDB executemany に空リストを渡すと問題になるバージョンがあります（コード中に guard 条件あり）。DuckDB のバージョン互換性に注意してください。
- テスト時は外部 API 呼び出し（OpenAI、urllib）をモックし、KABUSYS_DISABLE_AUTO_ENV_LOAD を使って環境の影響を切り離すと良いです。
- 監査テーブルは削除しない運用を想定しています（ON DELETE RESTRICT 等）。schema 初期化は慎重に行ってください。

ライセンス / コントリビューション
---------------------------------
（本リポジトリに LICENSE ファイルがあればそちらを参照してください。ない場合はプロジェクト管理者に確認してください。）

最後に
------
この README はコードベースの主要機能と使い始めのヒントをまとめたものです。各モジュールの docstring に詳細な設計意図や使用方法が記載されています。具体的な運用スクリプト（スケジューラ、デプロイ、監視連携等）は本リポジトリ外で定義される想定です。必要であれば運用例やサンプルスクリプトの追加も作成できますので、ご希望があれば教えてください。