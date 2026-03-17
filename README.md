# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買インフラ向けデータ基盤と補助機能群を収めた Python パッケージです。J-Quants API や RSS フィードからデータを収集し、DuckDB に冪等的に保存する ETL パイプライン、品質チェック、マーケットカレンダー管理、ニュース収集、監査ログ用スキーマ等を提供します。

主な設計方針: レート制限・リトライ・冪等性・Look-ahead bias 回避・SSRF 対策など運用を意識した堅牢な実装。

---

## 機能一覧

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レートリミット対応（120 req/min）
  - リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - 冪等的なテーブル作成（IF NOT EXISTS）および索引定義
  - 監査ログ（signal_events / order_requests / executions）の追加初期化

- ETL パイプライン
  - 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新（最終取得日からの差分取得）
  - バックフィルで API の後出し修正に対応
  - 品質チェック（欠損・スパイク・重複・日付不整合）

- ニュース収集
  - RSS フィード取得（gzip 対応）、XML の安全パース（defusedxml）
  - URL 正規化、トラッキングパラメータ除去、記事ID は正規化 URL の SHA-256（先頭32文字）
  - SSRF 対策（スキーム・プライベートIP の検査）
  - DuckDB への冪等保存（INSERT ... ON CONFLICT / RETURNING）

- マーケットカレンダー管理
  - 営業日判定、前後営業日計算、期間の営業日リスト取得
  - JPX カレンダー夜間更新ジョブ（差分取得＋バックフィル）

- 監査ログ（トレーサビリティ）
  - 発生したシグナルから発注・約定まで追跡可能なスキーマとインデックス
  - order_request_id を冪等キーとして二重発注防止

- 設定管理
  - .env（プロジェクトルート）自動読み込み（OS 環境変数優先）
  - 必須設定は Settings 経由で取得（未設定時はエラー）

---

## 前提

- Python 3.10 以上（型注釈に | 演算子を利用）
- DuckDB（Python パッケージとして duckdb）
- defusedxml（RSS/XML の安全パース）
- ネットワーク接続（J-Quants API、RSS）

主な依存（最低限）:
- duckdb
- defusedxml

（プロジェクト用に pyproject.toml / requirements.txt を用意している想定）

---

## セットアップ手順

1. 仮想環境作成（任意）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージと依存のインストール:
   - pip install -U pip
   - pip install duckdb defusedxml
   - （開発インストール）プロジェクトのルートで:
     - pip install -e .

3. 環境変数 (.env) の準備:
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（既定で自動ロード有効）。
   - 自動ロードを無効にする場合: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

例: .env（最低限必須のキー）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション API
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack (通知等)
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス (任意)
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

必須の環境変数（コード上で _require() によりチェックされるもの）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション:
- KABUSYS_ENV: development / paper_trading / live（既定: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
- DUCKDB_PATH / SQLITE_PATH

---

## 使い方（例）

ここでは主なユースケースの簡単なコード例を示します。実運用ではログ設定や例外処理を追加してください。

- DuckDB スキーマ初期化
```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリは自動作成）
conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ DB
# conn = schema.init_schema(":memory:")
```

- 日次 ETL 実行
```python
from kabusys.data import pipeline
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
# ETL を実行（target_date を省略すると今日）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

- ニュース収集ジョブ（RSS）
```python
from kabusys.data import news_collector
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# known_codes を与えると記事中の銘柄コード抽出→news_symbols への紐付けを行う
known_codes = {"7203", "6758", "9984"}  # 例
res = news_collector.run_news_collection(conn, known_codes=known_codes)
print(res)  # {'yahoo_finance': 12, ...}
```

- 監査スキーマ初期化（既存接続に追加）
```python
from kabusys.data import audit
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn)
```

- J-Quants の id_token を直接取得する
```python
from kabusys.data.jquants_client import get_id_token

token = get_id_token()  # .env の JQUANTS_REFRESH_TOKEN を利用
print(token)
```

- マーケットカレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data import calendar_management
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print(f"saved: {saved}")
```

---

## 主要 API（モジュール一覧・用途）

- kabusys.config
  - Settings クラス: 環境変数経由の設定管理
  - 自動でプロジェクトルートの .env/.env.local をロード（無効化可）

- kabusys.data.jquants_client
  - get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()
  - save_daily_quotes(), save_financial_statements(), save_market_calendar()
  - レートリミット・リトライ・ページネーション対応

- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)

- kabusys.data.pipeline
  - run_prices_etl(), run_financials_etl(), run_calendar_etl(), run_daily_etl()

- kabusys.data.news_collector
  - fetch_rss(), save_raw_news(), save_news_symbols(), run_news_collection()
  - SSRF 対策、XML 安全パース、記事正規化

- kabusys.data.calendar_management
  - is_trading_day(), next_trading_day(), prev_trading_day(), get_trading_days(), calendar_update_job()

- kabusys.data.quality
  - 各種品質チェック: check_missing_data(), check_spike(), check_duplicates(), check_date_consistency(), run_all_checks()

- kabusys.data.audit
  - 監査ログ用テーブルの初期化: init_audit_schema(), init_audit_db()

- kabusys.strategy, kabusys.execution, kabusys.monitoring
  - パッケージエントリは存在するが実装ファイルは空（戦略・実行・監視ロジックの拡張ポイント）

---

## ディレクトリ構成

以下は主要ファイル/モジュールのツリー（抜粋）:

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
      - quality.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

（README はこのツリーに合わせた説明を含みます。実装の追加・拡張は strategy / execution / monitoring 配下に行ってください。）

---

## 運用上の注意・ヒント

- 環境変数の自動ロードは .git または pyproject.toml が存在するプロジェクトルートを基準に行われます。テストや一時的に自動ロードを停止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のファイルパスは既定で `data/kabusys.duckdb`。スナップショットやバックアップを運用ポリシーに合わせて行ってください。
- J-Quants の API レート制限とリトライ設定は jquants_client 内で制御されていますが、大量の並列リクエストは避けてください。
- news_collector は RSS の XML を外部から取り込むため、defusedxml と SSRF チェックを実装しています。カスタム取得ロジックを追加する場合はこれらの安全措置を踏襲してください。
- run_daily_etl は複数ステップ（カレンダー・株価・財務・品質チェック）を個別に実行し、各ステップは独立してエラーハンドリングします。監査・通知連携は呼び出し側で行ってください。

---

## 貢献・拡張ポイント

- strategy / execution / monitoring モジュールは拡張ポイントです。戦略のシグナル生成、発注実行・再試行ロジック、監視アラートを実装して連携させてください。
- 監査テーブルは既に用意されています。order_request_id を冪等キーとして利用することで二重発注を防止できます。
- テストと CI の整備（モックによる外部 API の切り離し、_urlopen の差し替えなど）を推奨します。

---

README に書かれているサンプルは最小限の利用例です。実運用ではログ設定、例外ハンドリング、シークレット管理（Vault 等）の導入、監視・アラートの整備を行ってください。必要があればこの README の拡張（使い方の詳細、API リファレンス、運用手順）を作成します。