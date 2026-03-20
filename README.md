# KabuSys

日本株の自動売買プラットフォームに関するライブラリ群（データ収集 / ETL / 研究用ファクター計算 / 特徴量生成 / シグナル生成 / ニュース収集 / DuckDB スキーマなど）。

本リポジトリは内部コンポーネントをモジュール化しており、ETL や戦略の研究・運用に必要なユーティリティを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の機能を持つ日本株自動売買システム向けのコードベースです（モジュール群）:

- J-Quants API クライアント（株価、財務、マーケットカレンダー取得）と保存処理（DuckDB への冪等保存）
- ETL パイプライン（差分取得 / backfill / 品質チェック）
- DuckDB のスキーマ定義・初期化
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 特徴量エンジニアリング（正規化・ユニバースフィルタ）
- シグナル生成（ファクタースコア・AIスコア統合、BUY/SELL 生成、エグジット判定）
- ニュース（RSS）収集とテキスト前処理、銘柄紐付け
- マーケットカレンダー管理（営業日判定、前後営業日取得）
- 構成（環境変数）管理ユーティリティ

設計上、発注 API（ブローカーへの実際の注文送信）に直接依存しない層構造（Data / Research / Strategy / Execution）が採用されています。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API の呼び出し、トークンリフレッシュ、ページネーション、取得データの保存（raw_prices / raw_financials / market_calendar）
  - レートリミット制御、リトライ（指数バックオフ）対応
- data/schema.py
  - DuckDB のテーブル定義（Raw / Processed / Feature / Execution 層）と初期化関数 init_schema()
- data/pipeline.py
  - 日次 ETL（run_daily_etl）: カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック
- data/news_collector.py
  - RSS フィード取得、前処理、raw_news 保存、銘柄抽出と news_symbols 紐付け
- data/calendar_management.py
  - 営業日判定、next/prev 営業日、カレンダー更新ジョブ
- research/factor_research.py
  - モメンタム / ボラティリティ / バリューなどのファクター計算関数
- research/feature_exploration.py
  - 将来リターン計算、IC（Spearman）や統計サマリー計算
- strategy/feature_engineering.py
  - 研究で算出した raw factor を正規化して features テーブルへ格納（build_features）
- strategy/signal_generator.py
  - features と ai_scores を統合して final_score を算出、BUY/SELL シグナル生成（generate_signals）
- config.py
  - .env / 環境変数の自動読み込み、主要設定（トークン・DB パス・環境モード等）の取得

---

## セットアップ手順（開発環境）

以下はローカルで動かす際の一般的な手順例です。

1. リポジトリをクローン
   - git clone <repository-url>
   - cd <repository>

2. Python 仮想環境を作成（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要なパッケージをインストール
   - 最低限必要なパッケージ:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - 開発用にパッケージを編集可能な形でインストールする場合:
     - pip install -e .

   ※ 本リポジトリに requirements.txt がある場合はそれに従ってください。

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のある場所）に `.env` を配置すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数（最低限設定が必要なもの）:

     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
     - DUCKDB_PATH: DuckDB ファイルパス（省略時 data/kabusys.duckdb）
     - SQLITE_PATH: SQLite (monitoring 等) のパス（省略時 data/monitoring.db）
     - KABUSYS_ENV: 環境 "development" / "paper_trading" / "live"（デフォルト development）
     - LOG_LEVEL: ログレベル "DEBUG" / "INFO" / ...（デフォルト INFO）

   - .env の例（.env.example を元に作成してください）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - KABU_API_PASSWORD=your_kabu_api_password
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - DUCKDB_PATH=data/kabusys.duckdb
     - KABUSYS_ENV=development
     - LOG_LEVEL=DEBUG

5. DuckDB スキーマ初期化（Python REPL やスクリプトで）
   - 例:
     - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
   - もしくは簡単なスクリプト:
     - from kabusys.data.schema import init_schema
       conn = init_schema('data/kabusys.duckdb')

---

## 基本的な使い方（例）

以下は主要 API を使った簡単な利用例です。適宜 try/except やログ設定を追加してください。

1. DuckDB の初期化と接続
   - from kabusys.data.schema import init_schema, get_connection
     conn = init_schema("data/kabusys.duckdb")  # 初期化して接続を取得

2. 日次 ETL（J-Quants からデータ取得 & 保存）
   - from kabusys.data.pipeline import run_daily_etl
     result = run_daily_etl(conn)  # target_date を指定可能
     print(result.to_dict())

3. 特徴量の構築（strategy/features テーブルへの書き込み）
   - from kabusys.strategy import build_features
     from datetime import date
     n = build_features(conn, date(2025, 1, 10))
     print(f"features upserted: {n}")

4. シグナル生成（signals テーブルへ書き込み）
   - from kabusys.strategy import generate_signals
     from datetime import date
     total = generate_signals(conn, date(2025, 1, 10))
     print(f"signals written: {total}")

