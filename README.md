# KabuSys

バージョン: 0.1.0

日本株向けの自動売買プラットフォームのコアライブラリ（モジュール群）です。データ取得、DuckDB スキーマ定義、監査ログ、環境設定など、自動売買システムのバックエンド基盤を提供します。

---

## 概要

KabuSys は以下を目的としたライブラリ群です。

- J-Quants API からの市場データ（株価・財務・マーケットカレンダー）取得
- 取得データの DuckDB への永続化（Raw / Processed / Feature / Execution 層）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）用テーブル定義
- 環境変数による設定管理（.env の自動ロード機構）
- レート制御、リトライ、トークン自動リフレッシュなど API 呼び出しの堅牢化

設計上のポイント：
- J-Quants API 呼び出しは 120 req/min（固定間隔スロットリング）を尊重
- 401 受信時にリフレッシュトークンを用いた自動再取得を行い、ページネーション間でトークンを共有
- 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を低減
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で重複を排除

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）
  - 必須設定の取得とバリデーション

- データ取得（J-Quants）
  - 株価日足（OHLCV）: fetch_daily_quotes
  - 財務データ（四半期 BS/PL）: fetch_financial_statements
  - JPX マーケットカレンダー: fetch_market_calendar
  - 認証トークン取得: get_id_token
  - レート制限、リトライ、401 の自動リフレッシュ対応

- データ永続化（DuckDB）
  - スキーマ初期化: init_schema(db_path)
  - raw_prices / raw_financials / market_calendar 等のテーブル定義
  - save_* 関数: save_daily_quotes, save_financial_statements, save_market_calendar（冪等保存）

- 監査ログ（Audit）
  - signal_events / order_requests / executions のテーブル定義
  - init_audit_schema(conn) / init_audit_db(db_path)

- その他
  - 実行層・戦略層・モニタリング用のパッケージプレースホルダ（kabusys.execution, kabusys.strategy, kabusys.monitoring）

---

## 前提条件 / 依存

- Python 3.10 以上（PEP 604 の型記法などを使用）
- duckdb
- 標準ライブラリ（urllib, json, logging 等）

pip でのインストール例（プロジェクトルートで）:
```bash
pip install duckdb
# 開発インストール（setup があれば）
# pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン / ソース配置
2. Python 仮想環境を作成・有効化し、依存（duckdb 等）をインストール
3. プロジェクトルートに .env を作成（自動読み込みされます）

推奨される .env の例:
```env
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabuステーション API
KABU_API_PASSWORD=your_kabu_password_here
# KABU_API_BASE_URL は省略可（デフォルト: http://localhost:18080/kabusapi）

# Slack（通知等で使用）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# システム環境（development|paper_trading|live）
KABUSYS_ENV=development

# ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
LOG_LEVEL=INFO
```

自動で .env をロードしたくない場合は環境変数を設定して無効化できます:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 使い方（例）

以下は主要なユースケースの簡単なサンプルです。

- DuckDB スキーマ初期化:
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ
# conn = schema.init_schema(":memory:")
```

- 監査ログスキーマ初期化（既存接続へ追加）:
```python
from kabusys.data import audit
audit.init_audit_schema(conn)
# あるいは専用 DB を初期化
# audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

- J-Quants から日足を取得して DuckDB に保存:
```python
from kabusys.data import jquants_client
from kabusys.data import schema
import duckdb

# DB 初期化済みの conn を用意
conn = schema.get_connection("data/kabusys.duckdb")

# 全銘柄または特定銘柄コードを指定
records = jquants_client.fetch_daily_quotes(code="7203")  # トヨタ(例)
saved = jquants_client.save_daily_quotes(conn, records)
print(f"保存件数: {saved}")
```

- ID トークンを直接取得する:
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token が使われる
```

注意点:
- fetch_* 系はページネーションに対応しています。
- 内部で固定間隔のレート制御（120 req/min）を行います。高速連続呼び出しは避けてください。
- 401 応答を受けると自動的にリフレッシュトークンで id_token を更新してリトライします（1 回のみ）。
- save_* 関数は ON CONFLICT DO UPDATE を使い冪等的にデータを書き込みます。
- すべてのタイムスタンプは UTC を使用することを前提としています（監査ログ初期化時に SET TimeZone='UTC' を実行）。

---

## 環境設定（settings）

kabusys.config.Settings 経由でアプリ設定を参照できます:
- jquants_refresh_token: JQUANTS_REFRESH_TOKEN（必須）
- kabu_api_password: KABU_API_PASSWORD（必須）
- kabu_api_base_url: KABU_API_BASE_URL（省略時: http://localhost:18080/kabusapi）
- slack_bot_token: SLACK_BOT_TOKEN（必須）
- slack_channel_id: SLACK_CHANNEL_ID（必須）
- duckdb_path: DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- sqlite_path: SQLITE_PATH（デフォルト: data/monitoring.db）
- env: KABUSYS_ENV（development, paper_trading, live のいずれか）
- log_level: LOG_LEVEL（DEBUG/INFO/...）
- is_live / is_paper / is_dev のユーティリティプロパティ

例:
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

自動的に .env を読み込む挙動:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）にある .env を読み込みます。
- 上書き順序: OS 環境 > .env.local > .env
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

主なファイル / ディレクトリ構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py           - パッケージ初期化、__version__ = "0.1.0"
  - config.py             - 環境変数 / 設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py   - J-Quants API クライアント（fetch_*, save_* 等）
    - schema.py           - DuckDB スキーマ定義と初期化（init_schema, get_connection）
    - audit.py            - 監査ログ（signal_events, order_requests, executions）の定義と初期化
  - execution/
    - __init__.py         - 実行（発注・約定）関連のパッケージ（今後の実装領域）
  - strategy/
    - __init__.py         - 戦略関連のパッケージ（今後の実装領域）
  - monitoring/
    - __init__.py         - モニタリング / メトリクスのパッケージ（今後の実装領域）

DuckDB に定義される主なテーブル（抜粋）:
- Raw 層: raw_prices, raw_financials, raw_news, raw_executions
- Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature 層: features, ai_scores
- Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
- Audit（監査）: signal_events, order_requests, executions

---

## 注意事項 / ベストプラクティス

- DuckDB の初期化は一度だけ行い、以降は get_connection() を使って既存 DB に接続してください。
- 監査ログは基本的に削除しない前提で設計されています（ON DELETE RESTRICT）。
- order_requests.order_request_id は冪等キーとしての利用を想定しています。再送時の重複発注防止に利用してください。
- すべての TIMESTAMP は UTC で取り扱うことを推奨します（監査 DB は初期化時にタイムゾーンを固定します）。
- 大量の API 呼び出しを行うバッチ処理では、J-Quants のレート上限を超えないよう適切に間隔を確保してください。

---

## 今後の拡張（想定）

- 実際の発注実行（kabu ステーションとの連携）ロジックの実装
- 戦略実装サンプルおよびシミュレーション（バックテスト）サポート
- モニタリング・アラート（Slack 連携や Prometheus / Grafana 統合）
- テスト・CI の整備

---

フィードバックや改善提案があれば、Issue や PR をお願いします。