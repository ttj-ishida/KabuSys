# KabuSys

日本株自動売買プラットフォーム（ライブラリ）  
このリポジトリは、J-Quants や kabuステーション 等の外部 API から市場データを収集・保存し、ETL・品質チェック・監査ログ・ニュース収集・マーケットカレンダー管理を行うための基盤モジュール群を提供します。

主な設計方針：
- データの冪等保存（DuckDB の ON CONFLICT / DO UPDATE を活用）
- API レート制御・リトライ・トークン自動リフレッシュ
- Look-ahead bias 回避のため取得時刻（fetched_at）を記録
- セキュリティ配慮（XML の defusedxml 利用、RSS の SSRF 対策 等）
- テストしやすい設計（id_token 注入等）

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須環境変数チェック（settings オブジェクト）
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーの取得
  - レートリミッタ、指数バックオフによるリトライ、401 時のトークン自動リフレッシュ
  - DuckDB への冪等保存ヘルパー（save_*）
- ニュース収集（RSS）
  - RSS 取得、XML 安全パース、URL 正規化（トラッキングパラメータ除去）
  - 記事ID = 正規化 URL の SHA-256（先頭32文字）で冪等化
  - SSRF 対策（スキーム検証、プライベートアドレス検出、リダイレクト検査）
  - DuckDB へのバルク挿入（トランザクション、INSERT ... RETURNING を利用）
  - 銘柄抽出（本文中の 4 桁銘柄コード、known_codes フィルタ）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層 のテーブル定義と初期化
  - インデックスの作成
  - 監査ログ（signal_events / order_requests / executions 等）の初期化
- ETL パイプライン
  - 差分更新（最終取得日を基にバックフィル）
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
- マーケットカレンダー管理
  - 営業日判定・前後営業日探索・夜間バッチ更新ジョブ
- 監査ログ（トレーサビリティ）
  - 戦略→シグナル→発注要求→約定 の階層的トレーサビリティを保持
- モジュール化された strategy / execution / monitoring パッケージ（拡張用のエントリポイント）

---

## 必要条件

- Python 3.10+
  - （ソースは型注釈で `|` を使用しており、3.10 以上を想定）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
  - （ネットワーク系は標準 urllib を使用）
- 実際の運用では kabu API クライアントや Slack 等の追加パッケージが必要になる可能性があります。

インストール例（最低限の依存を入れる）:
```bash
python -m pip install duckdb defusedxml
```

もしパッケージ化されている場合は:
```bash
pip install -e .
```

---

## 環境変数（主なもの）

自動的にプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から `.env`／`.env.local` を読み込みます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（ライブラリの各機能で必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL")（デフォルト: INFO）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

.env のサンプル（.env.example を参考に作成してください）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=xxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト
2. Python 環境を作成（推奨: venv）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. 依存パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   ```
   プロジェクトに requirements.txt / pyproject.toml があればそちらを使ってください。
4. プロジェクトルートに `.env` を配置して必要な環境変数を設定
5. DuckDB スキーマの初期化（例）
   - Python REPL またはスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```
   - 監査ログ専用 DB を初期化する場合:
   ```python
   from kabusys.data.audit import init_audit_db
   conn_audit = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（主な例）

### 1) DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

### 2) 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を省略すると今日
print(result.to_dict())
```

オプション例:
- run_daily_etl(..., run_quality_checks=False)
- spike_threshold を変更してスパイク判定閾値を調整

### 3) ニュース収集ジョブを実行する
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "6501"}  # 既知の銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

個別 RSS フェッチ:
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
```

### 4) J-Quants クライアントの直接利用
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用して id_token を取得
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

### 5) 品質チェックを単体で実行
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

---

## ディレクトリ構成

大まかなファイル・フォルダ構成（ソースベース）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py             — RSS ニュース収集と DB 保存
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - schema.py                     — DuckDB スキーマ定義・初期化
    - calendar_management.py        — マーケットカレンダー管理（営業日判定等）
    - audit.py                      — 監査ログ（signal/order/execution）初期化
    - quality.py                    — データ品質チェック
  - strategy/
    - __init__.py                   — 戦略用エントリ / 拡張ポイント
  - execution/
    - __init__.py                   — 発注・約定管理の拡張ポイント
  - monitoring/
    - __init__.py                   — 監視関連（将来的に拡張）

（この README は現状の主要モジュールを反映しています。strategy / execution / monitoring は拡張用のパッケージとして用意されています。）

---

## 運用上の注意 / ベストプラクティス

- 環境変数は本番では安全に管理してください（シークレット管理システムの利用を推奨）。
- DuckDB ファイルはファイルロックやバックアップ運用を検討してください（複数プロセスの同時書き込み制御など）。
- J-Quants API レート制限を遵守するため、クライアントは内部でスロットリング・リトライを行いますが、大量収集時は十分に監視してください。
- ニュース RSS の取得では SSRF 対策とレスポンスサイズ制限を行っていますが、外部ソースの変更値や想定外の入力に対してはログを監視してください。
- 監査ログ（audit）の初期化では UTC タイムゾーンを強制しています。運用上は UTC を標準として扱うことを推奨します。

---

## 参考 / 拡張ポイント

- strategy パッケージに具体的な取引戦略を実装して signal_events / signal_queue を生成する
- execution パッケージでブローカー接続（kabuステーション）実装を追加し、order_requests → executions のフローを完成させる
- monitoring パッケージで Prometheus / Slack 通知等を追加し、ETL ジョブや実ポジションを監視する

---

問題点や追加したいドキュメント（例: API 利用手順、運用 runbook、サンプル戦略）について要望があれば知らせてください。必要に応じて README を拡張します。