# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
J-Quants API を用いた市場データ取得、DuckDB を用いたスキーマ・ETL、品質チェック、監査ログ（発注→約定のトレース）機能を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした軽量ライブラリです。

- J-Quants API からの株価（日次 OHLCV）、財務（四半期 BS/PL）、JPX 市場カレンダーの取得
- DuckDB を使った階層化されたデータスキーマ（Raw / Processed / Feature / Execution）
- 差分 ETL パイプライン（backfill 対応、冪等保存）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 発注・約定の監査ログ（UUID によるトレーサビリティ）
- 環境変数ベースの設定管理（.env 自動ロード）

設計上の注意点として、API レート制限の尊重（120 req/min）、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ、取得時刻（fetched_at）による Look-ahead バイアス回避などを実装しています。

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に検出）
  - 必須環境変数の検査 helper
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能

- J-Quants クライアント（kabusys.data.jquants_client）
  - get_id_token（リフレッシュトークン→IDトークン）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
  - DuckDB へ冪等に保存する save_* 関数（ON CONFLICT DO UPDATE）
  - レートリミットとリトライを内包

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル DDL
  - init_schema で初期化（冪等）
  - get_connection で接続取得

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（run_daily_etl）：カレンダー→株価→財務→品質チェック の順で差分更新
  - 差分更新ロジック（最終取得日＋バックフィル）
  - 品質チェック結果を ETLResult として返却

- 品質チェック（kabusys.data.quality）
  - 欠損（OHLC）検出
  - スパイク（前日比）検出
  - 重複（PK 重複）検出
  - 日付不整合（未来日付・非営業日のデータ）検出

- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions など監査用テーブル群
  - init_audit_schema / init_audit_db による初期化（UTC タイムスタンプ）

- パッケージ境界（空パッケージあり）
  - kabusys.strategy, kabusys.execution, kabusys.monitoring（戦略、発注、監視の拡張ポイント）

---

## セットアップ手順

前提:
- Python 3.9+ を想定（typing の | 演算子等に依存）
- DuckDB を利用するため pip でインストールします

1. リポジトリをクローン
   - git clone ... (プロジェクトルートに .git や pyproject.toml があること)

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb
   - （プロジェクトを編集可能インストールする場合）pip install -e .

   ※ 必要に応じて Slack, kabu-station との連携用パッケージ等を追加してください。

4. 環境変数（.env）を準備
   - プロジェクトルートの .env または .env.local に設定を置くと自動で読み込まれます（自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意:
     - KABUSYS_ENV (development | paper_trading | live) デフォルトは development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) デフォルト INFO
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（簡単なコード例）

1) DuckDB スキーマの初期化
```
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")  # ファイルを自動生成
```

2) 日次 ETL の実行（J-Quants トークンは内部で settings.jquants_refresh_token を使用）
```
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定しなければ今日が対象
print(result.to_dict())
```

3) 個別にデータ取得して保存する（テストやデバッグ用）
```
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes, save_daily_quotes

token = get_id_token()  # settings.jquants_refresh_token を使用
records = fetch_daily_quotes(id_token=token, code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
saved = save_daily_quotes(conn, records)
```

4) 監査ログテーブルの初期化（既存の conn に追加）
```
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```

5) 品質チェックだけ実行する
```
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

注意:
- run_daily_etl は各ステップを個別にエラーハンドリングして続行します。ETLResult の errors / quality_issues を確認してください。
- .env 自動読み込みはプロジェクトルートの検出に .git または pyproject.toml を使っています。CI やテストで自動ロードを抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## ディレクトリ構成

プロジェクト内の主要ファイル・モジュールは以下の通りです（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数 / 設定管理（.env 自動ロード、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（取得・保存・リトライ・レート制御）
    - schema.py              -- DuckDB スキーマ定義と init_schema/get_connection
    - pipeline.py            -- 差分 ETL パイプライン（run_daily_etl など）
    - audit.py               -- 監査ログ（signal_events, order_requests, executions）
    - quality.py             -- データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py            -- 戦略用パッケージ（拡張ポイント）
  - execution/
    - __init__.py            -- 発注実行用パッケージ（拡張ポイント）
  - monitoring/
    - __init__.py            -- 監視関連（拡張ポイント）

その他:
- .env / .env.local         -- プロジェクトルートに配置して自動ロード可能（例を参考に作成）

---

## 実装上のポイント / 注意事項

- J-Quants API は 120 req/min のレート制限を想定して実装（固定間隔スロットリング）。
- HTTP エラー（408/429/5xx 等）に対して指数バックオフで最大 3 回リトライします。429 の場合は Retry-After ヘッダを優先。
- 401 Unauthorized を受けた場合はリフレッシュトークンから id_token を再取得して 1 回だけリトライします。
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）を基本とし、ETL の再実行や部分リトライに耐えます。
- すべての監査用 TIMESTAMP は UTC で保存する設計（init_audit_schema で SET TimeZone='UTC' を設定）。
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかであることを期待します。

---

もし README に追加して欲しい内容（例: CI / テストの手順、実運用での注意点、実例ワークフロー、Docker サポートなど）があれば教えてください。