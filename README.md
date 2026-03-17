# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
J-Quants（株価・財務・市場カレンダー）や RSS フィードを収集し、DuckDB に蓄積・品質チェックを行い、戦略・実行・監視のための基盤を提供します。

主な設計方針：
- データの冪等性（ON CONFLICT / INSERT ... DO UPDATE）を重視
- API レート制限・リトライ・トークン自動更新を組み込み
- SSRF・XML Bomb 等の脅威を考慮した堅牢な収集処理
- DuckDB を中心に Raw / Processed / Feature / Execution / Audit のレイヤーでスキーマ管理

バージョン: 0.1.0

---

## 機能一覧
- 環境変数管理（.env 自動読み込み、必須設定の検査）
- J-Quants API クライアント
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 四半期財務データ取得
  - JPX 市場カレンダー取得
  - レート制限（120 req/min）、リトライ、401時の自動トークンリフレッシュ
- DuckDB スキーマ定義 / 初期化（raw / processed / feature / execution テーブル群）
- ETL パイプライン
  - 差分更新（最終取得日からの新規分のみ）
  - バックフィルによる後出し修正吸収
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS -> raw_news 保存、URL 正規化、トラッキング除去、SSRF 対策）
- 市場カレンダー管理（営業日判定・前後営業日検索・バッチ更新ジョブ）
- 監査ログ（signal / order_request / executions）用スキーマと初期化
- ニュースの銘柄抽出（4桁コード抽出 + known_codes によるフィルタリング）

---

## 動作環境 / 依存関係
- Python 3.10 以上（型注釈に `X | None` を使用）
- 必須ライブラリ（例）:
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS）

インストール例（開発環境、プロジェクトルートで実行）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# パッケージをローカルで編集しながら使いたい場合:
pip install -e .
```

---

## 環境変数（.env）
自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（CWD ではなくパッケージファイル位置を基準に探索）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（必須は明記）:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード（execution 関連）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 bot token
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境（development / paper_trading / live）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

サンプル `.env`（プロジェクトルートに配置）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: Settings API で未設定の必須変数へアクセスすると ValueError が発生します。

---

## セットアップ手順（簡易）
1. リポジトリをクローン / コピー
2. Python 仮想環境を作成し依存をインストール
3. `.env` を作成して必要な環境変数を設定
4. DuckDB スキーマを初期化

DuckDB スキーマ初期化例:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# conn は duckdb.DuckDBPyConnection
```

監査ログ専用 DB 初期化例:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（主要ユースケースの例）

- 設定値取得:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)   # 未設定なら ValueError
print(settings.duckdb_path)
```

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）:
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- RSS ニュース収集と DB 保存:
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄コードの集合（抽出精度向上のため）
known_codes = {"7203", "6758", "9984"}  # 例
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # { source_name: saved_count, ... }
```

- カレンダー更新バッチ:
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("saved", saved)
```

- J-Quants トークン取得（必要時）:
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を用いて ID トークンを取得
```

- 品質チェック単独実行:
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

注意点:
- run_daily_etl 等は内部で例外制御を行い、ステップごとに継続する設計です。戻り値（ETLResult）で品質問題や発生エラーを確認してください。
- J-Quants API 呼び出しはモジュールレベルで ID トークンをキャッシュし、自動リフレッシュを試みます。

---

## 開発者向けメモ
- 自動 .env 読み込みはパッケージロード時に行われます。テストや一時的に無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- RSS 取得では defusedxml を使って XML 攻撃を防いでいます。HTTP レスポンスは最大 10MB に制限されています。
- ニュース記事 ID は正規化された URL の SHA-256（先頭32文字）を使用して冪等性を担保しています。
- DuckDB への大量挿入はチャンク化してトランザクションで安全に実行します（news_collector など）。

---

## ディレクトリ構成（主要ファイルと説明）
（プロジェクトの src/kabusys 配下のファイル・モジュールの概観）

- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数 / 設定管理（.env 自動ロード、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch / save / 認証 / レート制御 / リトライ）
    - news_collector.py — RSS フィード収集、前処理、raw_news 保存、銘柄抽出
    - schema.py — DuckDB スキーマ定義と init_schema/get_connection
    - pipeline.py — ETL パイプライン（run_daily_etl + 個別 ETL ジョブ）
    - calendar_management.py — market_calendar 管理、営業日判定、バッチ更新
    - audit.py — 監査ログ用スキーマ（signal / order_request / executions）と init
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py — 戦略関連のプレースホルダ（将来的な戦略実装場所）
  - execution/
    - __init__.py — 発注 / ブローカ連携プレースホルダ
  - monitoring/
    - __init__.py — 監視 / メトリクス関連のプレースホルダ

---

## よくあるトラブルシューティング
- ValueError: 環境変数が未設定 — 必須 env（JQUANTS_REFRESH_TOKEN など）を .env で設定してください。
- duckdb に接続できない / ファイルパスの親ディレクトリがない — init_schema は親ディレクトリを自動作成しますが、パーミッションを確認してください。
- API レート制限により 429 が返る — jquants_client は Retry-After を考慮してリトライしますが、頻度を調整してください。

---

必要であれば、README に含めるサンプル .env.example、より詳細な API 呼び出し例、CI 用のコマンド、またはデプロイ手順（systemd / cron / GitHub Actions など）も作成します。どの情報を優先して追加しましょうか？