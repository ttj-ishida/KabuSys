# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）のREADME。  
このリポジトリはデータ取得・永続化・品質チェック・監査ログなどを備えた、戦略開発と実運用のための基盤モジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API からの市場データ取得（OHLCV、財務情報、JPXカレンダー）
- DuckDB を用いたデータスキーマ（Raw / Processed / Feature / Execution 層）の定義と初期化
- 監査ログ（シグナル→発注→約定のトレーサビリティ）テーブルの定義
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- 設定は環境変数 / .env ファイルから管理（自動ロード機能）

設計上の特徴：
- J-Quants API はレート制限（120 req/min）を尊重する RateLimiter を内蔵
- リトライ（指数バックオフ）と 401 時の自動トークンリフレッシュを実装
- DuckDB への書き込みは冪等（ON CONFLICT DO UPDATE）を意識
- すべてのタイムスタンプは UTC を想定

---

## 機能一覧

- data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ保存、冪等）
  - get_id_token（refresh token から id_token を取得）
  - レート制御・リトライ・トークン自動更新

- data.schema
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) による初期化と接続取得
  - get_connection(db_path)（既存 DB への接続）

- data.audit
  - 監査ログ（signal_events / order_requests / executions）DDL と初期化関数
  - init_audit_schema(conn) / init_audit_db(path)

- data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks で一括実行し QualityIssue のリストを返す

- config
  - .env または環境変数から設定を読み込み（自動ロード機能）
  - Settings クラス経由で各種設定にアクセス（例: settings.jquants_refresh_token）
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に .env → .env.local を適用
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化

---

## 前提 / 必要要件

- Python 3.10+
  - （ソースに | 型注釈を使用しているため 3.10 以上を推奨）
- 必要な Python パッケージ（最小）
  - duckdb
- ネットワークアクセス（J-Quants API へ接続する場合）
- 必要な環境変数（後述）

※ 実際のプロジェクトでは requirements.txt / Poetry 等で依存管理してください。

---

## 環境変数（必須/任意）

主要な環境変数（.env に設定して使用）:

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD    : kabuステーション API のパスワード
- SLACK_BOT_TOKEN      : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID     : Slack チャンネル ID

任意（デフォルト値あり）:
- KABU_API_BASE_URL    : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH          : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH          : SQLite（監視等）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV          : 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL            : ログレベル ("DEBUG","INFO",...)（デフォルト: INFO）

自動ロードについて:
- リポジトリルートの .env を自動で読み込み、続いて .env.local を上書き読み込みします（OS 環境変数は保護されます）。
- 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（ローカル開発向け）

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

2. 依存パッケージをインストール
   - pip install duckdb
   - （必要に応じて他のパッケージを追加）

3. リポジトリをインストール（開発モード）
   - python -m pip install -e .

4. 環境変数を用意
   - プロジェクトルートに .env を作成し、上記必須キーを設定
   - 例（.env）:
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678

5. DuckDB スキーマ初期化（例）
   - Python インタプリタまたはスクリプトから schema.init_schema を呼ぶ（下記参照）

---

## 使い方（簡単なコード例）

- スキーマ初期化と接続取得

```python
from kabusys.data import schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
# 既存 DB に接続する場合:
# conn = schema.get_connection(settings.duckdb_path)
```

- J-Quants から日足データを取得して保存

```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

# markets からデータ取得
records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)

# DuckDB に保存（conn は init_schema で取得した接続）
n = save_daily_quotes(conn, records)
print(f"保存レコード数: {n}")
```

- 財務データ / マーケットカレンダーも同様に fetch_* -> save_* を使用

- id_token の直接取得（必要な場面で）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を利用して取得
```

- 監査ログの初期化（既存接続に監査テーブルを追加）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

- データ品質チェックの実行
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=None)
for issue in issues:
    print(issue.check_name, issue.table, issue.severity, issue.detail)
```

---

## 実装の注意点 / 補足

- J-Quants クライアント:
  - レート制限: デフォルト 120 req/min（固定間隔スロットリング）
  - リトライ: 最大 3 回、指数バックオフ。HTTP 408/429/5xx 等でリトライ
  - 401 発生時はリフレッシュトークンを用いて自動で id_token を更新して 1 回リトライ
  - ページネーション対応: pagination_key を使って全ページ取得
  - fetched_at フィールドでデータ取得時刻（UTC）を保存し、Look-ahead bias を追跡可能に

- DuckDB スキーマ:
  - Raw / Processed / Feature / Execution 層を定義
  - ON CONFLICT DO UPDATE により冪等性を確保
  - init_schema で自動的に親ディレクトリを作成

- 監査ログ:
  - シグナル→発注→約定を UUID で連鎖し、トレーサビリティを担保
  - すべてのタイムスタンプは UTC で保存（init_audit_schema は TimeZone を UTC に設定）

- 環境変数自動ロード:
  - .env / .env.local を自動読み込み（OS 環境変数を上書きしない挙動、.env.local は上書き可）
  - ただしテスト等で自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## ディレクトリ構成

プロジェクトの主要ファイル・ディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py      # J-Quants API クライアント（取得・保存ロジック）
      - schema.py              # DuckDB スキーマ定義と初期化
      - audit.py               # 監査ログ（signal/order_requests/executions）
      - quality.py             # データ品質チェック
      - (その他: news, audit 補助等)
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

README 以外のドキュメント（例: DataSchema.md, DataPlatform.md）を参照する想定の箇所がソース内にあります。実際のプロダクション導入時はこれら設計文書と合わせて確認してください。

---

## 今後の拡張案（参考）

- kabu-station API を使った注文送信・約定受信モジュール（execution 層の実装）
- Slack 連携によるアラート・監視ダッシュボード
- ETL スケジューラとの統合（Airflow / Prefect 等）
- テストスイート（ユニット／統合テスト）と CI 設定

---

もし README に追記したい具体的な操作例（例: CI 用コマンド、Docker 化、具体的な .env.example のテンプレートなど）があれば教えてください。必要に応じて追記・テンプレートを作成します。