# KabuSys

日本株自動売買プラットフォームのライブラリ群です。データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集、DuckDBスキーマ管理、監査ログ（オーダー／約定トレーサビリティ）など、アルゴリズム取引システムの基盤機能を提供します。

バージョン: 0.1.0

---

## 目次

- プロジェクト概要
- 主な機能一覧
- 動作要件・依存関係
- セットアップ手順
- 環境変数（設定）
- 使い方（簡易ガイド）
  - DB 初期化
  - 日次 ETL 実行
  - ニュース収集ジョブ実行
  - 監査DB初期化
- ディレクトリ構成
- 設計上の注意点・セキュリティ
- 貢献・ライセンス

---

## プロジェクト概要

KabuSys は日本株自動売買システム向けのプラットフォーム基盤です。主に以下を目的としています。

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存
- RSS ベースのニュース収集と記事→銘柄紐付け
- ETL（差分取得、バックフィル、品質チェック）を組み合わせた日次パイプライン
- 監査ログ（signal → order_request → execution の追跡）ためのスキーマと初期化機能
- 市場カレンダーの扱い（営業日判定、next/prev/trading days）

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（トークン自動リフレッシュ、レート制御、リトライ、ページネーション）
  - fetch / save の各種関数: 日足（OHLCV）、財務データ、マーケットカレンダー
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- data/schema.py
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) でスキーマ初期化

- data/pipeline.py
  - 日次 ETL（run_daily_etl）: calendar → prices → financials → 品質チェック
  - 差分更新、backfill、品質チェックの統合

- data/news_collector.py
  - RSS フィード取得、記事正規化、前処理、記事ID生成（URL 正規化 + SHA-256）
  - SSRF 対策、gzip/レスポンスサイズ制限、defusedxml による XML 攻撃対策
  - raw_news / news_symbols への冪等保存（トランザクション、INSERT ... RETURNING）

- data/quality.py
  - 欠損データ、スパイク（前日比閾値）、重複、日付不整合などの品質チェック
  - QualityIssue 型で問題を収集し呼び出し元に返却

- data/calendar_management.py
  - JPX カレンダーの差分更新ジョブ
  - 営業日判定、next/prev/get_trading_days、SQ 判定

- data/audit.py
  - 監査ログ用のテーブル群（signal_events / order_requests / executions）定義
  - init_audit_schema / init_audit_db による初期化（UTCタイムゾーン固定）

- config.py
  - 環境変数管理（.env 自動ロード機能、必須設定チェック、KABUSYS_ENV 等）

---

## 動作要件・依存関係

- Python 3.10 以上（型ヒントで `|` 演算子を利用、`from __future__ import annotations` を想定）
- 主要依存パッケージ（例）:
  - duckdb
  - defusedxml
  - （標準ライブラリ: urllib, json, logging, datetime, hashlib 等）
- 実際のプロジェクトでは pyproject.toml / requirements.txt を用意して依存解決してください。

例（手動インストール）:
```
pip install duckdb defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン / 取得
2. 仮想環境を作成・有効化
3. 必要な依存をインストール（上記参照）
4. 環境変数を設定（.env または OS 環境変数）

設定は .env （プロジェクトルート） または .env.local を配置することで自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。自動ロードは、モジュールの配置位置からプロジェクトルート (.git または pyproject.toml) を探索して行われます。

簡易インストール例（開発用）:
```
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install duckdb defusedxml
```

---

## 環境変数（主なもの）

以下はコード内で参照される主な環境変数です。必須は README 中で明記します。

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。jquants_client.get_id_token で ID トークン取得に利用。

- KABU_API_PASSWORD (必須)
  - kabuステーション API 用パスワード。

- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
  - kabu ステーションのベース URL。

- SLACK_BOT_TOKEN (必須)
  - Slack 通知用トークン（必要な場合）。

- SLACK_CHANNEL_ID (必須)
  - Slack 通知先チャンネル ID。

- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
  - DuckDB ファイルパス。":memory:" でインメモリ DB。

- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
  - 監視用 DB（プロジェクトで使う場合）。

- KABUSYS_ENV (任意、デフォルト: development)
  - 有効値: development, paper_trading, live
  - is_live / is_paper / is_dev に影響。

- LOG_LEVEL (任意、デフォルト: INFO)
  - 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL

.env のサンプル（例）:
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

## 使い方（簡易ガイド）

以下は主要な操作のコード例です。Python REPL やスクリプトから利用できます。

1) DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数 DUCKDB_PATH を参照します
conn = init_schema(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection オブジェクト
```

