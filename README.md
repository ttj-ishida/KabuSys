# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買・データプラットフォームのコアライブラリです。J‑Quants API や RSS フィード等から市場データ・ニュースを取得し、DuckDB に保存・整形、品質チェックや ETL パイプライン、監査ログ（発注→約定トレーサビリティ）といった機能を提供します。

主な設計方針:
- 取得データのトレーサビリティ（fetched_at / UTC タイムスタンプ）
- 冪等性（INSERT ... ON CONFLICT / RETURNING を活用）
- API レート制御とリトライ（J‑Quants クライアント）
- セキュリティ配慮（news_collector の SSRF 防御・XML 防御・サイズ制限）
- DuckDB をコアにした軽量オンプレ／ローカルデータ基盤

---

## 機能一覧

- 環境設定読み込み
  - .env / .env.local / OS 環境変数から設定を読み込み（自動ロード、無効化可）
  - 必須設定の取得とバリデーション（Settings クラス）
- J‑Quants API クライアント（data/jquants_client.py）
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX カレンダーの取得
  - レート制限（120 req/min）とリトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存ユーティリティ（save_*）
- ニュース収集（data/news_collector.py）
  - RSS フィード取得 → テキスト前処理 → raw_news へ冪等保存
  - URL 正規化、トラッキングパラメータ除去、記事ID は SHA‑256（先頭32文字）
  - SSRF 対策、XML インジェクション対策（defusedxml）、受信サイズ制限
  - 銘柄コード抽出と news_symbols への紐付け
- データスキーマ管理（data/schema.py）
  - Raw / Processed / Feature / Execution 層の DuckDB DDL を定義
  - init_schema() による初期化（冪等）
- ETL パイプライン（data/pipeline.py）
  - 差分取得、バックフィル、品質チェックを組み合わせた日次 ETL（run_daily_etl）
  - 個別ジョブ: run_prices_etl / run_financials_etl / run_calendar_etl
- カレンダー管理（data/calendar_management.py）
  - カレンダー更新バッチ、営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
  - DB がない場合の曜日ベースフォールバック
- 監査ログ（data/audit.py）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化
  - すべての TIMESTAMP を UTC に固定する処理を実行
- 品質チェック（data/quality.py）
  - 欠損・重複・スパイク（前日比閾値）・日付不整合（未来日・非営業日）検出
  - QualityIssue を集約して呼び出し元に返す
- パッケージ構成（strategy / execution / monitoring などのプレースホルダ）

---

## 動作要件（推奨）

- Python 3.10 以上（型ヒントに | 演算子を使用）
- 依存ライブラリ（最低限）
  - duckdb
  - defusedxml

pip でインストールする場合の例:
```
pip install duckdb defusedxml
```

プロジェクト自体は src 配置のパッケージとして提供されることを想定しています（pip install -e . 等で開発インストール可能）。

---

## セットアップ手順

1. リポジトリをチェックアウト / クローン
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv && source .venv/bin/activate など
3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合）pip install duckdb defusedxml
4. 環境変数を用意
   - プロジェクトルートに .env を置くと自動で読み込まれます（.env.local は上書き）
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
5. 必須環境変数（実行に必要）
   - JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabu ステーション API パスワード
   - SLACK_BOT_TOKEN: Slack 通知に使う Bot トークン
   - SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID
6. オプション設定
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/...
   - KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB の DB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）

注意: .env.example を参考に .env を作成してください（プロジェクトルートに .git または pyproject.toml がある場所を基準に自動ロードします）。

---

## 使い方（基本例）

以下は Python REPL やスクリプトから呼び出す簡単な例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行する（J‑Quants トークンは Settings から自動取得）
```python
from kabusys.data import pipeline
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

3) ニュース収集を実行する
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄コードセット（例: {"7203", "6758", ...}）を渡すと銘柄紐付けを行う
res = run_news_collection(conn, known_codes={"7203", "6758"})
print(res)  # {source_name: 新規保存記事数, ...}
```

4) 監査ログテーブル初期化（別 DB にする場合）
```python
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/audit.duckdb")
# 既存 conn に追加する場合:
# audit.init_audit_schema(conn)
```

5) カレンダー更新バッチ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"saved {saved} records")
```

6) 簡易スクリプト例（run_etl.py）
```python
from kabusys.config import settings
from kabusys.data import schema, pipeline

conn = schema.init_schema(settings.duckdb_path)
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

---

## よく使う API/関数（抜粋）

- kabusys.config.settings
  - .jquants_refresh_token / .kabu_api_password / .slack_bot_token / .slack_channel_id など
- kabusys.data.schema
  - init_schema(db_path) / get_connection(db_path)
- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
  - save_daily_quotes(conn, records), save_financial_statements(...), save_market_calendar(...)
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl, run_financials_etl, run_calendar_etl
- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - run_news_collection(conn, sources=None, known_codes=None)

---

## ディレクトリ構成

プロジェクトの主要ファイル・ディレクトリ構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数読み込み・Settings
  - data/
    - __init__.py
    - jquants_client.py      # J‑Quants API クライアント + DuckDB 保存
    - news_collector.py      # RSS 取得・前処理・保存・銘柄抽出
    - schema.py              # DuckDB スキーマ定義・初期化
    - pipeline.py            # ETL パイプライン（差分更新・品質チェック統合）
    - calendar_management.py # 市場カレンダー管理・営業日判定
    - audit.py               # 監査ログ（signal/order/execution）のDDL・初期化
    - quality.py             # データ品質チェック
  - strategy/                 # 戦略モジュール（プレースホルダ）
    - __init__.py
  - execution/                # 発注実装（プレースホルダ）
    - __init__.py
  - monitoring/               # 監視・メトリクス（プレースホルダ）
    - __init__.py

---

## 運用上の注意・設計上のポイント

- J‑Quants API 呼び出しはレート制限（120 req/min）を遵守するため内部でスロットリングを行います。大量の並列リクエストは避けてください。
- ニュース収集では外部コンテンツの扱いに注意しています（defusedxml、SSRF 検査、受信バイト制限）。RSS ソースは信頼できるものを選んでください。
- DuckDB のファイルはデフォルトで data/kabusys.duckdb に作られます。バックアップ・ローテーションは運用で用意してください。
- 設定は .env / .env.local / OS 環境変数で管理します。機密情報（API トークン等）は git に含めないでください。
- audit テーブルは UTC タイムゾーン固定で初期化します。アプリケーションはタイムゾーンの扱いに注意してください。

---

## 開発・拡張

- strategy/ と execution/ は拡張ポイントです。戦略は信号（signals / signal_queue）を生成し、execution 層が発注ロジック（証券会社 API）を実装します。
- ETL・品質チェック・監査の出力はログに詳細を出すため、運用時は LOG_LEVEL を適切に設定してください。
- テストでは settings の自動 .env ロードを無効化するために環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用できます。

---

README に記載のない詳細（API エンドポイントのパラメータ仕様やデータ辞書など）は、プロジェクト内の DataPlatform.md / API ドキュメントに従ってください。

ご要望があれば、README に実際の例スクリプト（systemd ユニット・Cron・Dockerfile 等）のテンプレートや、CI / テスト実行手順を追加できます。どの情報が欲しいか教えてください。