# KabuSys

日本株向けの自動売買 / データプラットフォーム基盤ライブラリです。  
J-Quants API からマーケットデータ・財務データ・カレンダーを取得し、DuckDB に整備・保存、品質チェックや監査ログ（トレーサビリティ）用のスキーマを提供します。戦略・発注・監視コンポーネントと連携して自動売買システムの基盤として利用できます。

---

## 主な特徴（Features）

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPXマーケットカレンダーの取得
  - API レート制限（120 req/min）対応のレートリミッタ
  - リトライ（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ対応
  - 取得時刻（fetched_at）をUTCで記録し Look‑ahead bias を抑制

- ETL パイプライン（差分更新）
  - 差分（未取得分）＋バックフィル（デフォルト 3 日）で API から差分のみ取得
  - カレンダー先読み（デフォルト 90 日）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- DuckDB スキーマ定義
  - Raw / Processed / Feature / Execution（および監査）レイヤーを含むテーブル群
  - 頻出クエリに対するインデックスを作成

- 品質チェック（quality）
  - 欠損データ、主キー重複、スパイク（前日比）、
    日付不整合（未来日付、非営業日のデータ）検出
  - 各チェックは QualityIssue のリストを返し、重大度に応じたハンドリングが可能

- 監査ログ（audit）
  - シグナルから発注・約定までを UUID 連鎖でトレース可能にする監査テーブル群
  - 発注の冪等キー（order_request_id）やタイムスタンプ（UTC）を扱う

- 設定管理
  - .env / .env.local / OS 環境変数から設定を自動ロード（プロジェクトルート判定）
  - 必要な環境変数の取得を Settings クラスで一元化
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## セットアップ手順

前提:
- Python 3.9+（コードは型注釈に Python 3.10 の型合体等を使用しているため、3.10 以上を推奨します）
- duckdb（DuckDB Python パッケージ）

例:

1. リポジトリをクローン（既にコードがある場合は不要）
   git clone <your-repo>

2. 仮想環境作成・有効化（任意）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   pip install duckdb

   ※ プロジェクトが pyproject.toml / setup.cfg を持つ場合は
   pip install -e . 
   を実行してローカルインストールしてください。

4. 環境変数（.env）を用意
   プロジェクトルート（.git または pyproject.toml の親ディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   必須例（.env）:
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   オプション（デフォルト値あり）:
   KABUSYS_ENV=development  # development / paper_trading / live
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_DISABLE_AUTO_ENV_LOAD=0

---

## 使い方（基本的な例）

ここでは Python から主要機能を使うサンプルを示します。

1) DuckDB スキーマ初期化（1回だけ行う）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 監査ログ用スキーマ初期化（既存接続に追加）
```python
from kabusys.data.audit import init_audit_schema
# 上で作成した conn を使う
init_audit_schema(conn)
```

3) J-Quants からデータ取得して保存（低レベル）
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings

id_token = jq.get_id_token()  # settings.jquants_refresh_token を利用して取得
records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2023,1,1), date_to=date(2023,12,31))
jq.save_daily_quotes(conn, records)
```

4) 日次 ETL（高レベル）：差分取得・保存・品質チェックを一括で実行
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定しなければ今日
print(result.to_dict())
```

5) 品質チェック単体実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

注意点:
- run_daily_etl は内部で market_calendar を先に取得して営業日調整を行います。
- J-Quants の ID トークンは内部でキャッシュされ、必要時に自動でリフレッシュされます（401 時に一度のみリトライ）。
- DuckDB ファイルパスは settings.duckdb_path（デフォルト data/kabusys.duckdb）を利用できます。

---

## 環境変数一覧（Settings）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャネル ID

任意 / デフォルトあり:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) (default: development)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) (default: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env 自動ロードを無効化

.env の自動読み込みは、プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行われます。

---

## ディレクトリ構成

ソースツリー（主要ファイル）:

src/
  kabusys/
    __init__.py             # パッケージ初期化、公開モジュール一覧
    config.py               # 環境設定・.env 自動ロード・Settings クラス
    data/
      __init__.py
      jquants_client.py     # J-Quants API クライアント（取得 + 保存関数）
      schema.py             # DuckDB スキーマ定義と初期化ロジック
      pipeline.py           # ETL パイプライン（差分取得・品質チェック）
      audit.py              # 監査ログ（シグナル→発注→約定トレーサビリティ）
      quality.py            # データ品質チェック（欠損・スパイク・重複・日付不整合）
      pipeline.py
    strategy/
      __init__.py           # 戦略関連モジュール置き場（未実装ファイルあり）
    execution/
      __init__.py           # 発注/実行関連モジュール置き場（未実装ファイルあり）
    monitoring/
      __init__.py           # 監視・メトリクス関連（未実装ファイルあり）

主要モジュールの役割:
- kabusys.config: 環境変数読み込み、Settings による設定アクセス
- kabusys.data.jquants_client: API 呼び出し、レート制御、リトライ、DuckDB への保存
- kabusys.data.schema: DuckDB テーブル群とインデックスを作成する init_schema/get_connection
- kabusys.data.pipeline: 差分 ETL と品質チェックの統合エントリポイント
- kabusys.data.quality: データ品質の各チェック実装
- kabusys.data.audit: 監査テーブル（signal / order_request / execution）定義・初期化

---

## 運用上の補足

- レート制限とリトライ:
  J-Quants の API レート制限（120 req/min）を満たすためモジュール内で固定間隔のスロットリングを行っています。429 や 5xx 発生時は指数バックオフでリトライします。429 の場合は Retry‑After ヘッダを優先します。

- 冪等性:
  DuckDB への保存は ON CONFLICT DO UPDATE を用いて冪等性を担保しています。ETL は再実行可能です。

- ロギング:
  設定の LOG_LEVEL によりログ出力レベルを制御してください。コード内で logger を利用して詳細な実行ログを出力します。

- テストと自動化:
  ETL の呼び出しや品質チェックは引数に id_token を注入できるため、モックトークンを渡してユニットテストが行いやすく設計されています。

---

必要であれば、README に以下の追加情報を追記できます:
- 例となる .env.example ファイル
- CI / デプロイ手順（Docker / systemd / cron）
- 典型的な運用フロー（ETL のスケジューリング、監査ログの確認、アラート設定）
- 具体的な SQL サンプルや DuckDB のクエリ例

追記希望があれば教えてください。