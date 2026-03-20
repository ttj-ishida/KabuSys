# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群です。データ収集（J‑Quants）→ ETL → 特徴量作成 → シグナル生成 → 発注監査までの主要コンポーネントを含み、研究（research）と運用（execution）で共通に使えるユーティリティを提供します。

主な設計方針：
- ルックアヘッドバイアス防止（target_date 時点のデータのみ使用）
- 冪等性（DB への保存は ON CONFLICT やトランザクションで安全に）
- 外部依存を最小化（DuckDB を中心に標準ライブラリで実装）
- セキュリティ配慮（RSS の SSRF 対策、XML パース保護など）

---

## 機能一覧（要約）

- 環境設定管理
  - .env / .env.local をプロジェクトルートから自動ロード（無効化可能）
  - 必須環境変数の検証（例: JQUANTS_REFRESH_TOKEN 等）

- データ取得・保存（J‑Quants クライアント）
  - 日足（OHLCV）、財務データ、マーケットカレンダー取得（ページネーション対応）
  - レート制限・リトライ・トークン自動リフレッシュ対応
  - DuckDB へ冪等保存（raw_prices / raw_financials / market_calendar 等）

- ETL パイプライン
  - 差分更新（最終取得日に基づく差分取得 + バックフィル）
  - 日次 ETL ジョブ（カレンダー → 株価 → 財務 → 品質チェック）

- スキーマ管理
  - DuckDB のスキーマ初期化（Raw / Processed / Feature / Execution 層）
  - テーブル定義・インデックス定義をまとめて作成

- 特徴量計算（research / strategy）
  - Momentum / Volatility / Value などのファクター計算
  - Z スコア正規化ユーティリティ
  - features テーブルへの日付単位 UPSERT（冪等）

- シグナル生成
  - features と ai_scores を統合して最終スコアを計算
  - Bear レジーム考慮、BUY/SELL シグナル生成、SELL（エグジット）判定
  - signals テーブルへ日付単位置換（トランザクション）

- ニュース収集
  - RSS フィード取得、記事の正規化、raw_news への冪等保存
  - 記事→銘柄紐付け（正規化 URL → SHA256 頭32文字で記事ID）
  - SSRF / XML Bomb / レスポンスサイズ制限 等の安全対策

- 監査ログ（audit）
  - signal_events / order_requests / executions などの監査テーブルを定義
  - 発注から約定までのトレーサビリティを確保

---

## 前提・依存

推奨 Python バージョン: 3.10 以上（PEP 604 の型記法を使用）

主な依存ライブラリ（例）:
- duckdb
- defusedxml

（プロジェクトの requirements.txt がある場合はそれを利用してください。なければ最低限上記を pip インストールしてください）

例:
pip install duckdb defusedxml

---

## 環境変数（主な必須項目）

必須:
- JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意／デフォルトあり:
- KABUSYS_ENV — 開発モード等（valid: development, paper_trading, live）。デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）。デフォルト: INFO
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視等）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動読み込みを無効化

.env の例（プロジェクトルートに配置）:
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development

---

## セットアップ手順（最小）

1. リポジトリを取得
2. 仮想環境を作成して有効化
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
3. 必要パッケージをインストール
   pip install duckdb defusedxml
   （プロジェクトで requirements があればそれを使用）
4. 環境変数を設定（.env/.env.local をプロジェクトルートに配置）
5. DuckDB スキーマを初期化
   - 例（Python から）:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

---

## 使い方（代表的な操作例）

以下は Python スクリプトから呼び出す例です。スクリプトはプロジェクトルートで実行してください（.env が自動読込されます）。

- DuckDB スキーマ初期化
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- 日次 ETL 実行（市場カレンダー・株価・財務を取得して保存）
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())

- 特徴量ビルド（features テーブルに書き込む）
  from kabusys.data.schema import init_schema
  from kabusys.strategy import build_features
  from datetime import date
  conn = init_schema("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2025, 1, 15))
  print(f"features upserted: {n}")

- シグナル生成（signals テーブルへ書き込む）
  from kabusys.data.schema import init_schema
  from kabusys.strategy import generate_signals
  from datetime import date
  conn = init_schema("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2025, 1, 15))
  print(f"signals written: {total}")

- ニュース収集ジョブ（RSS 収集→raw_news 保存→銘柄紐付け）
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection
  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", ...}  # 有効な銘柄コード集合
  res = run_news_collection(conn, known_codes=known_codes)
  print(res)  # {source_name: saved_count, ...}

- J‑Quants から直接データ取得（テスト用）
  from kabusys.data import jquants_client as jq
  records = jq.fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,15))
  print(len(records))

注意:
- 上記関数群は DuckDB 接続を受け取ることを想定しています。init_schema() は接続とスキーマ初期化を行います。
- ETL 実行時は設定された JQUANTS_REFRESH_TOKEN 等の環境変数が必要です。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
  - 環境変数の自動読み込み、Settings クラス（J‑Quants トークン等）
- data/
  - __init__.py
  - jquants_client.py — J‑Quants API クライアント（取得・保存関数含む）
  - news_collector.py — RSS 収集・前処理・保存ロジック
  - schema.py — DuckDB スキーマ定義と init_schema/get_connection
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - pipeline.py — ETL パイプライン（run_daily_etl 他）
  - calendar_management.py — market_calendar 管理と営業日計算
  - audit.py — 監査ログ用 DDL（signal_events, order_requests, executions 等）
- research/
  - __init__.py
  - factor_research.py — Momentum / Value / Volatility ファクター計算
  - feature_exploration.py — 将来リターン、IC、統計サマリー 等（研究用）
- strategy/
  - __init__.py
  - feature_engineering.py — 生ファクターを正規化して features に保存
  - signal_generator.py — features / ai_scores 統合 → signals 生成
- execution/
  - __init__.py
  - （発注層はここに実装される想定）
- monitoring/
  - （監視・アラート用モジュールを配置する想定）

---

## 開発上の注意・補足

- 自動 .env 読み込み
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に .env / .env.local を読み込みます。
  - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- ロギング／環境
  - KABUSYS_ENV により動作モード（development / paper_trading / live）を切替可能。is_live / is_paper / is_dev プロパティを Settings で利用できます。
  - LOG_LEVEL でログレベルを指定してください。

- テスト容易性
  - 多くの関数は id_token の注入や接続の注入を受け付け、モックがしやすい設計になっています。
  - ネットワークアクセスや外部 API 呼び出し箇所は小さなユーティリティに切り出されているため置き換え・モックが可能です。

---

この README はコードベースの主要機能と使用方法の概要をまとめたものです。より詳細な設計仕様（StrategyModel.md / DataPlatform.md / DataSchema.md 等）や運用手順は別途ドキュメントを参照してください。必要であれば README に含めるサンプルスクリプトや CLI ラッパー例を追記します。