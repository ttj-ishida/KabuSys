KabuSys
=======

概要
----
KabuSys は日本株のデータ取得・加工・特徴量生成・シグナル生成・ETL を行う自動売買プラットフォーム向けライブラリです。  
DuckDB をデータストアに用い、J-Quants API や RSS（ニュース）などからデータを収集し、研究（research）→ 特徴量（features）→ 戦略（strategy）→ 発注（execution, audit）といった層を分離して実装しています。

このリポジトリには以下の主要コンポーネントが含まれます（概要）:
- data: J-Quants クライアント、ETL パイプライン、DuckDB スキーマ、ニュース収集、マーケットカレンダー管理、統計ユーティリティなど
- research: ファクター計算・特徴量探索ユーティリティ（研究用ロジック）
- strategy: 特徴量の正規化・合成と売買シグナルの生成ロジック
- execution: 発注・約定・ポジション管理（パッケージ階層は存在しますが、実装は別途）
- config: 環境変数／設定の自動ロードと管理

バージョン: 0.1.0

主な機能
--------
- J-Quants API クライアント
  - 日次株価（OHLCV）、財務データ、JPX カレンダーをページネーション・リトライ・レート制限対応で取得
  - トークン自動リフレッシュと取得のユーティリティ
- ETL パイプライン
  - 差分更新（バックフィル対応）、品質チェック、カレンダー先読み
  - 日次 ETL の統合実行（run_daily_etl）
- DuckDB スキーマ定義と初期化
  - Raw / Processed / Feature / Execution 層のテーブル定義（冪等性あり）
- ニュース収集
  - RSS フィードから記事を取得、前処理、ID 生成、raw_news / news_symbols への冪等保存
  - SSRF 対策・受信サイズ制限・XML 攻撃対策を考慮
- 研究用ファクター計算
  - Momentum / Volatility / Value 等のファクターを prices_daily / raw_financials から計算
  - 将来リターン（forward returns）、IC（Spearman）計算、ファクター統計
- 特徴量エンジニアリング
  - ファクターのマージ、ユニバースフィルタ（株価・流動性）、Z スコア正規化、features テーブルへの UPSERT
- シグナル生成
  - features / ai_scores を統合して final_score を算出
  - Bear レジーム抑制、BUY / SELL シグナル生成、signals テーブルへの置換（冪等）

動作要件
--------
- Python 3.10 以上（typing の | 演算子等を利用）
- 主要依存パッケージ（最低限）:
  - duckdb
  - defusedxml
- ネットワークアクセスが必要（J-Quants API、RSS フィード等）

環境変数（代表的なもの）
-----------------------
KabuSys は .env/.env.local もしくは OS 環境変数から設定を読み込みます（config モジュール）。自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動読み込みが不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須（実運用で必要なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabu ステーション API パスワード（発注連携時）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意（デフォルト値あり）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると自動 .env 読み込みを無効にする
- KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: デフォルト DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

セットアップ手順
--------------
1. Python と仮想環境の作成（例）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール:
   - pip install duckdb defusedxml
   （必要に応じてその他パッケージを追加）

3. 環境変数設定:
   - プロジェクトルートに .env を作成するか、シェル環境にエクスポートします。
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=your_slack_token
     SLACK_CHANNEL_ID=your_slack_channel_id
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

   - 自動ロードについて:
     config.py はプロジェクトルートの .env / .env.local を自動で読み込みます（OS 環境変数が優先）。テスト時などで自動読み込みを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. DuckDB スキーマ初期化:
   - Python REPL やスクリプトで以下を実行します:

     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

   - これにより必要なテーブルとインデックスが作成されます。

使い方（よく使う例）
-------------------

1) DuckDB の初期化
   Python スクリプト例:

   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

2) 日次 ETL を実行（J-Quants からデータ取得 → 保存 → 品質チェック）
   from datetime import date
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())  # ETLResult の概要

   - 注意: JQUANTS_REFRESH_TOKEN が環境変数に設定されているか、id_token を直接渡してください。

3) 特徴量を構築して features テーブルへ保存
   from datetime import date
   from kabusys.data.schema import get_connection
   from kabusys.strategy import build_features

   conn = get_connection("data/kabusys.duckdb")
   n = build_features(conn, date(2026, 3, 20))  # target_date を指定
   print(f"upserted {n} features")

4) シグナルを生成して signals テーブルへ保存
   from datetime import date
   from kabusys.data.schema import get_connection
   from kabusys.strategy import generate_signals

   conn = get_connection("data/kabusys.duckdb")
   total = generate_signals(conn, date(2026, 3, 20))
   print(f"generated {total} signals")

5) ニュース収集ジョブ（RSS）
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   # sources: {name: rss_url} を渡せる。省略時は既定ソースを利用
   results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
   print(results)

6) カレンダー更新ジョブ（夜間バッチ）
   from kabusys.data.calendar_management import calendar_update_job
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print(f"saved calendar entries: {saved}")

API の挙動・設計メモ
-------------------
- 冪等性: データ保存（save_*）は ON CONFLICT を用いて冪等に行われます。ETL は同じ範囲を何度実行しても安全です。
- Look-ahead バイアス対策: 取得時の fetched_at を UTC で記録するなど「いつそのデータを知り得たか」を追跡できる設計です。
- レート制限 / リトライ: J-Quants クライアントは固定間隔スロットリング（120 req/min）とリトライ戦略（指数バックオフ、401 の場合はトークンリフレッシュ）を実装しています。
- セキュリティ: RSS の取得は SSRF 対策、受信サイズ制限、defusedxml による XML の安全なパースを実施しています。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                       — 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py             — J-Quants API クライアント & 保存関数
  - news_collector.py             — RSS 取得・前処理・DB 保存
  - schema.py                     — DuckDB スキーマ定義と init_schema
  - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
  - stats.py                      — 統計ユーティリティ（zscore_normalize）
  - features.py                   — data.stats の再エクスポート
  - calendar_management.py        — マーケットカレンダー管理
  - audit.py                      — 監査ログスキーマ（signal_events/order_requests/executions）
- research/
  - __init__.py
  - factor_research.py            — Momentum / Value / Volatility の計算
  - feature_exploration.py        — 将来リターン / IC / 統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py        — features テーブル構築
  - signal_generator.py           — final_score 計算と signals 生成
- execution/
  - __init__.py                   — 発注層のエントリ（実装は別途）
- monitoring/                      — README の冒頭で __all__ に含まれているが実装ファイルがない場合あり

注意事項 / テスト時のヒント
-------------------------
- 自動 .env 読み込みはプロジェクトルート（.git / pyproject.toml）を探索して行います。CI やテストで明示的に環境を管理したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の初期化は init_schema() を必ず最初に実行してください。get_connection() は既存 DB へ接続しますが、テーブル作成は行いません。
- J-Quants へのリクエストはネットワーク・API レートの制約を受けます。テストでは id_token を直接渡す、あるいは jquants_client のネットワーク呼び出しをモックしてください。
- NewsCollector は外部ネットワークを実行するため、ユニットテストでは _urlopen 等をモックして副作用を回避すると良いです。

ライセンス
---------
（ここにプロジェクトのライセンス情報を記載してください）

補足
----
この README はソースコードのコメント・設計方針に基づいて作成しています。実運用に際しては DataPlatform.md / StrategyModel.md などの設計ドキュメントと合わせて読み、必要な環境変数や運用手順を整備してください。必要であればサンプルの .env.example や運用スクリプトを追加することを推奨します。