# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ。データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを一貫して提供します。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を収めた Python パッケージです。

- J-Quants API からの株価・財務・カレンダー取得（レート制御・リトライ・トークン自動更新対応）
- DuckDB を用いたデータスキーマの定義・初期化（Raw / Processed / Feature / Execution 層）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 特徴量の正規化・合成（features テーブルへの冪等アップサート）
- シグナル生成（特徴量＋AI スコア統合、BUY/SELL 生成、エグジット判定）
- ニュース収集（RSS、記事正規化、銘柄抽出、raw_news 保存）
- マーケットカレンダー管理（営業日判定・前後営業日の取得等）
- 監査ログ（シグナル→オーダー→約定のトレーサビリティ）

設計は「ルックアヘッドバイアス回避」「冪等性」「ロバストなエラーハンドリング」を重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション・レート制御・自動トークン更新・保存ユーティリティ）
  - schema: DuckDB スキーマ（テーブル・インデックス）定義と init_schema()
  - pipeline: 日次 ETL（差分更新・バックフィル・品質チェック）
  - news_collector: RSS 収集・前処理・raw_news / news_symbols 保存
  - calendar_management: 市場カレンダーの管理・営業日判定・前後営業日の取得
  - audit: 監査ログ（signal_events / order_requests / executions）
  - stats / features: Zスコア正規化などの統計ユーティリティ
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials ベース）
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー
- strategy/
  - feature_engineering.build_features: 生ファクターを正規化して features テーブルへ保存
  - signal_generator.generate_signals: features と ai_scores を統合して BUY/SELL シグナルを生成
- config.py: 環境変数ベースの設定（自動 .env ロード機能あり）

---

## 前提条件

- Python 3.9+（typing の Union 表記等を使用）
- duckdb
- defusedxml（ニュースRSSパース安全化に使用）
- （実運用で）J-Quants API アクセス権・リフレッシュトークン
- ネットワークアクセス（J-Quants、RSS ソース等）

依存パッケージの一例:
```
pip install duckdb defusedxml
```

（プロジェクトには他に必要なパッケージがあれば requirements.txt を参照してください）

---

## 環境変数（主なもの）

アプリは .env / .env.local / OS 環境変数を自動で読み込みます（プロジェクトルートの .git または pyproject.toml を検出して検索）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu API（発注）パスワード
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID

任意 / デフォルト:
- KABUSYS_ENV — 環境 ("development" / "paper_trading" / "live"), デフォルト "development"
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...), デフォルト "INFO"
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

例 .env:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージを取得）
2. Python 環境を作成・有効化（venv / conda 等）
3. 依存パッケージをインストール
   ```
   pip install -r requirements.txt
   # または最低限
   pip install duckdb defusedxml
   ```
4. .env を作成（上記参照）
5. DuckDB スキーマ初期化
   - Python REPL / スクリプトから:
     ```python
     from kabusys.config import settings
     from kabusys.data.schema import init_schema

     conn = init_schema(settings.duckdb_path)  # または ":memory:" をテスト用に指定
     ```
   - init_schema は親ディレクトリを自動作成します。

---

## 基本的な使い方（コード例）

以下は代表的なワークフロー例です。呼び出しは DuckDB 接続（duckdb.DuckDBPyConnection）を渡して行います。

- 日次 ETL の実行
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量生成（features テーブル作成）
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import build_features

  conn = get_connection("data/kabusys.duckdb")
  n = build_features(conn, target_date=date.today())
  print(f"built features for {n} symbols")
  ```

- シグナル生成
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import generate_signals

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print(f"signals generated: {total}")
  ```

- ニュース収集（RSS）
  ```python
  from kabusys.data.schema import get_connection
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = get_connection("data/kabusys.duckdb")
  # known_codes: 銘柄抽出に使う有効な4桁コード集合
  known_codes = {"7203", "6758", "9984", ...}
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- マーケットカレンダー更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"saved calendar records: {saved}")
  ```

- J-Quants からの生データ取得（低レベルAPI）
  ```python
  from kabusys.data import jquants_client as jq

  # id_token を渡すことも可（None の場合は内部キャッシュで自動取得）
  quotes = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

---

## 運用に関する注意点

- 自動 .env 読み込みはプロジェクトルート (.git or pyproject.toml を基準) を検出して行います。テスト時など自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を環境変数で設定してください。
- J-Quants のレート上限（120 req/min）を尊重するため、jquants_client は内部でスロットリングを行います。
- ETL / DB 書き込みは多くの場所でトランザクションを使用しており、冪等性（ON CONFLICT）を考慮して設計されています。
- production (KABUSYS_ENV=live) 環境では発注・監視ロジックの取り扱いに十分注意してください（誤発注防止、監査ログ）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境設定 / .env 自動ロード
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch/save 系）
    - schema.py — DuckDB スキーマ定義と init_schema()
    - pipeline.py — 日次 ETL（run_daily_etl など）
    - news_collector.py — RSS 取得・整形・保存
    - calendar_management.py — マーケットカレンダー管理
    - audit.py — 監査ログ用 DDL / 初期化
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - features.py — features の公開インターフェース
    - pipeline.py, audit.py, ...
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — build_features()
    - signal_generator.py — generate_signals()
  - execution/ — 発注周りの実装（発注層用モジュール）
  - monitoring/ — 監視・メトリクス格納用（SQLite 等）

各モジュールは「DuckDB 接続を受け取る」「ルックアヘッド回避（target_date 時点のデータのみ使用）」「発注 API への直接依存を避ける」などの設計方針に従っています。

---

## 開発・テストのヒント

- テスト時はメモリ DB を使うと高速:
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema(":memory:")
  ```
- ニュース収集等のネットワーク呼び出しはモック可能。news_collector._urlopen などを差し替える設計になっています。
- settings（kabusys.config.settings）を直接参照して設定値を取得できます。

---

## ライセンス・貢献

この README はコードベースの説明を目的としています。実際のリポジトリに LICENSE、CONTRIBUTING、pyproject.toml / requirements.txt が含まれている場合はそちらの指示に従ってください。

---

必要であれば、README に含める具体的なコマンド（例えば systemd ジョブや cron 実行例、Dockerfile、CI 設定例）や .env.example のテンプレートを作成します。どの情報を追加しますか？