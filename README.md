KabuSys
=======

概要
----
KabuSys は日本株を対象としたデータプラットフォーム＋自動売買（戦略生成）ライブラリです。  
主に以下を提供します。

- J-Quants API 経由で株価・財務・カレンダー等のデータを取得して DuckDB に保存する ETL（差分更新／バックフィル対応）
- RSS ニュース収集と記事→銘柄紐付けのパイプライン
- 研究（research）モジュールによるファクター計算（Momentum / Volatility / Value など）
- 特徴量エンジニアリング（Z スコア正規化、ユニバースフィルタ）
- 戦略シグナル生成（final_score の計算、BUY/SELL シグナルの出力）
- DuckDB のスキーマ初期化・監査ログなどのデータ定義

主な設計方針は「冪等性」「ルックアヘッドバイアス回避（target_date 時点のデータのみ使用）」「API レート制御とリトライ」「外部依存を極力抑えた標準ライブラリ中心の実装」です。

機能一覧
--------
主な機能（モジュール単位）:

- kabusys.config
  - .env/.env.local の自動ロード（プロジェクトルート検出）
  - 必須環境変数の取得ラッパー（settings オブジェクト）

- kabusys.data
  - jquants_client: J-Quants API クライアント（レート制限・リトライ・トークン自動リフレッシュ対応）
  - schema: DuckDB スキーマ定義と init_schema()（DDL を一括作成）
  - pipeline: ETL ジョブ（run_daily_etl 等）、差分取得ロジック、品質チェック呼び出し
  - news_collector: RSS 収集、記事正規化、raw_news / news_symbols への保存
  - calendar_management: JPX カレンダー取得/判定ユーティリティ（is_trading_day など）
  - features / stats: Z スコア正規化や統計ユーティリティ

- kabusys.research
  - factor_research: mom/volatility/value 等のファクター計算（prices_daily / raw_financials 参照）
  - feature_exploration: 将来リターン計算 / IC（Information Coefficient） / 統計サマリー

- kabusys.strategy
  - feature_engineering.build_features: ファクター結合・フィルタ・正規化・features テーブルへの UPSERT
  - signal_generator.generate_signals: features + ai_scores を統合して final_score を算出し signals へ出力（BUY/SELL）

- kabusys.data.audit
  - 発注〜約定までをトレースする監査テーブル定義

セットアップ手順
--------------
1. リポジトリをクローンし、仮想環境を作る（任意）
   - git clone <repo>
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt があればそれを使ってください。パッケージ化されていれば pip install -e . も利用可）

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env（または .env.local）を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可）。

   必須の主な環境変数:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API のパスワード（kabu 関連の実装で使用）
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必要に応じて）
   - SLACK_CHANNEL_ID      : Slack チャンネル ID
   - （任意）KABUSYS_ENV : development / paper_trading / live（デフォルト development）
   - （任意）LOG_LEVEL : DEBUG/INFO/…（デフォルト INFO）
   - データベースのパスはデフォルトで data/kabusys.duckdb（DUCKDB_PATH 環境変数で変更可）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで以下を実行してデータベースとテーブルを作成します:

   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)  # ":memory:" を指定するとインメモリ DB
   ```

使い方（簡易サンプル）
---------------------

- 日次 ETL（株価・財務・カレンダーの差分取得 + 品質チェック）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # デフォルトで本日を処理
  print(result.to_dict())
  ```

- 特徴量作成
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.strategy import build_features
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024, 1, 31))
  print(f"built features for {n} symbols")
  ```

- シグナル生成
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.strategy import generate_signals
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2024, 1, 31))
  print(f"signals generated: {total}")
  ```

- RSS ニュース収集（既定ソース）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = init_schema("data/kabusys.duckdb")
  # known_codes に有効銘柄コードセットを渡すと記事→銘柄紐付けを行う
  res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  print(res)
  ```

- カレンダー更新ジョブ（夜間バッチ）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.calendar_management import calendar_update_job

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn, lookahead_days=90)
  print(f"saved {saved} calendar rows")
  ```

設定・挙動に関する補足
--------------------
- settings（kabusys.config.settings）はプロパティベースで環境変数を読み込みます。未設定の必須変数を参照すると ValueError を送出します。
- 自動 .env 読み込みはプロジェクトルート（.git か pyproject.toml）を基準に行います。テストや特殊用途で無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants クライアントはレート制限（120 req/min）とリトライ（指数バックオフ）を行い、401 受信時はリフレッシュトークンでトークン更新を試みます。
- DuckDB への保存は多くの箇所で冪等（ON CONFLICT DO UPDATE / DO NOTHING）を採用しています。

ディレクトリ構成（抜粋）
-----------------------
以下はコードベース内の主なファイル・モジュール（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数/設定管理
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント
    - news_collector.py              — RSS 取得・前処理・DB 保存
    - schema.py                      — DuckDB スキーマ定義 / init_schema
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py         — カレンダー判定/更新ジョブ
    - features.py                    — features 方便ユーティリティ
    - stats.py                       — zscore_normalize 等の統計ユーティリティ
    - audit.py                       — 発注〜約定監査テーブル定義
  - research/
    - __init__.py
    - factor_research.py             — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py         — 将来リターン・IC・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py         — features テーブル作成ロジック
    - signal_generator.py            — final_score 算出・signals 作成
  - execution/                        — （発注・ブローカー連携のための階層、未詳細）
  - monitoring/                       — 監視・メトリクス用（未詳細）

貢献・拡張
----------
- 新しい RSS ソースを追加する場合は kabusys.data.news_collector.DEFAULT_RSS_SOURCES を拡張してください。
- strategy の重みや閾値は generate_signals() の引数で上書き可能です（weights, threshold）。
- kabuステーション等のブローカー連携は execution 層で実装する想定です（現状は戦略生成とデータ基盤が中心）。

ライセンス
--------
（プロジェクトに応じてここにライセンス表記を記入してください）

最後に
-----
この README はコードの現状（src 配下にあるモジュール）をもとにした概要・使い方のまとめです。実行時の詳細な振る舞いや追加の設定項目（Slack通知の実装、kabu API 呼び出しなど）は各モジュールのドキュメント文字列（docstring）を参照してください。必要であれば各機能の詳細な使い方や運用手順書を別途作成します。