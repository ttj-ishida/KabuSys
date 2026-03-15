# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ取得・スキーマ管理・監査ログ基盤・戦略/実行/監視の基礎モジュールを含む軽量なコードベースです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計されたライブラリ群です。  
主に次を目的としています。

- J-Quants API からの市場データ取得（株価日足、財務データ、マーケットカレンダー）
- DuckDB を用いた永続化（Raw / Processed / Feature / Execution 層）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 設定管理（環境変数 / .env 読み込み）
- 将来的な戦略・発注（strategy / execution / monitoring）拡張の土台

設計上の特徴:
- API レート制限順守（J-Quants: 120 req/min、固定間隔スロットリング）
- リトライ／指数バックオフ／401 のトークン自動リフレッシュ対応
- データ取得時間（fetched_at）を UTC で保存して Look-ahead Bias を防止
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で設計

---

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml で検出）
  - 必須環境変数の取得ラッパー、環境・ログレベルの検証
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- J-Quants API クライアント（kabusys.data.jquants_client）
  - get_id_token（リフレッシュトークンから ID トークンを取得）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
  - レートリミッタ、リトライ、401 自動リフレッシュ、fetched_at 記録
  - DuckDB に保存する save_* 関数（raw_prices / raw_financials / market_calendar）

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス定義
  - init_schema(db_path) / get_connection(db_path)

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル定義
  - init_audit_schema(conn) / init_audit_db(db_path)
  - 発注の冪等性（order_request_id）やステータス管理を想定

- パッケージ基礎（kabusys.__init__）: 公開サブパッケージ宣言

---

## セットアップ手順

前提:
- Python 3.10 以上（PEP 604 の union 型等を使用）
- duckdb ライブラリ（DuckDB 接続用）

1. リポジトリをクローン / 取得

2. 仮想環境を作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb
   - （プロジェクト配布時に pyproject.toml / requirements.txt があればそれに従ってください）
   - 開発中で editable install を使う場合:
     - pip install -e .

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を配置すると自動読み込みされます。
   - 読み込み順:
     - OS 環境変数（最優先）
     - .env（初期読み込み）
     - .env.local（.env を上書きする）
   - 自動読み込みを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数に設定

5. 必要な環境変数（主要）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
   - KABU_API_BASE_URL: kabuAPI ベース URL（省略時: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack ボットトークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（モニタリング）パス（省略時: data/monitoring.db）
   - KABUSYS_ENV: development | paper_trading | live（省略時: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（省略時: INFO）

.env の基本例:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

.env のパーサーはシングル/ダブルクォート、export プレフィックス、インラインコメント（スペースの際のみ）等に対応しています。

---

## 使い方（基本例）

以下は主要な使い方の短い例です。

- DuckDB スキーマ初期化（永続ファイル）
```
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は Path オブジェクトを返します（デフォルト: data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

- J-Quants から日足を取得して保存
```
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, _get_cached_token

conn = init_schema(settings.duckdb_path)

# 銘柄コードまたは期間を指定して取得可能
records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)

# raw_prices テーブルへ保存（冪等）
n = save_daily_quotes(conn, records)
print(f"保存件数: {n}")
```

- 監査ログテーブルの初期化（既存 conn に追加）
```
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```

- 監査専用 DB を作る
```
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

注意点:
- fetch_* 系関数は内部でレートリミット・リトライ・401 リフレッシュを行います。
- データを保存する際、primary key 欠損の行はスキップされます（警告ログが出ます）。
- save_* 関数は ON CONFLICT DO UPDATE による冪等性を担保しています。

---

## 設計上の挙動（重要なポイント）

- 自動 .env 読み込み:
  - プロジェクト内で .git または pyproject.toml を検出し、そのディレクトリをルートと見なして .env/.env.local を読み込みます。
  - OS 環境変数は保護され、.env の読み込みで上書きされません（.env.local は override=True のため上書きが可能。ただし OS 環境変数は protected）。
  - テストなどで自動読み込みを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- J-Quants クライアント:
  - 最小待機間隔 = 60 / 120 秒（=0.5s）で固定間隔スロットリングを行います。
  - 408/429/5xx 系に対して指数バックオフで最大 3 回リトライ。
  - 401 が返ったらリフレッシュを行い 1 回だけ再試行（無限ループを防止）。
  - ページネーションは pagination_key を利用して自動で全件取得。
  - データ保存時に fetched_at を UTC で記録することで、データが「いつ取得されたか」を追跡可能。

- DuckDB スキーマ:
  - Raw/Processed/Feature/Execution の 3 層＋監査ログを定義。
  - init_schema は親ディレクトリを自動作成します（":memory:" はインメモリ DB）。
  - 監査ログは init_audit_schema で追加、または init_audit_db で専用 DB を作成できます。

---

## ディレクトリ構成

プロジェクトの主要ファイル（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                 # 環境変数・設定管理
    - execution/                # 発注・ブローカー連携系（未実装の拡張ポイント）
      - __init__.py
    - strategy/                 # 戦略ロジック（未実装の拡張ポイント）
      - __init__.py
    - monitoring/               # 監視/メトリクス（未実装の拡張ポイント）
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py       # J-Quants API クライアント（取得 + 保存ロジック）
      - schema.py               # DuckDB スキーマ初期化/接続ユーティリティ
      - audit.py                # 監査ログ用スキーマ（signal/order_request/execution）
- pyproject.toml (想定)
- .git/ (想定)

---

## 拡張・運用のヒント

- 戦略開発:
  - strategy パッケージに戦略実装を置き、signal_events テーブルにレコードを残すことで監査と連携できます。
  - features / ai_scores テーブルに戦略で利用する前処理・スコアを保存する設計になっています。

- 実稼働運用:
  - KABUSYS_ENV を `paper_trading` や `live` に切り替え、settings.is_paper / is_live をフローで参照して発注抑止や安全措置を実装します。
  - 発注の冪等性は order_request_id（UUID）で担保してください。order_requests テーブルは二重実行防止を想定しています。

- ロギング:
  - settings.log_level を使ってログレベル検証が行われます。ライブラリを使うアプリ側で logging.basicConfig 等を設定してください。

---

必要に応じて README を拡張して、具体的な戦略テンプレート、実際の発注フロー例、CI/デプロイ手順、テストガイドラインなどを追加できます。必要な項目があれば教えてください。