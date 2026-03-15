# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ取得、スキーマ定義、監査ログ、設定管理などの基盤機能を提供します。

注意: このリポジトリはフレームワーク・ライブラリ層であり、戦略実装や注文実行の具体的な実装は別途追加する想定です。

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API から株価や財務、マーケットカレンダーを安全に取得するクライアント
- DuckDB 上のデータスキーマ（Raw / Processed / Feature / Execution 層）を定義・初期化する機能
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマの初期化
- 環境変数／設定の読み込みと管理（.env 自動ロード対応）
- （将来的に）戦略・発注・監視などのモジュールを統合するためのパッケージ構造

主な設計方針：
- API レート制御（J-Quants: 120 req/min）と再試行（指数バックオフ）
- 認証トークンの自動リフレッシュ（401 時に一度リトライ）
- 取得時刻（fetched_at）の記録による Look-ahead bias の軽減
- DuckDB への書き込みは冪等（ON CONFLICT DO UPDATE）で重複を防止

---

## 機能一覧

- 環境・設定管理
  - .env/.env.local をプロジェクトルートから自動読み込み（必要に応じて無効化可能）
  - 必須設定は Settings クラス経由で取得・バリデーション

- J-Quants クライアント（kabusys.data.jquants_client）
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - fetch系の結果を DuckDB に保存する save_daily_quotes / save_financial_statements / save_market_calendar

- DuckDB スキーマ（kabusys.data.schema）
  - init_schema(db_path) : 全テーブル（Raw/Processed/Feature/Execution）とインデックスを作成して接続を返す
  - get_connection(db_path) : 既存 DB へ接続（初期化は行わない）

- 監査ログ（kabusys.data.audit）
  - init_audit_schema(conn) : 既存 DuckDB 接続に監査テーブルを追加
  - init_audit_db(db_path) : 監査専用 DB を初期化して接続を返す

- パッケージ構成
  - kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring（strategy/execution/monitoring は拡張ポイント）

---

## セットアップ手順

前提:
- Python 3.10 以上を推奨（型注釈に | を使用）
- pip が使用可能

1. リポジトリをクローン／チェックアウト
2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb
   - （HTTP クライアントは標準 urllib を使用していますが、他に logger 等を追加する場合は requirements に追記してください）

4. 環境変数の準備
   - プロジェクトルートに `.env`（および必要であれば `.env.local`）を用意します。
   - 自動読み込みの優先順位は OS 環境変数 > .env.local > .env です。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD : kabuステーション API 用パスワード（必須）
   - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID : Slack チャンネル ID（必須）
   - 省略時デフォルトが設定されるもの
     - KABUSYS_ENV (default: development) 有効値: development, paper_trading, live
     - LOG_LEVEL (default: INFO)
     - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)

例 .env の行（参考）
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 使い方（基本例）

以下は代表的な利用フローの例です。

1) DuckDB スキーマを初期化する（ファイル DB）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# conn は duckdb connection オブジェクト
```

2) J-Quants から日足を取得して保存する
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
# conn は init_schema で得た接続
records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)
n = save_daily_quotes(conn, records)
print(f"保存件数: {n}")
```

3) 財務情報・カレンダー取得と保存
```python
from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements
from kabusys.data.jquants_client import fetch_market_calendar, save_market_calendar

fin = fetch_financial_statements(code="7203")
save_financial_statements(conn, fin)

cal = fetch_market_calendar()
save_market_calendar(conn, cal)
```

4) 監査ログテーブルを追加する（既存接続に対して）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
# 以降、signal_events / order_requests / executions が使えるようになる
```

注意点・挙動：
- fetch_* 系はページネーションに対応し、内部でトークンキャッシュ・自動リフレッシュを行います。
- API リクエストは固定間隔のレート制御（120 req/min）と、408/429/5xx に対する指数バックオフリトライを適用します。
- save_* 関数は冪等で、ON CONFLICT DO UPDATE を利用して既存行を更新します。
- すべてのタイムスタンプは UTC を想定して扱われます（監査 DB 初期化時に SET TimeZone='UTC' を実行）。

---

## 環境変数と設定（まとめ）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション（デフォルトあり）:
- KABUSYS_ENV: development | paper_trading | live （default: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL （default: INFO）
- KABU_API_BASE_URL: kabuAPI のベース URL（default: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（default: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

.env のパースルール:
- export KEY=val 形式に対応
- シングル/ダブルクォート内部はエスケープを考慮して解析
- クォート無しの # は前に空白/タブがある場合のみコメントとして扱う

---

## ディレクトリ構成

以下は主要ファイル・モジュールの一覧（抜粋）です。

- src/kabusys/
  - __init__.py  (パッケージ定義、__version__ = "0.1.0")
  - config.py    (環境変数・Settings 管理、.env 自動読み込み)
  - data/
    - __init__.py
    - jquants_client.py   (J-Quants API クライアント、取得・保存ロジック)
    - schema.py          (DuckDB スキーマ定義・初期化)
    - audit.py           (監査ログテーブル定義・初期化)
    - (その他: raw/processed/feature/execution に関する定義)
  - strategy/
    - __init__.py        (戦略モジュールのエントリ、拡張ポイント)
  - execution/
    - __init__.py        (発注実装のエントリ、拡張ポイント)
  - monitoring/
    - __init__.py        (監視・メトリクス用のエントリ、拡張ポイント)

（ファイル名・関数名はソースコード内の実装に基づく）

---

## 開発・拡張ポイント

- strategy パッケージに戦略実装（シグナル生成）を追加し、signal_events に記録
- execution パッケージで order_requests を作成・送信し、証券会社の応答を executions に記録
- monitoring で DuckDB / 監査テーブルを参照して運用ダッシュボードや SLA チェックを実装
- Slack 通知やエラーハンドリングを整備して運用性を向上

---

## 参考・注意事項

- DuckDB テーブル定義は厳密な型・チェック制約を含みます。データを投入する際は型・NULL に注意してください。
- J-Quants API のレート制限やエラーコードに応じた挙動は jquants_client に組み込まれていますが、運用中は実際の API 制限・利用ポリシーを遵守してください。
- 本パッケージはライブラリ層であり、実運用での発注（特に live 環境）を行う場合は厳格なリスク管理とテストを行ってください。

---

必要であれば、README に以下項目を追記できます：
- CI/テスト実行手順（pytest 等）
- 依存関係リスト（requirements.txt）
- 実運用チェックリスト（安全なデプロイ手順）
- サンプル .env.example ファイル

追記希望があれば教えてください。