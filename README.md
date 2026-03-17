# KabuSys

日本株向けの自動売買（データ収集・ETL・監査）ライブラリ/フレームワークです。J-Quants や RSS フィードからのデータ収集、DuckDB スキーマ定義、日次 ETL パイプライン、ニュースの前処理・銘柄抽出、監査ログ（発注→約定トレース）などを提供します。

---

## 主な特徴（機能一覧）

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）対応のスロットリング
  - リトライ（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ
  - fetched_at（UTC）記録による Look-ahead Bias 対策

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層を含む完全な DDL
  - インデックス定義、冪等なテーブル作成（CREATE IF NOT EXISTS）
  - init_schema(), get_connection(), init_audit_db() での初期化サポート

- ETL パイプライン
  - 差分更新（最終取得日を参照）、バックフィル機能
  - 日次 ETL エントリ run_daily_etl()
  - 品質チェック（欠損・スパイク・重複・日付不整合）の実行

- ニュース収集（RSS）
  - RSS 取得、XML の安全パース（defusedxml）
  - URL 正規化、トラッキングパラメータ除去、SHA-256 ベースの記事 ID 生成（冪等）
  - SSRF 対策（スキーム検証・プライベートホスト検出・リダイレクト検査）
  - raw_news / news_symbols への冪等保存（バルク INSERT、INSERT ... RETURNING）

- 監査ログ（Audit）
  - signal_events / order_requests / executions 等で戦略→発注→約定のトレーサビリティを保証
  - order_request_id を冪等キーとして二重発注防止
  - UTC 時間管理

- データ品質モジュール
  - QualityIssue 型で問題を集約、run_all_checks() で一括実行

---

## セットアップ

前提:
- Python 3.9+（型注釈や Path 型が使用されています）
- DuckDB を利用するため duckdb パッケージ
- RSS XML パースのため defusedxml

例: pip でインストール
```
pip install duckdb defusedxml
```

環境変数:
- 自動でプロジェクトルート（.git または pyproject.toml）を探し、`.env` と `.env.local` をロードします（優先度: OS 環境 > .env.local > .env）。
- 自動ロードを無効化するには環境変数を設定:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数（Settings で必須とされるもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID

任意／デフォルト:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（値は任意の真値）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）

例: .env の最小例（実際の値は秘密情報なので置換してください）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 初期化・使い方（主な API）

以下は Python スクリプトから使う基本パターンです。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema

# ファイル DB を作成して全テーブル・インデックスを作成
conn = schema.init_schema("data/kabusys.duckdb")
# 既存 DB に接続する場合は:
# conn = schema.get_connection("data/kabusys.duckdb")
```

2) 監査 DB 初期化（監査専用 DB を分離する場合）
```python
from kabusys.data import audit

audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

3) 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
```python
from datetime import date
from kabusys.data import pipeline, schema

conn = schema.get_connection("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

オプション:
- id_token を渡してトークン注入することも可能（テスト用）
- run_quality_checks=False にして品質チェックをスキップ可能

4) J-Quants の個別クライアント（直接利用）
```python
from kabusys.data import jquants_client as jq
# トークンは settings.jquants_refresh_token を利用して自動で取得されます
prices = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
# DuckDB へ保存するには conn を渡す
saved = jq.save_daily_quotes(conn, prices)
```

5) ニュース収集ジョブ
```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")
# sources を省略すると DEFAULT_RSS_SOURCES を使用
results = news_collector.run_news_collection(conn, known_codes={"7203", "6758"})  # known_codes は候補コード集合
print(results)  # {source_name: saved_count}
```

6) 銘柄抽出（ユーティリティ）
```python
from kabusys.data.news_collector import extract_stock_codes
codes = extract_stock_codes("本日の注目銘柄は 7203 と 6758 です", known_codes={"7203","6758"})
# -> ['7203','6758']
```

---

## 実装上の注意点 / 設計ポリシー（簡潔に）

- J-Quants API に対しては固定間隔のレートリミット（120 req/min）を守るよう実装されています。
- API 通信は最大3回のリトライ（指数バックオフ）を行い、401 は自動でトークンをリフレッシュして再試行します。
- データの保存は冪等（ON CONFLICT DO UPDATE / DO NOTHING）で行われ、再実行可能な ETL を想定しています。
- ニュース取得は SSRF や XML Bombe 等の攻撃対策を施しています（スキーム検証、プライベートアドレス検査、defusedxml、レスポンスサイズ上限）。
- 監査ログは発注から約定までを UUID 連鎖で完全にトレース可能に設計されています。

---

## 推奨ワークフロー（運用例）

- 夜間バッチ:
  1. schema.init_schema() 実行（初回のみ）
  2. run_daily_etl() を cron / Airflow 等で毎朝実行
  3. calendar_update_job() を定期的に実行して market_calendar を先読み
  4. ニュース収集を定期実行して raw_news を蓄積・銘柄紐付け

- ライブ取引:
  - KABUSYS_ENV を `live` に設定し、監査ログ（init_audit_db）を有効にして発注フローを運用
  - リスク管理・ポジション管理の層でシグナルの棄却ログ等も記録

---

## ディレクトリ構成

（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境設定・Settings クラス（.env 自動ロード、必須キーチェック）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（fetch/save 系）
    - news_collector.py           — RSS ニュース収集・前処理・DB 保存ロジック
    - schema.py                   — DuckDB スキーマ定義・初期化（init_schema）
    - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py      — カレンダー管理ユーティリティ（is_trading_day 等）
    - audit.py                    — 監査ログ（signal_events, order_requests, executions）
    - quality.py                  — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py                 — 戦略層（拡張用）
  - execution/
    - __init__.py                 — 発注・約定管理（拡張用）
  - monitoring/
    - __init__.py                 — 監視・メトリクス（拡張用）

---

## 追加情報 / トラブルシューティング

- .env の自動ロードが行われない場合:
  - プロジェクトルートの判定は __file__ を起点に `.git` または `pyproject.toml` を探索します。ルートが見つからない場合は自動ロードをスキップします。
  - テスト等で自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

- DuckDB のファイルパス:
  - デフォルトは data/kabusys.duckdb。別パスを環境変数 DUCKDB_PATH にて指定可能。

- ロギング:
  - 環境変数 LOG_LEVEL でログレベルを制御可能（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

---

README はここまでです。必要であれば以下を追加作成できます:
- .env.example のテンプレートファイル
- 具体的な cron / systemd / Airflow の実行例
- 戦略・発注フローのサンプルコード（strategy/execution 層のテンプレ）
- テストの実行方法（ユニットテスト、モックの置き換え方）