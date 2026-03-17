# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ KabuSys の README（日本語）

---

目次
- プロジェクト概要
- 主な機能
- 必須／推奨環境変数
- セットアップ手順
- 使い方（クイックスタート）
  - DB スキーマ初期化
  - 日次 ETL の実行
  - ニュース収集ジョブの実行
  - 監査ログテーブルの初期化
- ディレクトリ構成（主要ファイル説明）
- 注意点 / 設計上のポイント

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買システムのためのデータ基盤・ヘルパー群です。  
J-Quants API など外部データソースからのデータ取得、DuckDB によるデータ保存、ETL パイプライン、データ品質チェック、RSS によるニュース収集、監査ログなどを提供します。各コンポーネントは冪等性（ON CONFLICT）、レート制御、リトライ、SSRF 対策など実運用を意識した設計になっています。

---

## 主な機能

- J-Quants API クライアント
  - 日次株価（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得
  - レート制御（120 req/min）、リトライ、トークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を防止
- DuckDB スキーマ定義 / 初期化
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - インデックス定義、冪等的な CREATE TABLE
- ETL パイプライン
  - 差分取得（最終取得日から差分のみ）、バックフィル（デフォルト 3 日）対応
  - 市場カレンダー先読み（デフォルト 90 日）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集
  - RSS フィードから記事取得、前処理、URL 正規化、トラッキングパラメータ除去
  - SSRF 対策・gzip サイズチェック・XML 安全パース（defusedxml）
  - DuckDB への冪等保存（INSERT ... RETURNING）
  - 記事中の銘柄（4 桁）抽出と紐付け
- 監査ログ（audit）
  - シグナル → 発注リクエスト → 約定 のトレーサビリティ用テーブル群
  - order_request_id を冪等キーとして二重発注を防止

---

## 必須／推奨環境変数

自動読み込み: プロジェクトルート（.git または pyproject.toml があるディレクトリ）にある `.env` / `.env.local` を自動で読み込みます。無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API のパスワード（発注等で使用）
- SLACK_BOT_TOKEN — Slack 通知用 bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用など）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

注意: Settings 部分は環境変数未設定時に ValueError を投げるため、必須変数は事前にセットしてください。

---

## セットアップ手順

前提: Python >= 3.10（PEP 604 の union 型記法（X | Y）を使用しているため）

1. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール（例）
   - pip install duckdb defusedxml

   （プロジェクト化している場合は、setup / pyproject に応じて pip install -e . 等を利用してください）

3. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、必要な環境変数を OS に設定してください（上記参照）。
   - .env の自動読み込みは、`src/kabusys/config.py` によって行われます。
     - 読み込み順序: OS 環境変数 > .env.local > .env
     - テスト等で自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. DuckDB スキーマ初期化（後述の例参照）

---

## 使い方（クイックスタート）

下に示す例は Python スクリプトや REPL で実行できます。

1) DB スキーマ初期化（DuckDB）
```python
from kabusys.data import schema

# デフォルト: data/kabusys.duckdb を使用したい場合
conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ
# conn = schema.init_schema(":memory:")
```

2) 日次 ETL（株価 / 財務 / カレンダーの差分取得と品質チェック）
```python
from kabusys.data import pipeline
from kabusys.data import schema
from datetime import date

# DB 初期化（既に行っていれば get_connection でも可）
conn = schema.init_schema("data/kabusys.duckdb")

# 日次 ETL 実行（target_date を指定しない場合は今日）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

- run_daily_etl は内部で:
  - 市場カレンダーを先読み（デフォルト 90 日先）
  - 株価の差分取得（最終取得から backfill_days 前まで再取得、デフォルト 3 日）
  - 財務データの差分取得
  - 品質チェック（run_quality_checks=True がデフォルト）

3) ニュース収集（RSS）
```python
from kabusys.data import news_collector
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")

# 単一フィード取得
articles = news_collector.fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
new_ids = news_collector.save_raw_news(conn, articles)
print("新規挿入記事数:", len(new_ids))

# 全ソース一括実行（default sources を使用）
results = news_collector.run_news_collection(conn, known_codes={"7203","6758", ...})
print(results)
```

4) 監査ログテーブル初期化
```python
from kabusys.data import audit
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
audit.init_audit_schema(conn)  # 既存接続に監査関連テーブルを追加する
# あるいは専用 DB を作る:
# audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

## ディレクトリ構成（主要ファイル）

（ルートは src/kabusys 以下を中心に示します）

- src/kabusys/
  - __init__.py                           — パッケージ初期化（version 等）
  - config.py                             — 環境変数/設定管理（.env 自動ロード、Settings）
  - data/
    - __init__.py
    - jquants_client.py                    — J-Quants API クライアント（取得 / 保存）
    - news_collector.py                    — RSS ニュース収集・前処理・保存ロジック
    - schema.py                            — DuckDB スキーマ定義と初期化関数
    - pipeline.py                          — ETL パイプライン（日次処理・差分更新）
    - calendar_management.py               — マーケットカレンダー判定・更新ジョブ
    - audit.py                             — 監査ログ（signal / order_request / executions）
    - quality.py                           — データ品質チェック
  - strategy/
    - __init__.py                          — 戦略層（将来的な戦略コード用）
  - execution/
    - __init__.py                          — 発注 / execution 層インターフェース
  - monitoring/
    - __init__.py                          — 監視用（未実装のプレースホルダ）
- pyproject.toml / setup.cfg (プロジェクトに応じて配置)

各ファイルの主要機能:
- jquants_client:
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_* 系で DuckDB に冪等保存
  - レートリミッタ / HTTP リトライ / トークン自動更新
- news_collector:
  - fetch_rss: SSRF 対策・gzip 上限・defusedxml を用いた安全なパース
  - save_raw_news / save_news_symbols: チャンク INSERT と RETURNING を用いた保存
  - extract_stock_codes: テキスト中の 4 桁銘柄コード抽出
- schema:
  - init_schema(db_path) で全テーブルとインデックスを作成
- pipeline:
  - run_daily_etl で一連の ETL と品質チェックを実行
- quality:
  - 欠損 / スパイク / 重複 / 日付不整合のチェック群を提供

---

## 注意点 / 設計上のポイント

- Python バージョン: 本コードは少なくとも Python 3.10 を想定しています（`X | Y` 型注釈を使用）。
- 環境変数管理:
  - .env の自動ロードはプロジェクトルートを基準に行われます。CWD に依存しません。
  - テスト時など自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DB 操作:
  - DuckDB を使った設計で、各 save_* 関数は冪等に設計されています（ON CONFLICT）。
  - 大きなバルク INSERT の際はチャンク分割（デフォルト 1000）で SQL / メモリ上限を回避しています。
- ネットワーク安全性:
  - ニュース収集では SSRF 対策（リダイレクト先のスキーム・プライベート IP 検査）、受信サイズ上限（10 MB）、gzip 解凍後のサイズチェックを実施しています。
- ETL の堅牢性:
  - 各ステップは独立して例外処理され、1 ステップ失敗でも他は継続します。結果は ETLResult に格納され、品質問題は詳細とともに返却されます。
- 監査ログ:
  - 監査テーブル群は UTC タイムゾーン保存を前提とし、order_request_id によって冪等性を担保します。

---

この README はコードベース（src/kabusys）を基にした概要と利用方法の要約です。各モジュールの詳細な関数仕様・引数・戻り値は該当ファイル内のドキュメンテーション（docstring）を参照してください。必要があれば、実行サンプルや CI 向けのセットアップ（requirements.txt / pyproject.toml の整備）も追記できます。