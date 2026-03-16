# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（モジュール群）。データ取得・蓄積・品質チェック・監査ログ・戦略／実行の基盤機能を提供します。

主な設計方針：
- データの取得から発注に至るまでのトレーサビリティを重視
- DuckDB を用いた冪等なデータ保存
- J-Quants API のレート制限・リトライ・トークン更新に対応
- データ品質チェック（欠損・重複・スパイク・日付不整合）を実装

バージョン: 0.1.0

---

## 機能一覧

- 環境変数／設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得ラッパー（例: settings.jquants_refresh_token）
  - KABUSYS_ENV / LOG_LEVEL の検証

- J-Quants API クライアント
  - 日足（OHLCV）取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）取得（ページネーション対応）
  - JPX マーケットカレンダー取得
  - レート制限（120 req/min）対応の内部 RateLimiter
  - リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス定義、初期化ユーティリティ（init_schema / get_connection）

- 監査ログ（audit）
  - シグナル生成〜発注〜約定までを UUID 連鎖で追跡するテーブル群
  - 発注要求は冪等キー（order_request_id）で重複送信を防止
  - init_audit_schema / init_audit_db を提供

- データ品質チェック（quality）
  - 欠損データ検出
  - スパイク（前日比）検出
  - 重複（主キー）検出
  - 日付不整合（未来日付／非営業日データ）検出
  - 全チェックをまとめて実行する run_all_checks

---

## セットアップ手順

前提:
- Python 3.10 以上（型注釈や union 型（|）を使用）
- DuckDB が必要（Python パッケージ）

推奨の手順（仮想環境を使用）:

1. 仮想環境作成・有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 依存パッケージをインストール
   ```
   pip install duckdb
   ```

3. 開発中であればパッケージを editable install（プロジェクトルートに pyproject.toml 等がある想定）
   ```
   pip install -e .
   ```

4. 環境変数を設定（.env/.env.local をプロジェクトルートに配置するか OS 環境変数を利用）
   - 自動読み込み:
     - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml）を基準に `.env` および `.env.local` を読み込みます。
     - 読み込み優先順位: OS 環境変数 > .env.local > .env
     - 自動読み込みを無効化する場合:
       ```
       export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
       ```

必須の環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト INFO）

例 .env:
```
JQUANTS_REFRESH_TOKEN=xxxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡易サンプル）

以下は代表的な操作の例です。

- 設定・パスの確認:
```python
from kabusys.config import settings

print(settings.duckdb_path)
print(settings.is_dev)
```

- DuckDB スキーマを初期化して接続を取得:
```python
from kabusys.data import schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
# またはインメモリ:
# conn = schema.init_schema(":memory:")
```

- J-Quants から日足を取得して保存:
```python
from datetime import date
from kabusys.data import jquants_client

# 日付範囲や銘柄コードを指定して取得
records = jquants_client.fetch_daily_quotes(code="7203", date_from=date(2023, 1, 1), date_to=date(2023, 12, 31))

# DuckDB に保存（conn は init_schema で取得した接続）
inserted = jquants_client.save_daily_quotes(conn, records)
print(f"保存件数: {inserted}")
```

- 財務データ／市場カレンダーの取得と保存:
```python
fin = jquants_client.fetch_financial_statements(code="7203")
jquants_client.save_financial_statements(conn, fin)

cal = jquants_client.fetch_market_calendar()
jquants_client.save_market_calendar(conn, cal)
```

- 監査ログテーブルの初期化（既存 conn に追加）:
```python
from kabusys.data import audit

audit.init_audit_schema(conn)
# あるいは監査専用 DB を初期化:
# audit_conn = audit.init_audit_db("data/audit.duckdb")
```

- データ品質チェック:
```python
from datetime import date
from kabusys.data import quality

issues = quality.run_all_checks(conn, target_date=date(2023, 12, 31))
for issue in issues:
    print(issue.check_name, issue.severity, issue.detail)
    for row in issue.rows:
        print("  ", row)
```

注意点:
- J-Quants へのリクエストは内部でレート制御・リトライ・トークン更新を行います。
- save_* 関数は ON CONFLICT DO UPDATE により冪等にデータを保存します。
- すべてのタイムスタンプは UTC で扱われることを想定しています（監査ログなど）。

---

## ディレクトリ構成

パッケージの主要ファイル一覧（本リポジトリに含まれるものの抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ロジック）
    - schema.py              — DuckDB スキーマ定義・初期化
    - audit.py               — 監査ログ（トレーサビリティ）定義・初期化
    - quality.py             — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py            — 戦略モジュール（拡張ポイント）
  - execution/
    - __init__.py            — 実行（発注）モジュール（拡張ポイント）
  - monitoring/
    - __init__.py            — 監視・モニタリング関連（拡張ポイント）

各モジュールの責務:
- data: 外部 API からの取得、DB スキーマ、品質チェック、監査ログをまとめるコア
- strategy: 戦略ロジックの格納場所（ユーザ実装を想定）
- execution: 証券会社 API（kabuステーション等）とのやり取りを行う場所（ユーザ実装を想定）
- monitoring: Slack などによる通知やプロセス監視の実装場所

---

## その他 / 運用メモ

- 環境判定:
  - settings.env は "development" / "paper_trading" / "live" のいずれかである必要があります。
  - settings.is_live / is_paper / is_dev で判定可能。

- ロギング:
  - settings.log_level でログレベルを制御します（環境変数 LOG_LEVEL）。

- テスト:
  - 自動環境変数読み込みはテスト時に影響を与えることがあるため、テスト実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると安全です。

---

必要に応じて README にサンプルの .env.example、ユニットテスト、CI 設定、パッケージング手順（pyproject.toml 等）を追加できます。README の補足やサンプルコードの追加が必要であれば教えてください。