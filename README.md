# KabuSys

日本株向けの自動売買プラットフォームのコア部分（データ取得・ETL・スキーマ・品質チェック・監査ログ）を含む軽量ライブラリです。  
このリポジトリは J-Quants API から市場データを取得して DuckDB に保存し、品質チェックや監査トレーサビリティを提供します。戦略・発注・監視モジュールの雛形も含まれます。

---

## 主な特徴（Features）

- J-Quants API クライアント
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）遵守（固定間隔スロットリング）
  - 再試行（指数バックオフ、最大3回）、401 時は自動トークンリフレッシュ
  - ページネーション対応・フェッチ時刻（fetched_at）の記録で Look-ahead バイアス対策
  - DuckDB へ冪等的に保存（ON CONFLICT DO UPDATE）
- DuckDB ベースのスキーマ定義
  - Raw / Processed / Feature / Execution の多層スキーマ
  - インデックス・外部キーを考慮した初期化関数
- ETL パイプライン
  - 差分更新（最終取得日からの差分取得 + バックフィル）
  - 市場カレンダーの先読み（lookahead）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - エラーや品質問題は収集して呼び出し元に返却
- 監査ログ（audit）
  - シグナル→発注→約定まで UUID 連鎖で完全トレース
  - 発注冪等キー（order_request_id）、タイムスタンプは UTC
- 設定管理
  - .env / .env.local / OS 環境変数から自動ロード（自動ロードは無効化可能）

---

## 必要条件

- Python 3.10+
- duckdb
- （J-Quants API を利用するためにネットワーク接続と有効な API トークンが必要）

インストール例（最低限）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb
# パッケージを開発インストールする場合（pyproject.toml がある前提）
pip install -e .
```

プロジェクトに依存関係を追加している場合は、requirements.txt / pyproject.toml に従ってインストールしてください。

---

## 環境変数 / 設定

自動でプロジェクトルート（.git または pyproject.toml を基準）を探し、`.env` → `.env.local` の順で読み込みます。OS 環境変数が優先され、`.env.local` は `.env` を上書きします。

自動ロードを無効にするには:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

主に利用される環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネルID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"

簡単な .env.example:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成して依存をインストールします。
2. プロジェクトルートに `.env`（または `.env.local`）を作成し、上記の必須環境変数を設定します。
3. DuckDB スキーマを初期化します（以下の使用例参照）。

---

## 使い方（例）

以下は基本的な起動 / ETL 実行の例です。

1) DuckDB スキーマの初期化と接続取得
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数に基づくデフォルトパス
conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL を実行（市場カレンダー・株価・財務取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # 引数を指定せずに実行すると本日分が対象
print(result.to_dict())
if result.has_errors:
    print("ETL 中にエラーが発生しました:", result.errors)
if result.has_quality_errors:
    print("品質チェックで重大な問題が検出されました")
```

3) 監査ログ用スキーマを追加する（既存の conn を利用）
```python
from kabusys.data.audit import init_audit_schema

# init_schema() で作成した conn に対して監査テーブルを追加
init_audit_schema(conn)
```

4) 直接トークンをリフレッシュする（テスト等）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使って取得
```

注意点:
- run_daily_etl は各ステップを個別に例外ハンドリングします。エラーがあっても可能な処理は継続して行い、最終的な ETLResult に結果がまとめられます。
- J-Quants API のレート制限（120 req/min）を厳守する設計になっています。大量一括処理を行う場合は時間的な余裕を確保してください。

---

## API / 主要モジュール概要

- kabusys.config
  - 環境変数の自動読み込み・バリデーション（settings オブジェクト）
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token（リフレッシュトークンから取得）
  - レート制限・リトライ・ページネーション・fetched_at 記録などを実装
- kabusys.data.schema
  - DuckDB のテーブル定義（Raw/Processed/Feature/Execution）
  - init_schema(db_path) / get_connection(db_path)
- kabusys.data.pipeline
  - 差分更新ロジック、run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl
  - 品質チェックの統合
- kabusys.data.quality
  - check_missing_data / check_duplicates / check_spike / check_date_consistency / run_all_checks
  - QualityIssue データクラス
- kabusys.data.audit
  - 監査ログ用テーブルの定義・初期化（init_audit_schema / init_audit_db）
- kabusys.strategy, kabusys.execution, kabusys.monitoring
  - パッケージ雛形（実装は用途に応じて拡張）

---

## ディレクトリ構成

以下は主要ファイルを抜粋した構成です（実際のツリーはさらに細分化されている可能性があります）。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - schema.py
      - pipeline.py
      - audit.py
      - quality.py
    - strategy/
      - __init__.py
      - (戦略用モジュールを配置)
    - execution/
      - __init__.py
      - (発注/ブローカー連携モジュールを配置)
    - monitoring/
      - __init__.py
      - (監視・アラート関連を配置)

主要テーブル（schema.py に定義）
- Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer: features, ai_scores
- Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
- Audit（監査）: signal_events, order_requests, executions

---

## 運用上の注意

- 本ライブラリは J-Quants の API 利用規約・レート制限を守る設計になっていますが、運用環境に合わせた追加のレート制御やスロットリングの調整が必要になる場合があります。
- DuckDB ファイルは単一ファイルとして管理されます。バックアップや排他アクセス（複数プロセスから同時書き込みする場合）の方針を事前に策定してください。
- 環境変数に機密情報（API トークン等）を置く際は適切なアクセス制御を行ってください。
- KABUSYS_ENV を "live" に設定すると実運用モードとなる想定です。実運用前に十分なテスト（paper_trading / development）を行ってください。

---

この README はコードベースの現状実装に基づく概要と利用手順をまとめたものです。戦略ロジックやブローカー連携、監視・通知部分は用途に応じて拡張してください。必要であれば、サンプルワークフローや運用手順のテンプレートも作成できます。必要があれば教えてください。