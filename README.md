# KabuSys — 日本株自動売買プラットフォーム（README）

このリポジトリは「KabuSys」と呼ばれる、日本株向けの自動売買・データ基盤・リサーチ用ライブラリセットです。DuckDB をデータ層に用い、J-Quants API や RSS ニュースを取り込み、特徴量構築→シグナル生成→発注／監査の各レイヤを想定した設計になっています。

以下はこのコードベースの概要、機能、セットアップと基本的な使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

- DuckDB を中心にしたデータ基盤（Raw / Processed / Feature / Execution 層）。
- J-Quants API クライアントを備えた差分 ETL（株価・財務・市場カレンダー）。
- RSS ベースのニュース収集と記事→銘柄の紐付け（SSRF 対策・サイズ制限・重複除去）。
- 研究（research）向けのファクター計算（Momentum / Volatility / Value）と統計ユーティリティ。
- 戦略層（feature_engineering / signal_generator）：正規化済み特徴量から最終スコアを算出し BUY/SELL シグナルを生成。
- 発注・実行・監査のスキーマ（テーブル設計）と基礎ユーティリティ（スキーマ初期化、トレーサビリティ）。
- ロバスト性を重視：API レート制限、リトライ、トランザクションでの原子性、冪等保存など。

---

## 主な機能一覧

- data/schema.py
  - DuckDB のフルスキーマ（raw_prices, raw_financials, prices_daily, features, signals, orders, executions, positions, raw_news 等）を定義・初期化。
- data/jquants_client.py
  - J-Quants API クライアント（ページネーション対応、レート制限、リトライ、トークン自動リフレッシュ）。
  - fetch / save のペア関数（株価・財務・カレンダー保存用）。
- data/pipeline.py
  - 差分取得ロジック（backfill 対応）を含む日次 ETL 実行（run_daily_etl）。
- data/news_collector.py
  - RSS 取得・前処理・正規化・DB 保存（記事ID は正規化URLの SHA-256 で生成）。
  - SSRF 対策・gzip サイズチェック・トラッキングパラメータ除去。
- data/calendar_management.py
  - market_calendar の更新ジョブ、営業日判定・前後営業日取得等のユーティリティ。
