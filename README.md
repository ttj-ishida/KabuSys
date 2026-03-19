# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
主に J-Quants API から市場データや財務データを取得し、DuckDB に格納して特徴量を生成、研究（ファクター解析）や戦略・発注層と連携するためのユーティリティ群を提供します。

- パッケージ名: kabusys
- バージョン: 0.1.0（src/kabusys/__init__.py）

---

## プロジェクト概要

KabuSys は以下の役割を持つモジュール群で構成されています。

- データ取得 & ETL（J-Quants クライアント、RSS ニュース収集、DuckDB スキーマ・保存）
- データ品質チェック（欠損・重複・スパイク・日付不整合の検出）
- マーケットカレンダー管理（JPX の祝日・半日・SQ判定）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、統計サマリ）
- 監査ログ（シグナル→発注→約定のトレーサビリティ用テーブル構築）
- 設定管理（.env / 環境変数を利用）

設計方針の一部：
- DuckDB を一次データベースに採用（オンディスク / インメモリ可）
- J-Quants API に対してレート制御・リトライ・トークン自動リフレッシュを実装
- ETL は冪等（ON CONFLICT）で再実行可能
- 研究関係の関数は外部 API にアクセスせず、prices_daily / raw_financials のみ参照

---

## 主な機能一覧

- jquants_client
  - J-Quants API から株価日足、財務データ、マーケットカレンダーを取得
  - レートリミット制御、リトライ、401 時のトークン自動リフレッシュ
  - DuckDB へ冪等に保存する save_* 関数

- data.pipeline / etl
  - 差分更新（最終取得日からの差分取得 + バックフィル）
  - 市場カレンダー先読み
  - 品質チェックを実行して問題を収集

- data.schema / audit
  - DuckDB のスキーマ初期化（Raw / Processed / Feature / Execution 層）
  - 監査ログ用の別個 DB 初期化ユーティリティ

- data.news_collector
  - RSS からニュースを収集・前処理・正規化・DB 保存
  - SSRF 対策、gzip サイズ上限、トラッキングパラメータ除去、記事IDの SHA-256 ベース生成
  - 記事と銘柄コードの紐付け機能

- data.quality
  - 欠損 / 重複 / スパイク / 日付不整合チェック

- research
  - calc_momentum, calc_volatility, calc_value（ファクター計算）
  - calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize（研究支援）

- config
  - .env 自動読み込み（プロジェクトルートの .env / .env.local、環境変数優先）
  - 必須設定のチェック（未設定時は ValueError）

---

## セットアップ手順

前提
- Python 3.10 以上（型記法（X | Y）や一部の構文を使用）
- DuckDB を利用するためネイティブ拡張が使える環境

1. リポジトリをクローンしてパッケージをインストール（開発環境）
   - 例（プロジェクトルートで）:
     ```
     python -m venv .venv
     source .venv/bin/activate  # Windows: .venv\Scripts\activate
     pip install --upgrade pip
     pip install duckdb defusedxml
     # 必要に応じて他の依存を追加
     ```

   ※ requirements.txt は含まれていない想定のため、必要なパッケージを上記のように手動でインストールしてください。

2. 環境変数 / .env の準備
   - プロジェクトルートに `.env`（必要に応じて `.env.local`）を作成します。
   - 自動読み込みは kabusys.config により行われます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   最低限設定が必要な環境変数（config.Settings より）:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - SLACK_BOT_TOKEN (必須)
   - SLACK_CHANNEL_ID (必須)

   オプション／デフォルト:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1：自動 .env 読み込みを無効化
   - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
   - SQLITE_PATH: data/monitoring.db（デフォルト）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

3. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから schema を初期化します。
   - 例:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # ディレクトリは自動作成される
     # 必要に応じて conn を保持して以降の処理に渡す
     ```

   - 監査ログ専用 DB を初期化する場合:
     ```python
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（代表的な例）

- 設定値を参照する:
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)         # Path オブジェクト
  print(settings.is_dev)              # True/False
  token = settings.jquants_refresh_token  # 必須（未設定だと例外）
  ```

- 日次 ETL を実行する:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 単体の ETL（株価のみ）:
  ```python
  from kabusys.data.pipeline import run_prices_etl
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  print(f"fetched={fetched}, saved={saved}")
  ```

- ニュース収集ジョブ:
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
  res = run_news_collection(conn, sources=None, known_codes=known_codes)
  print(res)  # {source_name: 新規保存件数}
  ```

- 研究（ファクター計算）:
  ```python
  from kabusys.research import calc_momentum, calc_volatility, zscore_normalize
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  recs = calc_momentum(conn, date(2024, 1, 31))
  recs_norm = zscore_normalize(recs, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
  ```

- 将来リターン / IC 計算:
  ```python
  from kabusys.research import calc_forward_returns, calc_ic
  fwd = calc_forward_returns(conn, date(2024,1,31), horizons=[1,5,21])
  ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
  ```

---

## 環境変数（要点）

- 自動読み込み:
  - パッケージ import 時に、プロジェクトルート（.git または pyproject.toml ベース）を探索し `.env` と `.env.local` を自動読み込みします。
  - OS 環境変数が優先され、`.env.local` は `.env` を上書きします。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化できます（テスト等）。

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID

- オプション:
  - KABUSYS_ENV (development | paper_trading | live)
  - LOG_LEVEL (DEBUG|INFO|...)
  - DUCKDB_PATH / SQLITE_PATH

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得 + 保存）
    - news_collector.py      — RSS ニュース収集・前処理・保存
    - schema.py              — DuckDB スキーマ定義・init_schema / get_connection
    - pipeline.py            — ETL パイプライン（差分取得・品質チェック）
    - features.py            — 特徴量ユーティリティ（公開インターフェース）
    - stats.py               — Zスコアなど統計ユーティリティ
    - calendar_management.py — マーケットカレンダー関連ユーティリティ
    - audit.py               — 監査ログ用スキーマ初期化
    - etl.py                 — ETL 関連の公開インターフェース（型等）
    - quality.py             — データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py — 将来リターン / IC / 統計サマリ等
    - factor_research.py     — Momentum / Volatility / Value 等のファクター計算
  - strategy/
    - __init__.py            — 戦略層（未実装ファイル群のプレースホルダ）
  - execution/
    - __init__.py            — 発注層（未実装ファイル群のプレースホルダ）
  - monitoring/
    - __init__.py            — 監視 / メトリクス（未実装プレースホルダ）

---

## 補足・開発上の注意

- DuckDB の SQL 実行はパラメータバインド（?）で行っています。SQL インジェクションに対する配慮がされていますが、外部からの未検証文字列を直接渡さないでください。
- ニュース収集モジュールは外部 URL を開くため SSRF 対策を施しています（スキーム検証・プライベート IP 検出・リダイレクト検査・サイズ上限）。
- J-Quants の API レート制限（120 req/min）に対応するため固定間隔のスロットリングを実装しています。
- ETL は冪等性を重視して設計されていますが、スキーマ変更や外部からの直接挿入がある場合は品質チェックを実行して整合性を確保してください。
- production では KABUSYS_ENV を `live` に設定し、発注ロジックや実アカウントへのアクセスに十分注意してください（このコードベースでは発注層はプレースホルダのため別実装が必要です）。

---

もし README に追加したいセクション（例: API ドキュメント、運用手順、CI/CD、サンプルデータのロード手順など）があれば教えてください。必要に応じて実際のコマンドやサンプル .env.example も作成します。