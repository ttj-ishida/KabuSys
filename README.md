KabuSys — 日本株自動売買プラットフォーム
======================================

概要
----
KabuSys は日本株向けのデータ収集・前処理・特徴量構築・シグナル生成・発注トレーサビリティを想定したライブラリ群です。主に以下の役割を持つモジュールで構成されています。

- データ取得 (J-Quants API / RSS ニュース)
- DuckDB ベースのスキーマ定義・永続化
- 研究用ファクター計算・特徴量正規化
- 戦略層の特徴量合成（feature engineering）およびシグナル生成
- ETL パイプライン（差分取得・品質チェック）
- カレンダー管理・ニュース収集・監査ログ等の補助機能

ライブラリ設計のポイント:
- DuckDB を中心としたローカルデータベース設計（Raw / Processed / Feature / Execution 層）
- 冪等性（DB 保存は ON CONFLICT / トランザクションで整合性確保）
- ルックアヘッドバイアス対策（取得時刻・対象日ベースの計算）
- API レート制御・リトライ・トークン自動更新（J-Quants クライアント）
- 外部依存を最小化（pandas 等に依存しない設計）

主な機能一覧
-------------
- 環境変数管理（kabusys.config: .env 自動読み込み・必須チェック）
- DuckDB スキーマ定義・初期化（kabusys.data.schema.init_schema / get_connection）
- J-Quants API クライアント（株価・財務・カレンダー取得、保存）
  - レート制限、リトライ、ID トークン自動更新を内包
- ニュース収集（RSS 取得・前処理・DB 保存、銘柄抽出）
  - SSRF 対策、XML 安全パーサ、防御的実装
- ETL パイプライン（差分取得・バックフィル・品質チェック統合）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 特徴量エンジニアリング（正規化・ユニバースフィルタ・features テーブルへ保存）
- シグナル生成（特徴量＋AI スコア統合 → BUY / SELL シグナル生成、SELL 優先）
- マーケットカレンダー管理（営業日判定 / next/prev_trading_day / 更新ジョブ）
- 監査ログ（signal_events / order_requests / executions 等）

セットアップ手順
----------------

前提
- Python 3.10 以上（union 型 | を使用）
- DuckDB を動かせる環境

推奨パッケージ（最小限の例）
- duckdb
- defusedxml

例: 仮想環境作成と依存インストール
- Unix 系（bash）:
  1. python -m venv .venv
  2. source .venv/bin/activate
  3. pip install --upgrade pip
  4. pip install duckdb defusedxml

インストール方法
- 開発環境でソースを使う場合:
  - プロジェクトルートに移動して (setup.py / pyproject.toml がある想定)
  - pip install -e .

環境変数
- 自動読み込み:
  - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml を基準）から `.env` → `.env.local` を順に自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 必須環境変数（kabusys.config.Settings が要求）:
  - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD — kabu ステーション API パスワード（発注/ブローカー連携用）
  - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
  - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- 任意 / デフォルト付き:
  - KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）

使い方（主要ユースケース）
-----------------------

1) DuckDB スキーマ初期化
- Python から:
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")
  - これで必要なテーブル・インデックスが作成されます

2) 日次 ETL 実行（株価・財務・カレンダー取得・品質チェック）
- from datetime import date
- from kabusys.data.pipeline import run_daily_etl, get_connection, init_schema
- conn = init_schema("data/kabusys.duckdb")  # 初回のみ
- result = run_daily_etl(conn, target_date=date.today())
- result は ETLResult で、保存件数や検出された品質問題・エラーの一覧を確認できます

3) 特徴量構築（research ファクターを正規化して features テーブルに保存）
- from datetime import date
- from kabusys.strategy import build_features
- conn = get_connection("data/kabusys.duckdb")
- n = build_features(conn, target_date=date(2024, 1, 15))
- 戻り値 n は upsert した銘柄数

4) シグナル生成（features と ai_scores を統合して signals テーブルへ保存）
- from kabusys.strategy import generate_signals
- conn = get_connection("data/kabusys.duckdb")
- total = generate_signals(conn, target_date=date(2024, 1, 15))
- total は生成されたシグナル数（BUY + SELL）

5) ニュース収集ジョブ（RSS から raw_news へ）
- from kabusys.data.news_collector import run_news_collection
- conn = get_connection("data/kabusys.duckdb")
- known_codes = {"7203", "6758", ...}  # 既知の銘柄コードセット
- results = run_news_collection(conn, known_codes=known_codes)
- results はソースごとの新規保存件数を返します

6) J-Quants からのデータ取得（低レベル API 利用）
- from kabusys.data import jquants_client as jq
- id_token = jq.get_id_token()  # settings から refresh token を使って取得
- records = jq.fetch_daily_quotes(id_token=id_token, date_from=..., date_to=...)
- jq.save_daily_quotes(conn, records)

実行時の注意点
- J-Quants API: レート制限 120 req/min を厳守（モジュール内で固定間隔スロットリングを適用）
- トークン切れ: 401 を受けると自動で refresh を試みる実装があります（1 回のみ再取得して再試行）
- DB 書き込みは基本的にトランザクションで囲まれ、冪等的に設計されています
- research / strategy 層はルックアヘッドバイアスを避けるため target_date 時点のデータのみを使用します

ディレクトリ構成（主なファイル）
------------------------------

src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込み・設定取得ロジック（自動 .env ロード・必須チェック）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py — RSS 取得・正規化・保存・銘柄抽出
  - schema.py — DuckDB スキーマ定義・初期化
  - stats.py — z-score 正規化等の汎用統計ユーティリティ
  - features.py — zscore_normalize の再エクスポート
  - pipeline.py — ETL パイプライン（差分取得・バックフィル・品質チェック）
  - calendar_management.py — 市場カレンダー管理・営業日計算・更新ジョブ
  - audit.py — 監査ログ（signal_events, order_requests, executions 等）の DDL
  - (その他: quality モジュール等はコードベースに含まれている想定)
- research/
  - __init__.py — 研究用 API を公開
  - factor_research.py — momentum / volatility / value 等のファクター計算
  - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py — 生ファクターを結合・正規化して features テーブルへ保存
  - signal_generator.py — features + ai_scores を統合して signals を生成
- execution/
  - __init__.py — 発注/実行層の足がかり（実装は別途）
- monitoring/  (パッケージ初期化で公開予定の監視関連モジュール)

補足
----
- このリポジトリはライブラリ層の実装に焦点を当てており、実際のブローカー接続・運用オーケストレーション（スケジューラ、監視・アラート）や UI は別実装を想定しています。
- テストしやすさのため、API トークンの注入やネットワーク呼び出しの差し替え（モック）が考慮された設計になっています（例: jquants_client._request の id_token 注入、news_collector._urlopen をテストで差し替え可能）。

ライセンス・貢献
----------------
本 README はコードベースの内容から生成しています。実際のプロジェクトに組み込む際はライセンス表記、貢献ルール、CI/CD の手順、.env.example の用意などを追加してください。

必要であれば、README にサンプル .env.example、実行スクリプト（cron / systemd / Docker Compose）やサンプル SQL を追記します。どの情報を優先的に追加したいか教えてください。