# KabuSys — 日本株自動売買システム

簡潔な紹介:
KabuSys は日本株向けのデータ基盤および自動売買の基礎ライブラリ群です。J-Quants API から市場データ（株価日足・財務・マーケットカレンダー）を安全に取得・保存し、DuckDB 上に三層（Raw / Processed / Feature）＋実行・監査用テーブルを備えたデータプラットフォームを提供します。ETL、データ品質チェック、監査ログ（トレーサビリティ）を備え、戦略や発注モジュールと連携できる設計です。

主な設計方針（抜粋）
- レート制限（J-Quants: 120 req/min）を守る固定間隔スロットリング
- 失敗時のリトライ（指数バックオフ、401 → トークン自動更新）
- Look-ahead bias を防ぐため取得時刻（UTC）を記録
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）
- 品質チェックは全件収集型（Fail-Fast ではない）

---

## 機能一覧

- データ取得（J-Quants API）
  - 株価日足（OHLCV）
  - 財務データ（四半期 BS/PL）
  - JPX マーケットカレンダー（祝日・半日・SQ）
- API クライアントの信頼性処理
  - レートリミット制御、リトライ（408/429/5xx）、401 時のトークンリフレッシュ
- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution 層のテーブル群、インデックス
- 監査ログ（audit）
  - signal_events / order_requests / executions によるトレーサビリティ
- ETL パイプライン
  - 差分取得（最終取得日+バックフィル）、保存（冪等）、品質チェック
- データ品質チェック
  - 欠損検出、主キー重複、価格スパイク、日付不整合（未来日付／非営業日）

---

## セットアップ手順

前提
- Python 3.10+（typing の Union | 記法等を想定）
- pip、仮想環境推奨

1. リポジトリをクローン（またはパッケージソースを取得）
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   - 本コードベースで明示的に使用している主要依存は `duckdb` です。
   - パッケージ形式で配布している場合は
     ```
     pip install -e .
     ```
     または最低限
     ```
     pip install duckdb
     ```
   - 実運用で Slack 連携や HTTP クライアント（urllib は標準）等を使う場合は別途依存を追加してください。

4. 環境変数設定
   - ルートに `.env` / `.env.local` を置くと自動で読み込まれます（CWD に依存せず、パッケージの場所からプロジェクトルートを探索）。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用）。
   - 必須環境変数（設定がないと起動時に例外が出ます）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意/デフォルト:
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — default: INFO

   例（.env の最小例）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（基本例）

以下はライブラリを使って DuckDB を初期化し、日次 ETL を実行する最小の例です。

1. DuckDB スキーマを初期化して接続を得る
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
```

2. 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

3. 監査ログ（audit）スキーマを追加する
```python
from kabusys.data.audit import init_audit_schema

# 既存の conn に監査テーブルを追加
init_audit_schema(conn)
```

4. 低レイヤーの API 呼び出し例
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings
from kabusys.data.schema import get_connection

# トークンは settings.jquants_refresh_token から自動で使われる
records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
conn = get_connection(settings.duckdb_path)
jq.save_daily_quotes(conn, records)
```

ログ出力やエラーハンドリングは各関数内で行われます。ETL の結果は ETLResult（data.pipeline.ETLResult）で返り、品質チェック結果やエラー一覧を参照できます。

---

## 主な API / モジュール説明

- kabusys.config
  - 環境変数のロード・検証・ラッパー（settings オブジェクトを利用）
  - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml）

- kabusys.data.jquants_client
  - J-Quants API クライアント実装
  - fetch_*（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）
  - save_*（save_daily_quotes, save_financial_statements, save_market_calendar）
  - get_id_token（リフレッシュトークンから idToken を取得）

- kabusys.data.schema
  - DuckDB のテーブル DDL 定義と初期化関数
  - init_schema(db_path) / get_connection(db_path)

- kabusys.data.pipeline
  - 差分ETL ロジック（run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl）
  - バックフィル・カレンダーの先読み・品質チェック統合

- kabusys.data.quality
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
  - run_all_checks でまとめて実行し QualityIssue のリストを返す

- kabusys.data.audit
  - 監査ログ（signal_events / order_requests / executions）のDDL と初期化関数
  - init_audit_schema / init_audit_db

---

## 実運用の注意点

- J-Quants のレート制限（120 req/min）および API 利用規約を遵守してください。
- 本ライブラリは取得時刻（fetched_at）を記録して Look-ahead Bias を軽減しますが、上位の戦略はさらに注意を払ってください。
- 本番（live）モードでは KABUSYS_ENV を `live` に設定するとフラグが切り替わります。Paper/Live の振る舞いは実装側で切り替えて下さい（このパッケージではフラグのみ提供）。
- DuckDB ファイルはバックアップやファイルの整合性管理を運用側で行ってください。監査ログは原則削除しない方針です。

---

## ディレクトリ構成

（主要ファイルを抜粋）

- src/
  - kabusys/
    - __init__.py                         — パッケージのバージョン定義
    - config.py                           — 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py                 — J-Quants API クライアント（取得/保存）
      - schema.py                         — DuckDB スキーマ定義・初期化
      - pipeline.py                       — ETL パイプライン（差分更新・品質チェック）
      - audit.py                          — 監査ログ（トレーサビリティ）DDL/初期化
      - quality.py                        — データ品質チェック
    - strategy/
      - __init__.py                        — 戦略モジュール用プレースホルダ
    - execution/
      - __init__.py                        — 発注/約定処理用プレースホルダ
    - monitoring/
      - __init__.py                        — 監視関連プレースホルダ

---

## 追加情報／拡張ポイント

- 発注（kabu ステーション）連携：config で KABU_API_BASE_URL と KABU_API_PASSWORD を管理しています。execution 層で実際の注文送信・管理を実装してください。
- Slack 通知：settings.slack_bot_token / slack_channel_id を利用して ETL 結果やアラートを通知すると運用が楽になります（実装は別途）。
- テスト性：pipeline の関数は id_token を注入できるためモックや統合テストが容易です。自動ロードを無効化する環境変数も用意されています。

---

何か追加したいセクション（例: CLI コマンド、CI 設定、.env.example のテンプレートなど）があれば教えてください。README をそれに合わせて追記・整形します。