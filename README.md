# KabuSys

KabuSys は日本株の自動売買基盤（データプラットフォーム＋戦略エンジン）の実装骨格です。  
主に DuckDB をデータレイク／特徴量保存に使い、J-Quants API や RSS 等からデータを取得し、特徴量生成・シグナル生成を行います。コードベースは ETL（データ取得） → 特徴量計算 → シグナル生成 → 発注監査（スキーマ設計まで）といった流れを想定したモジュール群で構成されています。

バージョン: 0.1.0

---

## 主な機能一覧

- データ取得（J-Quants API クライアント）
  - 日足（OHLCV）、財務情報、市場カレンダーの取得（ページネーション・リトライ・レート制御対応）
- ETL パイプライン
  - 差分取得（最終取得日ベース）、バックフィル、品質チェックといった日次 ETL（run_daily_etl）
- データベース（DuckDB）スキーマ定義・初期化（init_schema）
  - Raw / Processed / Feature / Execution 層のテーブルを定義
- ニュース収集（RSS）
  - RSS 取得、URL 正規化、記事保存、銘柄コード抽出・紐付け
- 研究用ファクター計算（research）
  - Momentum / Volatility / Value ファクター計算、将来リターン・IC 計算、統計サマリー
- 特徴量エンジニアリング（strategy.feature_engineering）
  - ファクターの正規化、ユニバースフィルタ、features テーブルへの冪等書き込み
- シグナル生成（strategy.signal_generator）
  - features と ai_scores を統合して final_score を算出、BUY/SELL シグナルを生成し signals テーブルへ保存
- 監査／発注用スキーマ（audit）
  - signal_events / order_requests / executions 等の監査テーブル定義

---

## 前提条件

- Python 3.10 以上（| 型ヒントや match は使っていませんが、PEP604 の `X | Y` を使っているため 3.10+ を想定）
- 必要パッケージ（抜粋）:
  - duckdb
  - defusedxml
  - （標準ライブラリのみで実装されているユーティリティが多いです）
- J-Quants API のリフレッシュトークン等の環境変数

---

## セットアップ手順

1. リポジトリをクローン／チェックアウトする

2. 仮想環境を作成して依存をインストールする（例: pip）

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb defusedxml
   ```

   （必要に応じて requirements.txt を用意している場合はそちらを使用してください）

3. .env を作成する

   プロジェクトルートに `.env`（あるいは `.env.local`）を配置すると自動的に読み込まれます（ただしテスト等で無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください）。

   例 `.env`:

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマを初期化する

   例えば REPL やスクリプトで:

   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```

   - メモリ DB を使う場合は `":memory:"` を渡せます。
   - `init_schema` は親ディレクトリがない場合は自動作成します。

---

## 使い方（代表的な呼び出し例）

以下は最小限の操作例です。実運用ではログ・エラーハンドリング・認証トークンの管理を行ってください。

- 日次 ETL を実行（市場カレンダー取得 → 株価 → 財務 → 品質チェック）

  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  conn.close()
  ```

- 特徴量を構築（features テーブルへ書き込み）

  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import build_features

  conn = get_connection("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024, 1, 10))
  print(f"features upserted: {n}")
  conn.close()
  ```

- シグナルを生成して保存（signals テーブルへ）

  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import generate_signals

  conn = get_connection("data/kabusys.duckdb")
  count = generate_signals(conn, target_date=date(2024, 1, 10), threshold=0.6)
  print(f"signals written: {count}")
  conn.close()
  ```

- ニュース収集ジョブを実行して保存（raw_news / news_symbols）

  ```python
  from kabusys.data.schema import get_connection
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203","6758", ...}  # 既知銘柄コードのセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  conn.close()
  ```

- カレンダー更新バッチ（夜間ジョブ）

  ```python
  from kabusys.data.schema import get_connection
  from kabusys.data.calendar_management import calendar_update_job

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("calendar saved:", saved)
  conn.close()
  ```

---

## 主要な環境変数（settings から参照されるもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite DB パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境（development / paper_trading / live）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — set to 1 to disable auto .env loading

注意: Settings の必須項目が未設定の場合は起動時に ValueError が発生します。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py — パッケージエントリ（version 等）
  - config.py — 環境変数・設定管理（.env 自動読み込み / Settings）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py — ETL パイプライン（run_daily_etl, 個別 ETL ジョブ）
    - schema.py — DuckDB スキーマ定義と初期化（init_schema, get_connection）
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - news_collector.py — RSS 収集・前処理・保存、銘柄抽出
    - calendar_management.py — 市場カレンダー管理・営業日ロジック
    - features.py — data.stats の再エクスポート
    - audit.py — 発注～約定の監査ログ用 DDL（signal_events / order_requests / executions）
    - pipeline.py — ETL 実行ロジック、差分取得の補助
  - research/
    - __init__.py — 研究用 API エクスポート
    - factor_research.py — Momentum/Volatility/Value 等の生ファクター計算
    - feature_exploration.py — calc_forward_returns, calc_ic, factor_summary 等
  - strategy/
    - __init__.py — strategy API エクスポート
    - feature_engineering.py — ファクター統合・正規化 → features テーブルへ
    - signal_generator.py — final_score 計算・BUY/SELL シグナル生成 → signals テーブルへ
  - execution/
    - __init__.py — 発注実行層（空ファイル: 将来的に実装）
  - monitoring/ — モニタリング関連（DB 保存先: sqlite 等） ※実装ファイルは本コードリストに含まれません

---

## 開発メモ / 注意点

- 自動 .env ロードは project root (.git または pyproject.toml のあるディレクトリ) を基準に行われます。テストや特殊環境で無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants クライアントはレート制御（120 req/min）、リトライ、401 の自動リフレッシュに対応しています。
- DuckDB への保存は可能な限り冪等（ON CONFLICT / DO UPDATE / DO NOTHING）で行う設計です。
- News Collector は SSRF 対策・受信サイズ制限・XML の安全パース（defusedxml）などセキュリティ対策を実装しています。
- strategy 層は発注 API への直接依存を持たず、signals テーブルにシグナルを書き出すだけに留めています（execution 層で安全に処理する想定）。
- 型ヒントと設計コメント（README に相当する設計文書名がコード内で言及されています）が多いため、実装拡張の際に整合性を保ちやすい構成になっています。

---

もし README の特定セクション（例: デプロイ手順、CI 設定、より詳細な API 使用例、.env.example のテンプレートなど）を追加したければ、用途（ローカル実行／本番運用／Docker 化 等）を教えてください。それに合わせて具体例を追記します。