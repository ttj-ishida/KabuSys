# KabuSys

日本株向け自動売買プラットフォームのライブラリ群です。データ取得（J-Quants）、DuckDB を用いたデータ基盤、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、発注／監査用スキーマなど、研究〜実運用に必要な機能をモジュール単位で提供します。

主な設計方針：
- ルックアヘッドバイアス防止（各処理は target_date 時点の情報のみを使用）
- 冪等性（DB 保存は ON CONFLICT / トランザクションで安全化）
- ネットワーク回復力（API リトライ・レートリミット制御）
- テスト容易性（外部依存の注入、環境変数自動読み込みの抑止等）

バージョン: 0.1.0

---

## 機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（株価・財務・カレンダー）
  - raw データを DuckDB に冪等保存するユーティリティ
  - 差分 ETL（run_daily_etl）と個別 ETL ジョブ（株価 / 財務 / カレンダー）

- データ基盤
  - DuckDB スキーマ定義と初期化（init_schema）
  - テーブル群：raw_prices, prices_daily, raw_financials, raw_news, features, ai_scores, signals, orders, trades, positions, 監査テーブル等

- データ処理 / 研究補助
  - ファクター計算（momentum / volatility / value）
  - Z-score 正規化ユーティリティ
  - 将来リターン計算、IC（Spearman）計算、統計サマリー

- 特徴量生成 / シグナル
  - 特徴量作成（build_features）：research モジュールの生ファクターを統合・正規化して features に保存
  - シグナル生成（generate_signals）：features + ai_scores を使って final_score を計算し BUY/SELL シグナルを signals に保存

- ニュース収集
  - RSS フィード収集（fetch_rss / run_news_collection）
  - テキスト前処理、記事 ID 正規化、銘柄コード抽出、raw_news / news_symbols 保存
  - SSRF 対策・gzip サイズ制限・XML セキュリティ対策を実装

- マーケットカレンダー管理
  - market_calendar 更新ジョブ、営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）

- 監査 / トレーサビリティ
  - signal_events, order_requests, executions などの監査テーブル（UUID を用いた追跡）

---

## 前提・依存関係

- Python >= 3.10（型記法に | を使用）
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセスが必要（J-Quants API、RSS フィード等）

pip によるインストール例（プロジェクトルートで）:
- 開発中インストール:
  - pip install -e .
- 依存のみ:
  - pip install duckdb defusedxml

（プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

---

## 環境変数 / 設定

このパッケージはプロジェクトルートの `.env` / `.env.local` を自動読み込みします（優先度: OS 環境 > .env.local > .env）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（Settings で参照されるもの）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN : Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID : 通知先チャンネルID（必須）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用途の SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV : 実行環境 (development|paper_trading|live)、デフォルト: development
- LOG_LEVEL : ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)

例 `.env`（実運用では機密情報は安全に管理してください）:
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -e .           （ローカル開発インストール）
   - または最低限: pip install duckdb defusedxml

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、実行環境で環境変数をセットします。

5. DuckDB スキーマ初期化
   - Python からスキーマを作成します（親ディレクトリは自動作成されます）:

     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)

---

## 使い方（主な API と例）

以下は基本的なワークフローのサンプルコードです。すべて DuckDB の接続オブジェクト（kabusys.data.schema.init_schema が返す conn）を渡して利用します。

- DuckDB 初期化 + 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）:

  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())

- 特徴量ビルド（features テーブル作成）:

  from kabusys.strategy import build_features
  from datetime import date

  count = build_features(conn, date.today())
  print(f"features upserted: {count}")

- シグナル生成（signals テーブルへの書き込み）:

  from kabusys.strategy import generate_signals
  from datetime import date

  total_signals = generate_signals(conn, date.today(), threshold=0.6)
  print(f"signals written: {total_signals}")

- ニュース収集ジョブ（RSS 取得 → raw_news に保存 → 銘柄紐付け）:

  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  # known_codes は銘柄抽出に使用する有効銘柄コード集合（任意）
  known_codes = {"7203", "6758", "7974"}
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)

- カレンダー更新バッチ（夜間ジョブ）:

  from kabusys.data.calendar_management import calendar_update_job

  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")

- スキーマ再利用（既存 DB への接続）:

  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")

ログや実行環境に応じて、KABUSYS_ENV・LOG_LEVEL を調整してください（settings.env / settings.log_level を参照）。

---

## 実行における注意点 / 運用メモ

- J-Quants API 利用
  - レート制限（120 req/min）とリトライロジックを実装済みです。
  - 認証はリフレッシュトークンを使用して ID トークンを取得します（settings.jquants_refresh_token が必須）。

- データ品質
  - ETL 後に quality モジュールのチェックを行います（run_daily_etl 内で呼び出し）。重大な品質問題があっても ETL は継続し、検出結果は ETLResult.quality_issues に集約されます。

- セキュリティ
  - RSS パーサーは defusedxml を使用し、SSRF 対策・受信サイズ制限・gzip 解凍後のサイズチェックを行います。
  - 環境変数 (.env) に機密情報を保存する場合はアクセス制御に注意してください。

- 実運用モード
  - KABUSYS_ENV を `paper_trading` / `live` に切り替え可能。settings.is_live / is_paper / is_dev を参照して条件分岐できます。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / Settings 管理、自動 .env 読み込みロジック
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ユーティリティ・リトライ・レートリミット）
    - schema.py
      - DuckDB スキーマ定義、init_schema / get_connection
    - pipeline.py
      - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - features.py
      - zscore_normalize の再エクスポート
    - news_collector.py
      - RSS 取得・前処理・DB 保存・銘柄抽出・統合ジョブ
    - calendar_management.py
      - market_calendar 更新、営業日判定・検索ユーティリティ
    - audit.py
      - 監査ログ用の追加スキーマ・DDL（signal_events, order_requests, executions 等）
    - pipeline.py (上記)
  - research/
    - __init__.py
    - factor_research.py
      - momentum / volatility / value のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py
      - features テーブル作成ロジック（正規化・ユニバースフィルタ）
    - signal_generator.py
      - final_score 計算、BUY/SELL 生成、signals 保存
  - execution/
    - (発注連携用モジュール群: 現在空のパッケージシェル)
  - monitoring/
    - (監視 / メトリクス用モジュール: 実装があればここに格納)

---

## 開発・テストのヒント

- 自動 .env ロードを抑止：
  - テスト実行時は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると .env の自動読み込みを無効化できます。

- DuckDB をメモリで使う：
  - テストでは init_schema(":memory:") を使うことで一時 DB を作成できます。

- 外部 API をモック：
  - jquants_client._request や news_collector._urlopen をモックしてネットワーク依存を切り離せます。

---

当リポジトリはライブラリ群の骨格（データ層・戦略層・研究ユーティリティ）を提供します。運用環境での稼働には API キー管理、監視・リトライ方針、リスク管理ルール（ポジション制限・最大ドローダウン等）を追記してご利用ください。必要があれば README にサンプル cron / systemd タスクや Docker 運用手順も追加できます。