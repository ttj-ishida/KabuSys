# KabuSys

KabuSys は日本株のデータ取得・ETL・品質管理・ニュース収集・監査ログなどを備えた自動売買プラットフォームのライブラリ群です。J-Quants API や kabuステーション、DuckDB を用いたローカル DB によって、データの差分取得／安全な保存／監査可能な発注フローを提供します。

主な設計方針：
- データの冪等性（ON CONFLICT）を重視して再実行可能に設計
- API レート制限とリトライ（指数バックオフ）を組み込み
- Look-ahead バイアス回避のため取得時刻（UTC）を記録
- RSS ニュース収集で SSRF・XML 攻撃対策を実装
- DuckDB を中心に Raw / Processed / Feature / Execution / Audit 層を明確に分離

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（必要に応じて無効化可能）
  - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN 等）
- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レートリミット制御（120 req/min）、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ニュース（RSS）収集
  - RSS の取得／前処理（URL除去・空白正規化）
  - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等保存
  - SSRF・gzip Bomb・XML Forgery 対策を実装
  - 銘柄コード抽出と news_symbols への紐付け
- ETL パイプライン
  - 差分更新（最終取得日からの差分のみ取得）
  - backfill による直近再取得（API の修正を吸収）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
- カレンダー管理
  - JPX 市場カレンダーの定期更新ジョブ
  - 営業日判定 / 前後営業日の取得 / 期間内営業日リスト
- 監査ログ（Audit）
  - signal_events / order_requests / executions など監査向けテーブル
  - 発注フローの完全トレーサビリティ（UUID ベース）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化ユーティリティ

---

## 前提条件

- Python 3.10 以上（typing の | 型注釈などを使用）
- DuckDB（Python パッケージ）
- defusedxml（RSS の安全な XML パース）
- 基本ライブラリ: urllib, logging, datetime 等（標準ライブラリ）
- その他: pip / virtualenv 等の環境管理ツール

推奨パッケージ（例）:
- duckdb
- defusedxml

---

## セットアップ手順

1. リポジトリをクローン / ローカルに配置
2. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)
3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトに setup.py / pyproject.toml があれば pip install -e . で開発インストール）
4. 環境変数を設定 (.env または OS 環境変数)
   - プロジェクトルート（.git または pyproject.toml の親）を起点に .env/.env.local が自動読み込みされます。
   - 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

例: .env（プロジェクトルート） — 必須項目のみ
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C1234567890
# 任意
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABU_API_BASE_URL=http://localhost:18080/kabusapi
```

---

## データベース初期化

DuckDB スキーマを初期化するには、kabusys.data.schema.init_schema を使用します。

例:
```python
from kabusys.config import settings
from kabusys.data import schema

# settings.duckdb_path は .env の DUCKDB_PATH（デフォルト data/kabusys.duckdb）
conn = schema.init_schema(settings.duckdb_path)
# これで全テーブルとインデックスが作成されます（冪等）
```

監査ログ用スキーマのみ別 DB に初期化する場合:
```python
from kabusys.data import audit
conn = audit.init_audit_db("data/audit.duckdb")
```

---

## 使い方（主要 API の例）

- J-Quants トークン取得（明示的に必要な場合）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token が使われる
```

- 日次 ETL の実行
```python
from datetime import date
import kabusys
from kabusys.data import pipeline, schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- RSS ニュース収集ジョブ
```python
from kabusys.data import news_collector, schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)
# sources をカスタムすることも可（{source_name: rss_url}）
res = news_collector.run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(res)
```

- 市場カレンダーの夜間更新ジョブ
```python
from kabusys.data import calendar_management, schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)
saved = calendar_management.calendar_update_job(conn)
print("saved calendar rows:", saved)
```

- 品質チェック単体実行
```python
from kabusys.data import quality, schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn, target_date=date.today())
for issue in issues:
    print(issue)
```

---

## 環境変数設定一覧

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants の refresh token（get_id_token に使用）
- KABU_API_PASSWORD : kabuステーション API パスワード（実行モジュールで使用）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID : Slack 通知チャンネル ID

任意 / デフォルトあり:
- KABU_API_BASE_URL : kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルのパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite のパス（デフォルト data/monitoring.db）
- KABUSYS_ENV : 実行モード (development | paper_trading | live)（デフォルト development）
- LOG_LEVEL : ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

備考:
- .env/.env.local はプロジェクトルートから自動読み込みされます（OS 環境変数が優先）。
- 自動読み込みを一時的に無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## セキュリティ & 実運用上の注意

- J-Quants API 呼び出しはレート制限（120 req/min）を厳守する実装になっています。外部からの直接大量呼び出しは避けてください。
- RSS の取得では SSRF 防止（スキーム検証、プライベート IP ブロック）、XML パーサーに defusedxml を使用、受信サイズ上限や gzip 解凍後のサイズ検査を行っていますが、追加のセキュリティ対策は運用環境に応じて実施してください。
- DuckDB のファイル権限や保存先については運用ポリシーに従い適切なアクセス制御を行ってください。
- 実売買（live）モードでの実行は十分なテストとレビューを経て行ってください（KABUSYS_ENV=live を設定すると is_live フラグが有効になります）。

---

## ディレクトリ構成

パッケージの主要ファイルとディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境設定読み込み・Settings
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - news_collector.py      — RSS ニュース収集、前処理、DB 保存
    - schema.py              — DuckDB スキーマの定義・初期化
    - pipeline.py            — ETL パイプライン（差分取得・品質チェック等）
    - calendar_management.py — 市場カレンダー管理・営業日ロジック
    - audit.py               — 監査ログ用スキーマ（signal/order/execution）
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py            — 戦略関連モジュール（拡張ポイント）
  - execution/
    - __init__.py            — 実行（発注）関連モジュール（拡張ポイント）
  - monitoring/
    - __init__.py            — 監視・メトリクス関連（拡張ポイント）

---

## 拡張ポイント / 開発メモ

- strategy/ と execution/ は空のパッケージとして用意しているため、戦略実装・リスク管理・発注アダプタ（kabuステーション）をここに実装して統合してください。
- news_collector の _urlopen はテスト時にモック差し替え可能な設計になっています。
- ETL パイプラインは id_token を注入してテストしやすいようになっています。
- DuckDB の SQL はパラメータバインド（?）を使うことでインジェクションリスクを低減しています。

---

## ライセンス / 貢献

（ここにプロジェクトのライセンス情報や貢献方法を記載してください。リポジトリの LICENSE を参照するなど）

---

README はこのコードベースの主要な利用方法と構造をまとめたものです。追加で CLI やユニットテストの実行方法、CI 設定例、運用手順（デプロイ／ローテーション／バックアップ）などを含めたい場合は、必要な情報を教えてください。