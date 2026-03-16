# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（KabuSys）。  
J-Quants API からマーケットデータ・財務データ・市場カレンダーを取得し、DuckDB に保存して ETL／品質チェック／監査ログを提供します。戦略・実行・モニタリングの基盤として利用できるモジュール群を含みます。

---

## 特徴（機能一覧）

- J-Quants API クライアント
  - 日足（OHLCV）、四半期財務、JPX マーケットカレンダーを取得
  - レート制限（120 req/min）対応（固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回）および 401 自動リフレッシュ処理
  - 取得時刻（fetched_at）を UTC で記録して look-ahead bias を防止

- データベース & スキーマ（DuckDB）
  - Raw / Processed / Feature / Execution（監査含む）を意識したスキーマ設計
  - 冪等的に保存（ON CONFLICT DO UPDATE）
  - インデックス・整合性制約を備えたテーブル群

- ETL パイプライン
  - 差分更新（最終取得日からの差分取得・バックフィル対応）
  - 市場カレンダーの先読み（lookahead）
  - 品質チェック（欠損、スパイク、重複、日付不整合）を実行して問題を収集

- データ品質チェック
  - 欠損データ、急騰／急落（スパイク）、主キー重複、将来日付／非営業日データ検出
  - QualityIssue による検出結果の集約（severity: error / warning）

- 監査ログ（Audit）
  - signal → order_request → executions のトレーサビリティを UUID 連鎖で記録
  - 発注の冪等キー（order_request_id）をサポート
  - すべての TIMESTAMP は UTC 保存

- 設定管理
  - .env / .env.local を自動でプロジェクトルート（.git / pyproject.toml）から読み込み
  - 環境変数をラップした Settings オブジェクトで必須値を明示

---

## 必要条件

- Python 3.10+
  - 型ヒントに `|`（ユニオン）を利用しているため 3.10 以上を想定しています
- 依存パッケージ（主に）
  - duckdb

インストール例（最小）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb
```

プロジェクトをパッケージとしてセットアップする場合は、setup/pyproject を整備して `pip install -e .` を利用してください。

---

## 環境変数（主な設定項目）

KabuSys は環境変数（またはプロジェクトルートの .env/.env.local）を参照します。以下は主な変数と説明です。

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。get_id_token 等で使用。

- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード（発注連携を行う場合）。

- KABU_API_BASE_URL (任意)
  - kabu API のベース URL。デフォルト: http://localhost:18080/kabusapi

- SLACK_BOT_TOKEN (必須 for Slack 通知)
- SLACK_CHANNEL_ID (必須 for Slack 通知)

- DUCKDB_PATH (任意)
  - DuckDB ファイルパス。デフォルト: data/kabusys.duckdb

- SQLITE_PATH (任意)
  - 監視用 SQLite パス（デフォルト: data/monitoring.db）

- KABUSYS_ENV (任意)
  - 実行環境。allowed: development | paper_trading | live（デフォルト: development）

- LOG_LEVEL (任意)
  - ログレベル。DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

- KABUSYS_DISABLE_AUTO_ENV_LOAD (任意)
  - 値を `1` にすると .env 自動読み込みを無効化（テスト時に便利）

注意: Settings クラスは必須項目が欠けている場合に ValueError を投げます（明示的にエラーを出して設定漏れを知らせます）。

---

## セットアップ手順（簡易）

1. リポジトリをクローンして仮想環境を作成
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール
   ```
   pip install duckdb
   ```
   （その他、Slack 連携や kabu API クライアント等を追加する場合は個別パッケージをインストールしてください）

3. 環境変数を用意
   - プロジェクトルートに `.env` を作成するか、環境変数を直接設定します。
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. DuckDB スキーマ初期化
   - Python REPL もしくはスクリプトから初期化します（親ディレクトリは自動作成されます）。
   ```python
   from kabusys.data.schema import init_schema, get_connection
   conn = init_schema("data/kabusys.duckdb")
   # 以降 conn を使って ETL 等を実行
   ```

---

## 使い方（主要な利用例）

以下はライブラリの代表的な使い方例です。

- J-Quants の ID トークンを取得
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を使う
```

- DuckDB スキーマを初期化して日次 ETL を実行
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を省略すると今日
print(result.to_dict())
```

- ETL の各ジョブを個別に実行
```python
from datetime import date
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl

conn = init_schema("data/kabusys.duckdb")
today = date.today()

# カレンダーのみ先読み
run_calendar_etl(conn, today)

# 株価のみ（差分 + backfill default 3日）
run_prices_etl(conn, today)

# 財務のみ
run_financials_etl(conn, today)
```

- 品質チェックの実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)  # 全件チェック
for i in issues:
    print(i)
```

- 監査ログ用スキーマの初期化（既存の connection に追加）
```python
from kabusys.data.audit import init_audit_schema
conn = init_schema("data/kabusys.duckdb")  # 既存 DB
init_audit_schema(conn)  # 監査テーブルを追加
```

ログやエラーは標準的な Python ロギングで出力されます。環境変数 `LOG_LEVEL` でログ出力レベルを変更できます。

---

## ディレクトリ構成（主要ファイル）

以下は本リポジトリの主要なモジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings 管理（.env 自動読み込み含む）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得／保存ロジック）
    - schema.py                    — DuckDB スキーマ定義・初期化
    - pipeline.py                  — ETL パイプライン（差分更新・品質チェック）
    - quality.py                   — データ品質チェック
    - audit.py                     — 監査ログ（audit）スキーマ初期化
    - pipeline.py、audit.py 等が ETL + 監査の主要ロジック
  - strategy/
    - __init__.py                  — 戦略モジュールのエントリ（将来的な拡張）
  - execution/
    - __init__.py                  — 発注・約定処理のエントリ（将来的な拡張）
  - monitoring/
    - __init__.py                  — モニタリング関連（将来的な拡張）

（各ファイルの詳細はソースコード内のドキュメンテーションを参照してください）

---

## 実運用上の注意点 / 設計上のポイント

- レート制限（J-Quants 120 req/min）を厳守するため、jquants_client に固定間隔の RateLimiter を採用しています。高頻度での並列アクセスは避けてください。
- 取得したデータには fetched_at を付与し、いつシステムがそのデータを取得したかを明示しています（look-ahead bias の防止）。
- ETL は Fail-Fast ではなく各ステップごとにエラーを収集して処理を継続します。呼び出し元で ETLResult の errors / quality_issues を見て運用判断を行ってください。
- 監査ログは削除しない前提で設計されています（ON DELETE RESTRICT 等）。履歴トレーサビリティを重視する運用に適しています。
- Settings は必須変数が欠けると例外を投げます。運用前に必須環境変数の設定を確認してください。

---

## 今後の拡張例

- kabuステーション API を用いた実際の発注実装（execution 層）
- Slack 通知や Prometheus との連携によるモニタリング
- 戦略モジュール（strategy）に特徴量計算・スコアリングエンジンを実装
- マルチプロセス／分散 ETL 対応（レート制限に注意）

---

README はここまでです。必要であれば、セットアップスクリプト例、CI 用のコマンド、さらに詳しい API 使用例（関数別のシグネチャや返り値のサンプル）を追加で作成します。どの部分を詳しくしたいか教えてください。