# KabuSys

日本株向け自動売買／データプラットフォーム用ライブラリ（初期バージョン）
バージョン: 0.1.0

概要: J-Quants / kabuステーション 等の外部データ・ブローカー API と連携し、データ収集・保存（DuckDB）・スキーマ管理・監査ログ・データ品質チェックを提供するモジュール群です。戦略層・発注層は別モジュールで実装できます（strategy/、execution/、monitoring/ のための基盤を提供）。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得とバリデーション（env / log level）
- J-Quants API クライアント（data/jquants_client.py）
  - 日足（OHLCV）、財務データ（四半期）、マーケットカレンダーの取得
  - レート制限（120 req/min）を守る固定間隔スロットリング
  - リトライ（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ
  - ページネーション対応、取得時刻（fetched_at）を UTC で記録
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）
- DuckDB スキーマ管理（data/schema.py）
  - Raw / Processed / Feature / Execution の 3 層（＋監査層）のテーブル定義
  - init_schema(db_path) で初期化（冪等）、get_connection で接続取得
- 監査ログ（data/audit.py）
  - シグナル→発注→約定のトレーサビリティテーブル（UUID 連鎖）
  - init_audit_schema(conn) / init_audit_db(db_path)
- データ品質チェック（data/quality.py）
  - 欠損データ、前日比スパイク、重複（PK）、日付不整合（未来日付／非営業日）をチェック
  - run_all_checks(conn, ...) で一括実行し、QualityIssue オブジェクトのリストを返す

---

## セットアップ（開発用）

前提
- Python 3.10+（typing の | 型などを利用）
- duckdb 等の依存パッケージ（プロジェクトの requirements.txt を用意している場合はそちらを参照）

例:
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb
   - （プロジェクト配布時は）pip install -e . あるいは pip install -r requirements.txt

3. 環境変数（.env）を用意
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）から
     `.env` と `.env.local` が自動読み込みされます（OS環境変数が優先）。
   - 自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

必須（例）
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...

任意（デフォルトあり）
- KABUSYS_ENV=development|paper_trading|live  (default: development)
- LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL   (default: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1  # 自動 .env 読み込みを無効にする

DB パス（デフォルト）
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db

例 - 最小の .env（プロジェクトルートに配置）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（基本）

以下は主要なユースケースのサンプルコード例。

1) DuckDB スキーマ初期化:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) J-Quants から日足を取得して保存:
```python
from kabusys.data import jquants_client
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
records = jquants_client.fetch_daily_quotes(code="7203")  # 銘柄コード例
inserted = jquants_client.save_daily_quotes(conn, records)
print(f"saved {inserted} rows")
```

3) 財務データ・マーケットカレンダーの取得と保存:
```python
fs = jquants_client.fetch_financial_statements(code="7203")
jquants_client.save_financial_statements(conn, fs)

mc = jquants_client.fetch_market_calendar()
jquants_client.save_market_calendar(conn, mc)
```

4) 監査ログスキーマの初期化（既存 conn に追加）:
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)  # conn は init_schema で作成したものを想定
```

5) データ品質チェックの実行:
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

6) 設定を取得する（環境変数経由）:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.kabu_api_base_url)  # デフォルトは http://localhost:18080/kabusapi
print(settings.is_live)
```

注意点:
- J-Quants の認証はリフレッシュトークン経由で ID トークンを取得します。get_id_token() は自動リフレッシュを内部で行います。
- API リクエストは内部でレート制御・リトライを行いますが、大量取得時は実行時間に注意してください。
- DuckDB の保存関数は冪等性（ON CONFLICT DO UPDATE）を備えています。

---

## ディレクトリ構成

プロジェクト内の主要ファイル（抜粋）:
```
src/
  kabusys/
    __init__.py            # パッケージ初期化、__version__ = "0.1.0"
    config.py              # 環境変数 / 設定管理
    data/
      __init__.py
      jquants_client.py    # J-Quants API クライアント（fetch/save）
      schema.py            # DuckDB スキーマ定義・初期化
      audit.py             # 監査ログ（トレーサビリティ）初期化
      quality.py           # データ品質チェック
    strategy/
      __init__.py          # 戦略用パッケージ（拡張ポイント）
    execution/
      __init__.py          # 発注/実行関連パッケージ（拡張ポイント）
    monitoring/
      __init__.py          # 監視（将来的に拡張）
```

主要な DB テーブル（概要）
- Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer: features, ai_scores
- Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
- Audit: signal_events, order_requests, executions

---

## 実運用上の注意

- KABUSYS_ENV によって挙動（本番 / ペーパートレード / 開発）を切り替えます。live を設定する場合は十分にテストを行ってください。
- 発注・実際のブローカー連携はこのリポジトリ内の execution/ 以下等で実装することを想定しています。本 README にある保存・監査・品質チェックはインフラ／基盤部分です。
- 監査ログは削除しない前提で設計されています（オンプレ・クラウドいずれでも長期保管の方針を検討してください）。
- すべてのタイムスタンプは UTC を利用することが前提です（audit.init_audit_schema は TimeZone='UTC' を設定します）。

---

## 貢献・拡張ポイント

- strategy/ で投資戦略を実装し、signals を生成して signal_queue に流すワークフローの追加
- execution/ で実際のブローカー（kabu API 等）への送信・レスポンス処理の実装
- monitoring/ にモニタリング用機能（Slack 通知、アラート、定期チェック）を追加
- テストと CI（自動 DB 初期化、モック API での E2E テスト）を整備

---

質問や利用の目的に合わせた具体的なサンプルが必要でしたら、どのユースケース（例: 日次 ETL、監査ログの追跡、異常検知の運用など）を想定しているか教えてください。関連するコード例や .env のテンプレート、CI ワークフロー例を用意します。