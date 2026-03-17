# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ兼ツール群。データ収集（J-Quants）、ETL、データ品質チェック、ニュース収集、マーケットカレンダー管理、監査ログ等の基盤機能を提供します。

- 現在のバージョン: 0.1.0

## プロジェクト概要
KabuSys は日本株自動売買システムに必要な「データ基盤」と「監査／トレーサビリティ」を中心に実装されたモジュール群です。主な目的は以下です。

- J-Quants API から株価・財務・カレンダーを安全に取得し、DuckDB に冪等的に保存する
- RSS からニュースを収集して前処理・銘柄抽出・保存を行う
- ETL パイプライン（差分取得・バックフィル・品質チェック）を提供する
- マーケットカレンダー管理と営業日判定のユーティリティを提供する
- 監査ログ（シグナル → 発注 → 約定）を追跡するためのスキーマ／初期化処理を提供する

設計上の特徴：
- API レート制御、リトライ、トークン自動リフレッシュ
- Look-ahead bias を防ぐための fetched_at / UTC 管理
- DuckDB に対する冪等保存（ON CONFLICT）
- RSS の SSRF 防止・サイズ制限・XML 攻撃対策
- データ品質チェック（欠損・スパイク・重複・日付不整合）

## 機能一覧
- 環境設定管理（.env 自動読み込み、必須変数チェック）
- J-Quants API クライアント
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務（四半期 BS/PL）取得（ページネーション対応）
  - JPX カレンダー取得
  - トークン自動リフレッシュ、レート制御、リトライ
- DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日判定／次営業日／前営業日／範囲取得）
- RSS ニュース収集・前処理・記事保存（記事ID = 正規化 URL の SHA-256 ハッシュ先頭32文字）
- 銘柄コード抽出（本文中の 4 桁数字を known_codes と比較）
- 監査ログスキーマ（signal_events / order_requests / executions）と初期化ヘルパ
- データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）

## セットアップ手順

前提
- Python 3.10 以上（コード中で `X | Y` の型記法を使用）
- duckdb と defusedxml が必要

例 — 仮想環境作成と依存パッケージのインストール：

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# 実運用では他に slack 等のクライアントや kabu API ラッパーが必要になる場合があります
```

環境変数
- 必須（Settings クラスで require されるもの）
  - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD — kabu ステーション API パスワード
  - SLACK_BOT_TOKEN — Slack 通知用（利用する場合）
  - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（利用する場合）
- 任意
  - KABUSYS_ENV — 環境 (development | paper_trading | live)（デフォルト: development）
  - LOG_LEVEL — ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)（デフォルト: INFO）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

自動 .env 読み込み
- パッケージはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、
  .env → .env.local の順で環境変数を読み込みます。
- 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

## 使い方

以下は代表的な利用例です。Python インタプリタやスクリプトから使えます。

1) DuckDB スキーマ初期化（初回のみ）

```python
from kabusys.data import schema
from kabusys.config import settings

# settings.duckdb_path は Settings.duckdb_path (Path) を返します
conn = schema.init_schema(settings.duckdb_path)
# これで全テーブルとインデックスが作成されます
```

2) 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）

```python
from kabusys.data import pipeline
from kabusys.data import schema
from kabusys.config import settings
from datetime import date

conn = schema.get_connection(settings.duckdb_path)  # or init_schema()
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 個別 ETL ジョブ（株価や財務だけ実行する場合）

```python
from kabusys.data import pipeline
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
```

4) カレンダー夜間バッチジョブ

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
```

5) RSS ニュース収集と保存

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# known_codes: 抽出に使う有効銘柄コードの集合（省略すると紐付けは実行されない）
results = run_news_collection(conn, known_codes={"7203","6758"})
print(results)  # ソース毎の新規保存件数
```

6) 監査ログテーブルの初期化（監査テーブルを別DBで管理する場合）

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
# または既存の conn に対して init_audit_schema(conn)
```

ログ設定
- 簡単な例:
```python
import logging, os
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
```

テスト／開発用ヒント
- in-memory DuckDB を使うには db_path に ":memory:" を渡します。
- jquants_client の HTTP 呼び出しや news_collector._urlopen などはテストでモック可能です。

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なソースツリー（`src/kabusys`）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数／設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py      — RSS 収集・前処理・保存
    - schema.py              — DuckDB スキーマ定義・初期化
    - pipeline.py            — ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py — マーケットカレンダー管理と営業日ユーティリティ
    - audit.py               — 監査ログ（signal/order/execution）スキーマ初期化
    - quality.py             — データ品質チェック（欠損・スパイク等）
  - strategy/
    - __init__.py            — 戦略用のエントリ（将来的に戦略を追加）
  - execution/
    - __init__.py            — 発注実行層（将来的にブローカラッパー実装）
  - monitoring/
    - __init__.py            — 監視用モジュール（未実装部分のプレースホルダ）

各モジュールは役割ごとに分離されており、ETL/データ層は `kabusys.data` 配下に集約されています。

## 注意点 / 運用上のポイント
- 環境変数やシークレット（J-Quants リフレッシュトークン等）は漏洩しないよう .env ファイルや secrets 管理を利用してください。
- J-Quants API のレートリミット（デフォルト 120 req/min）を守る設計になっていますが、運用状況に応じて設定確認を行ってください。
- DuckDB のファイルパスはバックアップ／アクセス権に注意してください。監査ログは削除しない前提の設計です。
- news_collector は外部 URL を扱うため、SSRF・Gzip Bomb 等の保護ロジックを含んでいます。独自に拡張する場合はこれらの安全設計を壊さないようにしてください。
- KABUSYS_ENV に応じて実運用（live）／紙トレード（paper_trading）／開発（development）の振る舞いを切り替えることを想定しています。環境設定値の検証が Settings クラスで行われます。

---

この README は現在のコードベース（src/kabusys 以下）に基づいて作成しています。戦略層（strategy）や実行層（execution）、監視（monitoring）などは今後の実装により拡張される想定です。必要があれば、README に操作手順（cron / systemd / Docker 化）や追加の依存関係、運用フロー（アラート／Slack通知）を追記できます。