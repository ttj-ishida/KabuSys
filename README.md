# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
J-Quants API / RSS ニュース等からデータを収集し、DuckDB に保存、ETL・品質チェック・監査ログ・カレンダー管理などを行うためのモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買基盤向けに設計された Python ライブラリです。  
主に以下を目的としています。

- J-Quants API から株価・財務・マーケットカレンダーを差分取得して保存
- RSS フィードからニュースを収集しテキスト前処理・銘柄紐付けを行う
- DuckDB を用いた三層（Raw / Processed / Feature）データスキーマの初期化
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダーの管理（営業日判定、前後営業日検索）
- 監査ログ（シグナル → 発注 → 約定のトレース）スキーマの提供

設計上、API レート制限・リトライ・冪等性（ON CONFLICT）・SSRF 対策・XML の安全パースなどを配慮しています。

---

## 機能一覧

- J-Quants API クライアント（jquants_client）
  - ID トークン取得（自動リフレッシュ）
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーの取得
  - レートリミット遵守（120 req/min）、リトライ／指数バックオフ実装
  - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）

- ニュース収集（news_collector）
  - RSS フィード取得、XML の安全パース（defusedxml）
  - URL 正規化・トラッキングパラメータ除去、記事ID は正規化 URL の SHA-256（先頭32文字）
  - SSRF 対策（ホストのプライベートアドレス検査、スキーム検証）
  - DuckDB への冪等保存（raw_news, news_symbols）

- DuckDB スキーマ管理（schema, audit）
  - Raw / Processed / Feature / Execution / Audit 各レイヤーのテーブル定義
  - スキーマ初期化関数（init_schema, init_audit_schema / init_audit_db）

- ETL パイプライン（pipeline）
  - 日次 ETL エントリ（run_daily_etl）：カレンダー・日足・財務の差分取得＋品質チェック
  - 部分 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
  - 差分更新 + backfill サポート（API 後出し修正に対応）

- 品質チェック（quality）
  - 欠損（OHLC）検出、スパイク（前日比）検出、重複検出、日付不整合検出
  - QualityIssue オブジェクトで報告（severity: error / warning）

- マーケットカレンダー管理（calendar_management）
  - 営業日判定、前後営業日取得、期間内営業日列挙
  - カレンダー夜間更新ジョブ（calendar_update_job）

- 設定管理（config）
  - 環境変数 / .env 自動読み込み機能（プロジェクトルートの検出）
  - 必須値チェック、環境（development / paper_trading / live）判定、ログレベル判定

---

## 前提 / 必要環境

- Python 3.9+（型ヒントに union 表現や typing の機能を使用）
- 必要な Python パッケージ例:
  - duckdb
  - defusedxml

（プロジェクトに requirements.txt があればそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローン

   git clone <リポジトリURL>
   cd <プロジェクトディレクトリ>

2. 仮想環境作成（推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール

   pip install duckdb defusedxml
   # 実際は requirements.txt があれば:
   # pip install -r requirements.txt

4. 環境変数設定（.env を作成）
   プロジェクトルートに `.env`（または `.env.local`）を置くと自動でロードされます（※自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   必須環境変数（例）:
   - JQUANTS_REFRESH_TOKEN  （J-Quants のリフレッシュトークン）
   - KABU_API_PASSWORD      （kabuステーション用パスワード）
   - SLACK_BOT_TOKEN        （Slack 通知に使う BOT トークン）
   - SLACK_CHANNEL_ID       （Slack チャンネル ID）

   オプション:
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - KABUSYS_ENV (development | paper_trading | live) デフォルト development
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマの初期化

   Python REPL またはスクリプト内で:

   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

   監査ログ（audit）を別 DB に分ける場合:
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（主要な使用例）

以下は典型的な利用フローの抜粋です。

- J-Quants API を直接呼ぶ（ID トークン取得・データ取得）

```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes

# id_token を明示的に取得（自動で settings.jquants_refresh_token を参照）
token = get_id_token()

# 特定銘柄の日足取得
records = fetch_daily_quotes(id_token=token, code="7203", date_from=date(2024,1,1), date_to=date(2024,2,1))
```

- 日次 ETL 実行（推奨エントリポイント）

```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # デフォルトで本日分を処理して品質チェックも実行
print(result.to_dict())
```

- ニュース収集ジョブ（RSS を収集して保存、銘柄紐付け）

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")

# known_codes は抽出に使用する有効銘柄コードの集合（例: 4桁コード文字列）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

- 市場カレンダー更新ジョブ（夜間バッチ）

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved", saved)
```

- 品質チェック単体実行

```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

注意点:
- jquants_client は内部でレートリミットとリトライを管理します（120 req/min、最大 3 回リトライ、401 の場合は自動リフレッシュを試みます）。
- news_collector は SSRF 対策、gzip 解凍サイズ制限、XML 安全パースを行います。
- ETL は差分取得・backfill を行い、品質チェック結果を ETLResult にまとめて返します。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py  — 環境変数/設定管理
- execution/ __init__.py
- strategy/  __init__.py
- monitoring/ __init__.py
- data/
  - __init__.py
  - jquants_client.py        — J-Quants API クライアント（取得・保存）
  - news_collector.py       — RSS ニュース収集と保存
  - schema.py               — DuckDB スキーマ定義・初期化
  - pipeline.py             — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py  — マーケットカレンダー管理
  - audit.py                — 監査ログ（signal/events/orders/executions）
  - quality.py              — データ品質チェック

プロジェクトルート（想定）
- .env / .env.local （環境変数）
- pyproject.toml または setup.py（パッケージ化）
- README.md（本ファイル）

---

## 運用上のヒント

- 自動環境ロードはプロジェクトルートの .env/.env.local を優先して読み込みます。テスト時などに無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB ファイルはデフォルトで data/kabusys.duckdb に作成されます。永続化先は DUCKDB_PATH で変更可能です。
- production（実資金運用）時は KABUSYS_ENV を `live` に設定して挙動を明示してください（例: ログレベル・エラーハンドリング方針などを環境に応じて分岐可能）。
- Cron やジョブスケジューラで
  - 夜間に calendar_update_job を走らせカレンダーを更新
  - 日次で run_daily_etl を実行
  - 定期的に run_news_collection を実行（例: 15分毎）
  といった運用を想定しています。

---

## 貢献・ライセンス

本ドキュメントはコードベースの説明に基づいて作成しています。実装を変更する場合はテストとレビューを行い、特に外部 API 呼び出し・DB 書き込み部分の安全性と冪等性に注意してください。  
（ライセンスやコントリビュート方針はリポジトリのルートに LICENSE / CONTRIBUTING などを追加してください）

---

以上が KabuSys の簡易 README になります。必要であれば「セットアップ / Cron 設定の具体例」「.env.example のテンプレート」「よくあるトラブルシュート」などを追記します。どの情報を追加しましょうか？