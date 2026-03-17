# KabuSys

日本株向けの自動売買データ基盤 & ETL ライブラリ。J-Quants / JPX などから市場データ・財務データ・ニュースを取得して DuckDB に保存し、品質チェック・カレンダー管理・監査ログをサポートします。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 環境変数（.env）
- 使い方（抜粋例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API から株価（日足）、四半期財務データ、JPX マーケットカレンダーを取得
- RSS からニュースを収集し前処理して保存
- DuckDB を用いた 3 層データスキーマ（Raw / Processed / Feature）と実行層（orders/trades/positions）
- ETL パイプライン（差分更新・バックフィル）とデータ品質チェック
- カレンダー（営業日）判定ユーティリティ
- 監査ログ（signal → order → execution のトレース用スキーマ）
- 可搬性・冪等性を重視した実装（ON CONFLICT / トランザクション / idempotent 保存）

設計上のポイント：
- API レート制御・リトライ・自動トークンリフレッシュ
- Look-ahead bias 対策のため fetched_at 等のトレース情報を保存
- SSRF や XML Bomb に対するセキュリティ対策（defusedxml、ホストチェック、最大受信サイズ制限）

---

## 機能一覧

主要機能（モジュール別）

- kabusys.config
  - .env / 環境変数の自動読み込み（プロジェクトルートを探して `.env`, `.env.local` を読み込む）
  - 各種設定（J-Quants トークン、Kabu API パスワード、Slack トークン、DB パス、実行環境など）

- kabusys.data.jquants_client
  - get_id_token（リフレッシュトークンから id_token 取得）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ冪等保存）
  - API レート制御・リトライ・ページネーション対応

- kabusys.data.news_collector
  - RSS フィード取得（gzip 対応・サイズ制限）
  - URL 正規化・トラッキングパラメータ除去、記事ID は正規化 URL の SHA-256（先頭 32 文字）
  - SSRF 対策（スキーム検証、プライベートIP 拒否、リダイレクト検査）
  - raw_news / news_symbols への冪等保存（INSERT ... RETURNING を利用）

- kabusys.data.schema
  - DuckDB スキーマ定義（raw_prices, raw_financials, market_calendar, features, signals, orders, trades, positions, audit 等）
  - init_schema(db_path) による初期化（冪等）

- kabusys.data.pipeline
  - 差分 ETL（prices, financials, calendar）
  - run_daily_etl による一括 ETL + 品質チェック（run_all_checks）

- kabusys.data.calendar_management
  - 営業日判定・前後営業日取得（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）
  - calendar_update_job（夜間バッチで JPX カレンダーを更新）

- kabusys.data.audit
  - 監査ログ用テーブル（signal_events, order_requests, executions）と初期化ユーティリティ
  - init_audit_db / init_audit_schema

- kabusys.data.quality
  - 欠損チェック / 重複チェック / スパイク検出 / 日付不整合チェック
  - QualityIssue データクラスと run_all_checks

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の型記法 `X | None` を使用）
- pip が使用可能

推奨インストール（開発時）
1. リポジトリをクローンしてプロジェクトルートへ移動
2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate (Unix) / .venv\Scripts\activate (Windows)
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （開発時: pip install -e . を用意している場合はパッケージを編集可能モードでインストール）

注意: このコードベースは外部依存を最小にしていますが、実際の運用ではログ・Slack・HTTP クライアントなどを追加することがあるため、必要に応じて追加パッケージを導入してください。

---

## 環境変数（.env）

パッケージはプロジェクトルートの `.env` / `.env.local` を自動的に読み込みます（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを無効化）。

主な環境変数

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。get_id_token の元になります。
- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード
- KABU_API_BASE_URL (任意)
  - デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意)
  - デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意)
  - デフォルト: data/monitoring.db
- KABUSYS_ENV (任意)
  - 値: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意)
  - 値: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

`.env` の例（.env.example を参照して作成してください）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

.env のパースは一般的な shell 形式をサポートし、クォートやコメントにも対応します。

---

## 使い方（抜粋）

以下は代表的な利用例です。詳細は各モジュールを参照してください。

1) スキーマ（DuckDB）初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は Environment から読み取られる
conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL 実行（市場カレンダー取得 → 株価・財務データ差分取得 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) J-Quants API 呼び出し（個別）
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema(":memory:")
id_token = get_id_token()
records = fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, records)
```

4) RSS ニュース収集と銘柄抽出
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は有効な銘柄コード集合（例: 全上場銘柄の 4 桁コード）
known_codes = {"7203", "6758", ...}
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

5) カレンダー系ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = init_schema("data/kabusys.duckdb")
d = date(2026, 3, 17)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

6) 監査ログの初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

7) 品質チェックの実行（個別）
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date.today(), spike_threshold=0.5)
for i in issues:
    print(i)
```

注意:
- DuckDB への保存は多くが冪等（ON CONFLICT で更新）になっています。
- API 呼び出しはレート制御・リトライを内蔵していますが、運用での追加制御は検討してください（複数プロセスからの同時呼び出しなど）。

---

## ディレクトリ構成

プロジェクトの主要ファイル配置（抜粋）
```
src/
  kabusys/
    __init__.py
    config.py
    data/
      __init__.py
      jquants_client.py
      news_collector.py
      pipeline.py
      schema.py
      calendar_management.py
      audit.py
      quality.py
    strategy/
      __init__.py
    execution/
      __init__.py
    monitoring/
      __init__.py
```

主要モジュールの役割:
- data/: データ取得・保存・ETL・スキーマ・品質チェック
- strategy/: 戦略実装（プレースホルダ）
- execution/: 発注実装（プレースホルダ）
- monitoring/: 監視・メトリクス（プレースホルダ）

パッケージルートに `.env` / `.env.local` を置くと自動読み込みされます（ただしプロジェクトルート判定は `.git` または `pyproject.toml` を基準に行われます）。

---

## 運用上の注意点

- 環境（KABUSYS_ENV）が `live` の場合は発注・実行に関わるモジュールを慎重に扱ってください。paper_trading 環境で十分に検証してから移行してください。
- DuckDB ファイルはバックアップ・スナップショットが取れる場所に配置してください。大規模データを扱う場合はストレージ容量に注意。
- RSS 等の外部コンテンツ取得では、ソースごとに個別のエラー処理を行っていますが、過度なリトライや不正な URL のフォローは行わないでください。
- J-Quants の API レート制限（120 req/min）を尊重してください。内部で固定間隔スロットリングを行っていますが、運用で複数インスタンスを動かす場合は外部制御が必要です。

---

README は以上です。さらに「インストール用の pyproject.toml / requirements.txt を追加してほしい」「使用例を具体的にノート化してほしい」などの要望があれば、目的に合わせて追記します。