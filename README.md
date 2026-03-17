# KabuSys

日本株向けの自動売買プラットフォーム（ライブラリ）です。  
データ取得（J-Quants）、ETL パイプライン、ニュース収集、データ品質チェック、DuckDB スキーマ、監査ログ（発注〜約定トレース）などを提供します。

主な用途は、マーケットデータの自動収集・前処理、戦略や実行コンポーネントとの連携基盤の提供です。

---

## 機能一覧

- 環境変数／.env 自動読み込みと設定管理（kabusys.config）
  - 必須環境変数を明示的に取得し未設定時は例外を出力
  - 自動ロードはプロジェクトルート（.git / pyproject.toml）を基準に行う。無効化オプションあり

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日次株価（OHLCV）、四半期財務、JPX マーケットカレンダーを取得
  - レート制限（120 req/min）対応
  - リトライ（指数バックオフ、HTTP 408/429/5xx 対応）
  - 401 時の自動トークンリフレッシュ
  - DuckDB へ冪等的に保存する save_* 関数

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集、XML の安全パース（defusedxml）
  - URL 正規化・トラッキングパラメータ除去・記事ID（SHA-256 の先頭32文字）
  - SSRF 対策（スキーム／プライベートアドレス検査）、レスポンスサイズ上限
  - DuckDB への冪等保存（INSERT ... ON CONFLICT / RETURNING）

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - インデックス生成、初期化関数（init_schema, get_connection）

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日に基づく差分取得 + backfill）
  - 市場カレンダー、株価、財務の一括日次 ETL（run_daily_etl）
  - 品質チェックとの連携（quality モジュール）

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定 / 次・前営業日取得 / 期間の営業日リスト取得
  - 夜間バッチでのカレンダー差分更新ジョブ

- データ品質チェック（kabusys.data.quality）
  - 欠損データ検出、主キー重複、スパイク（前日比閾値）、
    日付整合性（未来日付・非営業日のデータ）を検出し QualityIssue を返す

- 監査ログ（kabusys.data.audit）
  - signal → order_request → execution を UUID でトレースする監査テーブル群
  - 発注の冪等性やステータス遷移をログに残す設計

- 戦略 / 実行 / 監視 用の名前空間（kabusys.strategy, kabusys.execution, kabusys.monitoring）
  - （このリポジトリではモジュール初期化のみ。拡張用）

---

## 必要条件（依存）

- Python 3.10 以上（ソース内での型 | 合成を使用）
- パッケージ（例）
  - duckdb
  - defusedxml

実際の requirements.txt はプロジェクトに合わせて用意してください。

---

## セットアップ手順

1. リポジトリを取得（例）
   - git clone ... / ダウンロード

2. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\activate     (Windows PowerShell)

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （その他の依存パッケージがあれば同様に）

4. 開発インストール（任意）
   - pip install -e .

5. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意（デフォルト有り）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|...) — デフォルト: INFO
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

例 .env（参考）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=passw0rd
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（基本例）

以下は Python スクリプトからの利用例です。各コードはアプリケーション側で適宜エラーハンドリング・ログ出力してください。

- DuckDB スキーマ初期化（最初に一度実行）
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL を実行（市場カレンダー・株価・財務を差分取得し品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- ニュース収集ジョブの実行
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758"}  # 既知の銘柄コードセット（抽出に利用）
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

- J-Quants API クライアントの直接利用例
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# トークンは settings.jquants_refresh_token を参照するため通常は不要
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,2,1))
jq.save_daily_quotes(conn, records)
```

- 監査スキーマの追加初期化（監査用テーブルを追加する）
```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn)
```

- 設定取得（環境変数）
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.kabu_api_base_url)
print(settings.duckdb_path)
```

---

## 実装上の注意点 / 設計ポリシー（抜粋）

- J-Quants クライアントはレートリミットとリトライを厳守する実装です。大量データ取得時は API 制限に注意してください。
- データの取得時刻（fetched_at）は UTC で記録し、Look-ahead bias のトレースを可能にしています。
- DuckDB への保存は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）で設計されています。
- ニュース収集は SSRF 対策や XML 脆弱性対策（defusedxml）、レスポンスサイズ制限などセキュリティを考慮しています。
- ETL は Fail-Fast を採らず、各ステップのエラーを収集して戻り値に含めます（呼び出し側で判断）。

---

## 主要モジュール / ディレクトリ構成

リポジトリ本体（主要部分、src/kabusys 以下を抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env ロードと Settings クラス
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch / save 等）
    - news_collector.py     — RSS ニュース収集・記事抽出・保存
    - schema.py             — DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py— マーケットカレンダー管理（営業日判定・更新ジョブ）
    - audit.py              — 監査ログ（signal / order_request / executions）
    - quality.py            — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/                — 戦略実装用名前空間（拡張ポイント）
  - execution/               — 発注実行用名前空間（拡張ポイント）
  - monitoring/              — 監視・アラート用名前空間（拡張ポイント）

（上記以外にテスト・ドキュメント・スクリプト等を配置することを想定）

---

## 開発 / テストのヒント

- 自動 .env ロードを無効にする場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利）。
- DuckDB をメモリで使いたい場合は db_path に `":memory:"` を指定して init_schema を呼び出します。
- news_collector._urlopen は単体テストでモック可能に設計されています。
- jquants_client のトークンリフレッシュやレートリミットは実運用での API 制限を意識しているため、テスト時は外部 API をモックすることを推奨します。

---

もし README に追加したい内容（例: 実運用時の注意、CI 設定例、要求される追加依存、.env.example のテンプレート、サンプル ETL ジョブスケジュール）があれば教えてください。必要に応じて追記・調整します。