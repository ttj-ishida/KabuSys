# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。J-Quants API や RSS を用いたデータ収集、DuckDB ベースのスキーマ・ETL・品質チェック、監査ログ（発注→約定のトレース）などを提供します。

主な設計方針：
- データ取得はレート制限・リトライ・トークン自動更新を備える
- DuckDB へ冪等に保存（ON CONFLICT / INSERT ... DO UPDATE / DO NOTHING）
- ニュース収集は SSRF・XML Bomb 対策・トラッキングパラメータ除去などを実装
- 品質チェック（欠損、スパイク、重複、日付不整合）を行い ETL の健全性を確認

バージョン: 0.1.0

---

## 機能一覧

- 環境設定の自動読み込み（.env / .env.local、環境変数優先）
- J-Quants API クライアント
  - 日足（OHLCV）・財務（四半期）・市場カレンダーの取得
  - レートリミッタ、リトライ、401 時のトークン自動更新
  - DuckDB への冪等保存用関数（save_daily_quotes 等）
- RSS ベースのニュース収集
  - URL 正規化・トラッキングパラメータ削除・記事IDは正規化 URL の SHA-256（先頭32文字）
  - SSRF 防止、gzip サイズ上限、defusedxml による XML セーフガード
  - raw_news テーブルへのバルク挿入・銘柄コード抽出と紐付け
- DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日判定、前後営業日の取得、夜間更新ジョブ）
- 監査ログスキーマ（signal / order_request / executions 等）および初期化
- データ品質チェック（欠損、スパイク、重複、日付不整合）

---

## セットアップ

前提
- Python 3.9+（型注釈に union 型などを使用）
- pip

例: 仮想環境の作成と依存インストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
# 必要なライブラリ（例）
pip install duckdb defusedxml
# パッケージを開発モードでインストールする場合（プロジェクトルートに pyproject.toml/setup.py がある前提）
pip install -e .
```

環境変数（必須 / 推奨）
- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD : kabuステーション API のパスワード
  - SLACK_BOT_TOKEN : Slack 通知用ボットトークン
  - SLACK_CHANNEL_ID : Slack チャンネル ID
- 任意（デフォルト値あり）
  - KABUSYS_ENV : development | paper_trading | live （デフォルト: development）
  - LOG_LEVEL : DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
  - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- テスト等で自動 .env ロードを無効化する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

サンプル .env
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（基本例）

以下は主要機能の使い方サンプル。API は Python モジュールとして直接利用します。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ:
# conn = schema.init_schema(":memory:")
```

2) J-Quants から日次 ETL を実行
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")
# known_codes があれば抽出して銘柄紐付けを行う（set of strings, 例: {"7203","6758"}）
res = run_news_collection(conn, sources=None, known_codes=None)
print(res)  # 各ソースの新規保存件数を返す
```

4) 監査ログ用スキーマ初期化（発注トレース用）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

5) J-Quants のトークン取得（明示的に取得したい場合）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
```

主要エントリーポイント：
- データ初期化: kabusys.data.schema.init_schema / get_connection
- 日次 ETL: kabusys.data.pipeline.run_daily_etl
- ニュース収集: kabusys.data.news_collector.run_news_collection
- カレンダー更新バッチ: kabusys.data.calendar_management.calendar_update_job
- 監査 DB 初期化: kabusys.data.audit.init_audit_db

---

## よくある運用ワークフロー（例）

- 夜間バッチ（Cron）:
  1. DB 接続を作成（schema.get_connection）
  2. calendar_update_job を実行（lookahead で先読み）
  3. run_daily_etl を実行して株価／財務を差分取得
  4. run_news_collection を実行してニュース収集
  5. 品質チェックは pipeline が自動実行、結果をログ or Slack に通知

- 発注／実行トレース:
  - 戦略が生成したシグナル、発注要求（冪等キー order_request_id）、証券会社からの約定を audit テーブル群で保存して追跡可能にする

---

## ディレクトリ構成

src/kabusys/
- __init__.py
- config.py                        — 環境変数 / 設定管理（.env 自動ロード、Settings クラス）
- data/
  - __init__.py
  - jquants_client.py               — J-Quants API クライアント（取得・リトライ・保存）
  - news_collector.py               — RSS ニュース収集・前処理・DB保存・銘柄抽出
  - schema.py                       — DuckDB スキーマ（DDL）と初期化関数
  - pipeline.py                     — ETL パイプライン（差分取得・バックフィル・品質チェック）
  - calendar_management.py          — マーケットカレンダー管理（営業日判定、夜間更新）
  - audit.py                         — 監査ログ（signal / order_request / executions）初期化
  - quality.py                       — データ品質チェック（欠損・スパイク・重複・日付不整合）
- strategy/                         — 戦略層（空のパッケージ、戦略実装先）
- execution/                        — 実行層（空のパッケージ、発注ラッパ等を想定）
- monitoring/                       — 監視系（空のパッケージ、監視用コードを配置）

主要ファイルの責務:
- config.py: .env の自動ロード、必須 env の検証、Settings インスタンス提供
- jquants_client.py: API 呼び出し（RateLimiter、retry）、データ取得・DuckDB 保存関数
- news_collector.py: RSS 取得、XML 安全化、URL 正規化、記事 ID 生成、DB 保存
- schema.py: 全テーブル DDL とインデックス、init_schema 関数
- pipeline.py: 差分 ETL、バックフィル、品質チェック（quality モジュール呼び出し）
- calendar_management.py: 営業日判定、カレンダー更新ジョブ
- audit.py: 監査ログ用 DDL と初期化ロジック
- quality.py: 各種データ品質チェック

---

## 運用上の注意点 / 実装上のポイント

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。必要なら KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- J-Quants のレート制限（120 req/min）を意識して設計されています。大量ページネーションを行う場合は注意してください。
- DuckDB の接続とトランザクション管理：bulk insert はトランザクションを使う箇所とそうでない箇所があるため、運用スクリプトで適切にエラーハンドリングしてください。
- news_collector は外部 URL にアクセスするため SSRF 対策やサイズ上限を設けています。テスト時は _urlopen をモックして差し替えられます。
- audit.init_audit_schema は TIMESTAMP を UTC に固定します（SET TimeZone='UTC' を実行）。

---

## 開発・テスト

- 単体テストや CI を追加する場合：
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して環境依存を切る
  - duckdb の ":memory:" を用いてインメモリ DB を使うとテストが高速・独立に行えます

---

不明点や追加で README に含めたい内容（例：具体的な戦略実装テンプレート、CI 設定、運用用 systemd / cron サンプルなど）があれば教えてください。必要に応じてサンプルスクリプトや運用手順を追記します。