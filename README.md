# KabuSys

日本株向け自動売買基盤（軽量プロトタイプ）。  
J-Quants / DuckDB を利用したデータプラットフォームと、戦略→発注までの監査ログ/ETL/品質チェックの基盤を提供します。

主な目的は「データ収集（J-Quants）→ DuckDB へ保存（Raw/Processed/Feature/Execution 層）→ 品質チェック → 戦略・発注のトレーサビリティ」を実現することです。

---

## 主な機能

- J-Quants API クライアント
  - 日次株価（OHLCV）、四半期財務、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）対応（固定間隔スロットリング）
  - リトライ（指数バックオフ、最大3回）、401 時の自動トークンリフレッシュ対応
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead バイアス防止を意識

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層を含むテーブル定義
  - 冪等性を意識した INSERT（ON CONFLICT DO UPDATE）による保存
  - インデックス定義や監査テーブル（signal_events / order_requests / executions）を提供

- ETL パイプライン
  - 差分更新（最終取得日からの差分取得＋バックフィル）
  - カレンダー先読み（デフォルト 90 日）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - run_daily_etl による日次一括処理（カレンダー→株価→財務→品質チェック）

- 品質チェック
  - 欠損データ、スパイク（前日比閾値）、主キー重複、日付不整合の検出
  - QualityIssue データ構造で問題を収集・報告

- 監査ログ（トレーサビリティ）
  - 戦略生成シグナルから発注、約定に至る一連の UUID 連鎖で追跡可能

---

## 要件

- Python 3.10+（型ヒントで | 型合成を使用しているため 3.10 以上を推奨）
- duckdb
- 標準ライブラリ（urllib 等）を使用
- 実運用では J-Quants の API トークン、kabu API、Slack などの外部認証情報が必要

（プロジェクトの pyproject.toml / requirements.txt があればそこから依存をインストールしてください）

---

## セットアップ手順

1. 仮想環境の作成（任意）
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

2. 依存のインストール
   - 例（最低限 duckdb をインストール）:
     ```
     pip install duckdb
     ```
   - プロジェクトに requirements.txt / pyproject.toml があればそれを使ってください。

3. 環境変数（.env）を用意
   - プロジェクトルートに `.env` / `.env.local` を置くと自動でロードします（CWD に依存せず、パッケージファイルを起点にプロジェクトルートを判定）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. DuckDB スキーマの初期化（サンプル）
   - Python REPL やスクリプトで:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     ```
   - 監査ログテーブルを追加する場合:
     ```python
     from kabusys.data import audit
     audit.init_audit_schema(conn)
     ```

---

## 必須 / 推奨の環境変数

settings モジュールから参照される主なキー（.env に設定する例）:

- J-Quants
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン

- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)

- Slack
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)

- DB パス
  - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (任意, デフォルト: data/monitoring.db)

- システム
  - KABUSYS_ENV (任意, デフォルト: development) — 有効値: development, paper_trading, live
  - LOG_LEVEL (任意, デフォルト: INFO) — 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL

注意:
- Settings は未設定の必須環境変数に対して ValueError を発生させます。
- .env ファイルのパースはシェルライク（export 対応、クォート、コメントの扱いをある程度サポート）です。
- OS 環境変数は .env で上書きされません（ただし .env.local は上書き可能）。自動読込はプロジェクトルート（.git または pyproject.toml）を基準に行われます。

---

## 使い方 — 代表的な例

### DuckDB スキーマ初期化
```python
from kabusys.data import schema

# ファイル DB を作成・初期化
conn = schema.init_schema("data/kabusys.duckdb")
```

### 監査ログ（Audit）テーブルの初期化（既存 conn に追加）
```python
from kabusys.data import audit

audit.init_audit_schema(conn)
```

### 日次 ETL 実行
run_daily_etl は市場カレンダー → 株価 → 財務 → 品質チェックまで一括で実行します。
戻り値は ETLResult オブジェクトで、取得件数・保存件数・品質問題・エラーの概要を含みます。

```python
from datetime import date
from kabusys.data import pipeline, schema

conn = schema.init_schema("data/kabusys.duckdb")

# target_date を指定しないと今日を使います
result = pipeline.run_daily_etl(conn, target_date=date.today())

# 結果の確認
print(result.to_dict())
if result.has_errors:
    print("ETL 中にエラーが発生しました:", result.errors)
if result.has_quality_errors:
    print("品質チェックで重大エラーが検出されました")
```

### J-Quants クライアントを直接使う（トークンは settings を参照）
```python
from kabusys.data import jquants_client as jq
import duckdb
from kabusys.config import settings

# 手動で ID トークンを取得する（省略すると内部キャッシュを使用）
id_token = jq.get_id_token()

# DuckDB 接続
conn = duckdb.connect("data/kabusys.duckdb")

# 日足データ取得と保存
records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2023,1,1), date_to=date(2023,12,31))
saved = jq.save_daily_quotes(conn, records)
print(f"取得 {len(records)} 件、保存 {saved} 件")
```

---

## ディレクトリ構成

リポジトリ内の主なファイル/ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理（.env 自動ロード、Settings）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得 / 保存 / リトライ / レート制御）
    - schema.py              — DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py            — ETL パイプライン（差分取得・保存・品質チェック）
    - audit.py               — 監査ログ（signal/events/order_requests/executions）DDL と初期化
    - quality.py             — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py            — 戦略関連の概観（詳細実装はここに追加）
  - execution/
    - __init__.py            — 発注・ブローカー連携層（拡張ポイント）
  - monitoring/
    - __init__.py            — 監視・メトリクス関連（拡張ポイント）

コードベースは Raw → Processed → Feature → Execution → Audit の層モデルを意識したディレクトリ/スキーマ構成になっています。

---

## 実装上の注意点 / 設計ポリシー

- J-Quants クライアントは 120 req/min のレート制限を固定間隔スロットリングで守ります。大量の API 呼び出しを行う場合は留意してください。
- API 呼び出しにはリトライと指数バックオフを実装（408/429/5xx など）。429 の場合は Retry-After ヘッダを優先して待機します。
- 401 エラーの場合はリフレッシュトークンにより id_token を自動更新して 1 回だけリトライします。
- データ保存は基本的に冪等（ON CONFLICT DO UPDATE）として設計されています。
- ETL は Fail-Fast ではなく、各ステップのエラーを収集して処理を続行します。戻り値の ETLResult を確認のうえ監査ログやアラートを出すことを想定しています。
- すべての TIMESTAMP は UTC を前提に扱う実装になっています（監査ログ初期化で TimeZone='UTC' を設定）。

---

## よくある質問 / トラブルシューティング

- .env が読み込まれない
  - .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）検出に基づきます。テストなどで無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
  - OS 環境変数が優先され、.env による上書きは行われません（ただし .env.local は override=True で上書き可能）。

- DuckDB ファイルの親ディレクトリが無い場合
  - init_schema / init_audit_db は親ディレクトリがない場合に自動作成します。

- スパイク検出の閾値
  - pipeline.run_daily_etl / quality.check_spike の閾値は引数で変更可能です（デフォルト 0.5 = 50%）。

---

この README はコードベースの主要な機能と利用方法の概要を示しています。戦略（strategy）・発注（execution）・監視（monitoring）層は拡張ポイントとして用意されています。必要に応じて具体的なブローカー連携や Slack 通知、ジョブスケジューラ（cron / Airflow 等）との統合を実装してください。