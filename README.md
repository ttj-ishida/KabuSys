# KabuSys

日本株自動売買システムのコアライブラリ群（データ収集・ETL・品質チェック・監査ログ基盤など）

このリポジトリは、J-Quants や kabuステーション 等の外部 API からデータを取得して DuckDB に格納し、ETL／品質チェック／ニュース収集／マーケットカレンダー管理／監査ログ基盤を提供する Python モジュール群です。戦略・約定部分の骨格を含みつつ、データ基盤と運用用ユーティリティを中心に実装されています。

## 主な機能

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務（BS/PL）、JPX マーケットカレンダーの取得
  - レートリミット制御（120 req/min）、リトライ（指数バックオフ）、トークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し Look‑ahead Bias を抑制
  - DuckDB への冪等保存（ON CONFLICT）

- ニュース収集（RSS）
  - RSS フィード取得、前処理（URL除去・空白正規化）、ID（正規化URLのSHA-256先頭32文字）による冪等保存
  - SSRF / XML Bomb 対策（スキーム検証、プライベートIPチェック、defusedxml、レスポンスサイズ制限）
  - 銘柄コード抽出と news_symbols への紐付け

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義と初期化関数
  - インデックスと外部キーを含む冪等な初期化

- ETL パイプライン
  - 差分更新（最終取得日からバックフィル）、カレンダー先読み、自動営業日調整
  - 品質チェック（欠損・重複・スパイク・日付不整合）を実行するフロー

- マーケットカレンダー管理
  - JPX カレンダーの夜間差分更新ジョブと営業日判定ユーティリティ（next/prev/get/is_sq_day 等）

- 監査ログ（Audit）
  - シグナル→発注→約定 のトレーサビリティを確保する監査用テーブル群（UUIDベース／冪等キー／UTCタイムスタンプ）

## 動作要件

- Python 3.10 以上（PEP 604 の型表記（|）などを使用）
- 必要な Python パッケージ（例）
  - duckdb
  - defusedxml
  - （標準ライブラリの urllib 等を使用）
- ネットワークアクセス（J-Quants API、RSS フィード等）

※実際の運用では外部 API の利用に応じた認証情報およびネットワーク環境が必要です。

## セットアップ手順

1. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （開発パッケージがある場合は requirements.txt / pyproject.toml があればそれに従ってください）
   - ローカル開発インストール（パッケージとして使う場合）
     - pip install -e .

3. 環境変数 / .env の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を配置すると自動で読み込みます。
   - 自動ロードを無効にする場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で有用）。
   - 必須の環境変数（少なくとも以下を設定してください）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に利用）
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - 任意 / デフォルト
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

   .env の書式は一般的な KEY=VALUE 形式に対応し、export プレフィックスやクォート・コメントを扱えます（config._parse_env_line を参照）。

4. DuckDB スキーマ初期化
   - Python から init_schema を呼んでデータベースとテーブルを作成します（親ディレクトリがなければ自動作成されます）。

例:
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

また監査ログ専用に初期化する場合:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

## 使い方（主要 API / 実行例）

- 設定値へのアクセス
```python
from kabusys.config import settings
token = settings.jquants_refresh_token
is_live = settings.is_live
duckdb_path = settings.duckdb_path
```

- DuckDB スキーマ初期化（既述）
```python
from kabusys.data import schema
conn = schema.init_schema(settings.duckdb_path)
```

- 日次 ETL を実行する（株価・財務・カレンダー取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
from kabusys.data import schema

conn = schema.get_connection(settings.duckdb_path)  # 事前に init_schema を実行していること
result = run_daily_etl(conn)  # target_date を指定して任意日を処理可能
print(result.to_dict())
```

- ニュース収集（RSS）ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.get_connection(settings.duckdb_path)
# sources のフォーマット: {"source_name": "https://.../feed.xml"}
results = run_news_collection(conn)
print(results)  # {source_name: 新規保存件数}
```

- マーケットカレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("saved calendar rows:", saved)
```

- 品質チェック単体実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

- J-Quants クライアント直接呼び出し（トークン指定可）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
id_token = get_id_token()  # settings.jquants_refresh_token を使用して ID トークンを取得
records = fetch_daily_quotes(id_token=id_token, code="7203", date_from=..., date_to=...)
```

注意: 各 API 呼び出しはレート制限やリトライ、401時の自動リフレッシュなどに配慮して実装されています。長時間の連続取得では J-Quants の利用規約・レート制限に従ってください。

## ディレクトリ構成

プロジェクトの主要なファイル配置（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数/設定管理
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得/保存/リトライ/レート制限）
    - news_collector.py         — RSS ベースのニュース収集と DB 保存
    - schema.py                 — DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py    — マーケットカレンダー管理ユーティリティと更新ジョブ
    - audit.py                  — 監査ログ用テーブル定義と初期化
    - quality.py                — データ品質チェック
  - strategy/
    - __init__.py                — 戦略関連のエクスポート領域（拡張ポイント）
  - execution/
    - __init__.py                — 約定/発注関連（拡張ポイント）
  - monitoring/
    - __init__.py                — 監視関連（拡張ポイント）

（README はこの抜粋に基づくため、実際のリポジトリに他のファイルやドキュメントがある場合があります）

## 実運用での留意点

- 認証情報（トークン・パスワード）は厳格に管理してください（Git にコミットしない、Secrets 管理を利用する等）。
- J-Quants の API レート制限や利用規約を順守してください。本ライブラリは 120 req/min を想定したスロットリングを実装していますが、運用環境に合わせて調整してください。
- DuckDB ファイルのバックアップ・ローテーションを考慮してください（データ量や永続性要件による）。
- RSS フィードの取得は外部ネットワークに依存するため、タイムアウトやエラーハンドリングを監視してください。
- 品質チェックは警告/エラーを返しますが、運用ポリシーに従って自動停止するか通知するかを設計してください。

## 開発と拡張

- strategy / execution / monitoring パッケージは拡張ポイントです。戦略ロジックや約定ドライバ、監視アダプタをここに実装して統合してください。
- テストを書く際は環境変数の自動ロードを無効にする `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使うと良いです。
- ネットワークアクセス部分（news_collector._urlopen など）はテストでモック可能に設計されています。

---

不明点や README に追加してほしいサンプル（例: CI ワークフロー、より詳しい .env.example、運用チェックリスト）があれば教えてください。README を用途に合わせて拡張します。