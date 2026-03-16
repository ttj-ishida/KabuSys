# KabuSys

日本株自動売買システムのライブラリ（SDK）／データプラットフォーム基盤コンポーネントです。  
主にデータ収集・保存（DuckDB）、品質チェック、監査ログ、外部 API クライアント（J-Quants）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構築するための基盤モジュール群です。設計方針として以下を重視しています。

- 外部データ取得（J-Quants）におけるレート制限・リトライ・トークン自動更新の対応
- DuckDB を用いた三層データレイヤ（Raw / Processed / Feature）と Execution 層
- 発注から約定に至る監査ログ (audit) による完全なトレーサビリティ（UUID 連鎖）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 環境変数/.env による設定管理（自動ロード・保護）

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - .env / .env.local の自動読み込み（プロジェクトルートを検出）
  - 必須設定のラップ（Settings クラス）
  - 環境切替（development / paper_trading / live）やログレベル検証
- kabusys.data.jquants_client
  - J-Quants API クライアント（OHLCV, 財務データ, JPX マーケットカレンダー）
  - 固定間隔のレート制限 (120 req/min)、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - DuckDB へ冪等的に保存する save_* 関数
- kabusys.data.schema
  - DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution）
  - テーブルとインデックスの生成（init_schema / get_connection）
- kabusys.data.audit
  - 監査ログ用スキーマ（signal_events / order_requests / executions）
  - 監査 DB の初期化（init_audit_schema / init_audit_db）
  - 発注の冪等キーやステータス遷移管理を想定
- kabusys.data.quality
  - データ品質チェック（欠損データ、スパイク、重複、日付不整合）
  - run_all_checks による一括実行と問題検出のレポート（QualityIssue）

※ strategy, execution, monitoring のパッケージはインターフェース用に用意されています（現時点では空の __init__.py）。

---

## セットアップ手順

前提

- Python 3.10 以降（コード内の型ヒントで `|` を使用）
- DuckDB を利用するため duckdb パッケージをインストール

推奨手順（例）

1. リポジトリをクローン／取得

   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化（任意）

   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .\.venv\Scripts\activate    # Windows
   ```

3. 依存パッケージをインストール（最低限）

   ```
   pip install duckdb
   ```

   実運用では `requests` や Slack 通知等のライブラリが必要な場合があります。プロジェクトに requirements.txt があればそれを使用してください。

4. 環境変数を設定

   プロジェクトルートに `.env` または `.env.local` を配置できます。自動読み込みはデフォルトで有効です（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化）。

   必須環境変数（Settings から）:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - SLACK_BOT_TOKEN: Slack ボットトークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID

   オプション（デフォルトを示す）:

   - KABUSYS_ENV: {development, paper_trading, live}（デフォルト: development）
   - LOG_LEVEL: {DEBUG, INFO, WARNING, ERROR, CRITICAL}（デフォルト: INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視用途）（デフォルト: data/monitoring.db）

   例 (.env):

   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（簡単なコード例）

以下は主要ユースケースの例です。実行前に必ず環境変数を設定してください。

- DuckDB スキーマ初期化

```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# ファイルパスは settings.duckdb_path を利用可能
conn = init_schema(settings.duckdb_path)
# 以降 conn を使ってデータ挿入やクエリを実行できます
```

- J-Quants から日足を取得して保存する

```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)

# 必要ならトークンを明示取得
id_token = get_id_token()

# 銘柄コード・期間を指定して取得
records = fetch_daily_quotes(id_token=id_token, code="7203", date_from=None, date_to=None)

# DuckDB に保存（冪等）
n = save_daily_quotes(conn, records)
print(f"保存したレコード数: {n}")
```

- 監査ログスキーマの初期化（既存接続へ追加）

```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
init_audit_schema(conn)
```

- データ品質チェックを実行

```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
issues = run_all_checks(conn)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

- .env の自動ロードを無効化する（テスト時など）

```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## API の設計上のポイント（実装ノート）

- J-Quants クライアントは 120 req/min を守るため固定間隔スロットリングを行います。
- リトライ: ネットワークエラーや 408/429/5xx に対して指数バックオフで最大 3 回リトライします。429 の場合は `Retry-After` ヘッダを優先利用します。
- 401 受信時: refresh token を用いて id_token を自動更新し、1 回だけ再試行します（無限再帰を防止）。
- データ保存: DuckDB への保存は ON CONFLICT DO UPDATE による冪等化を行っています。
- 監査ログ: 発注フローを UUID 連鎖で追跡できるように設計されており、order_request_id による冪等制御を想定しています。
- 時刻: すべての TIMESTAMP は UTC を原則としています（audit 初期化では TimeZone='UTC' を設定）。

---

## ディレクトリ構成

リポジトリ内の主要ファイル・モジュール（抜粋）

- src/kabusys/
  - __init__.py                — パッケージ初期化（version）
  - config.py                  — 環境変数 / .env ロードと Settings クラス
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（fetch / save）
    - schema.py                — DuckDB スキーマ定義と init/get_connection
    - audit.py                 — 監査ログ（signal_events / order_requests / executions）
    - quality.py               — データ品質チェック（欠損・スパイク・重複・日付）
  - strategy/
    - __init__.py              — 戦略層のパッケージ（拡張ポイント）
  - execution/
    - __init__.py              — 発注実行層のパッケージ（拡張ポイント）
  - monitoring/
    - __init__.py              — 監視/メトリクス用（拡張ポイント）

ファイル単位の説明

- config.py
  - プロジェクトルート検出（.git または pyproject.toml）に基づく .env 自動読み込み
  - _parse_env_line: シェル風の .env フォーマットを解析
  - Settings: 各種必須/任意設定のラッパ

- data/jquants_client.py
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token: refresh token から id_token を取得

- data/schema.py
  - Raw / Processed / Feature / Execution 層の DDL を内包
  - init_schema: 全テーブル作成（冪等）
  - get_connection: 既存 DB 接続取得

- data/audit.py
  - 監査ログ用 DDL とインデックス定義
  - init_audit_schema / init_audit_db

- data/quality.py
  - QualityIssue データクラス
  - 各チェック関数と run_all_checks の実装

---

## 開発・運用上の注意

- 環境変数やトークンは適切に管理してください（リポジトリにトークンを含めない）。
- DuckDB ファイルのバックアップや永続化戦略を検討してください（ファイルベース DB のため）。
- 実際の発注ロジック・証券会社 API 連携（kabuステーション API）を組み込む場合は、order_requests → executions → trades の流れと監査テーブルの整合性を厳密に扱ってください。
- 本ライブラリは基盤モジュール群の提供に焦点を当てており、実際の売買戦略やポジション管理ロジックは別途実装が必要です。

---

以上が README の概要です。必要であれば以下を追加します：

- 具体的な requirements.txt の候補
- .env.example のテンプレート
- CI / テスト実行手順（pytest 等）
- よくあるトラブルシューティング（トークンエラー、DuckDB ロック等）

どれを追加しますか？