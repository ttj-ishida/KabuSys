# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）。  
データ取得、DuckDBスキーマ管理、監査ログ、発注フローの骨組みを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とした内部ライブラリです。

- J-Quants 等の外部 API から株価・財務・マーケットカレンダーを取得して保存する
- DuckDB を用いてデータレイヤ（Raw / Processed / Feature / Execution）を定義・初期化する
- 発注フローの監査（signal → order_request → execution）を追跡可能にする監査スキーマを提供する
- 発注実行・戦略・モニタリングのための骨組み（パッケージ構成）を持つ

設計上の特徴:
- API レート制限（J-Quants: 120 req/min）を尊重する RateLimiter を実装
- リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ、ページネーション対応
- 取得時刻（fetched_at）や UTC タイムスタンプでのトレーサビリティを重視
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）を想定

---

## 機能一覧

- 環境設定管理（.env 自動ロード、必須チェックを行う Settings クラス）
- J-Quants API クライアント
  - 日足（OHLCV）取得（ページネーション対応）
  - 四半期財務データ取得（ページネーション対応）
  - JPX マーケットカレンダー取得
  - レート制限、リトライ、トークン自動リフレッシュ対応
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution レイヤのテーブルを定義・初期化
  - インデックス作成
- 監査ログ（audit）
  - signal_events / order_requests / executions の監査テーブル定義・初期化
  - UTC タイムゾーン固定、FK とインデックス含む
- パッケージ構成（strategy / execution / monitoring）を用意（実装拡張向け）

---

## 動作環境 / 依存関係

- Python 3.10 以上（PEP 604 の型記法などを使用）
- 必要な主なライブラリ:
  - duckdb
- ネットワークアクセスが必要（J-Quants API、kabuステーション、Slack など）

（実際の requirements.txt / setup はプロジェクトに合わせて用意してください）

---

## セットアップ手順

1. リポジトリをクローン／配置
   - 例: git clone ... （パッケージ配布形態に依存）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb
   - （その他、HTTPやSlack連携に必要なパッケージを追加）

4. 環境変数を設定
   - プロジェクトルートに .env を置くと自動で読み込まれます（.env.local で上書き可）
   - 自動読み込みを無効にする場合: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. DuckDB スキーマ初期化（例: Python REPL またはスクリプト）
   - from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")

---

## 必須 / 推奨 環境変数

Settings クラスで使われる主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants の refresh token
- KABU_API_PASSWORD — kabu ステーション API のパスワード
- SLACK_BOT_TOKEN — Slack ボットトークン
- SLACK_CHANNEL_ID — 通知先 Slack チャンネル ID

オプション（デフォルトあり）:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（任意）
- KABUSYS_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

例 (.env):
```
JQUANTS_REFRESH_TOKEN="xxxxxxx"
KABU_API_PASSWORD="secret"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

注意: .env のパースはシェル風の仕様に準拠（export プレフィックス対応、クォート内のエスケープ、コメント扱いなど）。

---

## 使い方（簡単な例）

J-Quants の日足を取得して DuckDB に保存する最小例。

```python
from datetime import date
import duckdb
from kabusys.data import jquants_client, schema
from kabusys.config import settings

# 1) スキーマ初期化（初回のみ）
conn = schema.init_schema(settings.duckdb_path)

# 2) データ取得（個別銘柄・日付範囲）
recs = jquants_client.fetch_daily_quotes(
    code="7203",
    date_from=date(2023, 1, 1),
    date_to=date(2023, 12, 31),
)

# 3) DuckDB に保存（冪等）
inserted = jquants_client.save_daily_quotes(conn, recs)
print(f"Inserted/Updated rows: {inserted}")
```

トークン取得（明示的に必要な場合）:

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使う
```

監査スキーマ初期化（監査専用 DB を使う場合）:

```python
from kabusys.data import audit
conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

## API の設計上の注意点

- J-Quants クライアント:
  - レート制限: 120 req/min を守るため内部でスロットリング（固定間隔）を行います。
  - リトライ: 最大 3 回。408 / 429 / 5xx やネットワークエラーに対して指数バックオフ。
  - 401 発生時は自動でリフレッシュトークンから id_token を再取得し 1 回リトライします。
  - ページネーション: pagination_key を API に渡して全ページを取得します。
  - 取得時刻（fetched_at）は UTC の ISO 形式で記録され、Look-ahead Bias の回避を支援します。
- DuckDB への保存関数は ON CONFLICT DO UPDATE により冪等性を保証します。
- 監査ログは削除しない運用を想定しており、FK は ON DELETE RESTRICT（履歴保持）。

---

## ディレクトリ構成

主要ファイル・モジュール:

- src/kabusys/
  - __init__.py  (パッケージ初期化、__version__ = "0.1.0")
  - config.py    (環境変数 / Settings の管理、.env 自動ロード)
  - data/
    - __init__.py
    - jquants_client.py  (J-Quants API クライアント、保存ユーティリティ)
    - schema.py          (DuckDB スキーマ定義・初期化)
    - audit.py           (監査ログスキーマの定義・初期化)
    - (raw/news/executions に対応する DDL を含む)
  - strategy/
    - __init__.py        (戦略層の拡張ポイント)
  - execution/
    - __init__.py        (発注実行層の拡張ポイント)
  - monitoring/
    - __init__.py        (監視用モジュールの拡張ポイント)

README で扱っていない詳細（例: strategy/execution の具象実装）は、プロジェクトごとの拡張により追加します。

---

## 開発・テスト時のヒント

- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）から行われます。ユニットテスト等で自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の ":memory:" を指定するとインメモリ DB を利用できます（テストに便利）。
- 監査テーブルは init_audit_schema(conn) で既存接続に追加できます（既存のアプリ DB をそのまま使用可能）。
- すべての TIMESTAMP は監査モジュール内で UTC を前提に保存されます（init_audit_schema は SET TimeZone='UTC' を実行）。

---

## 今後の拡張案（参考）

- kabuステーションとの発注実装（REST/WebSocket 経由）
- Slack 通知用ユーティリティ
- スケジューラ／ETL ジョブ（データ取得自動化）
- strategy / execution 層の共通インターフェース実装

---

必要であれば、README に含める具体的な .env.example、requirements.txt、セットアップスクリプト、またはより詳細な API 使用例を追加で作成します。どの情報を優先して追記しますか？