5. ニュース収集ジョブ
   - from kabusys.data.news_collector import run_news_collection
     known_codes = {"7203", "6758", "..."}  # 既知の銘柄コードセット（抽出用）
     res = run_news_collection(conn, known_codes=known_codes)
     print(res)

6. カレンダー更新ジョブ
   - from kabusys.data.calendar_management import calendar_update_job
     saved = calendar_update_job(conn)
     print(f"calendar saved: {saved}")

注意:
- 上記 API は DuckDB のテーブル（prices_daily / raw_financials / features / ai_scores / positions 等）を参照／更新します。事前に init_schema を実行してテーブルを作成してください。
- J-Quants API を使う操作は認証トークン (JQUANTS_REFRESH_TOKEN) が必要です。

---

## 環境変数の自動読み込みについて

- `kabusys.config` モジュールはプロジェクトルート（.git または pyproject.toml を持つディレクトリ）にある `.env` と `.env.local` を自動で読み込みます。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - OS 環境変数は保護 (protected) され `.env` による上書きを防ぎます（明示的に override=True の場合は例外）。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利です）。
- `Settings` クラス経由で設定値を取得します。必須値が足りないと ValueError が送出されます。

主要な設定プロパティ（settings）:
- settings.jquants_refresh_token
- settings.kabu_api_password
- settings.kabu_api_base_url (デフォルト http://localhost:18080/kabusapi)
- settings.slack_bot_token
- settings.slack_channel_id
- settings.duckdb_path (Path)
- settings.sqlite_path (Path)
- settings.env (development|paper_trading|live)
- settings.log_level (DEBUG|INFO|...)

---

## ディレクトリ構成（主なファイル）

- src/
  - kabusys/
    - __init__.py
    - config.py                       — 環境変数/設定読み込み
    - data/
      - __init__.py
      - jquants_client.py             — J-Quants API クライアント + 保存ロジック
      - news_collector.py             — RSS ニュース収集・DB 保存
      - schema.py                     — DuckDB スキーマ定義 & init_schema()
      - stats.py                      — Zスコア正規化等の統計ユーティリティ
      - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
      - calendar_management.py        — カレンダー取得・営業日ユーティリティ
      - features.py                   — data.stats の再エクスポート
      - audit.py                      — 監査ログ用スキーマ（エントリ）
    - research/
      - __init__.py
      - factor_research.py            — モメンタム/ボラティリティ/バリュー計算
      - feature_exploration.py        — forwarding return, IC, summary utilities
    - strategy/
      - __init__.py
      - feature_engineering.py        — build_features
      - signal_generator.py           — generate_signals
    - execution/                       — 発注・実行関連（シンプルなプレースホルダ／拡張点）
    - monitoring/                      — 監視・メトリクス（未詳述）
- pyproject.toml / setup.cfg / README.md など（プロジェクトルート）

（上記は現状の主なファイル群の要約です。詳細はソースを参照してください。）

---

## 注意事項・設計上のポイント

- ルックアヘッドバイアス回避:
  - ファクター計算・シグナル生成は target_date 時点で利用可能なデータのみを使用する設計です。
  - 取得データには fetched_at を付与し、いつデータがシステムに入ったかを追跡できます。
- 冪等性:
  - DuckDB への保存は ON CONFLICT（upsert）を使用することにより冪等に実装されています。
  - ETL や features/signals の書き込みは日付単位の置換（DELETE + bulk INSERT）で原子性を確保します（トランザクション使用）。
- セキュリティ／堅牢性:
  - news_collector は SSRF 防止、XML DoS（defusedxml）、応答サイズ上限を導入しています。
  - jquants_client はレート制御、リトライ、401 のトークンリフレッシュに対応します。
- 実運用環境（live）はリスクが高くなるため settings.is_live / is_paper で分岐可能です。KABUSYS_ENV を正しく設定してください。

---

## よくある操作例（スクリプト）

簡単なフロー（初期化 → ETL → 特徴量 → シグナル生成）:

python
- from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.strategy import build_features, generate_signals
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  etl_result = run_daily_etl(conn)
  trading_day = etl_result.target_date
  build_features(conn, trading_day)
  generate_signals(conn, trading_day)

（必要な環境変数を .env または OS 環境に設定してから実行してください）

---

## 追加メモ

- ユニットテストや CI の設定ファイルはプロジェクトに応じて追加してください。本コードベースはテストしやすいように id_token の注入や _urlopen のモック等を想定した設計になっています。
- 発注（broker）側の実装は本リポジトリの外側でプラグイン的に実装することが想定されています（execution 層の拡張）。

---

問題や不明点があればソースの該当モジュール（例: data/pipeline.py, research/factor_research.py, strategy/*）を参照するか、具体的な利用シナリオを教えてください。サンプルスクリプトや .env.example のテンプレート作成も支援できます。