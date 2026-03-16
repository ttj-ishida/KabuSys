# KabuSys

日本株向け自動売買基盤の一部を実装した Python パッケージです。  
主にデータ取得（J-Quants API）、DuckDB スキーマ定義・初期化、データ保存、データ品質チェック、監査ログ（トレーサビリティ）を提供します。

## プロジェクト概要
- J-Quants API を用いて株価（日足）、財務データ、JPX マーケットカレンダーを取得
- 取得データを DuckDB に永続化（冪等性を考慮した保存）
- DuckDB のスキーマを 3 層（Raw / Processed / Feature）＋ Execution / Audit 層で定義・初期化
- データ品質チェック（欠損・異常値・重複・日付不整合）
- 監査ログ（signal → order_request → execution）を保持し、発注フローのトレーサビリティを担保
- 環境変数を .env / .env.local から自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）

## 主な機能一覧
- data/jquants_client.py
  - get_id_token(): リフレッシュトークンから ID トークンを取得
  - fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar(): ページネーション対応でデータ取得
  - save_daily_quotes(), save_financial_statements(), save_market_calendar(): DuckDB に冪等的に保存
  - 内部で 120 req/min のレート制限とリトライ（指数バックオフ、401 の自動リフレッシュ等）を実施
- data/schema.py
  - init_schema(db_path): DuckDB の全テーブルとインデックスを作成（冪等）
  - get_connection(db_path): 既存 DB へ接続
- data/audit.py
  - init_audit_schema(conn) / init_audit_db(db_path): 監査ログ用テーブルとインデックスを作成
  - 監査テーブルには UUID ベースの冪等キーと created_at/updated_at を想定
- data/quality.py
  - check_missing_data(), check_spike(), check_duplicates(), check_date_consistency(), run_all_checks()
  - 問題は QualityIssue のリストで返却（error / warning を区別）
- config.py
  - .env 自動読み込み（.env, .env.local）、必須設定の取得ラッパー（Settings クラス）
  - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可

## 要求環境 / 依存パッケージ（例）
- Python 3.10+（型アノテーションに | を使用）
- duckdb
- （標準ライブラリで urllib 等を使用）
※ 実際のセットアップ用の requirements.txt / pyproject.toml はプロジェクトに応じて用意してください。

## セットアップ手順（例）
1. リポジトリをクローン / ダウンロード
2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb
   - あるいはプロジェクトに pyproject.toml / requirements.txt があれば pip install -e . / pip install -r requirements.txt
4. 環境変数を設定
   - プロジェクトルートに `.env`（および必要に応じて `.env.local`）を作成すると自動読み込みされます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

## 必要な環境変数（Settings が要求するもの）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション API パスワード（必須）
- KABU_API_BASE_URL : kabu API ベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN : Slack ボットトークン（必須）
- SLACK_CHANNEL_ID : Slack チャンネル ID（必須）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : SQLite ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV : 実行環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

例 .env (最小)
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

## 使い方（簡単なコード例）

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ファイル DB を作成し接続を返す
# またはメモリ DB:
# conn = init_schema(":memory:")
```

- J-Quants から日足を取得して保存する（例）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# 明示的にトークンを取得する場合（省略可。モジュールキャッシュが自動で扱います）
id_token = get_id_token()

records = fetch_daily_quotes(id_token=id_token, code="7203", date_from=None, date_to=None)
n = save_daily_quotes(conn, records)
print(f"{n} 件保存しました")
```

- 財務データやカレンダーも同様に fetch_* と save_* を使用できます。

- データ品質チェックを実行する
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=None)
for issue in issues:
    print(issue.check_name, issue.severity, issue.detail)
    for row in issue.rows:
        print(row)
```

- 監査ログ用 DB 初期化（監査専用 DB を使う場合）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```
または既存の conn に監査テーブルを追加:
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)  # conn は init_schema() で初期化した接続
```

## 実装上の注意点 / 挙動
- .env 自動読み込み
  - プロジェクトルートを `.git` または `pyproject.toml` を起点に探し、見つかれば `.env`（読み込み優先度低）→ `.env.local`（上書き）を順に読み込みます。
  - OS 環境変数は上書きされません（`.env.local` は override=True だが OS 環境変数は protected）。
  - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットします。
- J-Quants API クライアント
  - レート制限: 120 req/min（内部で固定間隔スロットリングを実装）
  - リトライ: ネットワークエラーや 408/429/5xx に対して最大 3 回のリトライ（指数バックオフ）。429 の場合は Retry-After を優先。
  - 401 Unauthorized を受けた場合は refresh token で ID トークンを自動更新して 1 回だけリトライ
  - 取得日時（fetched_at）は UTC で記録し、Look-ahead Bias の追跡に活用可能
- DuckDB への保存
  - INSERT は ON CONFLICT DO UPDATE を用いて冪等性を保つ（重複挿入時は更新）
  - テーブルやインデックスは init_schema() で冪等的に作成される
- データ品質チェック
  - すべてのチェックは検出された問題をリストで返す（Fail-Fast ではなく全件収集）
  - 呼び出し元で重大度を見て処理を止めるかどうかを判断する設計

## ディレクトリ構成
（リポジトリの一部ファイルを抜粋）
```
src/
  kabusys/
    __init__.py
    config.py
    data/
      __init__.py
      jquants_client.py
      schema.py
      audit.py
      quality.py
      (other data modules...)
    strategy/
      __init__.py
      (戦略関連コードを配置)
    execution/
      __init__.py
      (発注・ブローカー連携コードを配置)
    monitoring/
      __init__.py
```

主要ファイル:
- src/kabusys/config.py : 環境変数管理 (.env 読み込み・Settings)
- src/kabusys/data/jquants_client.py : J-Quants API クライアント（取得・保存ロジック）
- src/kabusys/data/schema.py : DuckDB スキーマ定義・初期化
- src/kabusys/data/audit.py : 監査ログ用テーブル定義と初期化
- src/kabusys/data/quality.py : データ品質チェック

## よくある質問 / トラブルシュート
- .env が読み込まれない
  - プロジェクトルートが `.git` 或いは `pyproject.toml` の場所を基準に検出されます。パッケージ配布後やテスト環境などで自動検出が不要な場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自前で環境変数をセットしてください。
- J-Quants への接続が 401 を返す
  - リフレッシュトークンが不正または期限切れの可能性があります。`JQUANTS_REFRESH_TOKEN` を確認してください。
- DuckDB の初期化時に権限エラーやディレクトリがない
  - init_schema は親ディレクトリが存在しない場合に自動作成しますが、OS 権限やパスが正しいか確認してください。

---

その他の機能（発注実行、ポジション管理、監視連携など）は strategy / execution / monitoring 以下に実装予定／拡張可能です。README の内容はコードベースからの抜粋説明です。使用時はユースケースに合わせて環境設定・ログ設定・例外ハンドリングを追加してください。