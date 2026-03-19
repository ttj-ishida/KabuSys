# KabuSys

日本株向けの自動売買システム向けライブラリ（KabuSys）。  
DuckDB をデータレイヤに使い、J-Quants API / RSS ニュースの収集、特徴量計算、シグナル生成、ETL パイプライン、マーケットカレンダー管理、監査ログなどを提供します。

---

## プロジェクト概要

KabuSys は次のような責務を持つモジュール群を含みます。

- データ収集（J-Quants API 経由の株価・財務・カレンダー、RSS ニュース）
- DuckDB スキーマ定義と初期化
- ETL パイプライン（差分取得・保存・品質チェック）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 特徴量（features）生成・正規化（Z スコア）
- シグナル生成（final_score に基づく BUY/SELL 判定、エグジット判定）
- マーケットカレンダー管理（営業日判定 / next/prev_trading_day 等）
- ニュース収集・銘柄抽出・DB 保存
- 監査ログ / 発注トレーサビリティ用スキーマ

設計上の重要点：
- ルックアヘッドバイアス防止（target_date 時点のデータのみを使用）
- 冪等性（DB 保存は ON CONFLICT / トランザクションで安全に）
- 外部依存（発注 API など）は strategy 層や execution 層が担い、解析／生成モジュールは直接依存しない

---

## 主な機能一覧

- data/
  - jquants_client：J-Quants API クライアント（レート制限・リトライ・トークン自動更新）
  - news_collector：RSS 取得・前処理・記事保存・銘柄抽出
  - schema：DuckDB のスキーマ定義と init_schema()
  - pipeline：日次 ETL（run_daily_etl 等）
  - calendar_management：営業日判定や calendar_update_job
  - stats：Z スコア正規化 等の統計ユーティリティ
- research/
  - factor_research：モメンタム/ボラティリティ/バリューのファクター計算
  - feature_exploration：将来リターン計算、IC、統計サマリー
- strategy/
  - feature_engineering.build_features：生ファクターを正規化して features テーブルへ保存
  - signal_generator.generate_signals：features と ai_scores を統合して signals を作成
- config：
  - 環境変数読み込み（.env / .env.local 自動ロード）、Settings オブジェクト
- monitoring / execution：
  - （プロジェクト構成上の名前空間。実装は execution 層向けに拡張可能）

---

## セットアップ手順

前提
- Python 3.10 以上（typing における PEP 604 の union 型（A | B）を使用）
- DuckDB を利用可能な環境

1. リポジトリをクローン（またはパッケージをインストール）
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要なパッケージをインストール（最低限）
   ```
   pip install duckdb defusedxml
   ```
   ※ 実行環境や追加機能（Slack 通知等）に応じて他パッケージが必要になる場合があります。

4. 環境変数を設定
   プロジェクトルート（`.git` または `pyproject.toml` があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

   必須な環境変数（Settings により参照・検証されます）:
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD — kabu ステーション API パスワード（発注等で使用）
   - SLACK_BOT_TOKEN — Slack 通知用ボットトークン
   - SLACK_CHANNEL_ID — Slack チャンネル ID

   任意（デフォルト値あり）:
   - KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH — DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — モニタリング用 SQLite パス（デフォルト: data/monitoring.db）

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要な API と実行例）

下記は最小限の動作例です。すべて Python から呼び出します。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")  # ファイル DB（親ディレクトリを自動作成）
  ```

- 既存 DB へ接続
  ```python
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")
  ```

- 日次 ETL の実行（市場カレンダー・株価・財務・品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2025, 3, 1))
  print(result.to_dict())
  ```

- 特徴量（features）構築
  ```python
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  count = build_features(conn, target_date=date(2025, 3, 1))
  print(f"features upserted: {count}")
  ```

- シグナル生成
  ```python
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2025, 3, 1), threshold=0.6)
  print(f"signals generated: {total}")
  ```

- RSS ニュース収集ジョブ（既知の銘柄コードセットを渡して銘柄紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- カレンダー更新バッチ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"calendar records saved: {saved}")
  ```

注意点：
- 各関数は DuckDB 接続を引数に取るため、接続管理（コネクションの生成・閉鎖）は呼び出し側で行ってください。
- ETL / データ取得機能は外部 API を呼ぶため、環境変数（トークン等）が正しく設定されている必要があります。

---

## 環境設定の挙動（config.Settings）

- 自動で `.env` / `.env.local` をプロジェクトルートから読み込みます（読み込み順: OS 環境 > .env.local > .env）。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途等）。
- Settings で参照される主要プロパティ:
  - jquants_refresh_token (JQUANTS_REFRESH_TOKEN) — 必須
  - kabu_api_password (KABU_API_PASSWORD) — 必須
  - kabu_api_base_url (KABU_API_BASE_URL) — デフォルト: http://localhost:18080/kabusapi
  - slack_bot_token / slack_channel_id — 必須（Slack 通知を使う場合）
  - duckdb_path / sqlite_path — デフォルト値あり
  - env — KABUSYS_ENV（development / paper_trading / live）
  - log_level — LOG_LEVEL（DEBUG〜CRITICAL）

未設定の必須環境変数を参照すると ValueError が発生します。

---

## ディレクトリ構成

主要ファイル / モジュールを抜粋します（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - calendar_management.py
    - features.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/         (名前空間/拡張用)
  - monitoring/        (名前空間/拡張用)

各モジュールの役割は前項「主な機能一覧」を参照してください。

---

## 開発・拡張のヒント

- DuckDB を使った SQL と Python の組合せで多数の処理を実装しているため、調査・デバッグ時は conn.execute("SQL").fetchall() で中間結果を確認すると良いです。
- research モジュールは外部ライブラリに依存しない実装を目指しています。必要に応じて pandas 等を導入して高速化する余地があります。
- ニュース取得は SSRF / XML Bomb 等の脆弱性対策を行っていますが、外部 RSS の扱いには注意してください（接続先ホストの検証やタイムアウト設定など）。
- シグナル生成の重みや閾値は generate_signals の引数で調整可能です（weights, threshold）。

---

## サポート / 貢献

- バグ修正や機能追加は Pull Request を通じて受け付けてください。  
- 大きな設計変更を提案する場合は Issue で議論の上で実装してください。

---

README は以上です。必要があれば「セットアップの自動化スクリプト」や「.env.example」のテンプレート、または具体的な開発フロー（テスト・CI）の追記も提供できます。どの情報を追加しますか？