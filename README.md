# KabuSys

日本株向け自動売買プラットフォームのライブラリ群（KabuSys）。  
J-Quants / kabuステーション 等からデータを取得・蓄積し、ETL・品質チェック・ニュース収集・監査ログ等の基盤機能を提供します。

---

## プロジェクト概要

KabuSys は次のような用途を想定した内部ライブラリです。

- J-Quants API から株価（日足）、財務データ、JPX カレンダーを取得して DuckDB に保存
- RSS フィードからニュースを収集して記事テーブルに保存し、銘柄コードと紐付け
- ETL パイプライン（差分取得・バックフィル・品質チェック）の実装
- マーケットカレンダーを用いた営業日判定ユーティリティ
- 監査ログ（シグナル → 発注 → 約定）用スキーマの定義と初期化

設計上の特徴:
- API レート制御、リトライ、トークン自動更新を備えた堅牢なクライアント実装
- DuckDB に対する冪等保存（ON CONFLICT）とトランザクション管理
- RSS 取得における SSRF 対策・サイズ制限・XML サニタイズ
- 品質チェックで欠損・スパイク・重複・日付不整合を検出

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants からのデータ取得（株価、財務、カレンダー）
  - レート制限、リトライ、id_token 自動更新
  - DuckDB への保存関数（save_*） — 冪等性を保証

- data/pipeline.py
  - 日次 ETL（run_daily_etl）: カレンダー→株価→財務→品質チェックの順で差分更新
  - 個別 ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
  - 差分取得・バックフィルロジック

- data/news_collector.py
  - RSS フィード取得（fetch_rss）、記事前処理、ID 生成、DuckDB への保存（save_raw_news）
  - 銘柄抽出（extract_stock_codes）、一括紐付け保存

- data/schema.py
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) による初期化

- data/calendar_management.py
  - 営業日判定、次/前営業日取得、期間内営業日列挙、夜間カレンダー更新ジョブ

- data/quality.py
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - run_all_checks でまとめて実行し QualityIssue リストを返す

- data/audit.py
  - 監査用テーブル（signal_events, order_requests, executions）定義と初期化

- config.py
  - 環境変数 / .env 読み込み（プロジェクトルート自動検出）
  - settings オブジェクト経由で各種設定にアクセス

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントに `X | None` を使用）
- Git クローン済みでプロジェクトに pyproject.toml または .git が存在することを想定

推奨パッケージ（本コードベースで使用している外部依存）
- duckdb
- defusedxml

例: 仮想環境を作って依存を入れる
```
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# 開発インストール（パッケージ化されている場合）
pip install -e .
```

環境変数設定
- プロジェクトルートの `.env` / `.env.local` を自動で読み込みます（優先順位: OS 環境 > .env.local > .env）。
- 自動読み込みを無効にするには環境変数を設定:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（settings で参照されるもの）
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（省略時: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（省略時: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...)（省略時: INFO）

例（.env の最小例）
```
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的な例）

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# conn は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）
```

2) 日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")  # 事前に schema.init_schema を呼ぶこと
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) RSS ニュース収集（既知銘柄コードを渡して紐付け）
```python
from kabusys.data.news_collector import run_news_collection
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9432"}  # 例: 有効な銘柄コードセット
results = run_news_collection(conn, sources=None, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

4) カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved={saved}")
```

5) 監査ログスキーマの追加（既存の DB 接続に対して）
```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn)
```

6) 設定の参照（コード内）
```python
from kabusys.config import settings
token = settings.jquants_refresh_token
is_live = settings.is_live
db_path = settings.duckdb_path
```

ログや詳細なエラーは Python の logging 設定で出力先・レベルを制御してください。

---

## ディレクトリ構成（抜粋）

以下はソースツリーの主要ファイル一覧（src/kabusys 配下）です。

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

主要な機能は data パッケージに集中しており、strategy / execution / monitoring は将来の拡張ポイントになります。

---

## 開発メモ / 実運用上の注意

- Python バージョンは 3.10 以上を推奨（型ヒントと新しい構文を使用）。
- DuckDB ファイルはパスの親ディレクトリが自動作成されますが、バックアップやローテーション運用を検討してください。
- J-Quants API のレート制限（120 req/min）および ID トークンの管理は jquants_client で行いますが、運用負荷に応じて適切にスケジューリングしてください。
- ニュース取得では外部 URL の検証（SSRF 対策）と受信サイズ制限が組み込まれていますが、不審なフィードは監視・ブロックしてください。
- run_daily_etl は各ステップでエラーをキャッチして継続する設計です。結果オブジェクト（ETLResult）の errors / quality_issues を必ず確認して運用判断を行ってください。
- .env の自動読み込みはプロジェクトルートを基準に行います。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自前で環境をセットアップしてください。

---

## 貢献

バグレポートや機能追加は Pull Request / Issue を送ってください。コードの変更はユニットテストおよび DuckDB に対するクリーンなスキーマ変更を伴うことを推奨します。

---

以上。必要であれば README にサンプル .env.example、より詳細な起動スクリプト、CI / cron での運用例などを追加します。どの情報を優先して追記しますか？