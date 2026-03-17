# KabuSys

日本株向けの自動売買基盤ライブラリです。データ収集（J-Quants / RSS）、ETL パイプライン、データ品質チェック、マーケットカレンダー管理、監査ログ（発注〜約定トレース）など、アルゴリズム取引に必要な基盤機能を提供します。

主な設計方針：
- データ取得は冪等（idempotent）に保存する（DuckDB の ON CONFLICT / DO UPDATE を利用）
- API レート制御・リトライ・トークン自動刷新などを組み込み
- データ品質チェックを自動化して、ETL 後に問題を検知可能
- RSS ニュース収集は SSRF / XML Bomb 等のセキュリティ対策を実装

---

## 機能一覧

- J-Quants API クライアント
  - 株価日足（OHLCV）/ 財務（四半期 BS/PL）/ JPX マーケットカレンダー取得
  - レートリミット（120 req/min）対応、指数バックオフ・リトライ、401 時のトークン自動刷新
  - 取得タイミング（fetched_at）を UTC で記録（Look-ahead Bias 対策）
- DuckDB スキーマ定義と初期化
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - インデックス定義、監査ログ用のスキーマ初期化も提供
- ETL パイプライン
  - 差分取得（最終取得日を基に自動算出）とバックフィル
  - prices / financials / market calendar の日次 ETL（run_daily_etl）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS）
  - RSS フィード取得 → 前処理 → raw_news に冪等保存
  - 記事ID は正規化 URL の SHA-256（先頭32文字）
  - SSRF 対策、受信サイズ制限、XML パースの安全化（defusedxml）
  - 銘柄コード抽出と news_symbols への紐付け
- マーケットカレンダー管理
  - 営業日判定 / 翌営業日・前営業日 / 期間の営業日リスト / SQ 判定
  - 夜間バッチ更新ジョブ（calendar_update_job）
- 監査ログ（audit）
  - signal_events / order_requests / executions のスキーマ
  - 発注から約定までのトレーサビリティを保持

---

## 必須要件（推奨）

- Python 3.10+
- 依存パッケージ（例）
  - duckdb
  - defusedxml

（実プロジェクトでは pyproject.toml / requirements.txt を用意してください）

---

## セットアップ手順

1. リポジトリをチェックアウト／クローン
   - 例: git clone <repo-url>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージ配布がある場合は pip install -e . など）

4. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（ただしテスト時などは自動ロードを無効化可能）。
   - 自動ロードを無効化する場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

---

## 環境変数

config.Settings から参照される主要な環境変数：

必須:
- JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      — kabuステーション API のパスワード
- SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       — Slack チャンネル ID

オプション（デフォルトあり）:
- KABU_API_BASE_URL      — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV            — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL              — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

例 .env（最低限の必須項目を埋める）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## データベース初期化

DuckDB スキーマを初期化するには data.schema.init_schema を使います。

Python スクリプト例:
```python
from kabusys.data import schema
# ファイル DB を作成して全テーブルを初期化
conn = schema.init_schema("data/kabusys.duckdb")
# 監査ログを別 DB にする場合:
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

既存 DB に接続する場合:
```python
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")
```

監査テーブルを既存接続に追加する:
```python
from kabusys.data import audit
audit.init_audit_schema(conn)
```

---

## 使い方（主要 API）

以下はライブラリを直接呼び出す方法の例です。

1) 日次 ETL の実行（株価・財務・カレンダー取得 + 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

オプション:
- id_token を渡してトークンを注入可能（テスト用）
- run_quality_checks=False で品質チェックをスキップ

2) 市場カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn, lookahead_days=90)
print("saved:", saved)
```

3) ニュース収集（RSS）と保存
```python
from kabusys.data.news_collector import run_news_collection
# known_codes: 銘柄コードのセット（抽出に使う）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

4) J-Quants からの個別取得（例: 株価日足フェッチ）
```python
from kabusys.data import jquants_client as jq
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
# DuckDB 保存
saved = jq.save_daily_quotes(conn, records)
```

5) 品質チェックの直接実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None, reference_date=None)
for i in issues:
    print(i)
```

---

## ログ・実行モード

- 環境変数 KABUSYS_ENV により動作モードを切替（development / paper_trading / live）。
- LOG_LEVEL でログレベルを制御。
- 自動環境変数の .env 読み込みはデフォルトで有効。テスト時に無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## ディレクトリ構成

リポジトリの主要ファイル/モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得 + DuckDB 保存）
    - news_collector.py      — RSS ニュース収集・保存・銘柄抽出
    - pipeline.py            — ETL パイプライン（run_daily_etl 他）
    - calendar_management.py — マーケットカレンダー管理（判定/更新ジョブ）
    - schema.py              — DuckDB スキーマ定義・初期化
    - audit.py               — 監査ログスキーマ（signal/order/execution）
    - quality.py             — データ品質チェック
  - strategy/                 — 戦略関連（未実装のエントリ）
  - execution/                — 発注実行関連（未実装のエントリ）
  - monitoring/               — 監視関連（未実装のエントリ）

---

## 開発 / テストに関する注意

- モジュールは多くの箇所でネットワークアクセスやファイル I/O を行います。ユニットテストでは外部呼び出し（_urlopen, urllib, jquants API 等）をモックして実行してください。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を推奨します。
- DuckDB を用いるため、軽量にローカルでの実行・検証が可能です。

---

補足や README に加えたい内容（例: コマンドラインツール、CI 設定、運用手順、Slack 通知のサンプル）があれば教えてください。必要に応じて README を拡張します。