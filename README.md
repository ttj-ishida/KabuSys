# KabuSys

日本株向けの自動売買 / データプラットフォーム基盤ライブラリです。  
J‑Quants API から市場データを取得して DuckDB に格納・管理し、品質チェックや監査ログを提供します。戦略・発注・監視モジュールと連携して売買システムの基盤を構築することを目的としています。

---

## 主な特徴

- J‑Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得
  - API レート制限（120 req/min）に合わせたスロットリング
  - 401 時の自動トークンリフレッシュ、指数バックオフによるリトライ（最大 3 回）
  - 取得時刻（fetched_at）を UTC で記録して Look‑ahead Bias を抑制
  - ページネーション対応
- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution 層を含むスキーマの DDL を定義
  - インデックスや外部キーを考慮した初期化関数
- ETL パイプライン
  - 差分更新（最終取得日からのバックフィル）による効率的な更新
  - 市場カレンダー先読み（デフォルト 90 日）で営業日調整
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - 各ステップは独立して例外処理され、結果集約（ETLResult）
- 監査ログ（Audit）
  - シグナル → 発注 → 約定のトレーサビリティを UUID 階層で記録
  - 発注冪等キー、ステータス管理、UTC タイムスタンプ保存
- データ品質検査モジュール
  - 欠損データ、前日比スパイク、主キー重複、将来日付 / 非営業日データ検出

---

## 必要条件

- Python 3.10 以上（PEP 604 の型記法などを使用）
- duckdb Python パッケージ
- ネットワーク接続（J‑Quants API へアクセスする場合）
- J‑Quants のリフレッシュトークン等、必要な環境変数（下記参照）

必要な Python パッケージのインストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb
```

（プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）

---

## 環境変数 / .env

パッケージはプロジェクトルートの `.env` / `.env.local` を自動読み込みします（OS 環境変数が優先）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主に利用する環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=./data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン / ソースを入手
2. 仮想環境を作成して有効化
3. 依存ライブラリをインストール（最低限 duckdb）
4. プロジェクトルートに `.env` を作成して必要な環境変数を設定
5. DuckDB スキーマを初期化する

スニペット:
```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install duckdb
# .env を作成する（.env.example を参考に）
```

---

## 使い方（基本例）

以下は最小限の ETL 実行例です。J‑Quants トークン等が `.env` に設定されている前提です。

Python スクリプト例:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

# DuckDB を初期化（ファイルが無ければ作成・DDL 実行）
conn = init_schema(settings.duckdb_path)

# 日次 ETL を実行（target_date を省略すると本日）
result = run_daily_etl(conn)

# 結果を確認
print(result.to_dict())
```

監査ログ用 DB を別途初期化する例:
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db("data/audit.duckdb")
```

重要な公開 API:
- data.jquants_client
  - get_id_token(refresh_token: str | None) -> str
  - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None) -> list[dict]
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records) -> int
  - save_financial_statements(conn, records) -> int
  - save_market_calendar(conn, records) -> int
- data.schema
  - init_schema(db_path) -> duckdb.Connection
  - get_connection(db_path) -> duckdb.Connection
- data.pipeline
  - run_prices_etl(conn, target_date, ...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
  - run_daily_etl(conn, target_date=None, ...)
- data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

ETL の戻り値は data.pipeline.ETLResult で、fetched / saved の件数や品質問題（quality.QualityIssue）・エラーメッセージを含みます。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
      - .env 読み込み、Settings クラス（環境変数アクセス）
    - data/
      - __init__.py
      - jquants_client.py
        - J‑Quants API クライアント（取得・保存ロジック）
      - schema.py
        - DuckDB スキーマ定義 & init_schema / get_connection
      - pipeline.py
        - ETL パイプライン（差分更新、backfill、品質チェック）
      - quality.py
        - データ品質チェック（欠損・スパイク・重複・日付不整合）
      - audit.py
        - 監査ログ（signal_events / order_requests / executions 等）
    - strategy/
      - __init__.py
      - (戦略実装はここに実装)
    - execution/
      - __init__.py
      - (発注ロジック・ブローカ連携)
    - monitoring/
      - __init__.py
      - (運用監視・メトリクス周り)

---

## 設計上の注意点 / 運用メモ

- J‑Quants API のレート制限（120 req/min）を厳守するため、内部で固定間隔スロットリングを実装しています。大量の同時リクエストは避けてください。
- HTTP エラー時は指数バックオフでリトライします。401 は一度トークンをリフレッシュして再試行します。
- DuckDB の INSERT は ON CONFLICT DO UPDATE による冪等化を行っています。ETL は差分更新かつバックフィル（既存データの数日前から再取得）を推奨します。
- すべてのタイムスタンプは UTC を使用する設計になっています（監査 DB では明示的に SET TimeZone='UTC' を実行）。
- 自動 .env ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

---

## 今後の拡張案（参考）

- strategy / execution / monitoring の具象実装（戦略モデル、ポートフォリオ最適化、ブローカ API 実装）
- Slack 通知やメトリクスエクスポート（Prometheus など）
- バックアップ / マイグレーションツール
- 単体テスト・統合テスト用のテストヘルパー（モック J‑Quants サーバ等）

---

もし README に追記したいサンプル（戦略の骨子、デプロイ手順、CI 設定など）があれば、目的に応じてテンプレートを作成します。必要な内容を教えてください。