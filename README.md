# KabuSys

日本株向けの自動売買・データパイプライン基盤ライブラリ。  
J-Quants からの市場データ取得、DuckDB ベースのデータスキーマ、ファクター計算・特徴量合成、シグナル生成、RSS ニュース収集、マーケットカレンダー管理、監査ログなどを提供します。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を含む Python パッケージです。

- J-Quants API を用いた株価・財務・カレンダーの取得（差分取得・ページング対応、トークン自動更新、レート制御、リトライ）
- DuckDB を用いたデータスキーマの定義と初期化（Raw → Processed → Feature → Execution レイヤ）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- 研究（research）向けのファクター計算・特徴量探索ユーティリティ
- 戦略層：特徴量を合成して features テーブルへ保存（feature_engineering）、features + ai_scores から売買シグナルを生成（signal_generator）
- ニュース収集（RSS）と銘柄紐付け
- マーケットカレンダー管理（営業日判定・翌営業日取得など）
- 監査ログ（signal → order → execution のトレース用テーブル群）

設計方針は「ルックアヘッドバイアス回避」「冪等性」「API レート制御・リトライ」「DB での原子性（トランザクション）」等に重点を置いています。

---

## 主な機能一覧

- 環境変数管理（ローカルの `.env` / `.env.local` を自動読み込み、無効化可）
- DuckDB スキーマ定義・初期化（init_schema）
- J-Quants クライアント
  - 株価日足、財務データ、マーケットカレンダー取得（ページネーション対応）
  - トークン自動リフレッシュ、120 req/min のレート制御、リトライ
  - DuckDB へ冪等保存（ON CONFLICT を利用）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 研究用のファクター計算（モメンタム / ボラティリティ / バリュー 等）
- 特徴量エンジニアリング（Zスコア正規化、ユニバースフィルタ、features テーブルへの UPSERT）
- シグナル生成（final_score による BUY/SELL の作成、Bear レジームフィルタ、エグジット判定）
- RSS ベースのニュース収集（SSRF 防御、トラッキングパラメータ除去、前処理、raw_news へ冪等保存）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day、calendar update job）
- 監査ログ（signal_events / order_requests / executions など）

---

## セットアップ手順

1. 必要環境を用意
   - Python 3.9+（コードは型アノテーション等で新しいバージョンを想定）
   - DuckDB（Python パッケージ）
   - defusedxml（RSS 解析で使用）
   - （必要に応じて）その他依存パッケージ

   例（pip）:
   ```
   pip install duckdb defusedxml
   ```

   ※ プロジェクトに requirements ファイルが無い場合は上記を目安に追加してください。

2. リポジトリをクローンしてインストール（開発モード）
   ```
   git clone <repo-url>
   cd <repo>
   pip install -e .
   ```

3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと、自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu API のパスワード（execution 層利用時）
     - SLACK_BOT_TOKEN — Slack 通知用（必要に応じて）
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化
   Python REPL またはスクリプトから:
   ```python
   from kabusys.data.schema import init_schema, get_connection, settings
   conn = init_schema(settings.duckdb_path)
   # または
   # conn = init_schema("data/kabusys.duckdb")
   ```

---

## 使い方（代表的な例）

- 日次 ETL（取得 → 保存 → 品質チェック）
  ```python
  from datetime import date
  import kabusys
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(kabusys.config.settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量構築（features テーブルへ書き込む）
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import build_features

  conn = get_connection("data/kabusys.duckdb")
  count = build_features(conn, target_date=date(2026, 1, 31))
  print(f"features upserted: {count}")
  ```

- シグナル生成
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import generate_signals

  conn = get_connection("data/kabusys.duckdb")
  total_signals = generate_signals(conn, target_date=date(2026, 1, 31))
  print(f"signals generated: {total_signals}")
  ```

- ニュース収集ジョブ
  ```python
  from kabusys.data.schema import get_connection
  from kabusys.data.news_collector import run_news_collection

  conn = get_connection("data/kabusys.duckdb")
  # known_codes は銘柄抽出に使う有効コードの集合（任意）
  counts = run_news_collection(conn, known_codes={"7203","6758"})
  print(counts)
  ```

- カレンダー更新ジョブ（夜間バッチ）
  ```python
  from kabusys.data.schema import get_connection
  from kabusys.data.calendar_management import calendar_update_job

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

---

## 主要モジュール（概要）

- kabusys.config
  - 環境変数の読み込み・検証。自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（無効化可）。
  - settings オブジェクトで各種設定へアクセス。

- kabusys.data
  - jquants_client: J-Quants API クライアント & DuckDB 保存ユーティリティ
  - schema: DuckDB スキーマ定義 / init_schema / get_connection
  - pipeline: ETL パイプライン（run_daily_etl 等）
  - news_collector: RSS 取得・正規化・DB 保存・銘柄抽出
  - calendar_management: JPX カレンダー更新・営業日関連ユーティリティ
  - stats / features: 統計ユーティリティ（Z スコア正規化 など）
  - audit: 監査ログ / 監査用テーブル定義

- kabusys.research
  - factor_research: momentum / volatility / value のファクター算出
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）、統計サマリー等

- kabusys.strategy
  - feature_engineering: raw factor を正規化・合成して features テーブルへ保存
  - signal_generator: features と ai_scores を統合して BUY/SELL シグナルを生成

- kabusys.execution
  - 発注・約定・ポジション管理（パッケージ構造上は存在、実装は実行層に依存）

- kabusys.monitoring
  - 監視・アラート用（パッケージ内に名前空間を確保）

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - calendar_management.py
      - audit.py
      - features.py
      - stats.py
      - (その他 data 関連モジュール)
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
    - monitoring/
      - (監視関連モジュール)

---

## 設定上の注意事項・運用メモ

- 環境変数はローカルの `.env` / `.env.local` から自動読み込みされます。テストや CI で自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- settings.env は `development` / `paper_trading` / `live` のいずれかである必要があります。
- J-Quants API はレート制限（120 req/min）とレスポンスのページネーションがあるため、jquants_client はレート制御とページネーション対応、リトライ・トークン自動更新を実装しています。
- DuckDB の初期化は init_schema() を一度だけ実行しておくこと（スキーマは冪等なので何度呼んでも安全）。
- features と signals の生成は target_date を明示することでルックアヘッドバイアスを避ける設計になっています。
- news_collector は RSS フィードの安全性（SSRF、XML Bomb 等）に対する対策を含みます。

---

## 貢献 / 開発

- コードのスタイルは各モジュールの docstring に設計方針・注意点を明記しています。新しい機能はまずユニットテストと小規模のローカル実行で検証してください。
- 重要な DB 操作はトランザクションで囲まれているため、操作失敗時は自動でロールバックされます。エラー発生時はログを確認してください。

---

疑問点や README に追加してほしい使用例があれば教えてください。必要であれば具体的なセットアップスクリプトや Docker 化手順の雛形も作成します。