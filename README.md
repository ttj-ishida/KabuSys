# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（プロトタイプ）。  
データ収集（J-Quants / RSS）、ETL パイプライン、データ品質チェック、監査ログ（取引フローのトレーサビリティ）、DuckDB スキーマ定義などを提供します。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を含むパッケージです。

- J-Quants API からのマーケットデータ（OHLCV、財務、マーケットカレンダー）収集
- RSS フィードからのニュース記事収集と銘柄紐付け
- DuckDB を用いたスキーマ定義・永続化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 監査ログ（シグナル→発注→約定 の UUID 連鎖によるトレーサビリティ）
- 市場カレンダー管理・営業日判定ロジック

設計方針として、API レート制限やリトライ、冪等性（ON CONFLICT）、SSRF対策、XML攻撃対策など運用上の実装配慮が施されています。

---

## 主な機能一覧

- データ取得
  - J-Quants クライアント（株価日足、四半期財務、マーケットカレンダー）
    - レート制限（120 req/min）
    - 指数バックオフ付きリトライ（408/429/5xx）
    - 401 時の自動トークンリフレッシュ（1 回）
    - fetched_at による取得時刻記録（Look-ahead Bias の追跡）
  - RSS ニュース収集（gzip / XML の安全な処理、SSRF 対策、トラッキングパラメータ除去）
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成
    - raw_news 保存（INSERT ... RETURNING、チャンク処理）
    - 銘柄コード抽出（4桁数字、既知銘柄セットとの照合）

- データベース
  - DuckDB スキーマ初期化（data/schema.init_schema）
  - Raw / Processed / Feature / Execution 層のテーブルを定義
  - 監査ログ用スキーマ（signal_events / order_requests / executions）を別モジュールで初期化可能

- ETL パイプライン
  - 日次 ETL エントリ（data.pipeline.run_daily_etl）
  - 差分更新、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
  - 市場カレンダー先読み（lookahead）

- カレンダー管理
  - 営業日判定・次/前営業日取得・期間内営業日取得
  - 夜間カレンダー更新ジョブ（calendar_update_job）

---

## 必要条件 / 依存

- Python 3.10 以上（型ヒントに PEP 604 の `X | Y` 構文を使用）
- 以下の Python パッケージ（最小限）
  - duckdb
  - defusedxml

インストール例:

```bash
python -m pip install "duckdb" "defusedxml"
# またはプロジェクトの requirements.txt / pyproject.toml によるインストール
```

（このコードベースは setuptools/pyproject の定義が提供されていないため、プロジェクト配布方法に応じて調整してください）

---

## セットアップ手順

1. Python と依存ライブラリをインストール（上記参照）。
2. プロジェクトルートに `.env` を配置（下記の環境変数を設定）。
   - 自動的に `.env` と `.env.local` がプロジェクトルートから読み込まれます（環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化可能）。
3. DuckDB 初期化（アプリから以下を呼び出す）

例: Python REPL で初期化

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path の既定は data/kabusys.duckdb
conn = init_schema(settings.duckdb_path)
```

必須環境変数（例）:
- JQUANTS_REFRESH_TOKEN — J-Quants の refresh token（必須）
- KABU_API_PASSWORD — kabu API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）

任意 / デフォルトあり:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment (development / paper_trading / live)（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）

.env の例（プロジェクトルートに保存）:

```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡易ガイド）

以下は主なユースケースのサンプルです。各モジュールには詳細な関数ドキュメントがあります。

- DuckDB スキーマ初期化

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
```

- 日次 ETL の実行（株価・財務・カレンダーの差分取得 + 品質チェック）

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)
print(result.to_dict())
```

- 市場カレンダーの夜間更新ジョブ

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
saved = calendar_update_job(conn)
print(f"saved calendar rows: {saved}")
```

- RSS ニュース収集ジョブ

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# known_codes: 銘柄抽出に利用する有効なコードセット（例: 上場銘柄リスト）
known_codes = {"7203","6758", ...}
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- 監査ログスキーマ初期化（発注・約定トレース用）

```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db("data/audit_duckdb.db")
```

- 品質チェック単体実行

```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

注意点:
- J-Quants API のレート上限を守るため、API 呼び出しは内蔵の RateLimiter を通して行われます。
- get_id_token は refresh token を使用して idToken を取得し、キャッシュします。401 時のリフレッシュを自動で行います。
- news_collector は SSRF 対策や XML の安全処理（defusedxml）を行います。

---

## ディレクトリ構成

主要なファイル・モジュール（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・settings インスタンス
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch/save 関連）
    - news_collector.py
      - RSS 取得、記事正規化、raw_news 保存、銘柄抽出
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py
      - 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
    - calendar_management.py
      - 市場カレンダー更新・営業日判定ユーティリティ
    - audit.py
      - 監査ログ（signal_events, order_requests, executions）
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - strategy/
    - __init__.py
    - （戦略ロジックはここに追加）
  - execution/
    - __init__.py
    - （発注/ブローカー連携ロジックはここに追加）
  - monitoring/
    - __init__.py
    - （監視・アラート用モジュール）

（実際のリポジトリにはさらにテストやドキュメントが含まれる場合があります）

---

## 運用上の注意点 / 実装の特徴

- 環境変数の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` と `.env.local` を自動ロードします（既存 OS 環境変数は保護）。
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- 冪等性:
  - DB 保存は可能な限り ON CONFLICT（DO UPDATE / DO NOTHING）を用いて冪等化されています。
- セキュリティ配慮:
  - RSS の XML 処理には defusedxml を使用。
  - ニュース取得時は SSRF 対策（リダイレクト検査、プライベート IP 拒否）やレスポンスサイズ制限を実施。
- ロギング/品質:
  - 各処理はログ出力を行い、品質チェックは fail-fast せず検出結果を返却します。呼び出し側が結果に応じた対応を行ってください。

---

## 今後の拡張案（参考）

- strategy / execution モジュールに具体的な戦略実装と実ブローカー連携の実装（kabu API client）
- モニタリング/アラート（Slack 通知など）の実装
- テスト・CI の充実（ユニットテスト、統合テスト、モックでの外部 API シミュレーション）
- コンテナ化 / デプロイ手順（定期ジョブのスケジューリング）

---

ご不明点や README に追記したい具体的な使用例（例: 実際の ETL スケジュール設定、Dockerfile、CI 設定など）があれば教えてください。必要に応じてサンプルスクリプトや .env.example をより詳細に作成します。