# KabuSys

日本株向けの自動売買 / データ基盤ライブラリセットです。  
DuckDB を中心としたデータレイヤ、J-Quants API 連携、RSS ニュース収集、特徴量計算、ETL パイプライン、品質チェック、監査ログなどを備えています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、日本株のデータ取得・整形・特徴量生成・戦略検証・発注監査を一貫して実現するための内部ライブラリ群です。主な設計ポリシーは以下です。

- DuckDB を中心としたローカルデータベース（Raw / Processed / Feature / Execution / Audit 層）
- J-Quants API からの株価・財務・カレンダー取得（レート制御・リトライ・トークン自動更新）
- RSS によるニュース収集（SSRF対策、トラッキングパラメータ除去、冪等保存）
- ETL の差分更新、バックフィル、品質チェック
- 研究向けのファクター計算（モメンタム・ボラティリティ・バリュー等）と IC/統計ユーティリティ
- 発注トレースのための監査テーブル構成（order_request_id 等の冪等キー）

このリポジトリはライブラリとして利用することを想定しており、本番発注ループ等は呼び出し側で組み立てます。

---

## 主な機能一覧

- 設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック（settings オブジェクト）
- データ取得 / 保存
  - J-Quants API クライアント（fetch / save：日次株価・財務・マーケットカレンダー）
  - レート制御（120 req/min）、リトライ、401 の自動トークン更新
- ETL パイプライン
  - 差分取得、バックフィル、カレンダー先読み、品質チェックを含む日次 ETL
- データスキーマ管理
  - DuckDB 用のスキーマ初期化（raw_prices, prices_daily, features, signals, audit 等）
- ニュース収集
  - RSS 取得、前処理、ID の SHA-256 ベース生成、冪等保存、銘柄抽出
  - SSRF 対策・受信サイズ制限・gzip 対応
- 品質チェック
  - 欠損、重複、スパイク（前日比）や日付不整合チェック
- 研究 / ファクター計算
  - モメンタム、ボラティリティ、バリュー算出
  - 将来リターン計算、IC（Spearman）計算、Zスコア正規化
  - すべて標準ライブラリ＋DuckDB で完結（pandas 等に依存しない）
- 監査ログ
  - signal_events / order_requests / executions テーブルで発注フローをトレース可能

---

## 必要な環境変数

主に以下を使用します。`.env` に設定してください（プロジェクトルートの自動読み込みあり）。

- JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD：kabuステーション API パスワード（必須）
- KABU_API_BASE_URL：kabu API のベース URL（任意、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN：Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID：Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH：DuckDB ファイルパス（任意、デフォルト: data/kabusys.duckdb）
- SQLITE_PATH：監視用 SQLite パス（任意、デフォルト: data/monitoring.db）
- KABUSYS_ENV：実行環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL：ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

自動 .env 読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットすることで無効化できます（テスト時に便利）。

例（.env.example）:
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順（簡易）

1. Python 環境（3.9+ 推奨）を用意
   - 推奨: venv を使う
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必要ライブラリ（最低限）:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （追加でロギングや Slack 連携等を行う場合はそれらのクライアントを導入してください）

3. 環境変数（.env）をプロジェクトルートに配置
   - `.git` または `pyproject.toml` が存在するディレクトリをプロジェクトルートとして自動検出します。
   - `.env` → `.env.local` の順で読み込まれます（.env.local が上書き）。

4. DuckDB スキーマの初期化
   - Python から実行:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")

5. （監査DB を別ファイルで運用する場合）監査 DB 初期化
   - from kabusys.data.audit import init_audit_db
   - audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（代表的な例）

以下は基本的な利用例です。実行は Python スクリプトやジョブスケジューラから行います。

- DuckDB スキーマ初期化（既定のパスを使用）
  - Python:
    - from kabusys.data.schema import init_schema
    - conn = init_schema("data/kabusys.duckdb")

- 日次 ETL 実行（J-Quants からデータ取得 → 保存 → 品質チェック）
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

- 研究用: モメンタム等の計算
  - from kabusys.research import calc_momentum, calc_forward_returns, calc_ic
    conn = init_schema("data/kabusys.duckdb")  # データが揃っていること
    recs = calc_momentum(conn, target_date=date(2024,1,31))
    fwd = calc_forward_returns(conn, target_date=date(2024,1,31))
    ic = calc_ic(recs, fwd, factor_col="mom_1m", return_col="fwd_1d")
    print("IC:", ic)

- ニュース収集ジョブ（RSS）
  - from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
    conn = init_schema("data/kabusys.duckdb")
    known_codes = {"7203", "6758", "9432"}  # 事前に保持する有効銘柄コードセット
    stats = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
    print(stats)

- J-Quants の個別フェッチ（テストや単発実行）
  - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
    conn = init_schema("data/kabusys.duckdb")
    records = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
    saved = save_daily_quotes(conn, records)
    print(f"fetched={len(records)}, saved={saved}")

注意点:
- ETL や API 呼び出しは外部ネットワークとトークンが必要です。環境変数を正しく設定してください。
- DuckDB の SQL 実行はパラメータバインドを使用していますが、SQL を直接編集する際は注意してください。

---

## ディレクトリ構成

主要なファイル／モジュールを抜粋して示します（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数・設定管理（.env 自動読み込み、settings）
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（fetch / save）
    - news_collector.py      # RSS ニュース収集、前処理、DB 保存
    - schema.py              # DuckDB スキーマ定義・init_schema
    - stats.py               # 統計ユーティリティ（zscore_normalize）
    - pipeline.py            # ETL パイプライン（run_daily_etl 等）
    - features.py            # 特徴量インターフェース（re-export）
    - calendar_management.py # マーケットカレンダー管理（営業日判定・更新ジョブ）
    - audit.py               # 監査ログ（signal_events / order_requests / executions）
    - etl.py                 # ETL 公開インターフェース（ETLResult 再エクスポート）
    - quality.py             # データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py # 将来リターン計算、IC、統計サマリー等
    - factor_research.py     # モメンタム・ボラティリティ・バリュー計算
  - strategy/
    - __init__.py            # 戦略レイヤ（空のエントリポイント）
  - execution/
    - __init__.py            # 発注関連（空のエントリポイント）
  - monitoring/
    - __init__.py            # 監視用モジュール（空のエントリポイント）

上記以外にユーティリティや補助モジュールが含まれますが、主要機能は上記にまとまっています。

---

## 補足・運用上の注意

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。ライブラリを別場所で import する場合は挙動に注意してください。自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- J-Quants のレート制御は固定間隔（120 req/min）を前提としています。高頻度でのページネーション処理などは注意してください。
- DuckDB のトランザクションはモジュール内部で使用しています。init_schema 等は BEGIN/COMMIT を行いますが、監査スキーマ初期化は transactional 引数で制御可能です。
- 外部 API のレスポンスや RSS フィードは信頼できない入力です。news_collector では SSRF 対策・XML パース対策（defusedxml）・サイズ制限などを実装していますが、実運用ではさらに追加検証や段階的デプロイを推奨します。

---

## 開発・貢献

- コードはモジュール単位でテスト可能な設計を意識しています（例: jquants_client._urlopen や news_collector の内部関数をモックして単体テストを行う等）。
- テスト、CI、依存関係管理（requirements.txt / pyproject.toml など）は別途用意してください。

---

以上が KabuSys の README（日本語）です。必要であれば「.env.example の完全テンプレート」「実行スクリプトのサンプル」「CI / デプロイ手順」などの追記も作成しますのでご依頼ください。