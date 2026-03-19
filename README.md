# KabuSys

日本株向け自動売買 / データプラットフォームライブラリ

バージョン: 0.1.0

概要
----
KabuSys は日本株のデータ収集（J-Quants）、ETL、特徴量生成、戦略シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどをまとめた内部ライブラリ群です。DuckDB をデータレイヤに用い、研究（research）・データ（data）・戦略（strategy）・発注（execution）・監視（monitoring）などのコンポーネントを提供します。

主な設計方針
- ルックアヘッドバイアス対策（target_date 時点のデータのみ参照）
- 冪等性（DB への保存は ON CONFLICT / トランザクションで安全に）
- 外部 API 操作に対するレート制御・リトライ・トークン自動リフレッシュ
- 研究環境と本番環境の分離（研究モジュールは本番 API に依存しない）
- DB 初期化・スキーマ管理を提供し簡単にローカル実行可能

機能一覧
--------
- 環境設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local、無効化オプションあり）
  - 必須環境変数の取得ラッパー（settings）
- データレイヤ（data）
  - J-Quants クライアント（fetch/save、ページネーション、リトライ、レート制御）
  - News (RSS) 収集器（SSRF 対策、XML 脆弱性対策、トラッキングパラメータ除去）
  - DuckDB スキーマ定義・初期化（init_schema）
  - ETL パイプライン（差分取得・バックフィル・品質チェック統合）
  - マーケットカレンダー管理（営業日判定、次/前営業日取得、夜間更新ジョブ）
  - 監査ログスキーマ（signal_events / order_requests / executions 等）
  - 統計ユーティリティ（Z スコア正規化等）
- 研究（research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算（forward returns）・IC 計算・統計サマリー
- 戦略（strategy）
  - 特徴量エンジニアリング（research の raw factor を統合・正規化して features テーブルへ保存）
  - シグナル生成（features と ai_scores を統合し BUY/SELL シグナルを signals テーブルに書き込む）
- ニュース処理
  - RSS からの記事収集・前処理・raw_news への冪等保存、銘柄抽出と news_symbols への紐付け
- 実行（execution）
  - 発注・注文キュー・約定処理を扱うテーブル定義（モジュール実装はファイル構造に含まれます）
- 監視（monitoring）
  - 監視用 DB/ロギングのためのインターフェース（構成ファイル参照）

セットアップ手順
--------------
前提
- Python 3.9 以上（typing | from __future__ の記述に合わせて最低 3.9 推奨）
- DuckDB と必要なライブラリをインストール

1. リポジトリをチェックアウト
   git clone ... && cd ...

2. 仮想環境の作成（任意だが推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .\.venv\Scripts\activate   # Windows

3. 依存ライブラリをインストール
   pip install duckdb defusedxml

   （プロジェクトが requirements.txt / pyproject.toml を提供する場合はそちらを利用してください）

4. 環境変数を設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（ただしテスト時など自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD     : kabuステーション API のパスワード（発注連携用）
     - SLACK_BOT_TOKEN       : Slack 通知用ボットトークン
     - SLACK_CHANNEL_ID      : Slack チャネル ID
   - 任意（デフォルト値あり）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG | INFO | ...) — デフォルト INFO
     - DUCKDB_PATH (例: data/kabusys.duckdb)
     - SQLITE_PATH (例: data/monitoring.db)

5. DuckDB スキーマ初期化
   Python から次のように呼び出します（例）:

   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

   テスト用途なら ":memory:" を指定してインメモリ DB を使用できます。

使い方（主要 API 例）
-------------------

- 環境設定の取得
  from kabusys.config import settings
  token = settings.jquants_refresh_token

- DB 初期化 / 接続
  from kabusys.data.schema import init_schema, get_connection
  conn = init_schema("data/kabusys.duckdb")      # 初回は init_schema
  # 既存 DB に接続する場合
  conn = get_connection("data/kabusys.duckdb")

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- マーケットカレンダー更新ジョブ（夜間バッチ）
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)

- ニュース収集（RSS）
  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄抽出に使う有効コードセット（None で紐付けスキップ）
  res = run_news_collection(conn, sources=None, known_codes={"7203","6758"})

- 特徴量構築（strategy）
  from datetime import date
  from kabusys.strategy import build_features
  count = build_features(conn, target_date=date(2025, 1, 10))

- シグナル生成（strategy）
  from kabusys.strategy import generate_signals
  n_signals = generate_signals(conn, target_date=date(2025, 1, 10))

- J-Quants 直接利用例（データ取得のみ）
  from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
  quotes = fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,10))

補足
- J-Quants API はレート制限（120 req/min）に従う実装です。get_id_token によりトークンを自動リフレッシュします。
- News Collector は SSRF 対策・XML パース安全化（defusedxml）・トラッキングパラメータ除去・受信サイズ制限を実装しています。
- ETL は差分取得・バックフィルをサポートし、quality モジュールを呼んでデータ品質チェックを行います（quality モジュールは別ファイルとして存在します）。
- 自動 .env ロードはデプロイやテストで邪魔な場合 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                       — 環境変数/設定管理
- data/
  - __init__.py
  - jquants_client.py              — J-Quants API クライアント（fetch/save）
  - news_collector.py              — RSS ニュース収集・保存・銘柄抽出
  - schema.py                      — DuckDB スキーマ定義・初期化
  - stats.py                       — 統計ユーティリティ（zscore_normalize）
  - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py         — カレンダー管理（営業日判定・更新ジョブ）
  - features.py                    — データ層の特徴量公開ラッパ
  - audit.py                       — 監査ログ（signal/events/orders/executions）
  - execution/                      — 発注関連の実装（ディレクトリ）
  - monitoring/                     — 監視用モジュール（ディレクトリ）
- research/
  - __init__.py
  - factor_research.py             — モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py         — IC/forward_returns/factor_summary
- strategy/
  - __init__.py
  - feature_engineering.py         — features テーブル作成（build_features）
  - signal_generator.py            — signals テーブルへの BUY/SELL 生成
- execution/                        — 発注実行ロジック（プレースホルダー）
- monitoring/                       — 監視 / メトリクス収集（プレースホルダー）

開発・テストに関するメモ
-----------------------
- テスト実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして .env の自動読み込みを無効化できます。
- DuckDB でインメモリ DB（":memory:"）を使えば副作用なしで単体テストが可能です。
- ネットワーク周り（J-Quants / RSS）や時間に依存する処理は id_token の注入や _urlopen をモックしてテストできる設計になっています。
- ログレベルは LOG_LEVEL 環境変数で調整します。

ライセンス・貢献
----------------
この README はコードベースの説明を目的としています。実際のライセンス表記や貢献ガイドはリポジトリの LICENSE / CONTRIBUTING.md を参照してください。

問い合わせ
----------
実運用や API トークン、外部連携に関する質問は担当チームへ問い合わせてください。開発者向けの実行例や追加ユーティリティが必要であれば README を更新します。

以上。必要であれば README にサンプルコマンドや CI/CD フロー、より詳しい環境変数の説明（例：.env.example）を追加できます。どの項目を追記しますか？