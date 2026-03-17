# KabuSys

日本株自動売買プラットフォームのライブラリ群（KabuSys）。  
データ収集（J‑Quants / RSS）、ETLパイプライン、データ品質チェック、DuckDBスキーマ、監査ログなどを提供します。戦略・実行・監視層はパッケージ化されており、独自の実装を組み込んで拡張できます。

---
目次
- プロジェクト概要
- 主な機能
- 前提条件
- セットアップ手順
- 環境変数（設定項目）
- 使い方（主要API例）
- ディレクトリ構成
- その他（設計上の注意点）

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム用に設計されたライブラリ群です。主に以下の責務を持ちます。

- J‑Quants API からの株価・財務・市場カレンダー取得（レート制限・リトライ・トークン自動更新対応）
- RSS フィードからのニュース収集と前処理（SSRF対策、サイズ制限、トラッキング除去）
- DuckDB を用いたデータスキーマ（Raw / Processed / Feature / Execution 層）定義と初期化
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ用スキーマ（signal → order_request → executions のトレーサビリティ）

設計上、冪等性・トレーサビリティ・外部依存（APIレート、SSRF や XML 攻撃）への防御を重視しています。

---

## 主な機能

- jquants_client
  - 日足（OHLCV）、四半期財務（BS/PL）、JPXカレンダー取得
  - レート制御（120 req/min 固定間隔スロットリング）
  - リトライ（指数バックオフ、特定 status の再試行）、401 での自動トークンリフレッシュ
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- news_collector
  - RSS 取得・XML パース（defusedxml）、URL 正規化、トラッキング除去
  - SSRF 防止（スキーム検証・プライベートIPブロック・リダイレクト検査）
  - レスポンスサイズ制限、gzip 処理
  - DuckDB への冪等保存（INSERT ... RETURNING を用いた新規判定）
  - 記事中から銘柄コード（4桁）を抽出し、news_symbols に紐付け
- data.schema
  - DuckDB のテーブル定義（Raw / Processed / Feature / Execution）
  - インデックス定義、init_schema() による初期化
- data.pipeline
  - 差分 ETL（最終取得日に基づき未取得分のみ取得）
  - backfill による後出し修正吸収
  - run_daily_etl による一連の実行（カレンダー→価格→財務→品質チェック）
- data.quality
  - 欠損、スパイク（前日比閾値）、重複、日付不整合チェック
  - QualityIssue オブジェクトで問題を集約
- data.audit
  - 監査ログ用テーブル（signal_events / order_requests / executions）
  - init_audit_schema() で監査テーブルを初期化

---

## 前提条件

- Python 3.10 以上（typing の `A | B` 等を利用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

プロジェクト固有の requirements.txt がある場合はそちらを利用してください。

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. 仮想環境を作成・有効化（推奨）
3. 依存ライブラリをインストール（上記参照）
4. 環境変数を設定（.env / .env.local を利用可能、詳細は下記）
   - 自動ロード: パッケージ import 時にプロジェクトルート（.git または pyproject.toml）を探索し、.env / .env.local を自動で読み込みます。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
5. DuckDB スキーマ初期化
   - Python REPL もしくはスクリプトで:
     ```py
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)
     ```
   - 監査ログテーブルを追加する場合:
     ```py
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)
     ```

---

## 環境変数（主な設定項目）

KabuSys は環境変数で挙動を制御します。必須は次の通りです（未設定時は ValueError を送出）:

- JQUANTS_REFRESH_TOKEN : J‑Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション API 用パスワード（必須）
- SLACK_BOT_TOKEN : Slack 通知用 BOT トークン（必須）
- SLACK_CHANNEL_ID : Slack の投稿先チャンネル ID（必須）

オプション（デフォルトあり）:

- KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV : 環境（development / paper_trading / live）。デフォルト: development
- LOG_LEVEL : ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）。デフォルト: INFO

.env のロード順序:
OS 環境変数 > .env.local > .env（つまり .env.local は .env を上書き可能）。  
OS環境変数は protected として上書きされません。テスト時などに自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

.env のパースは一般的な shell 形式に準拠（export プレフィックス・クォート・コメント取り扱い等）。

---

## 使い方（主要 API の例）

ここでは基本的な使い方を示します。

- DuckDB スキーマ初期化
```py
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数 DUCKDB_PATH を参照（デフォルト data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

- 日次 ETL の実行
```py
from kabusys.data.pipeline import run_daily_etl
# conn は上で作成した DuckDB 接続
result = run_daily_etl(conn)
print(result.to_dict())
```

- 個別ジョブ（価格・財務・カレンダー）
```py
from datetime import date
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl

target = date.today()
fetched, saved = run_prices_etl(conn, target)
```

- RSS ニュース収集（既知銘柄セットを渡して銘柄紐付け）
```py
from kabusys.data.news_collector import run_news_collection

# known_codes: 有効な銘柄コードのセット（例: {'7203','6758',...}）
results = run_news_collection(conn, known_codes={'7203', '6758'})
print(results)  # 各ソースごとの新規保存数
```

- J‑Quants の低レイヤ呼び出し例
```py
from kabusys.data.jquants_client import fetch_daily_quotes

records = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
```

---

## ディレクトリ構成

リポジトリの主要ファイル/モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数/設定の読み込み
  - data/
    - __init__.py
    - jquants_client.py     — J‑Quants API クライアント（取得・保存）
    - news_collector.py     — RSS 収集・前処理・保存
    - schema.py             — DuckDB スキーマ定義・初期化
    - pipeline.py           — ETL パイプライン（差分更新・品質チェック）
    - audit.py              — 監査ログ（signal/order_request/executions）
    - quality.py            — データ品質チェック
  - strategy/
    - __init__.py           — 戦略層（拡張用）
  - execution/
    - __init__.py           — 発注/実行層（拡張用）
  - monitoring/
    - __init__.py           — 監視用モジュール（拡張用）

（DuckDB テーブル定義は data/schema.py に集約されています）

---

## 設計上の注意点 / 運用上の留意点

- J‑Quants API のレート制限（120 req/min）に合わせて固定間隔スロットリング実装あり。大量取得や並列化時は注意してください。
- HTTP エラー（408/429/5xx）に対する再試行・指数バックオフを備えています。401 はトークンを自動リフレッシュして1回リトライする仕組みです。
- NewsCollector は SSRF・XML攻撃・gzip/サイズ爆弾対策を実装していますが、外部ソースの扱いには注意してください。
- DuckDB の INSERT に対して冪等性を考慮しているため、通常は重複挿入を気にせず運用できます。
- run_daily_etl は品質チェックで検出された問題を返しますが、処理自体はできる限り継続して完了します。呼び出し元で重大度に応じた停止や通知を行ってください。
- 監査ログは削除しない前提です（トレーサビリティのため）。order_request_id を冪等キーとして二重発注防止が設計されています。

---

## 開発 / 貢献

- コードベースを読んで機能を拡張してください。strategy／execution／monitoring の各パッケージはプラグインのように戦略やブローカー実装を追加する箇所です。
- テストを書く際は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env ロードを抑制すると便利です。
- DuckDB のテスト用に ":memory:" を使うことができます（init_schema(":memory:")）。

---

必要であれば README にサンプル .env.example、より詳しい使い方（CLI スクリプト案内、定期実行の systemd / cron 設定例、Slack 通知の実装例など）を追加します。どの情報を優先して追記しましょうか？