KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けのデータプラットフォーム＋戦略実装を提供する軽量ライブラリです。  
主な目的は以下です。

- J-Quants から市場データ・財務データ・市場カレンダーを取得して DuckDB に保存（ETL）
- ニュース（RSS）を収集・前処理して DB に保存・銘柄紐付け
- 研究モジュールでファクターを計算（momentum / volatility / value 等）
- 特徴量の正規化・合成（features テーブル）
- 最終スコアを計算して売買シグナルを生成（signals テーブル）
- 発注／実行／ポジション管理に対応するスキーマを提供（audit / execution 層）

設計上の特徴:
- DuckDB を中心としたシンプルなローカルデータベース設計（Raw / Processed / Feature / Execution 層）
- API レート制御・リトライ・トークン自動更新を備えた J-Quants クライアント
- 冪等性（ON CONFLICT / PUT-DELETE で日次置換など）を重視
- ルックアヘッドバイアスを防ぐ設計（計算は target_date 時点のデータのみ利用）

主要機能一覧
------------
- データ取得（J-Quants）
  - 株価日足、四半期財務データ、JPX マーケットカレンダー
  - レート制限・リトライ・トークン自動更新実装
- ETL パイプライン
  - 差分取得（最終取得日に基づく差分／バックフィル）
  - 品質チェック（別モジュール quality 参照）
  - 日次 ETL 実行（run_daily_etl）
- ニュース収集
  - RSS フィード収集、前処理、記事ID生成（URL 正規化→SHA-256）、raw_news 保存
  - 記事から銘柄コード抽出（known_codes を利用）
- 研究（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
- 戦略（strategy）
  - 特徴量構築（build_features）
  - シグナル生成（generate_signals） — BUY / SELL の判定と signals テーブルへの保存
- スキーマ管理
  - DuckDB スキーマ定義と初期化（init_schema）
  - audit / execution 層の監査テーブルを含むフルスキーマ

動作要件
--------
- Python 3.10+
- 必要ライブラリ（最低限）:
  - duckdb
  - defusedxml
- （任意）J-Quants API 利用にはネットワークと有効なリフレッシュトークンが必要

セットアップ手順
----------------

1. レポジトリをクローン / パッケージを入手
   - 開発環境例:
     - git clone ... && cd repo_root

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # Unix/macOS
   - .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクトをパッケージ化している場合）
   - pip install -e .

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env を置くと自動で読み込まれます。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須 / 推奨環境変数
-------------------
（kabusys.config.Settings で参照される項目）

- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API のパスワード（execution 層で使用）
  - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（通知を使う場合）
  - SLACK_CHANNEL_ID — Slack チャネル ID

- 任意（デフォルトあり）:
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL — DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- .env の優先順:
  - OS 環境変数 > .env.local > .env

基本的な使い方（コード例）
-------------------------

以下は Python REPL / スクリプトでの最小ワークフロー例です。DuckDB にデータベースを作成し、日次 ETL → 特徴量構築 → シグナル生成を実行します。

1) DB スキーマ初期化
- メモリ DB:
  - from kabusys.data import schema
  - conn = schema.init_schema(":memory:")

- ファイル DB（デフォルトパス）:
  - from kabusys.config import settings
  - from kabusys.data import schema
  - conn = schema.init_schema(settings.duckdb_path)

2) 日次 ETL 実行（J-Quants トークンが設定されている前提）
- from datetime import date
- from kabusys.data.pipeline import run_daily_etl
- result = run_daily_etl(conn, target_date=date.today())
- print(result.to_dict())

3) 特徴量構築（features テーブルに書き込む）
- from datetime import date
- from kabusys.strategy import build_features
- cnt = build_features(conn, target_date=date.today())
- print(f"features upserted: {cnt}")

4) シグナル生成（signals テーブルに書き込む）
- from kabusys.strategy import generate_signals
- total = generate_signals(conn, target_date=date.today(), threshold=0.60)
- print(f"signals written: {total}")

5) ニュース収集の実行（例）
- from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
- saved_map = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={'7203','6758',...})
- print(saved_map)

Notes / 補足
------------
- idempotency（冪等性）:
  - データ保存関数（save_*）は ON CONFLICT を用いて重複を上書きまたはスキップします。日付単位で DELETE → INSERT を行う処理もあります（置換）。
- J-Quants クライアント:
  - レート制限（120 req/min）をモジュール内で制御
  - 401 受信時はリフレッシュトークンで id_token を自動更新して再試行
  - 408/429/5xx に対するリトライ（指数バックオフ）
- news_collector:
  - RSS の取得時に SSRF / private IP へのアクセスをブロック
  - 最大レスポンスサイズ制限・gzip 解凍後のサイズチェック
  - 記事 ID は URL 正規化後の SHA-256（先頭32文字）
- 環境依存動作:
  - プロジェクトルート検出は __file__ の親を辿って .git または pyproject.toml を探します。CWD に依存せず .env を自動ロードします。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを抑止できます。

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys 以下の主要モジュールを抜粋）

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（fetch/save 関数含む）
    - schema.py               — DuckDB スキーマ定義と init_schema
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - news_collector.py       — RSS 収集・前処理・DB 保存
    - calendar_management.py  — 市場カレンダー管理（is_trading_day など）
    - features.py             — features 公開インターフェース（再エクスポート）
    - audit.py                — 監査ログ関連 DDL（発注トレーサビリティ）
  - research/
    - __init__.py
    - factor_research.py      — momentum/volatility/value 計算
    - feature_exploration.py  — 将来リターン / IC / 統計要約
  - strategy/
    - __init__.py
    - feature_engineering.py  — 生ファクターの正規化・features への書き込み
    - signal_generator.py     — final_score 計算と signals 作成
  - execution/                 — 発注/実行関連（空パッケージ／実装箇所あり）
  - monitoring/                — 監視系（SQLite 等、別実装想定）

開発 / 貢献メモ
----------------
- 型アノテーションと docstring が豊富に付与されています。ユニットテストを追加して品質を保つことを推奨します。
- DB スキーマは DuckDB の制限（現状の FK / ON DELETE の扱い）を考慮しており、削除時の制約はアプリ側ロジックで処理する設計です。
- ETL / ニュース収集は外部 API に依存するため、テスト時は jquants_client._request や news_collector._urlopen をモックすることを推奨します。
- ログは標準 logging を使用。運用時は LOG_LEVEL を環境変数で制御してください。

ライセンス
---------
（このリポジトリにライセンスファイルがあれば追記してください）

問い合わせ
----------
実装方針や設計に関する質問、運用上の注意などがあれば README に追記します。必要なら利用ケースに合わせたサンプルスクリプト（cron / Airflow 用タスク例）を用意します。