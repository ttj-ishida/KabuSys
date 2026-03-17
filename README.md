# KabuSys

日本株向けの自動売買プラットフォームのコアライブラリ（プロトタイプ）。  
データ取得・ETL、ニュース収集、データ品質チェック、監査ログ／トレーサビリティ、DuckDB スキーマ定義など、取引システムの基盤的機能を提供します。

---

## プロジェクト概要

KabuSys は日本株向けに設計された自動売買システム基盤で、主に以下を目的としています。

- J-Quants API からの市場データ（株価日足・財務・マーケットカレンダー）取得
- RSS からのニュース収集と記事→銘柄紐付け
- DuckDB によるデータレイヤ（Raw / Processed / Feature / Execution）のスキーマ管理
- 日次 ETL パイプライン（差分取得 / 冪等保存 / 品質チェック）
- 監査ログ（signal → order → execution のトレース可能性）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の特徴として、API レート制御・リトライ・トークン自動リフレッシュ・冪等性確保・SSRF 対策などを備えています。

---

## 機能一覧

- 環境変数・設定管理（自動 .env ロード）
  - 自動でプロジェクトルートを探し `.env`, `.env.local` を読み込む（無効化可能）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - get_id_token（リフレッシュ）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - API レート制御（120 req/min）、リトライ、401 時の自動トークン更新
  - DuckDB への冪等保存関数（save_daily_quotes 等）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得（gzip 対応）、XML の安全パース（defusedxml）
  - URL 正規化・トラッキングパラメータ除去・記事 ID は URL ハッシュ（冪等）
  - SSRF 対策（スキーム/プライベート IP 検査）、レスポンス上限
  - raw_news / news_symbols への安全な一括保存
- スキーマ定義（kabusys.data.schema）
  - DuckDB の Raw / Processed / Feature / Execution 層テーブル定義
  - init_schema() での冪等初期化、インデックス作成
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日ベース）、バックフィル、品質チェック連携
  - run_daily_etl による一括実行（カレンダー → 価格 → 財務 → 品質チェック）
- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job による先読み更新（バックフィル含む）
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions など、監査用テーブルの初期化
  - init_audit_schema / init_audit_db
- 品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク、重複、日付不整合（future / non-trading-day）を検出
  - QualityIssue オブジェクトで詳細を返却

補足: strategy/execution/monitoring パッケージの初期化ファイルは用意されています（拡張ポイント）。

---

## セットアップ手順

前提:
- Python 3.9+ を想定（型ヒントに union 型などを使用）
- DuckDB を使用（pip インストール可能）
- ネットワークアクセス（J-Quants API, RSS）

1. リポジトリをクローン／チェックアウト
   - 例: git clone <repo-url>

2. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (macOS/Linux)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   最低限必要な外部依存:
   - duckdb
   - defusedxml
   例:
   - pip install duckdb defusedxml

   （パッケージ配布用の setup/pyproject があれば pip install -e . を使用してください）

4. 環境変数の設定
   プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` を置くと自動で読み込まれます（テスト時等で読み込みを無効化したい場合は env 変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   主に必要な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーションAPI パスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用 BOT トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 実行環境 [development|paper_trading|live]（デフォルト: development）
   - LOG_LEVEL: ログレベル [DEBUG|INFO|WARNING|ERROR|CRITICAL]（デフォルト: INFO）

   簡単な .env 例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（サンプル）

以下は主要なユースケースの簡単な例です。実行前に依存パッケージと `.env` を準備してください。

- DuckDB スキーマ初期化
```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリを自動作成）
conn = schema.init_schema("data/kabusys.duckdb")
```

- 監査ログスキーマ初期化（既存の接続に追加する）
```python
from kabusys.data import audit
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn)
```

- J-Quants から日次 ETL を実行（run_daily_etl）
```python
from kabusys.data import pipeline, schema

conn = schema.get_connection("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

- RSS ニュース収集（run_news_collection）
```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")
# known_codes を渡すと記事→銘柄紐付けを行う
known_codes = {"7203", "6758", "9984"}  # 実運用では有効な全銘柄コードを渡す
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)  # ソース毎の新規保存数
```

- J-Quants API を直接使う（認証・取得）
```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# トークンは settings から自動取得されるため通常は省略可能
records = jq.fetch_daily_quotes(code="7203", date_from=None, date_to=None)
jq.save_daily_quotes(conn, records)
```

注意点:
- run_daily_etl は品質チェックを行い、QualityIssue のリストを ETLResult に格納します。
- jquants_client はモジュールレベルで id_token をキャッシュし、401 を受け取ったら自動で一度リフレッシュして再試行します。
- save_* 関数は ON CONFLICT / DO UPDATE などを使い冪等性（重複更新）を担保します。

---

## 開発者向けメモ / 実装上の特徴

- 環境変数ローダーは .env を自動検出して読み込むが、CI やテスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
- jquants_client:
  - レート制限: 120 req/min（固定間隔スロットリング）
  - リトライ: ネットワークエラーや 408/429/5xx に対して指数バックオフで最大 3 回
  - 401 の場合はトークン自動リフレッシュ（1回）
  - ページネーション対応。ページ間で id_token を共有
  - データ取得時間（fetched_at）を UTC で保存し、Look-ahead bias を抑える設計
- news_collector:
  - defusedxml を使用して XML による攻撃対策
  - リダイレクト時にスキーム・ホストを検査しプライベートアドレスへのアクセスを防ぐ
  - レスポンスサイズ上限（デフォルト 10MB）や gzip 解凍後のサイズ検査を実施
  - 記事 ID は正規化 URL の SHA-256 の先頭 32 文字
- DuckDB スキーマ:
  - Raw / Processed / Feature / Execution / Audit を明確に分離
  - 多数の CHECK 制約・インデックスを定義（クエリ性能と整合性向上）
- 品質チェック:
  - 失敗時に ETL を止めない（Fail-Fast ではない）。呼び出し側が severity に応じて対応

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - news_collector.py      — RSS ニュース収集・保存
    - schema.py              — DuckDB スキーマ定義・初期化
    - pipeline.py            — ETL パイプライン（差分取得・品質チェック）
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - audit.py               — 監査ログ（signal/order/execution）の定義・初期化
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py            — 戦略層（拡張ポイント）
  - execution/
    - __init__.py            — 発注実行層（拡張ポイント）
  - monitoring/
    - __init__.py            — 監視関連（拡張ポイント）

---

## よくある質問 / 注意事項

- API 利用制限に従ってください（J-Quants のレート制限等）。
- DuckDB はシングルファイル DB であり、同一ファイルへ同時多プロセス書き込みは注意が必要です（運用設計に応じたロックや単一プロセス ETL を推奨）。
- .env の取り扱いには注意してください（シークレット管理: トークン類は安全に保管）。
- news_collector では外部 URL を読み込みます。運用環境でのネットワークポリシーや RSS ソースの信頼性を考慮してください。
- production（live）モードでは is_live フラグ等を利用して発注等の振る舞いを切り替えてください。

---

もし README に加えて、セットアップ用の requirements.txt や pyproject.toml、実行スクリプト（例: CLI、cron 用ジョブ）のテンプレートを作成したい場合は、その内容（希望する依存や CLI 仕様）を教えてください。