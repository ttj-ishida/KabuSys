# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（モジュール群）。  
データ取得（J-Quants）、DuckDB スキーマ管理、監査ログ、データ品質チェック等を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とした内部ライブラリです。

- J-Quants API から株価・財務・マーケットカレンダー等を取得するクライアント
- 取得データを保存する DuckDB のスキーマ定義と初期化
- 発注〜約定フローを追跡可能にする監査（audit）テーブルの定義
- データ品質チェック（欠損・重複・スパイク・日付不整合など）
- 環境変数ベースの設定管理（.env の自動読み込み、必須チェック）
- 将来の戦略／実行モジュールのためのパッケージ構造（strategy / execution / monitoring）

設計上のポイント：
- J-Quants クライアントは API レート制限（120 req/min）とリトライ、トークン自動リフレッシュに対応
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で重複を排除
- すべてのタイムスタンプは UTC を想定（監査用は明示的に UTC に設定）

---

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動読み込み（必要なら無効化可能）
  - 必須環境変数未設定時は明示的な例外を発生

- J-Quants API クライアント（kabusys.data.jquants_client）
  - get_id_token（リフレッシュトークンから ID トークンを取得）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
  - レートリミッタ、指数バックオフリトライ、401 での自動リフレッシュ
  - DuckDB へ保存する save_* 関数（raw_prices, raw_financials, market_calendar）

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層に分けたテーブル群を作成
  - インデックス定義、依存順序を考慮した初期化（init_schema, get_connection）

- 監査ログ（kabusys.data.audit）
  - シグナル → 発注要求 → 約定を追跡するためのテーブル群（冪等キー、ステータス、UTC タイム）
  - init_audit_schema / init_audit_db

- データ品質チェック（kabusys.data.quality）
  - 欠損データ検出、スパイク（前日比）検出、重複チェック、日付整合性チェック
  - QualityIssue 型で問題を集約し、run_all_checks で一括実行

---

## 前提・依存関係

- Python 3.10 以上（Union 型表記 `X | Y` を使用）
- 必要なパッケージ（最低限）
  - duckdb
- 標準ライブラリ: urllib, json, logging, datetime, pathlib など

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb
# パッケージとしてインストールする場合:
# pip install -e .
```

---

## 環境変数（主な設定項目）

以下はこのコードベースで参照する主要な環境変数（デフォルトや必須性を併記）:

- JQUANTS_REFRESH_TOKEN (必須)  
  - J-Quants のリフレッシュトークン。get_id_token に使用。

- KABU_API_PASSWORD (必須)  
  - kabuステーション API のパスワード（実際の実行モジュールで使用）。

- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)  
  - kabuステーション API のベース URL。

- SLACK_BOT_TOKEN (必須)  
  - Slack 通知用 Bot トークン。

- SLACK_CHANNEL_ID (必須)  
  - Slack 通知先チャンネル ID。

- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)  
  - DuckDB ファイルのパス。

- SQLITE_PATH (任意, デフォルト: data/monitoring.db)  
  - 監視用 SQLite のパス（コード内参照のための設定）。

- KABUSYS_ENV (任意, デフォルト: development)  
  - 有効値: development / paper_trading / live

- LOG_LEVEL (任意, デフォルト: INFO)  
  - 有効値: DEBUG / INFO / WARNING / ERROR / CRITICAL

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）から `.env` と `.env.local` を自動読み込みします。  
- 無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

注意:
- settings オブジェクトは必須項目が未設定だと ValueError を投げます。

---

## セットアップ手順

1. リポジトリをクローン／取得
2. 仮想環境を作成して有効化
3. 依存ライブラリをインストール（例: duckdb）
4. プロジェクトルートに `.env` を作成し、必要な環境変数を設定  
   例（.env の一部）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```
5. DuckDB スキーマを初期化

---

## 使い方（基本例）

以下はライブラリを用いて DB を初期化し、J-Quants から日足を取得して保存し、品質チェックを行う簡単なフロー例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema
from kabusys.config import settings

# settings.duckdb_path はデフォルト 'data/kabusys.duckdb'
conn = schema.init_schema(settings.duckdb_path)
```

2) J-Quants から日足を取得して保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

# 全銘柄・期間指定なしで取得（ページネーション対応）
records = fetch_daily_quotes()

# DuckDB 接続に保存（raw_prices テーブル）
n = save_daily_quotes(conn, records)
print(f"保存件数: {n}")
```

3) 監査テーブルを追加で初期化（必要時）
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```

4) データ品質チェック
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn)
for issue in issues:
    print(issue.check_name, issue.table, issue.severity, issue.detail)
```

その他利用可能な API:
- jquants_client.get_id_token(refresh_token=None)
- fetch_financial_statements(...), save_financial_statements(...)
- fetch_market_calendar(...), save_market_calendar(...)

各関数は引数や戻り値の説明を docstring に記載しています。詳しくは各モジュールの docstring を参照してください。

---

## ディレクトリ構成

主要ファイル／パッケージ構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                     # 環境設定・.env 自動読み込み
    - data/
      - __init__.py
      - jquants_client.py           # J-Quants API クライアント（fetch/save）
      - schema.py                   # DuckDB スキーマ定義・初期化
      - audit.py                    # 監査ログ（signal/order/execution）
      - quality.py                  # データ品質チェック
      - (others...)                 # 追加データモジュールなど
    - strategy/
      - __init__.py                 # 戦略モジュール（拡張用）
    - execution/
      - __init__.py                 # 発注／ブローカー連携（拡張用）
    - monitoring/
      - __init__.py                 # 監視系（拡張用）

---

## 実装上の注意点 / トラブルシューティング

- 環境変数が不足していると settings プロパティで ValueError が発生します。`.env.example` がある場合は参考にしてください（本リポジトリに無い場合は上記必須項目を設定してください）。
- J-Quants の API レスポンスが 401 の場合、ライブラリは自動でトークンをリフレッシュして 1 回再試行します。リフレッシュ失敗時は例外になります。
- rate limit（120 req/min）に従ってクライアント内でスロットリングを行います。大量データを連続で取得する際は時間がかかります。
- DuckDB の初期化は冪等（存在するテーブルはスキップ）です。別 DB を使いたい場合は settings.duckdb_path を差し替えてください。
- 監査テーブル初期化時は接続に対してタイムゾーンを UTC に設定します（SET TimeZone='UTC'）。

---

## さらに進めるために

- strategy / execution / monitoring パッケージに具体的な戦略、リスク管理、ブローカー連携の実装を追加して下さい。
- 品質チェックの結果を Slack に送る等の通知実装を monitoring モジュールに実装すると運用が容易になります。
- CLI や定期実行用のジョブ（ETL / backfill / daily run）を追加すると実運用に近づきます。

---

必要があれば README の英語版やサンプル `.env.example`、より詳しい使用例（バックフィル、ページネーションの扱い、エラーケースのサンプル）も作成できます。どの追加が必要か教えてください。