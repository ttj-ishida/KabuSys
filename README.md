# KabuSys

日本株向け自動売買基盤（データ収集・ETL・品質チェック・監査ログ基盤）の軽量実装です。  
主に J-Quants API や RSS を取り込み、DuckDB に冪等に保存し、戦略や実行レイヤへ提供するための基盤コンポーネントを含みます。

注意: このリポジトリはフレームワーク／ライブラリ層の実装であり、ブローカー連携や実運用用の完全なオーケストレーションは含みません。

## 主な特徴（機能一覧）
- 環境変数管理
  - プロジェクトルートの `.env` / `.env.local` を自動読込（必要に応じ無効化可能）
  - 必須設定はアクセス時に検証
- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - 日足・財務・マーケットカレンダー取得（ページネーション対応）
  - レートリミット（120 req/min）と指数バックオフによるリトライ
  - 401 時の自動トークンリフレッシュ
  - DuckDB へ冪等保存（ON CONFLICT 句を使用）
  - 取得時刻（fetched_at）を UTC で記録（Look-ahead Bias 対策）
- ニュース収集 (`kabusys.data.news_collector`)
  - RSS フィード取得・前処理（URL除去、空白正規化等）
  - URL 正規化と記事ID（SHA-256）による冪等保存
  - defusedxml による XML 攻撃対策、SSRF 対策、受信サイズ制限
  - DuckDB へのトランザクションまとめ挿入（INSERT ... RETURNING）
  - テキストから銘柄コード抽出（4桁）
- データスキーマ管理 (`kabusys.data.schema`)
  - Raw / Processed / Feature / Execution 層を含む DuckDB DDL
  - スキーマ初期化関数（init_schema, init_audit_db）
- ETL パイプライン (`kabusys.data.pipeline`)
  - 差分更新（最終取得日 + backfill）による取得
  - カレンダー先読み、株価・財務データの差分取得と保存
  - 品質チェック実行（`kabusys.data.quality`）
  - 日次 ETL の統合エントリポイント（run_daily_etl）
- カレンダー管理 (`kabusys.data.calendar_management`)
  - 営業日判定、次/前営業日取得、期間内営業日列挙
  - JPX カレンダー夜間バッチ更新ジョブ
- 監査ログ（Audit） (`kabusys.data.audit`)
  - シグナル → 発注リクエスト → 約定 に至るトレーサビリティ用テーブル群
  - Order request の冪等キー管理、UTC タイムゾーン固定
- 品質チェック (`kabusys.data.quality`)
  - 欠損・重複・スパイク・日付不整合の検出
  - 各チェックは QualityIssue リストで結果を返す（error/warning）

なお、`kabusys.strategy`, `kabusys.execution`, `kabusys.monitoring` は現在パッケージ置き場（初期化ファイルのみ）として用意されています。

## 要求環境 / 依存パッケージ
- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - defusedxml

インストール例:
- 仮想環境作成・有効化（省略可）
  - python -m venv .venv
  - source .venv/bin/activate
- パッケージのインストール（プロジェクトを editable install する場合）
  - pip install duckdb defusedxml
  - pip install -e .

（プロジェクトとして配布する場合は requirements.txt / pyproject.toml を用意してください）

## セットアップ手順

1. リポジトリをクローンし、仮想環境を用意する
   - git clone ...
   - python -m venv .venv && source .venv/bin/activate

2. 依存パッケージをインストール
   - pip install duckdb defusedxml

3. 環境変数の設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成するか、環境変数を直接設定してください。
   - 自動で .env を読み込む機能は有効（デフォルト）。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

.env の例（最低限必要な値）:
```
# J-Quants API
JQUANTS_REFRESH_TOKEN=あなたの_refresh_token

# kabuステーション（必要なら）
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack 通知（必要なら）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# DB パス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

4. DuckDB スキーマ初期化
   - Python からスキーマを作成します（`data/schema.init_schema` を使用）。
   - 例:
     ```
     from kabusys.config import settings
     from kabusys.data.schema import init_schema

     conn = init_schema(settings.duckdb_path)
     ```

## 使い方（代表的なコード例）

- 設定値の利用:
  ```
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  ```

- DB スキーマの初期化（DuckDB）:
  ```
  from kabusys.config import settings
  from kabusys.data.schema import init_schema

  conn = init_schema(settings.duckdb_path)
  ```

- 日次 ETL を実行する:
  ```
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- ニュース収集ジョブ:
  ```
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  # known_codes は銘柄抽出に使う有効銘柄コードのセット（None なら紐付けスキップ）
  stats = run_news_collection(conn, known_codes={'7203','6758'})
  print(stats)
  ```

- J-Quants の ID トークン取得・個別 API 呼び出し:
  ```
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes

  id_token = get_id_token()  # settings の refresh token を使用
  data = fetch_daily_quotes(id_token=id_token, date_from=..., date_to=...)
  ```

## 設計上の注意 / テスト時ヒント
- 自動 .env 読込はプロジェクトルート（.git または pyproject.toml を探索）を基準に行います。テストや CI で明示的に制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- news_collector._urlopen はテストでモック可能です（外部ネットワークアクセスの代替）。
- jquants_client の API 呼び出しはレート制限・リトライ・トークンリフレッシュのロジックを含むため、実 HTTP 呼出しの単体テストではモックを推奨します。
- DuckDB への接続は `init_schema`（スキーマ作成）と `get_connection`（既存 DB への接続）を使い分けてください。
- 型ヒントや union 型（X | Y）を多用しているため Python 3.10 以上を推奨します。

## ディレクトリ構成
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py        - パッケージ初期化・バージョン
  - config.py          - 環境変数／設定管理（.env 自動読込、Settings）
  - data/
    - __init__.py
    - jquants_client.py - J-Quants API クライアント（取得＋DuckDB保存）
    - news_collector.py - RSS 収集・前処理・DB 保存・銘柄紐付け
    - schema.py         - DuckDB スキーマ定義と初期化関数
    - pipeline.py       - ETL パイプライン（差分取得・保存・品質チェック）
    - calendar_management.py - 市場カレンダー管理・営業日ロジック
    - audit.py          - 監査ログ用テーブル定義と初期化
    - quality.py        - データ品質チェック
  - strategy/
    - __init__.py       - 戦略層（拡張用）
  - execution/
    - __init__.py       - 発注・約定関連（拡張用）
  - monitoring/
    - __init__.py       - モニタリング用（拡張用）

## 追加情報
- ログレベルは環境変数 `LOG_LEVEL`（デフォルト: INFO）で制御します。
- 実運用でのブローカー連携（注文送信・約定処理）、継続実行（cron / Airflow 等）、監視・アラートは本ライブラリを組み合わせて別途構築してください。
- 本リポジトリのコードは基盤部分を示すものであり、実運用に移す際はセキュリティ（API トークン管理、ネットワーク制御）、テスト、監査要件を十分に検討してください。

---

問題点の報告や改善提案があれば README の追記・コード修正を歓迎します。