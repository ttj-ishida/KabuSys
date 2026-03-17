# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ／コンポーネント群です。  
データ収集（J-Quants、RSS）、ETL パイプライン、データ品質チェック、DuckDB スキーマ定義、監査ログ（トレーサビリティ）など、アルゴリズム取引システムで必要となる基盤処理を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のような機能を持つモジュール群です。

- J-Quants API からの株価（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーの取得
  - レートリミット制御、リトライ、トークン自動リフレッシュ、ページネーション対応
  - 取得時刻（fetched_at）を保存して Look-ahead Bias を回避
- RSS フィードからのニュース収集（トラッキングパラメータ除去・SSRF 対策・gzip サイズ制限）
- DuckDB 用のスキーマ定義（Raw / Processed / Feature / Execution 層）
- 監査ログ（signal → order_request → execution）用スキーマ
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- 品質チェック（欠損・重複・スパイク・日付不整合検出）
- 環境変数による設定管理（.env 自動読み込みをサポート）

設計方針としては「冪等性」「堅牢なネットワーク処理」「監査性」を重視しています。

---

## 主な機能一覧

- data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar (DuckDB に冪等保存)
  - get_id_token（リフレッシュトークンからIDトークン取得）
  - 内部でレートリミット/リトライ/401リフレッシュを実装

- data.news_collector
  - fetch_rss（SSRF対策、gzip上限、XMLパースの安全化）
  - save_raw_news, save_news_symbols（DuckDB にトランザクションで保存、ON CONFLICTで重複排除）
  - extract_stock_codes（テキスト中の 4 桁銘柄コード抽出）

- data.schema / data.audit
  - DuckDB スキーマ作成 (init_schema, init_audit_schema, init_audit_db)
  - Raw / Processed / Feature / Execution / Audit テーブル定義、インデックス

- data.pipeline
  - run_daily_etl（カレンダー取得 → 株価 ETL → 財務 ETL → 品質チェック）
  - 差分更新、バックフィル、ETL 結果を ETLResult として返す

- data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency
  - run_all_checks（すべての品質チェックをまとめて実行）

- config
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - Settings API（settings.jquants_refresh_token など）で環境変数を抽象化
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化

---

## 前提 / 必要要件

- Python 3.10 以上（型アノテーションで `X | None` を使用）
- 必要ライブラリ（最低限）
  - duckdb
  - defusedxml

※ネットワーク呼び出しは標準ライブラリの urllib を使用しているため、requests は必須ではありませんが、プロダクション用途で別の HTTP クライアントを組み合わせることは可能です。

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

（プロジェクトをパッケージ化している場合は `pip install -e .` や requirements.txt を使ってください）

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（実運用で必要な場合）
- SLACK_BOT_TOKEN — Slack 通知用（必要な場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意 / デフォルトあり:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）

自動読み込み:
- プロジェクトルート（このモジュールのファイル位置から探索）にある `.env` と `.env.local` を自動で読み込みます。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化します。

未設定の必須変数を参照すると ValueError が発生します（Settings._require）。

---

## セットアップ手順（簡易）

1. リポジトリをクローン / プロジェクトを取得
2. Python 仮想環境を作成・有効化
3. 依存パッケージをインストール
   ```
   pip install duckdb defusedxml
   ```
4. 環境変数を設定
   - プロジェクトルートに `.env` を作成（または環境変数に直接設定）
   - 必須キー（上記参照）を設定
5. DuckDB スキーマの初期化
   - Python REPL またはスクリプトで実行:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     ```
6. （監査ログ用）監査スキーマの初期化（既存接続に追加）
   ```python
   from kabusys.data import audit
   audit.init_audit_schema(conn)
   ```

---

## 使い方（サンプル）

- J-Quants の ID トークンを手動で取得する:
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token が使われる
```

- 株価を取得して保存する（差分 ETL の小さい例）:
```python
from datetime import date
import duckdb
from kabusys.data import schema, jquants_client

conn = schema.init_schema("data/kabusys.duckdb")
# 直近日までの差分を取得して保存（run_prices_etl を使う例は pipeline 参照）
records = jquants_client.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date.today())
saved = jquants_client.save_daily_quotes(conn, records)
print(f"保存されたレコード数: {saved}")
```

- RSS 収集と保存:
```python
from kabusys.data import news_collector, schema
conn = schema.init_schema("data/kabusys.duckdb")

# デフォルトで定義されている RSS ソースから収集
results = news_collector.run_news_collection(conn, known_codes={"7203","6758", ...})
print(results)  # {source_name: 新規保存件数}
```

- 日次 ETL の実行:
```python
from kabusys.data import pipeline, schema
from datetime import date

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 品質チェックのみ実行:
```python
from kabusys.data import quality, schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

メソッドの多くは DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。ユニットテストなどでは ":memory:" を指定してインメモリ DB を利用できます。

---

## 注意点 / 実装上のポイント

- J-Quants クライアントは 120 req/min のレート制限を固定間隔スロットリングで守ります（RateLimiter）。
- HTTP エラー時は最大3回まで指数バックオフでリトライ。429 の場合は Retry-After を優先します。
- 401 受信時はリフレッシュトークンを使って ID トークンを自動更新して 1 回だけリトライします。
- DuckDB への保存は冪等性を考慮して ON CONFLICT DO UPDATE / DO NOTHING を使っています。
- RSS 収集は SSRF 対策（スキーム検査、プライベートホスト検査、リダイレクト検査）と XML の安全パーサ（defusedxml）を使用しています。
- news_collector は記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保します。
- config モジュールはプロジェクトルートの .env / .env.local を自動読み込みします（テスト時は無効化可能）。

---

## ディレクトリ構成

以下は本リポジトリ内の主要ファイル／モジュール構成の概観です（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得 + 保存）
    - news_collector.py             — RSS ニュース収集・保存
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - schema.py                     — DuckDB スキーマ定義と初期化
    - audit.py                      — 監査ログ（signal / order_requests / executions）
    - quality.py                    — データ品質チェック
  - strategy/
    - __init__.py                   — 戦略関連（拡張ポイント）
  - execution/
    - __init__.py                   — 発注関連（拡張ポイント）
  - monitoring/
    - __init__.py                   — モニタリング関連（拡張ポイント）

この構成は、Raw → Processed → Feature → Execution の層分けを反映しており、各層での拡張が容易な設計になっています。

---

## 拡張 / 統合のヒント

- kabuAPI（発注・約定処理）、Slack 通知、監視ジョブなどは strategy / execution / monitoring パッケージを拡張して実装してください。
- テスト時は環境自動ロードを無効化:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- DuckDB を複数プロセスで共有する場合は排他制御に注意してください（DuckDB の運用上の制約）。

---

## ライセンス / 貢献

この README はコードベースに基づくドキュメントです。実運用に導入する際は、外部 API の利用規約や認証情報の管理、システム運用（監視・障害対応）を十分に検討してください。

貢献や改善提案はプルリクエストで歓迎します。

--- 

必要があれば、README に実際の .env.example のテンプレートや、より詳細な運用手順（cron / Airflow / Prefect によるスケジューリング例、ログ設定、監視アラート設定など）を追記します。どの箇所を詳しく追加しますか？