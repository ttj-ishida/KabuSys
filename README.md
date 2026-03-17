# KabuSys

バージョン: 0.1.0

日本株向け自動売買／データプラットフォームのコアライブラリ群です。J-Quants や RSS を用いたデータ収集、DuckDB ベースのスキーマ定義・初期化、ETL パイプライン、ニュース収集、データ品質チェック、マーケットカレンダー管理、監査ログ（発注→約定のトレーサビリティ）などを提供します。

---

## 主な機能

- J-Quants API クライアント
  - 株価日足（OHLCV）・財務指標（四半期 BS/PL）・JPX マーケットカレンダー取得
  - レート制限（120 req/min）対応、リトライ（指数バックオフ）、401 自動リフレッシュ対応
  - 取得時刻（fetched_at）を UTC で記録
  - DuckDB へ冪等（ON CONFLICT）で保存

- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution 層のテーブル群
  - インデックス定義、監査ログ用テーブル（audit）を別途初期化可能

- ETL パイプライン
  - 差分更新（最終取得日からの再取得）、バックフィル、品質チェック連携
  - run_daily_etl による日次パイプライン

- ニュース収集（RSS）
  - RSS フィード取得と前処理（URL除去・空白正規化）
  - SSRF 対策、gzip/サイズ制限、XML パースの安全化（defusedxml）
  - 記事ID：正規化URLの SHA-256（先頭32文字）で冪等性保証
  - raw_news / news_symbols への保存（チャンク挿入、RETURNING で挿入件数を正確に取得）

- データ品質チェック
  - 欠損値、主キー重複、前日比スパイク、日付不整合（未来日付 / 非営業日）など検出
  - QualityIssue オブジェクトで詳細を返却

- マーケットカレンダー管理
  - JPX カレンダー差分更新ジョブ（calendar_update_job）
  - 営業日判定、次/前営業日・期間内営業日取得、SQ判定

- 監査ログ（Audit）
  - signal_events / order_requests / executions 等、発注から約定までのトレーサビリティ用テーブル群
  - order_request_id による冪等制御、UTC タイムゾーン固定オプション

---

## 要件

- Python 3.10+
- 必要パッケージ（最低限）
  - duckdb
  - defusedxml

インストール例:
```
python -m pip install duckdb defusedxml
```

（プロジェクトをパッケージとして配布する場合は requirements.txt / pyproject.toml を用意してください）

---

## セットアップ手順

1. リポジトリをクローン / コピー
2. 必要パッケージをインストール（上記参照）
3. 環境変数を設定（.env をプロジェクトルートに置くと自動ロードされます）
   - 自動ロードは以下の優先順位で行われます:
     - OS 環境変数
     - .env.local
     - .env
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください
4. DuckDB スキーマ初期化（例を下記に記載）

必須（または推奨）環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）

例 .env:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要 API 例）

以下は Python スクリプトからの利用例です。

- settings の取得
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection
```

- 監査ログスキーマの初期化（別DBにする場合）
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# 監査ログ専用 DB を初期化
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

- 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "1911"}  # 例: 有効な銘柄コードセット
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count}
```

- カレンダー更新ジョブ（夜間バッチ用）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("calendar records saved:", saved)
```

- J-Quants からデータを直接取得
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings

id_token = jq.get_id_token(settings.jquants_refresh_token)
records = jq.fetch_daily_quotes(id_token=id_token, code="7203", date_from=None, date_to=None)
```

注意:
- ETL 等は DuckDB 接続を明示的に受け取る設計です（テストしやすく、接続管理が呼び出し元に委ねられます）。
- run_daily_etl は内部で品質チェック（quality.run_all_checks）を実行します。必要に応じてフラグで無効化できます。

---

## 重要設計メモ / 動作上の注意

- 自動 .env 読み込み:
  - パッケージ起点でプロジェクトルートを探索（.git または pyproject.toml）して .env/.env.local を読み込みます。
  - テスト等で自動読み込みを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- J-Quants API:
  - rate limit（120 req/min）に対応する RateLimiter を実装。リトライは最大3回（408/429/5xx 対象）。
  - 401 はトークン自動更新して1度だけ再試行します。

- ニュース収集:
  - RSS の XML は defusedxml でパースしています。
  - SSRF 対策として、リダイレクト先のスキーム・ホスト検査、プライベートアドレス遮断を実施。
  - レスポンスサイズ制限（10 MB）と gzip 解凍後の再チェックを行います。

- DuckDB スキーマ:
  - ON CONFLICT / INSERT ... RETURNING を利用して冪等性と正確な挿入件数取得を行います。
  - 監査ログ（audit）は別途初期化可能。UTC タイムゾーン固定オプションあり。

- Python バージョン:
  - 型ヒント（| を使った union 型等）を使用しているため Python 3.10+ を想定しています。

---

## ディレクトリ構成

以下はコードベースの主要ファイル／モジュール構成です（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - calendar_management.py
    - audit.py
    - quality.py
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

主要モジュールの役割:
- config.py: 環境変数管理（.env 自動読み込み、settings オブジェクト）
- data/schema.py: DuckDB の全テーブル定義と init_schema()
- data/jquants_client.py: J-Quants API クライアント + DuckDB 保存ユーティリティ
- data/pipeline.py: ETL（差分取得・保存・品質チェック）
- data/news_collector.py: RSS 収集と raw_news / news_symbols 保存ロジック
- data/calendar_management.py: JPX カレンダー管理・営業日判定・更新ジョブ
- data/audit.py: 監査ログ（発注/約定トレーサビリティ）スキーマ初期化
- data/quality.py: データ品質チェック

---

## よくある運用パターン

- 日次処理（cron等）
  - 前夜または早朝に calendar_update_job → run_daily_etl を実行
  - ETL 後に品質チェックの結果を Slack 等に通知（必要に応じて実装）

- ニュース収集
  - 定期取得ジョブで RSS を収集し、raw_news に保存 → 特定銘柄との紐付け → アラート/特徴量化

- 監査ログ
  - 発注フローは order_requests / executions に必ず記録し、order_request_id を冪等キーとして外部コールで再送しても重複を防止

---

## サポート / 貢献

- バグ報告・機能要望は Issue にてお願いします（README は開発向けの基本ドキュメントです）。
- コードフォーマット・型チェック・ユニットテストの追加を歓迎します。

---

必要であれば、README に使い方の具体的な CLI 例や docker-compose / systemd 用のサービス定義テンプレート、より詳細な .env.example を追加します。どの情報を拡張しますか？