2) 日次 ETL を実行（J-Quants から差分取得して保存・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # 引数で target_date, id_token, run_quality_checks 等を指定可能
print(result.to_dict())
```

run_daily_etl は以下を実行します（順番）:
- 市場カレンダー ETL（先読み）
- 株価日足 ETL（差分 + backfill）
- 財務データ ETL（差分 + backfill）
- 品質チェック（quality.run_all_checks）

3) ニュース収集ジョブを実行
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# known_codes を渡すとテキスト内から銘柄コード抽出して news_symbols に紐付けを行う
known_codes = {"7203", "6758"}  # 例: トヨタ、ソニー等
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)  # {source_name: 新規保存数, ...}
```

4) 監査ログ（audit）を初期化（監査専用DBを作る例）
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db("data/audit_duckdb.duckdb")
# 以降、order_requests / signal_events / executions テーブルを使用
```

5) J-Quants への直接 API 呼び出し例（テスト／デバッグ）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
id_token = get_id_token()  # settings.jquants_refresh_token を利用
quotes = fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## ディレクトリ構成

主要ファイル・ディレクトリ（src/kabusys）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（取得・保存）
    - news_collector.py              — RSS ニュース収集・前処理・保存
    - schema.py                      — DuckDB スキーマ定義・初期化
    - pipeline.py                    — ETL パイプライン（差分取得 / 品質チェック）
    - calendar_management.py         — カレンダー管理・営業日ロジック
    - audit.py                       — 監査ログ（signal/order/execution）初期化
    - quality.py                     — データ品質チェック
  - strategy/
    - __init__.py                    — 戦略関連（拡張ポイント）
  - execution/
    - __init__.py                    — 発注・エグゼキューション関連（拡張ポイント）
  - monitoring/
    - __init__.py                    — 監視モジュール（拡張ポイント）

---

## 設計上の注意点・セキュリティ

- J-Quants クライアント
  - API レート制御（120 req/min）のため固定間隔スロットリングを採用
  - リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ（1 回のみ）
  - 取得時に fetched_at を UTC で記録し、Look-ahead Bias を防止する

- NewsCollector
  - defusedxml を用いた XML パースで XML 攻撃を防止
  - レスポンスサイズの上限（10MB）や gzip 解凍後サイズチェックを実施（メモリDoS対策）
  - リダイレクト時のホスト検査やスキーム検査で SSRF を防止
  - URL 正規化とトラッキングパラメータ除去により記事IDを安定化（冪等性）

- DB 保存
  - raw 層への保存は冪等（ON CONFLICT DO UPDATE / DO NOTHING）を意識
  - 多量データの INSERT はチャンク化して実行

- トランザクション
  - news_collector の保存や audit の一部関数はトランザクションで保護される（失敗時はロールバック）

---

## 開発・貢献

- strategy / execution / monitoring は拡張ポイントです。具体的な売買ロジックや接続（kabuステーション連携）実装はプロジェクトごとに追加してください。
- 変更を加える場合はユニットテストを追加し、特に ETL / 品質チェック / news_collector の境界条件（大きなレスポンス、XML 不正、非公開ホストのリダイレクト等）を重点的にテストしてください。

---

## ライセンス

このリポジトリのライセンス情報は含まれていません。利用・配布の前にライセンスを明確にしてください。

---

必要であれば、README に下記を追加できます：
- requirements.txt / pyproject.toml のサンプル
- CI/CD / GitHub Actions のワークフロー例（ETL の定期実行）
- 実運用時の監視・アラート設計（Slack 通知例）