- research/*
  - calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials を入力とするファクター計算）。
  - calc_forward_returns / calc_ic / factor_summary / rank（リサーチ向け解析ツール）。
- strategy/feature_engineering.py
  - 生ファクターの統合・Zスコア正規化・ユニバースフィルタ・features テーブルへの日付単位 UPSERT。
- strategy/signal_generator.py
  - features および ai_scores を組合せた最終スコア計算、Bear レジーム抑制、BUY/SELL 生成、signals テーブルへの日付単位置換。
- data/stats.py
  - クロスセクション Z スコア正規化ユーティリティ。
- audit / execution 層（スキーマ定義）
  - 監査ログ、order_requests、executions テーブルなどトレーサビリティ設計。

---

## 必要要件（推奨）

- Python >= 3.10（| 型ヒントなどの構文を使用）
- pip install でインストールする外部ライブラリ（最低限）:
  - duckdb
  - defusedxml
- ネットワークアクセス: J-Quants API、RSS フィード等へのアクセス

（実際の requirements.txt はリポジトリに含めてください。上記は最低限の依存例です）

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` でロードされます（自動ロードはデフォルトで有効）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

重要な環境変数（Settings クラスから抜粋）:

- JQUANTS_REFRESH_TOKEN (必須) : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) : kabuステーション API のパスワード
- KABU_API_BASE_URL (省略可) : デフォルト "http://localhost:18080/kabusapi"
- SLACK_BOT_TOKEN (必須) : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) : Slack 通知先チャンネル ID
- DUCKDB_PATH (省略可) : デフォルト "data/kabusys.duckdb"
- SQLITE_PATH (省略可) : デフォルト "data/monitoring.db"
- KABUSYS_ENV (省略可) : "development" | "paper_trading" | "live"（デフォルト "development"）
- LOG_LEVEL (省略可) : "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト "INFO"）

.env 例（.env.example を参考に作成してください）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカルでの開発用簡易手順）

1. リポジトリをクローンし、仮想環境を作成：
   ```
   git clone <repo_url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール（最低限）:
   ```
   pip install duckdb defusedxml
   ```
   ※プロジェクトが pip 配布可能であれば `pip install -e .` を使って開発インストールしてください。

3. `.env` を作成して必要な環境変数を設定（上記参照）。

4. DuckDB スキーマの初期化（デフォルトパスを使用する場合）:
   Python REPL またはスクリプトで次を実行：
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   print("Initialized:", conn)
   ```

---

## 基本的な使い方（サンプル）

- 日次 ETL（株価/財務/カレンダー取得 + 品質チェック）:
  ```python
  from datetime import date
  from kabusys.data import schema, pipeline

  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量構築（features テーブルに日付単位で保存）:
  ```python
  from datetime import date
  from kabusys.data import schema
  from kabusys.strategy import build_features

  conn = schema.get_connection("data/kabusys.duckdb")
  n = build_features(conn, date.today())
  print("features upserted:", n)
  ```

- シグナル生成（features / ai_scores / positions を参照して signals に保存）:
  ```python
  from datetime import date
  from kabusys.data import schema
  from kabusys.strategy import generate_signals

  conn = schema.get_connection("data/kabusys.duckdb")
  count = generate_signals(conn, date.today(), threshold=0.6)
  print("signals written:", count)
  ```

- RSS ニュース収集と保存:
  ```python
  from kabusys.data import news_collector, schema

  conn = schema.get_connection("data/kabusys.duckdb")
  # known_codes は抽出に使用する銘柄コードの集合（任意）
  res = news_collector.run_news_collection(conn, sources=None, known_codes=None)
  print(res)
  ```

- カレンダー更新ジョブ:
  ```python
  from kabusys.data import calendar_management, schema

  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn, lookahead_days=90)
  print("calendar saved:", saved)
  ```

---

## 運用上の注意 / 実装上のポイント

- J-Quants API のレート制限（120 req/min）に従うよう RateLimiter を実装しています。大量取得時は時間配分に注意してください。
- jquants_client は 401 を受けた場合にトークン自動リフレッシュを行い 1 回だけ再試行します。リトライは指数バックオフで最大 3 回。
- データ保存は ON CONFLICT / トランザクションで冪等性と原子性を担保しています。
- features や signals への書き込みは「日付単位で DELETE→INSERT」の置換を行い、同日分は常に上書き（冪等）。
- RSS 収集は SSRF 対策、コンテンツサイズ上限、gzip 解凍後の上限チェックを行っています。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行います。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを無効化可能です。
- KABUSYS_ENV による挙動切替（development / paper_trading / live）を用意しています。実運用時は `live` を使用してください。

---

## よく使うモジュール一覧（短い説明）

- kabusys.config — 環境変数 / 設定管理（.env 自動読み込み、必須変数チェック）
- kabusys.data.schema — DuckDB スキーマ初期化 / 接続ユーティリティ
- kabusys.data.jquants_client — J-Quants API クライアント + 保存ユーティリティ
- kabusys.data.pipeline — 差分 ETL / run_daily_etl
- kabusys.data.news_collector — RSS 収集・保存・銘柄抽出
- kabusys.data.calendar_management — 市場カレンダー管理・営業日計算
- kabusys.data.stats — zscore_normalize（クロスセクション正規化）
- kabusys.research.* — ファクター計算 & リサーチ用統計ツール
- kabusys.strategy.* — feature_engineering / signal_generator（戦略の核）

---

## ディレクトリ構成（主要ファイル）

あくまで本 README が解析したコードベースに基づく抜粋です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - schema.py
      - jquants_client.py
      - pipeline.py
      - news_collector.py
      - calendar_management.py
      - features.py
      - stats.py
      - audit.py
      - audit (監査関連 DDL)
      - ...（raw / processed / execution 層のDDL 定義等）
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/
      - __init__.py
    - monitoring/  (パッケージ化される想定の監視ロジックフォルダ)
    - その他（将来的なモジュール）

---

## 開発・貢献

- コードはテスト可能性を意識した設計（関数に接続やトークンを注入可能）になっています。ユニットテストでは DuckDB のインメモリ接続（":memory:"）や jquants_client の HTTP 呼び出しをモックしてください。
- 重大なデータ破壊操作はアプリ側で明示的に管理する前提です（監査ログは削除しない方針など）。

---

README の内容はコードベースから自動抽出した情報を元にまとめています。追加で「導入例スクリプト」「docker-compose」「CI 設定」「requirements.txt」「.env.example」の追記・整備をご希望でしたら、その旨を教えてください。