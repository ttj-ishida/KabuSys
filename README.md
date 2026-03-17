# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ群です。データ取得・ETL、ニュース収集、監査ログ、マーケットカレンダー管理、データ品質チェックなど、アルゴリズム取引に必要な基盤機能を提供します。

---

## プロジェクト概要

KabuSys は以下を目的としたライブラリセットです。

- J-Quants API など外部データソースからのデータ取得（株価、財務、マーケットカレンダー）
- DuckDB を用いたデータスキーマ定義と永続化
- RSS ベースのニュース収集と銘柄紐付け
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- カレンダー管理（営業日判定 / 翌営業日取得等）
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の特徴として、レート制限遵守、リトライ／トークン自動リフレッシュ、Look-ahead バイアス対策（fetched_at 記録）、冪等な DB 保存（ON CONFLICT）などを備えています。

---

## 主な機能一覧

- 環境変数管理（.env 自動ロード、保護機構）
- J-Quants API クライアント
  - 株価（日足）、財務、マーケットカレンダーの取得（ページネーション対応）
  - レート制限（120 req/min）とリトライ、401 時のトークン自動リフレッシュ
  - DuckDB への冪等保存ヘルパー
- ニュース収集（RSS）
  - URL 正規化、トラッキングパラメータ除去、記事ID の SHA-256 ハッシュ化
  - SSRF 対策、受信サイズ制限、defusedxml による XML 攻撃対策
  - raw_news / news_symbols への保存と銘柄抽出
- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution 層のテーブル定義とインデックス
  - 監査ログ（signal_events / order_requests / executions）初期化サポート
- ETL パイプライン
  - 差分更新（最終取得日から必要分のみ取得）、バックフィル、品質チェック統合
  - run_daily_etl による一括処理
- マーケットカレンダー管理
  - 営業日判定 / next/prev_trading_day / 期間内営業日取得
  - 夜間バッチ更新（calendar_update_job）
- 品質チェック
  - 欠損、スパイク（前日比閾値）、重複、日付不整合の検出
  - QualityIssue オブジェクトで詳細を返す

---

## セットアップ手順

必要事項（概略）

- Python 3.10 以上
- 必要パッケージ（例）:
  - duckdb
  - defusedxml

推奨手順（Unix/macOS）

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境作成 & 有効化
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージをインストール
   依存管理ファイルが無い場合は最低限以下をインストールしてください。
   ```
   pip install duckdb defusedxml
   ```
   （将来的に pyproject.toml / requirements.txt がある場合はそちらを使用してください）

4. 環境変数の設定
   ルートに `.env` を用意するか、OS 環境変数で下記を設定します。パッケージの config モジュールは自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

その他（任意/デフォルトあり）
- KABUSYS_ENV — `development` / `paper_trading` / `live`（デフォルト: development）
- LOG_LEVEL — `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（値が存在すれば無効化）

例（.env）
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（基本例）

下記は最低限の利用パターン例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
```

2) J-Quants トークン取得（明示的に）
```python
from kabusys.data.jquants_client import get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を使用して取得
```

3) 日次 ETL を実行
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を省略すると today が使われる
print(result.to_dict())
```

4) ニュース収集ジョブを実行（既知銘柄コードを渡して銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

known_codes = {"7203", "6758"}  # 有効な銘柄コードセット（例）
counts = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(counts)
```

5) 設定値の参照
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.is_live)
```

6) 監査ログ初期化（監査テーブルを追加）
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```

注意点:
- ETL や API 呼び出しはネットワークエラーや API 制限に伴うリトライを行いますが、適切なロギングと監視を行ってください。
- 自動 .env ロードを無効にしたいテストなどでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

プロジェクトの主要ファイル／モジュール構成（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数・設定管理（.env 自動ロード、必須チェック）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py      — RSS ニュース収集、正規化、DB 保存、銘柄抽出
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - schema.py              — DuckDB スキーマ定義・初期化
    - calendar_management.py — マーケットカレンダー管理（営業日判定・更新ジョブ）
    - audit.py               — 監査ログ（シグナル〜発注〜約定のトレーサビリティ）
    - quality.py             — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

各モジュールの責任は README の「主な機能一覧」を参照してください。

---

## 実運用・運用上の注意

- 環境（KABUSYS_ENV）により挙動が変わる想定（development / paper_trading / live）。live では特に注意して運用してください。
- DuckDB ファイルはデフォルト `data/kabusys.duckdb`。運用ではバックアップ戦略を検討してください。
- ニュース収集では外部 URL を取得するため SSRF 対策が組み込まれていますが、プロキシやネットワーク設定により追加の制御が必要な場合があります。
- 監査ログには機密情報を格納しない、適切なアクセス制御・バックアップを行ってください。
- ロギングは `LOG_LEVEL` で制御可能。運用時は適切なログ出力先（ファイル/外部ロギングサービス）を設定してください。

---

## 開発・拡張

- strategy / execution / monitoring パッケージは拡張ポイントです。戦略ロジック、証券会社実行（kabu ステーション連携）、モニタリング処理はこれらに実装してください。
- テストを書く際は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使うと .env 自動ロードを無効化できます。外部依存（ネットワーク、DuckDB）をモックするとテストが容易になります。

---

必要であれば README にサンプル .env.example、より詳しい運用手順（cron / Airflow / GitHub Actions を用いた定期実行例）や、SQL スキーマの詳細説明（テーブル定義ごとの用途）を追加できます。どの情報を優先して追記しましょうか？