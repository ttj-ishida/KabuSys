# KabuSys

日本株向けの自動売買（アルゴリズム取引）基盤ライブラリです。  
データ取得、DB スキーマ、監査ログ（トレーサビリティ）、および発注/戦略層の土台となるモジュール群を提供します。

現在のバージョン: 0.1.0

## 概要
KabuSys は以下の目的を持つ内部向けライブラリです。

- J-Quants API から市場データ・財務データ・マーケットカレンダーを取得するクライアントを提供
- DuckDB を用いたデータレイクのスキーマ定義と初期化
- 発注にまつわる監査（signal → order_request → execution）のための監査テーブルを提供し、フローの完全なトレースを可能にする
- 環境変数ベースの設定管理（.env の自動読み込みを含む）

設計上のポイント：
- J-Quants API はレート制限（120 req/min）に対応（固定間隔スロットリング）
- リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ（1 回）に対応
- データ取得時に fetched_at/UTC を付与して Look-ahead Bias を防止
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）を意識

## 機能一覧
- 環境設定管理（kabusys.config）
  - .env/.env.local の自動読み込み（プロジェクトルート判定）
  - 必須環境変数の取得ラッパー
  - 環境（development / paper_trading / live）・ログレベル検証
- J-Quants API クライアント（kabusys.data.jquants_client）
  - ID トークン取得（リフレッシュ）
  - 日足（OHLCV）取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）取得（ページネーション対応）
  - JPX マーケットカレンダー取得
  - DuckDB への保存関数（raw_prices / raw_financials / market_calendar）
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層を含む多層スキーマ
  - インデックス定義
  - init_schema(), get_connection()
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル定義と初期化
  - init_audit_schema(), init_audit_db()
- パッケージ基盤（strategy, execution, monitoring）を配置（拡張用）

## 要件
- Python 3.10+
  - 型注釈で |（PEP 604）を使用しているため 3.10 以降を想定しています
- 依存パッケージ
  - duckdb

（外部 API 呼び出しは標準ライブラリの urllib を使用しているため、requests は不要です）

## セットアップ手順

1. リポジトリをクローン（またはプロジェクトをセットアップ）
   - 例: git clone <your-repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（macOS/Linux）
   - .venv\Scripts\activate（Windows）

3. 依存パッケージをインストール
   - pip install duckdb

   （プロジェクトで requirements.txt / pyproject.toml を用意している場合はそちらからインストールしてください）

4. 環境変数を設定
   - プロジェクトルートに `.env`（および任意で `.env.local`）を置くと、自動的に読み込まれます。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

## 環境変数（主なもの）
必須のものは実行に必要です。欠けていると起動時に ValueError が発生します。

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live。デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL。デフォルト: INFO）

例 .env（プロジェクトルート）:
```
JQUANTS_REFRESH_TOKEN=xxxx...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

.env のパースは通常の KEY=VALUE に加え、export KEY=...、シングル/ダブルクォート、エスケープ、行末コメント等にある程度対応しています。

## 使い方（基本例）

以下は最小限の利用フロー例です。

- DuckDB スキーマを初期化する

```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# conn を使ってクエリや保存関数を呼び出す
```

- J-Quants から日足データを取得して保存する

```python
from kabusys.data import jquants_client
from kabusys.data import schema
import duckdb

# DB 初期化（既にある場合はスキップ）
conn = schema.init_schema("data/kabusys.duckdb")

# 全銘柄または特定コードを指定して取得
records = jquants_client.fetch_daily_quotes(code="7203")  # トヨタなどコード指定
# または date_from/date_to を指定して範囲取得

# 保存（raw_prices に挿入 / 更新）
inserted = jquants_client.save_daily_quotes(conn, records)
print(f"{inserted} 件を保存しました")
```

- 財務データ・マーケットカレンダーの取得・保存も同様です
  - fetch_financial_statements(...) / save_financial_statements(...)
  - fetch_market_calendar(...) / save_market_calendar(...)

- ID トークンを直接取得する
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()
```

- 監査ログの初期化（監査専用 DB を作る場合）
```python
from kabusys.data import audit
conn = audit.init_audit_db("data/kabusys_audit.duckdb")
# あるいは既存の conn に対して:
# from kabusys.data.schema import init_schema
# conn = init_schema("data/kabusys.duckdb")
# audit.init_audit_schema(conn)
```

注意点:
- J-Quants API は 120 req/min のレート制限を厳守するため、クライアント内部で固定間隔スロットリングとリトライ処理を行います。
- 401 が返ってきた場合は内部でリフレッシュを行い 1 回リトライします（無限ループにならないよう制御あり）。
- 保存関数は冪等性を保つため ON CONFLICT DO UPDATE を用いています。
- 監査系テーブルは UTC の TIMESTAMP を利用する設計になっています（init_audit_schema() は SET TimeZone='UTC' を実行します）。

## ディレクトリ構成

プロジェクト内の主なファイル/ディレクトリ:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py         # J-Quants API クライアント（取得・保存ロジック）
    - schema.py                 # DuckDB スキーマ定義・初期化
    - audit.py                  # 監査ログ（signal/order_request/execution）
    - audit.py
  - strategy/
    - __init__.py               # 戦略層（拡張ポイント）
  - execution/
    - __init__.py               # 発注／ブローカー連携（拡張ポイント）
  - monitoring/
    - __init__.py               # 監視用モジュール（拡張ポイント）

ルートに .env / .env.local を置くことで自動で環境変数が読み込まれます（.git または pyproject.toml を基準にプロジェクトルートを探します）。

## 開発メモ / 実装上の注意
- Python の標準 urllib を使って API 呼び出しを行っているためプロキシ設定やタイムアウト等は Request オブジェクト側で調整可能です（現在は timeout=30 秒）。
- J-Quants の API レスポンスは JSON を想定。JSON デコードエラー時には内容の一部を含む例外が発生します。
- DuckDB のスキーマは外部キーやチェック制約を多用しており、整合性を保つ設計です。
- audit モジュールの order_request_id は冪等キーとして機能する想定です。再送時は同一 order_request_id を渡してください。

---

この README は現状のコードベース（src/kabusys 以下）に基づいて作成しています。strategy / execution / monitoring の具体実装は拡張を前提として空のパッケージが存在します。必要に応じて戦略実装／発注ブリッジ／モニタリングルールを追加してください。