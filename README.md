# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（プロトタイプ）

KabuSys は、J-Quants 等の市場データを取り込み、DuckDB に保存・加工し、戦略（ファクター）計算、監査ログ、ニュース収集、ETL パイプライン等を提供するライブラリ群です。発注・モニタリング等のレイヤーを想定したモジュール構成になっています。

---

## 主な特徴

- データ取得・保存
  - J-Quants API クライアント（ページネーション・レート制御・自動トークン更新・リトライ付き）
  - DuckDB への冪等保存（ON CONFLICT による更新）
  - 市場カレンダー / 財務データ / 株価日足 / ニュース の ETL

- データ品質管理
  - 欠損・重複・スパイク・日付不整合チェック（quality モジュール）

- 研究・特徴量支援
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（スピアマンρ）計算、ファクター統計サマリー
  - Zスコア正規化ユーティリティ

- ニュース収集
  - RSS フィード取得、記事正規化、記事ID生成（SHA-256）、銘柄抽出、DuckDB への保存
  - SSRF / XML ボム / レスポンスサイズ対策などの安全対策実装

- 監査（Audit）
  - シグナル → 発注 → 約定 のトレーサビリティ用テーブル群と初期化ユーティリティ

- ETL パイプライン
  - 差分取得、バックフィル、カレンダー先読み、品質チェックを組み合わせた日次 ETL 実行

---

## 必要な環境変数

以下は Settings クラスで参照される主要な環境変数です（.env / 環境変数で設定）。

必須:
- JQUANTS_REFRESH_TOKEN  — J-Quants リフレッシュトークン
- KABU_API_PASSWORD      — kabuステーション API パスワード（発注連携がある場合）
- SLACK_BOT_TOKEN        — Slack 通知に利用するボットトークン
- SLACK_CHANNEL_ID       — Slack 通知先チャンネル ID

オプション（デフォルトあり）:
- KABUSYS_ENV            — 実行環境（development | paper_trading | live）、デフォルト `development`
- LOG_LEVEL              — ログレベル（DEBUG, INFO, ...）、デフォルト `INFO`
- KABUSYS_DISABLE_AUTO_ENV_LOAD — `1` を指定すると .env 自動ロードを無効化

データベースパス（デフォルト値）:
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH            — 監視用 SQLite 等（デフォルト: `data/monitoring.db`）

注意: Settings は環境変数が未設定だと ValueError を投げます。`.env.example` を元に `.env` を作成してください。

---

## セットアップ手順（ローカル開発向け）

1. Python バージョン
   - Python 3.10 以上（`|` 型注釈や組み込みの型ヒントを使用）

2. 仮想環境を作成・有効化
   - 例 (venv):
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```

3. 依存パッケージをインストール
   - 必要なライブラリ（代表例）:
     - duckdb
     - defusedxml
   - 例:
     ```bash
     pip install duckdb defusedxml
     ```
   - ※ プロジェクトに pyproject.toml / requirements.txt があればそれを使用してください。

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成（`.env.local` で上書き可）。自動ロードは config.py により行われます。
   - 例 `.env`:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     KABU_API_PASSWORD=your_password
     LOG_LEVEL=DEBUG
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     ```

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトで実行:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     # もしくはインメモリ:
     # conn = init_schema(":memory:")
     ```

---

## 使い方（代表的な呼び出し例）

- 日次 ETL 実行
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")  # 初回のみ
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 個別 ETL ジョブ（株価 / 財務 / カレンダー）
  ```python
  from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  run_prices_etl(conn, target_date=date.today())
  run_financials_etl(conn, target_date=date.today())
  run_calendar_etl(conn, target_date=date.today())
  ```

- ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 事前に保有する銘柄リスト等
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- ファクター計算 / 研究ユーティリティ
  ```python
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  target = date(2024, 1, 31)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)
  forward = calc_forward_returns(conn, target)
  ic = calc_ic(mom, forward, factor_col="mom_1m", return_col="fwd_1d")
  ```

- DuckDB に監査ログスキーマを追加（order/audit 用）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

---

## よくあるトラブルと対処

- ValueError: 環境変数が未設定
  - 必須環境変数（JQUANTS_REFRESH_TOKEN など）を `.env` に設定し、再起動してください。
  - 自動ロードを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

- DuckDB ファイル書き込みエラー
  - 保存先ディレクトリの権限を確認。`data/` ディレクトリを事前に作成するか、init_schema が自動で作成しますが権限は必要です。

- J-Quants API で 401 が返る
  - jquants_client は 401 時にリフレッシュを試みますが、リフレッシュトークンが無効だと失敗します。`JQUANTS_REFRESH_TOKEN` を確認してください。

- RSS 取得が失敗する / 空になる
  - ネットワークエラーや XML パースエラーはログに出ます。`fetch_rss` は不正レスポンスや大きすぎるレスポンスを安全にスキップします。

---

## ディレクトリ構成（主要ファイル）

プロジェクトは src/kabusys 以下に主要モジュールを配置しています。主な構成は以下の通りです。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存）
    - news_collector.py        — RSS ニュース収集・保存
    - schema.py                — DuckDB スキーマ定義 / init_schema
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - quality.py               — データ品質チェック
    - stats.py                 — 統計ユーティリティ（zscore_normalize）
    - features.py              — 特徴量ユーティリティ（再エクスポート）
    - calendar_management.py   — カレンダー管理（営業日判定、更新ジョブ）
    - audit.py                 — 監査ログテーブル定義 / 初期化
    - etl.py                   — ETL 公開インターフェース（再エクスポート）
  - research/
    - __init__.py
    - feature_exploration.py   — 将来リターン・IC・summary 等
    - factor_research.py       — momentum/value/volatility 計算
  - strategy/
    - __init__.py              — 戦略層（拡張ポイント）
  - execution/
    - __init__.py              — 発注/約定/ポジション管理（拡張ポイント）
  - monitoring/
    - __init__.py              — モニタリング用モジュール（拡張ポイント）

（上記はコードベースの主要モジュールを抜粋したものです）

---

## 設計上の注意点

- research / data モジュールは外部の発注 API などを直接呼ばない設計です（本番口座にアクセスしない）。
- J-Quants API のレート制限（120 req/min）や 401 自動リフレッシュ、再試行ロジックを実装済みです。
- DuckDB への INSERT は可能な限り冪等（ON CONFLICT ... DO UPDATE / DO NOTHING）にしています。
- ニュース RSS 周りは SSRF／XML ボム／大容量レスポンス対策等の安全措置が組み込まれています。

---

必要に応じて README に追記したい利用シナリオ（例: scheduler との連携、Docker 化、CI での DB 初期化スクリプト例など）があれば教えてください。