# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）です。  
J-Quants / kabuステーション などから市場データを取得して DuckDB に蓄積し、品質チェック・特徴量作成・発注監査までを想定したデータプラットフォーム／ETL の基盤を提供します。

## プロジェクト概要
- J-Quants API から株価（OHLCV）、財務データ、JPXマーケットカレンダーを取得して DuckDB に保存する ETL パイプラインを実装。
- API レート制御・リトライ・トークン自動リフレッシュや、データ保存の冪等性（ON CONFLICT DO UPDATE）に対応。
- データ品質チェック（欠損・スパイク・重複・日付不整合）を実行し問題を収集。
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマを提供。
- 将来的な戦略層 / 実行層 / モニタリングとの接続を想定したモジュール構成。

## 主な機能一覧
- J-Quants クライアント（jquants_client）
  - 日足（OHLCV）、財務データ、マーケットカレンダーの取得（ページネーション対応）
  - レートリミッター、指数バックオフリトライ、401時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録
- DuckDB スキーマ管理（data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - インデックス作成、冪等的初期化
- ETL パイプライン（data.pipeline）
  - 差分更新（最終取得日を基に未取得範囲を自動算出）
  - backfill による後出し修正吸収
  - 日次 ETL の統合エントリポイント（run_daily_etl）
- 品質チェック（data.quality）
  - 欠損、スパイク（前日比）、重複、日付不整合チェック
  - 問題を QualityIssue として収集
- 監査ログ（data.audit）
  - signal_events / order_requests / executions の監査スキーマ
  - UUID ベースのトレーサビリティと冪等キー設計

## 要件
- Python 3.10+
- 依存パッケージ（最低限）:
  - duckdb

（network 標準ライブラリは urllib を使用しているため追加依存は少なめです。プロジェクトの他の部分でさらにパッケージが必要になる可能性があります。）

## セットアップ手順

1. リポジトリをクローン
   - git clone <your-repo-url>

2. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb
   - （開発中であれば `pip install -e .` などでローカルインストール）

4. 環境変数設定
   - プロジェクトルート（.git や pyproject.toml がある場所）に `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須の環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD      : kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN        : Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID       : Slack チャンネル ID（必須）
   - オプション（デフォルト値あり）:
     - KABUSYS_ENV            : 実行環境 (development | paper_trading | live)、デフォルト `development`
     - LOG_LEVEL              : ログレベル（DEBUG/INFO/...）、デフォルト `INFO`
     - KABUS_API_BASE_URL     : kabu API のベース URL（デフォルトローカル）
     - DUCKDB_PATH            : DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
     - SQLITE_PATH            : モニタリングDB 等（デフォルト `data/monitoring.db`）

   例: .env の最小テンプレート
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password_here
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

## 使い方（基本例）

以下は Python から各機能を利用する例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# ファイル DB を初期化（親ディレクトリがなければ自動作成）
conn = init_schema("data/kabusys.duckdb")
```

2) 監査ログスキーマの初期化（既存接続に追加）
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)  # conn は init_schema の戻り値
```

3) 日次 ETL の実行（デフォルトで今日を対象）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

4) J-Quants から日足データのみ取得して保存（低レベル）
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
saved = jq.save_daily_quotes(conn, records)
print(f"fetched={len(records)} saved={saved}")
```

5) 品質チェックの実行
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

注意:
- run_daily_etl は内部で市場カレンダー → 株価 → 財務 → 品質チェックの順に実行します。各ステップは独立エラーハンドリングされ、失敗があっても他のステップを継続します（結果オブジェクトに errors を集約します）。
- J-Quants の ID トークンは自動でリフレッシュされ、モジュール内でキャッシュされます。必要に応じて get_id_token を直接呼べます。

## ディレクトリ構成（主要ファイル）
（リポジトリ内の src/kabusys を基点に記載）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得・保存ロジック）
    - schema.py                    — DuckDB スキーマ定義と初期化
    - pipeline.py                  — ETL パイプライン（差分更新 / run_daily_etl）
    - quality.py                   — データ品質チェック
    - audit.py                     — 監査ログ（signal/order/execution）スキーマ
    - audit.py / init_audit_db     — 監査専用 DB 初期化ユーティリティ
  - strategy/
    - __init__.py                  — 戦略層のエントリ（将来拡張）
  - execution/
    - __init__.py                  — 発注・実行層のエントリ（将来拡張）
  - monitoring/
    - __init__.py                  — 監視 / メトリクス（将来拡張）

## 運用上の留意点
- API レート制限（J-Quants: 120 req/min）を守る実装が入っていますが、同時実行するプロセスがある場合は全体で制御する必要があります。
- DuckDB は単一プロセスでの書き込みが安全で、複数プロセスの同時書き込みは注意が必要です（運用時は単一 ETL ワーカー／ロック管理等を検討してください）。
- すべてのタイムスタンプは UTC を想定しています（監査スキーマは明示的に TimeZone='UTC' を設定します）。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml がある場所）から行われます。テスト実行時など自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

## 開発・拡張
- 戦略（strategy）・発注実行（execution）・監視（monitoring）はプレースホルダを用意しています。ここにアルゴリズムやブローカー接続ロジック、監視ダッシュボード連携を実装してください。
- ETL のユニットテスト作成時は settings の自動 env ロードを無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）してテスト専用設定を注入すると良いです。
- 追加の外部依存（例えば Slack 通知、HTTP クライアント、バックグラウンドスケジューラ等）は要件に応じて導入してください。

---

この README はコードベースの主要機能・利用方法をまとめたものです。実際のデプロイ／運用では API トークンの管理、監査ログの永続性、冗長化、運用監視などを適切に設計してください。必要であれば README を拡張してデプロイ手順や運用ガイドを追加できます。