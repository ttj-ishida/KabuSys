KabuSys
=======

日本株向けの自動売買プラットフォーム用ライブラリ群です。  
データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、DuckDB スキーマ・監査ログなど、量的運用に必要な主要コンポーネントを含みます。

主な特徴
------
- J-Quants API クライアント（レート制限・リトライ・トークン自動更新対応）
- DuckDB ベースのデータスキーマ（Raw / Processed / Feature / Execution 層）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- ファクター計算（モメンタム / ボラティリティ / バリュー）と Z スコア正規化
- 戦略の特徴量構築（features テーブルへの UPSERT）とシグナル生成（BUY/SELL）
- ニュース収集（RSS）と記事 → 銘柄紐付け（SSRF や XML 攻撃対策あり）
- マーケットカレンダー（JPX）管理 & 営業日ユーティリティ
- 監査ログ（signal_events, order_requests, executions）でトレーサビリティを確保
- 環境変数 / .env からの設定ロード（自動ロード機能付き）

必要な環境変数
-------------
主に以下の環境変数を使用します（.env / .env.local から自動読み込み）。  
必要に応じて .env.example を作成して運用してください。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

（任意／デフォルトあり）
- KABUSYS_ENV — 環境 ("development" / "paper_trading" / "live")（default: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...)（default: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（default: data/monitoring.db）

自動読み込みの制御:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化します（テスト等で利用）。

セットアップ手順
-----------

1. Python 環境を準備
   - Python 3.9+ を推奨
   - 必要なパッケージ（例）
     - duckdb
     - defusedxml
   - 例（pip）:
     pip install duckdb defusedxml

2. リポジトリをチェックアウト

3. 環境変数を設定
   - プロジェクトルートに .env または .env.local を作成して上記の値を設定します。
   - パース規則は sh 形式の KEY=VAL に準拠し、export プレフィックスやクォートも扱えます。

4. データベーススキーマ初期化
   - DuckDB ファイルを作成・初期化します（例）:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

   - インメモリでテストする場合は ":memory:" を指定:
     conn = init_schema(":memory:")

使い方（主要なワークフロー）
----------------

以下は代表的な利用例です。実運用ではログ設定や例外ハンドリングを適宜追加してください。

1) DuckDB 初期化（1回）
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)

2) 日次 ETL の実行（株価・財務・カレンダー取得 + 品質チェック）
   from kabusys.data.pipeline import run_daily_etl

   result = run_daily_etl(conn)  # target_date を省略すると今日（営業日補正あり）

   result は ETLResult オブジェクトで、取得件数や品質問題・エラー情報を参照できます。

3) 特徴量の構築（features テーブルへ）
   from kabusys.strategy import build_features
   from datetime import date

   target = date(2024, 1, 5)
   count = build_features(conn, target)  # target_date 分を置換して書き込み

4) シグナル生成（signals テーブルへ）
   from kabusys.strategy import generate_signals

   total_signals = generate_signals(conn, target, threshold=0.60)
   # 戦略重みをカスタムしたい場合は weights=dict(...) を指定可能

5) ニュース収集ジョブ
   from kabusys.data.news_collector import run_news_collection
   known_codes = {"7203", "6758", ...}  # 既知銘柄セット
   results = run_news_collection(conn, known_codes=known_codes)
   # 各 RSS ソースごとの新規保存数が返ります

6) カレンダー更新ジョブ（夜間バッチ想定）
   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn)

主要モジュール & API（概要）
-----------------
- kabusys.config
  - settings: 環境変数ベースの設定オブジェクト（JQUANTS_REFRESH_TOKEN など）
  - 自動で .env / .env.local をプロジェクトルートから読み込みます（無効化可）

- kabusys.data
  - jquants_client: J-Quants API クライアント + 保存ユーティリティ（fetch_* / save_*）
  - schema: DuckDB スキーマ定義と init_schema / get_connection
  - pipeline: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - news_collector: RSS 取得・前処理・raw_news 保存・銘柄抽出
  - calendar_management: 営業日ユーティリティ、calendar_update_job
  - stats: zscore_normalize（共通統計ユーティリティ）
  - features: zscore 正規化の再エクスポート

- kabusys.research
  - factor_research: calc_momentum, calc_volatility, calc_value（研究用に公開）
  - feature_exploration: 将来リターン、IC、統計サマリーなど（研究用）

- kabusys.strategy
  - feature_engineering.build_features: features テーブルを構築
  - signal_generator.generate_signals: features + ai_scores → signals を生成

- kabusys.data.audit
  - 監査ログ用テーブル定義（signal_events, order_requests, executions）

ディレクトリ構成（抜粋）
-----------------
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント & 保存
    - schema.py             — DuckDB スキーマ定義・初期化
    - pipeline.py           — ETL パイプライン
    - news_collector.py     — RSS ニュース収集
    - calendar_management.py— カレンダー管理・営業日ユーティリティ
    - stats.py              — 統計ユーティリティ（zscore）
    - features.py           — features API（再エクスポート）
    - audit.py              — 監査ログ DDL（未完部分あり）
  - research/
    - __init__.py
    - factor_research.py    — ファクター計算
    - feature_exploration.py— 将来リターン / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py— feature の構築（build_features）
    - signal_generator.py   — シグナル生成（generate_signals）
  - execution/              — 空（発注実装層の想定）
  - monitoring/            — 監視用コード配置想定（SQLite など）

注意事項 / 実運用上のポイント
-----------------
- J-Quants API のレート制限を厳守する実装（120 req/min）となっています。大量のシンボルを取得する場合は注意してください。
- 多くの関数は「ルックアヘッドバイアス」を避ける設計（target_date 時点の情報のみ参照）になっていますが、運用時に外部処理やデータの保存順序で注意が必要です。
- DuckDB のスキーマは冪等に作成されますが、運用中のスキーマ変更は慎重に行ってください（バックアップ推奨）。
- news_collector は SSRF / XML インジェクション / Gzip bomb などの対策を組み込んでいますが、外部フィードの内容品質は監視してください。
- テストや CI 環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使い、意図的に環境を制御してください。

開発者向けメモ
-------------
- settings オブジェクトから設定を取得できます（例: settings.duckdb_path）。
- 多くの処理は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取るため、トランザクション管理や接続ライフサイクルは呼び出し元で制御してください。
- ロギングはモジュールレベルの logger を使用しています。ログ設定はアプリ側で行ってください。

例: 簡単なバッチスクリプト
-------------------
#!/usr/bin/env python3
from datetime import date
import logging
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.calendar_management import calendar_update_job
from kabusys.strategy import build_features, generate_signals
from kabusys.config import settings

logging.basicConfig(level=settings.log_level)

conn = init_schema(settings.duckdb_path)
# カレンダー更新（夜間バッチ）
calendar_update_job(conn)
# ETL（市場データ取得）
etl_result = run_daily_etl(conn)
# 特徴量作成とシグナル生成（対象は ETL の対象日）
today = date.today()
build_features(conn, today)
generate_signals(conn, today)

以上が README に含めるべき基本的な情報です。詳しい API の使い方やスキーマの詳細は各モジュール（src/kabusys 以下）の docstring を参照してください。補足やサンプルの追加が必要であれば教えてください。