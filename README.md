# KabuSys

日本株の自動売買プラットフォーム用ライブラリ（モジュール集合）。データ取得、永続化（DuckDB）、監査ログ、データ品質チェックなど、アルゴリズムトレーディング基盤で必要となる共通機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のような機能を提供し、戦略実装や実運用サービスの下地を整備します。

- J-Quants API から株価日足、財務データ、マーケットカレンダーを取得
- 取得データを DuckDB に冪等的に保存（ON CONFLICT DO UPDATE）
- 取得時刻（fetched_at）を UTC で記録し、Look-ahead bias を防止
- API レート制御（120 req/min）、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
- DuckDB スキーマ定義と初期化ユーティリティ
- 監査ログ（シグナル→発注→約定のトレーサビリティ）テーブルの初期化
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 設定管理（.env、自動読み込み、必須キーのチェック）

現状、strategy / execution / monitoring の各パッケージは参照点として用意されています（実装は用途に応じて拡張）。

---

## 機能一覧

- config
  - プロジェクトルートから `.env` / `.env.local` を自動読み込み（環境変数優先）
  - 必須 env チェック・簡易ユーティリティ
  - 自動ロードを無効化するフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- data.jquants_client
  - get_id_token: リフレッシュトークンから idToken を取得（POST）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar: ページネーション対応の取得関数
  - save_daily_quotes / save_financial_statements / save_market_calendar: DuckDB へ冪等保存
  - レート制御（120 req/min 固定）とリトライ（最大 3 回、401 は自動リフレッシュ）
- data.schema
  - DuckDB の全スキーマ（Raw / Processed / Feature / Execution）定義と初期化
  - init_schema(db_path) でテーブル・インデックスを作成
  - get_connection(db_path) で既存 DB に接続
- data.audit
  - 監査用テーブル（signal_events / order_requests / executions）の定義と初期化
  - init_audit_schema(conn) / init_audit_db(path)
- data.quality
  - 欠損データ検出（OHLC 欠損）
  - スパイク検出（前日比閾値、デフォルト 50%）
  - 主キー重複検出
  - 日付不整合検出（未来日付、market_calendar で非営業日のデータ）
  - run_all_checks で一括実行、QualityIssue のリストを返す

---

## セットアップ手順

前提: Python 3.9+（型ヒントの union 表記や Path の使い方に準拠）。実行環境に合わせて適宜調整してください。

1. リポジトリをクローン / 取得

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必須: duckdb
   - 例:
     - pip install duckdb

   ※ urllib 等は標準ライブラリで賄う設計です。追加の依存があれば pyproject.toml / requirements.txt を参照してください（本コード断片では含まれていません）。

4. 環境変数設定（.env）
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 主要な環境変数例:
     - JQUANTS_REFRESH_TOKEN  (必須) — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD      (必須) — kabuステーション API パスワード
     - KABU_API_BASE_URL      (オプション) — デフォルト: http://localhost:18080/kabusapi
     - SLACK_BOT_TOKEN        (必須) — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID       (必須) — Slack 通知先チャンネル ID
     - DUCKDB_PATH            (オプション) — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH            (オプション) — デフォルト: data/monitoring.db
     - KABUSYS_ENV            (オプション) — development | paper_trading | live (デフォルト: development)
     - LOG_LEVEL              (オプション) — DEBUG/INFO/WARNING/ERROR/CRITICAL (デフォルト: INFO)

   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（基本的な例）

以下に主要ユースケースの簡単なコード例を示します。実行前に `.env` の設定が必要です。

1) DuckDB スキーマ初期化

```python
from kabusys.data.schema import init_schema

# ファイル DB を初期化
conn = init_schema("data/kabusys.duckdb")
# またはインメモリ:
# conn = init_schema(":memory:")
```

2) J-Quants から株価を取得して保存

```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # settings.duckdb_path は Path を返す

# 例: 特定銘柄の期間を指定して取得・保存
from datetime import date
records = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
count = save_daily_quotes(conn, records)
print(f"保存件数: {count}")
```

ポイント:
- fetch_* 関数は自動的に id_token をキャッシュ・リフレッシュします。
- モジュールは内部でレート制御（120 req/min）と最大 3 回のリトライを行います。

3) 監査スキーマの初期化（既存 conn に追加）

```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn)
```

または監査専用 DB を単独で初期化:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/kabusys_audit.duckdb")
```

4) データ品質チェック

```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=None)  # target_date を指定可能
for issue in issues:
    print(issue.check_name, issue.severity, issue.detail)
    for row in issue.rows:
        print(row)
```

5) id_token を直接取得（必要時）

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
```

---

## 実装上の注意点

- レート制御
  - _RateLimiter により 120 req/min を固定間隔で守ります（モジュールレベルでのスロットリング）。
- リトライ
  - 対象: 408, 429, 5xx およびネットワークエラー。最大 3 回（指数バックオフ）。
  - 401 受信時にはリフレッシュを行い 1 回再試行します（無限再帰防止のため allow_refresh 制御）。
- データ永続化の冪等性
  - DuckDB への INSERT は ON CONFLICT DO UPDATE を使用して重複を排除します。
- 時刻（fetched_at / created_at / executed_at）
  - UTC を使用する設計。監査では SET TimeZone='UTC' を明示的に実行します。
- スキーマ変更／ETL 外部からのデータ注入に備え、データ品質チェックを定期実行してください。

---

## ディレクトリ構成

（コード断片に基づく主要ファイル一覧）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/
      - __init__.py
    - strategy/
      - __init__.py
    - monitoring/
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py
      - schema.py
      - audit.py
      - quality.py

主要モジュールの役割:
- config.py: 環境変数の自動読み込みと Settings クラス
- data/jquants_client.py: J-Quants API クライアント（取得・保存ロジック）
- data/schema.py: DuckDB スキーマ定義・初期化
- data/audit.py: 監査ログ（トレーサビリティ）定義・初期化
- data/quality.py: データ品質チェック
- strategy, execution, monitoring: 拡張ポイント（戦略ロジック・発注実行・監視）

---

## 今後の拡張案（例）

- kabuステーション（kabu API）との注文送受信実装（execution パッケージ）
- 戦略実装テンプレート（strategy パッケージ）
- 継続監視・アラート（monitoring パッケージ、Slack 通知との連携）
- CI 用のテスト / linter の追加、pyproject.toml に依存管理を明示化

---

## ライセンス / 注意事項

- 本リポジトリはサンプル実装・基盤ライブラリとして提供する想定です。実運用での売買は市場リスクを伴います。実際の資金を動かす前に十分なテストと監査を行ってください。
- API トークンやパスワードは漏洩に注意し、レポジトリにハードコードしないでください（.env を利用）。

---

この README はコードベースの現状（src 内の実装）に基づいて作成しています。追加の実装や要望があれば README を更新します。