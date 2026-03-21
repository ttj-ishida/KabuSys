# KabuSys

日本株向けの自動売買プラットフォーム基盤ライブラリです。データ取得（J-Quants）、ETL、特徴量エンジニアリング、シグナル生成、ニュース収集、マーケットカレンダー管理、DuckDBスキーマ／監査ログなど、戦略開発と運用に必要な基盤機能を提供します。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（短いコード例）
- 環境変数 / .env
- ディレクトリ構成
- 注意点 / トラブルシューティング

---

## プロジェクト概要

KabuSys は以下の用途を想定した Python パッケージです。

- J-Quants API からの株価・財務・カレンダー取得（レート制限・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いた Raw / Processed / Feature / Execution 層のスキーマ定義と初期化
- ETL パイプライン（差分取得 / バックフィル / 品質チェック連携）
- ニュース（RSS）収集と銘柄紐付け（SSRF や XML 攻撃対策あり）
- ファクター計算（モメンタム／ボラティリティ／バリュー等）と Z スコア正規化
- 戦略レベルの特徴量作成（features テーブル）およびシグナル生成（signals テーブル）
- マーケットカレンダー管理（営業日判定、next/prev 営業日）
- 監査ログ用テーブル（signal_events / order_requests / executions など）

設計方針として、ルックアヘッドバイアスを防ぐため「対象日時点」のデータのみを利用する、DB 操作は冪等（ON CONFLICT / トランザクション）で行うなどを採用しています。

---

## 主な機能

- data/jquants_client:
  - J-Quants API クライアント（ページネーション、リトライ、レート制御、token リフレッシュ）
  - raw_prices / raw_financials / market_calendar の取得・保存関数

- data/schema:
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema(db_path) による初期化

- data/pipeline:
  - run_daily_etl: カレンダー、株価、財務の差分取得→保存→品質チェック（オプション）

- data/news_collector:
  - RSS 取得、正規化、raw_news 保存、銘柄抽出・紐付け（SSRF・gzip・XML の安全対策を実装）

- research:
  - calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials に基づくファクター計算）
  - calc_forward_returns / calc_ic / factor_summary などの分析ユーティリティ

- strategy:
  - build_features: raw ファクターを正規化し features テーブルへ保存
  - generate_signals: features と ai_scores を統合して BUY/SELL シグナルを signals テーブルへ出力

- data/calendar_management:
  - market_calendar 更新ジョブ、is_trading_day / next_trading_day / prev_trading_day 等

- セキュリティ / 信頼性面:
  - J-Quants クライアントはレート制限・リトライ・401 の自動リフレッシュを実装
  - RSS 取得は SSRF 回避、受信サイズ上限、defusedxml による XML 攻撃防御
  - DB 操作はトランザクション・冪等に配慮

---

## セットアップ手順

前提:
- Python 3.10 以上（モジュール内で | 型注釈等を利用しているため）
- pip が利用可能

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 本リポジトリに requirements.txt がない場合は、最低限次を入れてください:
     - pip install duckdb defusedxml
   - 実運用や追加機能（Slack, kabuAPI client など）を使う場合はそれぞれの SDK を追加でインストールしてください（例: slack_sdk 等）。

4. データベース初期化（DuckDB）
   - Python で下記を実行して DB を作成・テーブルを初期化します（パスは環境変数で設定可、デフォルトは data/kabusys.duckdb）。
     - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

5. 環境変数を設定
   - .env ファイルか OS 環境変数を用いて設定します（詳細は次節）。

---

## 環境変数（主なもの）

KabuSys は環境変数または .env ファイルから設定を読み込みます（プロジェクトルートに .env/.env.local がある場合、自動で読み込みます。読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

主な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須、execution 層を使う場合）
- KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知を行う場合の Bot トークン（必須、通知を使う場合）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須、通知を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development / paper_trading / live)（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト: INFO）

例 (.env):
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（簡易コード例）

以下は代表的なタスクの実行例です。実運用では適切なエラーハンドリングとログ設定を追加してください。

- DuckDB スキーマ初期化
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")

- 日次 ETL を実行（J-Quants トークンは設定済み前提）
  - from kabusys.data.schema import init_schema
    from kabusys.data.pipeline import run_daily_etl
    conn = init_schema("data/kabusys.duckdb")
    result = run_daily_etl(conn)  # target_date を指定可能

- 特徴量の作成（features テーブルへ保存）
  - from kabusys.data.schema import init_schema
    from kabusys.strategy import build_features
    import duckdb
    from datetime import date
    conn = init_schema("data/kabusys.duckdb")
    n = build_features(conn, target_date=date.today())

- シグナル生成（signals テーブルへ保存）
  - from kabusys.data.schema import init_schema
    from kabusys.strategy import generate_signals
    from datetime import date
    conn = init_schema("data/kabusys.duckdb")
    total = generate_signals(conn, target_date=date.today())

- ニュース収集ジョブ（RSS）
  - from kabusys.data.schema import init_schema
    from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
    conn = init_schema("data/kabusys.duckdb")
    known_codes = {"7203", "6758", ... }  # 有効銘柄コードセット
    results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)

---

## ディレクトリ構成

（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                       -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py              -- J-Quants API クライアント（取得/保存）
    - news_collector.py              -- RSS 収集・正規化・DB 保存
    - schema.py                      -- DuckDB スキーマ定義・初期化
    - stats.py                       -- 統計ユーティリティ（Zスコア等）
    - pipeline.py                    -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py         -- マーケットカレンダー管理
    - features.py                    -- zscore_normalize の公開ラッパー
    - audit.py                       -- 監査ログテーブル DDL
    - (その他: quality モジュール想定)
  - research/
    - __init__.py
    - factor_research.py             -- ファクター計算（momentum/volatility/value）
    - feature_exploration.py         -- 将来リターン計算、IC、統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py         -- features テーブル構築ロジック
    - signal_generator.py            -- final_score 計算・BUY/SELL シグナル生成
  - execution/                       -- 発注／ブローカー連携レイヤ（パッケージ化済み、実装拡張箇所）
  - monitoring/                      -- 監視系・メトリクス（想定）

---

## 注意点 / トラブルシューティング

- Python バージョン:
  - typing の | union などを利用しているため Python 3.10 以上を推奨します。

- 環境変数の自動ロード:
  - config.py はプロジェクトルート（.git / pyproject.toml のあるディレクトリ）から .env / .env.local を自動で読み込みます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途）。

- J-Quants API:
  - レート制限（120 req/min）や 401 リフレッシュ、429/5xx リトライなどを考慮した設計です。長時間の backfill を行う際は API 制限に注意してください。

- DuckDB:
  - init_schema() は必要なディレクトリを作成します。初回は必ず init_schema を呼んでテーブルを作成してください。

- RSS / ニュース収集:
  - fetch_rss は SSRF 対策や受信サイズ上限、defusedxml による安全処理を行いますが、外部ソースの変更（非標準フィード）には適宜対応が必要です。

- 実運用（ライブ発注）について:
  - KabuSys は発注周りの設計（監査ログ、orders/trades テーブル）を含みますが、証券会社の API を使った実際の発注処理・リスク管理・資金管理ロジックはプロジェクト固有にカスタマイズする必要があります。まずは paper_trading 環境で十分に検証してください（KABUSYS_ENV を paper_trading に設定）。

---

追加の情報や利用例、CI 設定、運用ドキュメント（StrategyModel.md / DataPlatform.md 等）については別添のドキュメントを参照してください。README の内容に合わせてサンプルスクリプトやユニットテストを充実させることを推奨します。