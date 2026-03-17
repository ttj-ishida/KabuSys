# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
J-Quants や kabuステーション 等の外部 API からデータを取得して DuckDB に格納し、ETL・品質チェック・ニュース収集・監査ログなどを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のレイヤーを想定したデータ基盤と運用ユーティリティ群を提供します。

- データ収集（J-Quants API 経由の株価/財務/カレンダー、RSS ニュース）
- データ保存（DuckDB を用いた Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- カレンダー管理（JPX 営業日の判定や先読み更新）
- ニュース収集と銘柄紐付け（RSS → raw_news / news_symbols）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）
- 設定管理（.env または環境変数）

設計上の特徴：
- J-Quants API のレート制限遵守（120 req/min）とリトライ・トークンリフレッシュ処理
- DuckDB に対する冪等（ON CONFLICT）な保存
- ニュース収集時の SSRF や XML 攻撃対策、受信サイズ制限
- ETL の差分更新・バックフィル・品質チェック（欠損・スパイク・重複・日付不整合）

---

## 機能一覧

- settings（環境変数管理）
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込み（無効化可）
  - 必須環境変数の検証（例: JQUANTS_REFRESH_TOKEN 等）

- data.jquants_client
  - get_id_token（リフレッシュトークンから ID トークン取得）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ冪等保存）
  - レートリミッタ、リトライ、401 時の自動リフレッシュ等の実装

- data.news_collector
  - RSS 取得（gzip 対応、サイズ上限、XML 安全パーサ使用）
  - 記事正規化（URL 正規化・トラッキング除去・SHA-256 による記事ID）
  - raw_news 保存（INSERT ... RETURNING）、news_symbols 紐付け
  - SSRF 対策、プライベート IP 拒否、受信バイツ制限、gzip bomb 対策

- data.schema / data.audit
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema / init_audit_schema / get_connection

- data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl：日次 ETL の統合エントリポイント（品質チェック含む）
  - 差分更新・backfill に基づく安全なデータ取り込み

- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間のカレンダー差分更新ジョブ）

- data.quality
  - 欠損・スパイク・重複・日付不整合のチェック群
  - run_all_checks（品質問題を収集して返却）

- 監視 / 実行 / 戦略用のパッケージ構成（strategy, execution, monitoring — モジュールの入り口あり）

---

## セットアップ手順

前提: Python 3.9+（typing の新しい構文を使うため 3.10 以上を推奨）

1. リポジトリをクローン（あるいはソースを取得）

2. 仮想環境を作成して有効化
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要なパッケージをインストール
   - 最低限:
     ```
     pip install duckdb defusedxml
     ```
   - 開発用にローカル editable インストール:
     ```
     pip install -e .
     ```
     （プロジェクトに requirements.txt や pyproject.toml があればそちらを利用してください）

4. 環境変数の設定（.env の作成）
   - プロジェクトルートに `.env` あるいは `.env.local` を作成すると自動読み込みされます（自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須例（`.env` のサンプル）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_station_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     ```
   - 説明:
     - JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD は必須（Settings プロパティで _require によって検証されます）。
     - KABUSYS_ENV は "development", "paper_trading", "live" のいずれか。
     - LOG_LEVEL は "DEBUG","INFO","WARNING","ERROR","CRITICAL" のいずれか。
     - DUCKDB_PATH はデフォルト `data/kabusys.duckdb`。

---

## 使い方（簡単な例）

以下は Python スクリプトから主要な処理を行う最小例です。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)  # ファイル DB を作成・テーブルを作成
  # テストや一時実行では ":memory:" も可:
  # conn = init_schema(":memory:")
  ```

- 日次 ETL を実行する
  ```python
  from kabusys.data.pipeline import run_daily_etl

  # conn は init_schema の戻り値
  result = run_daily_etl(conn)
  print(result.to_dict())  # ETL のサマリ
  ```

- ニュース収集（RSS）を実行して DB に保存する
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758"}  # 既知の銘柄コード集合（抽出に使用）
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: saved_count, ...}
  ```

- J-Quants の API を直接利用する（トークン取得・日足取得）
  ```python
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  token = get_id_token()                 # settings から refresh token を使って取得
  quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,2,1))
  ```

- 監査スキーマの初期化（監査用テーブル追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  conn = init_schema("data/kabusys.duckdb")
  init_audit_schema(conn)
  ```

- テスト用にインメモリで実行する
  ```python
  conn = init_schema(":memory:")
  ```

ログレベルは環境変数 `LOG_LEVEL` で制御できます。KABUSYS_ENV によって振る舞い（本番/ペーパーなど）を切替可能です。

---

## 注意点 / 実運用上のポイント

- J-Quants API のレート上限（120 req/min）を遵守するため、jquants_client は内部で固定間隔のレートリミッタを使用しています。大規模な並列呼び出しは避けてください。
- ニュース収集モジュールは SSRF、XML Bomb、Gzip bomb などに対する保護を行っていますが、外部 URL 取得はネットワークポリシーに注意してください。
- DuckDB のファイルはデフォルトでプロジェクト内の `data/` に作成されます。運用時はバックアップやパスの管理を検討してください。
- 環境変数は `.env` / OS 環境変数で管理します。テスト時に自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

主要ファイル・モジュールの構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得/保存）
    - news_collector.py          — RSS ニュース収集・前処理・保存
    - schema.py                  — DuckDB スキーマ定義・初期化
    - pipeline.py                — ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py     — 市場カレンダー更新と営業日判定
    - audit.py                   — 監査ログ（signal/order/execution）
    - quality.py                 — データ品質チェック
  - strategy/
    - __init__.py                — 戦略用入口（戦略実装を配置）
  - execution/
    - __init__.py                — 発注 / ブローカー連携入口
  - monitoring/
    - __init__.py                — 監視・メトリクス（将来拡張）

（README はここにある各モジュール記述の要約を含みます。詳細は該当ソースファイルの docstring を参照してください。）

---

## 開発 / 貢献

- コードはモジュールごとにドキュメント文字列を付与しています。機能追加やバグ修正時はユニットテストの追加を推奨します。
- 外部 API 呼び出しを含むため、テストではモック（get_id_token, _urlopen などを差し替える）を利用してください。
- セキュリティ上重要な箇所（news_collector の URL 検証や jquants_client のトークン処理）を変更する場合は慎重にレビューしてください。

---

必要であれば、README に含めるサンプル .env.example ファイルや、よくあるトラブルシューティング（DB のパーミッション、API トークンの期限など）も追加します。追加希望があれば指示してください。