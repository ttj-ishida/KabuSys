# KabuSys

KabuSys は日本株の自動売買・データ基盤向けライブラリ群です。  
J-Quants API から市場データを取得して DuckDB に格納する ETL パイプライン、データ品質チェック、監査ログ（シグナル→発注→約定のトレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 主な特徴

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得
  - レート制御（120 req/min）・リトライ（指数バックオフ）・401 時のトークン自動リフレッシュ対応
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を抑制

- データ基盤（DuckDB）スキーマ
  - Raw / Processed / Feature / Execution の多層スキーマ定義
  - 冪等性を考慮した保存（ON CONFLICT DO UPDATE）
  - 実行履歴・監査用テーブル群（signal_events, order_requests, executions）

- ETL パイプライン
  - 差分取得（最終取得日からの再取得、backfill をサポート）
  - カレンダーの先読み（lookahead）により営業日調整を実施
  - 品質チェック（欠損、スパイク、重複、日付不整合）を実行して問題を収集

- データ品質チェックモジュール
  - 欠損データ、価格スパイク（前日比閾値）、重複、将来日付や非営業日データの検出
  - 問題は QualityIssue として集約（重大度に応じて呼び出し元で対応）

- 監査・トレーサビリティ
  - シグナルから約定まで UUID を連鎖して完全にトレース可能
  - 発注要求は冪等キー（order_request_id）を持ち多重送信を防止

---

## 機能一覧（モジュール）

- kabusys.config
  - .env / 環境変数の自動読み込み（プロジェクトルートを基準）
  - 必須設定のラッパー（settings オブジェクト）

- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar

- kabusys.data.schema
  - DuckDB スキーマ定義と初期化（init_schema, get_connection）

- kabusys.data.pipeline
  - run_prices_etl, run_financials_etl, run_calendar_etl
  - run_daily_etl（フル日次 ETL 実行。品質チェックオプションあり）

- kabusys.data.quality
  - 欠損・スパイク・重複・日付不整合チェック（run_all_checks）

- kabusys.data.audit
  - 監査ログ用テーブルの初期化（init_audit_schema / init_audit_db）

- kabusys.strategy / kabusys.execution / kabusys.monitoring
  - （パッケージプレースホルダ。戦略、実行、監視ロジックを実装する想定）

---

## 必要条件

- Python 3.10 以上（型ヒントで PEP 604 の Union 型（|）を使用）
- 依存パッケージ（最低限）:
  - duckdb
- ネットワークアクセス（J-Quants API、kabu API 等）

（実際の依存はプロジェクトの pyproject.toml / requirements.txt に従ってください）

---

## 環境変数 / 設定

自動的に .env および .env.local（存在する場合）から読み込みます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。プロジェクトルートは `.git` または `pyproject.toml` を基準に決定します。

主な環境変数:

- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD     : kabu ステーション API パスワード
  - SLACK_BOT_TOKEN       : Slack ボットトークン
  - SLACK_CHANNEL_ID      : 通知先 Slack チャンネル ID

- 任意（デフォルト値あり）
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロード無効化
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - KABUS_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）

なお、settings オブジェクト経由でこれらにアクセスできます（例: from kabusys.config import settings）。

---

## セットアップ手順（例）

1. リポジトリをクローンしてプロジェクトルートへ移動

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb
   - （必要に応じてプロジェクトの requirements.txt / pyproject.toml を使用）

4. .env を作成
   - .env.example（存在する場合）を参考に .env を作成し、必須環境変数を設定
   - .env.local があれば上書き読み込みされます（OS 環境変数は保護される）

5. DuckDB スキーマ初期化（例）
   - 下記の「使い方」参照

---

## 使い方（簡単なコード例）

以下は最小の使用例です。Python スクリプトや REPL で実行できます。

- DuckDB スキーマ初期化

```python
from kabusys.data import schema
from kabusys.config import settings

# settings.duckdb_path は .env に応じたパス（デフォルト: data/kabusys.duckdb）
conn = schema.init_schema(settings.duckdb_path)
```

- 日次 ETL を実行する（フルパイプライン: カレンダー→株価→財務→品質チェック）

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)  # 既存 DB 接続（初回は init_schema 推奨）
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- J-Quants から直接データを取得して保存する（テスト的に）

```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)

# トークンは settings.jquants_refresh_token より取得されます
records = jq.fetch_daily_quotes(code="7203")  # 例: トヨタ(7203)
saved = jq.save_daily_quotes(conn, records)
print(f"saved: {saved}")
```

- 品質チェックのみ実行する

```python
from kabusys.data import quality
from kabusys.data import schema
from kabusys.config import settings
from datetime import date

conn = schema.get_connection(settings.duckdb_path)
issues = quality.run_all_checks(conn, target_date=date.today(), reference_date=date.today())
for i in issues:
    print(i)
```

注意:
- ETL のバックフィル日数やカレンダー先読みは run_daily_etl の引数で調整できます（backfill_days, calendar_lookahead_days）。
- ログレベルは環境変数 LOG_LEVEL で制御してください。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（settings）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント + DuckDB 保存機能
    - schema.py              — DuckDB スキーマ定義 & 初期化
    - pipeline.py            — ETL（差分取得、保存、品質チェック）
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログ（signal/order/execution）定義
  - strategy/
    - __init__.py            — 戦略レイヤ（実装例を追加）
  - execution/
    - __init__.py            — 発注・ブローカー連携（実装例を追加）
  - monitoring/
    - __init__.py            — 監視・アラート連携（実装例を追加）

---

## 運用上の注意

- API レート制限を遵守するため、jquants_client は内部でスロットリングとリトライを行います。直接大量並列リクエストを作らないよう注意してください。
- DuckDB のファイルパスは settings.duckdb_path で制御できます。運用環境では適切な永続ストレージを使用してください。
- 監査ログは削除しない前提で設計されています。削除操作は慎重に行ってください。
- 環境変数は .env / .env.local で管理できますが、機密情報（トークン・パスワード）は安全に保管してください。

---

## 貢献・拡張

- strategy / execution / monitoring モジュールは拡張を想定しています。具体的な戦略実装、証券会社 API 連携、監視アラートの実装を追加してください。
- 新しいデータソースやチェックを追加する場合は、DuckDB スキーマの拡張と品質チェックの追加を行ってください。

---

README に含める情報の追加や、サンプルスクリプト（cron 用や CI 用）を用意する必要があれば教えてください。README をプロジェクトの実際の依存情報（pyproject.toml / requirements.txt）に合わせて調整できます。