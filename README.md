# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。J-Quants API から市場データ（OHLCV・財務・マーケットカレンダー等）を取得して DuckDB に保存する ETL パイプライン、品質チェック、監査（オーディット）スキーマなどを提供します。

主な用途:
- データ収集（差分取得・バックフィル）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査用の発注／約定ログスキーマ（発注トレース）
- 戦略・実行層の基盤（スキーマ定義・ETL）

---

## 機能一覧

- J-Quants API クライアント（jquants_client）
  - 日次株価（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得
  - レート制限（120 req/min）遵守、リトライ（指数バックオフ）、401 自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で保持（Look-ahead bias 対策）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- DuckDB スキーマ管理（data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - インデックスと外部キーを考慮した順序での作成

- ETL パイプライン（data.pipeline）
  - 日次 ETL（カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック）
  - 差分更新・バックフィル・カレンダー先読みの自動算出
  - 品質チェックを集約して ETL 結果（ETLResult）を返却

- データ品質チェック（data.quality）
  - 欠損データ、主キー重複、価格スパイク、日付不整合（未来日・非営業日）検出
  - 問題は QualityIssue オブジェクトで返却（severity: error/warning）

- 監査ログ（data.audit）
  - シグナル／発注要求／約定の監査テーブル群（UUID ベースのトレーサビリティ）
  - 発注要求は冪等キー（order_request_id）を持ち、UTC タイムスタンプを利用

---

## 要求環境 (推奨)

- Python 3.10+
  - 型ヒントに `X | None` 等の構文を使用しているため Python 3.10 以上を推奨します。
- 依存ライブラリ（例）
  - duckdb
  - （ネットワーク: 標準ライブラリ urllib を使用）
- 任意: Slack 連携用トークンなど

インストール例（仮に requirements.txt を用意する場合）:
```
pip install -r requirements.txt
```
もしくは最低限:
```
pip install duckdb
```

---

## セットアップ手順

1. リポジトリをチェックアウト（あるいはパッケージとしてインストール）。
2. Python と依存ライブラリをインストール。
3. プロジェクトルートに `.env`（および必要なら `.env.local`）を配置して環境変数を設定。
   - パッケージは起動時にプロジェクトルート（.git または pyproject.toml がある階層）を自動検出して `.env` を読み込みます。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
     ※テストなどで使います。

.env に最低限設定が必要なキー（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

例 `.env`:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（基本例）

以下は最小限の実行例です。DuckDB スキーマを初期化して日次 ETL を実行します。

Python スクリプト例:
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（ファイル: data/kabusys.duckdb を作成）
conn = init_schema("data/kabusys.duckdb")

# 日次 ETL を実行（target_date を省略すると今日）
result = run_daily_etl(conn)

# 結果を辞書化して表示
print(result.to_dict())
```

監査ログ用スキーマを追加する場合:
```python
from kabusys.data.audit import init_audit_schema
# conn は init_schema で得た接続
init_audit_schema(conn)
```

J-Quants の API を直接使って取得したい場合（テスト等）:
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

token = get_id_token()  # settings からリフレッシュトークンを利用
records = fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,1,31))
```

注意点:
- jquants_client は内部でレート制御、リトライ、401 自動リフレッシュを行います。
- save_* 系関数は DuckDB に対して冪等に保存します（ON CONFLICT DO UPDATE）。

---

## よく使う API 概要

- data.schema.init_schema(db_path)
  - DuckDB のスキーマを初期化して接続を返す（冪等）。

- data.schema.get_connection(db_path)
  - 既存 DB に接続（スキーマ初期化は行わない）。

- data.jquants_client.get_id_token(refresh_token=None)
  - リフレッシュトークンから idToken を取得。

- data.jquants_client.fetch_daily_quotes(...)
  - 日足データをページネーション対応で取得。

- data.jquants_client.save_daily_quotes(conn, records)
  - raw_prices に保存（ON CONFLICT DO UPDATE）。

- data.pipeline.run_daily_etl(conn, target_date=None, ...)
  - 日次 ETL（カレンダー→株価→財務→品質チェック）を実行し ETLResult を返す。

- data.quality.run_all_checks(conn, target_date=None, reference_date=None, ...)
  - 品質チェックをまとめて実行し QualityIssue のリストを返す。

- data.audit.init_audit_schema(conn) / init_audit_db(db_path)
  - 監査ログ用テーブルを初期化。

---

## 実運用時の注意事項

- 環境変数やシークレットは .env/.env.local や外部シークレット管理で適切に管理してください。
- J-Quants のレート制限（120 req/min）を必ず守る設計になっていますが、運用側でも API 呼び出し頻度に注意してください。
- KABUSYS_ENV を `live` に設定すると実行ロジック（将来的な実装想定）で実売買モードになる場合があるため注意して運用してください。
- DuckDB ファイルは単一プロセスでのアクセスを前提としています。分散アクセスや高頻度書込が必要なら運用設計を検討してください。

---

## ディレクトリ構成

リポジトリの主要なファイル/ディレクトリ構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数・設定管理（.env 自動ロード）
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（取得・保存ロジック）
    - schema.py              # DuckDB スキーマ定義と初期化
    - pipeline.py            # ETL パイプライン（差分更新・品質チェック）
    - audit.py               # 監査ログ（発注→約定トレーサビリティ）
    - quality.py             # データ品質チェック
  - strategy/
    - __init__.py            # 戦略コード（別途実装）
  - execution/
    - __init__.py            # 発注・ブローカー接続（別途実装）
  - monitoring/
    - __init__.py            # 監視 / メトリクス（別途実装）

---

## 開発・拡張

- 戦略層（strategy）・実行層（execution）・監視（monitoring）はインターフェースを整備済みで、個別戦略やブローカー実装を追加できます。
- ETL の単体テストは id_token を注入して行えるように設計されています（テスト容易性を確保）。
- 品質チェックは Fail-Fast ではなく全件収集を行う設計なので、UI やアラートのトリガー実装が容易です。

---

フィードバックや拡張提案があればお知らせください。README の加筆やサンプルスクリプト、運用手順（cron/コンテナ化/CI）などのドキュメントも作成できます。