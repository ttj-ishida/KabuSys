# KabuSys

日本株向け自動売買プラットフォームのコアライブラリです。  
データ取得（J-Quants/API経由）、ニュース収集、ETLパイプライン、マーケットカレンダー管理、データ品質チェック、監査ログなどの基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計されたライブラリ群です。主な役割は以下の通りです。

- J-Quants API から株価（日足・OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得
- RSS フィードからのニュース収集と銘柄紐付け
- DuckDB を用いたスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL（差分取得、冪等保存、品質チェック）パイプライン
- カレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ（シグナル → 発注 → 約定 のトレース）
- 各所での堅牢性設計（レート制限遵守、リトライ・バックオフ、SSRF対策、XMLパースの安全化、トランザクション管理）

設計上の注目点:
- API レート制限（120 req/min）に合わせた RateLimiter 実装
- HTTP リトライ（指数バックオフ、401 のトークン自動リフレッシュ等）
- DuckDB 側は冪等性を確保（INSERT ... ON CONFLICT）
- ニュース収集での SSRF / XML Bomb / Gzip Bomb 対策
- 品質チェックは Fail-Fast にせず検出結果を集約して報告

---

## 機能一覧

- data/jquants_client.py
  - J-Quants からのデータ取得（fetch_* 系）
  - ID トークン取得・キャッシュ（get_id_token）
  - レート制御、リトライ、レスポンスの JSON パース
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）
- data/news_collector.py
  - RSS 収集（gzip 対応、XML 安全パース）
  - URL 正規化・トラッキング除去・記事ID生成（SHA-256 の先頭32文字）
  - SSRF 防止（スキーム／ホスト検証、リダイレクト検査）
  - DuckDB への冪等保存（raw_news, news_symbols）
- data/schema.py
  - DuckDB の DDL（Raw / Processed / Feature / Execution テーブル）とインデックス
  - init_schema(db_path) による初期化
- data/pipeline.py
  - 差分更新型の ETL（run_daily_etl、日次ETL）
  - run_prices_etl / run_financials_etl / run_calendar_etl（backfill 対応）
  - 品質チェック連携（data.quality）
- data/calendar_management.py
  - market_calendar の夜間更新ジョブ（calendar_update_job）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
- data/quality.py
  - 欠損チェック、重複チェック、スパイク検知（前日比）、日付整合性チェック
  - QualityIssue による検査結果表現
- data/audit.py
  - 監査用スキーマ（signal_events, order_requests, executions）
  - init_audit_schema / init_audit_db による初期化
- config.py
  - 環境変数ロード（.env / .env.local をプロジェクトルートから自動読み込み）
  - 必須環境変数取得ヘルパー、設定オブジェクト（settings）
  - 自動読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
- その他: strategy / execution / monitoring パッケージ用のプレースホルダ

---

## セットアップ手順

前提
- Python 3.9+（typing, Path 型注釈が使用されています）
- DuckDB を利用します（duckdb パッケージ）
- RSS の安全な XML 解析に defusedxml を使用

推奨手順（簡易）

1. リポジトリをクローン / コピー
2. 仮想環境の作成と有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （必要に応じて他のパッケージを追加してください）
4. 環境変数の設定
   - プロジェクトルートに .env または .env.local を配置すると自動で読み込まれます（優先度: OS 環境 > .env.local > .env）
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

推奨される環境変数（例）
- JQUANTS_REFRESH_TOKEN ・・・ J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD      ・・・ kabuステーションAPI パスワード（必須）
- KABU_API_BASE_URL      ・・・ kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN        ・・・ Slack Bot トークン（必須）
- SLACK_CHANNEL_ID       ・・・ Slack チャンネル ID（必須）
- DUCKDB_PATH            ・・・ DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            ・・・ 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV            ・・・ environment (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL              ・・・ ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)（デフォルト: INFO）

例 .env（プロジェクトルート）
JAVA
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=yyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（代表的な操作例）

注意: 以下は Python スクリプト / REPL から利用する例です。

1) DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# ":memory:" を指定するとインメモリ DB を利用可能
```

2) 監査ログ専用 DB 初期化
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

3) J-Quants データを手動で取得して保存
```python
from kabusys.data import jquants_client as jq
# 既に init_schema で作った conn を渡す
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
jq.save_daily_quotes(conn, records)
```

4) 日次 ETL（市場カレンダー→株価→財務→品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

5) RSS ニュース収集（既知銘柄セットを渡して銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット
stats = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(stats)
```

6) カレンダー関連ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
d = date(2024, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

7) 品質チェックを個別に実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

注意点:
- J-Quants API の呼び出しはレート制限とリトライロジックが組み込まれています。
- get_id_token は refresh token から id token を取得します。fetch 関数は自動でトークンをキャッシュしリフレッシュします。
- ニュース収集は外部の RSS に接続するため、企業の環境やプロキシ設定に合わせて timeout や接続方法を調整してください。

---

## ディレクトリ構成

リポジトリ内の主なファイル・ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    -- 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py          -- J-Quants API クライアント（取得・保存）
    - news_collector.py          -- RSS ニュース収集、SSRF対策、DB保存
    - schema.py                  -- DuckDB スキーマ定義・初期化
    - pipeline.py                -- ETL パイプライン（差分取得、品質チェック）
    - calendar_management.py     -- マーケットカレンダー管理・ジョブ
    - audit.py                   -- 監査ログ（signal/order/execution）スキーマ
    - quality.py                 -- データ品質チェック
  - strategy/
    - __init__.py                -- 戦略層（拡張ポイント）
  - execution/
    - __init__.py                -- 発注実行層（拡張ポイント）
  - monitoring/
    - __init__.py                -- 監視系（未実装プレースホルダ）

（ファイル内容は README 作成時点の実装に基づきます）

---

## 開発上の注意事項 / 設計上のポイント

- 環境変数の自動ロード:
  - config.py はパッケージファイルの親ディレクトリからプロジェクトルート（.git または pyproject.toml）を探し、.env / .env.local を自動的に読み込みます。
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）。
  - 読み込み優先度: OS 環境 > .env.local > .env。override フラグにより .env.local は上書きします。
- セキュリティ:
  - XML のパースは defusedxml を使用して XML Bomb 等を防止しています。
  - RSS フェッチではスキーム検証（http/https のみ）・プライベートアドレス拒否・リダイレクト検査で SSRF を防いでいます。
  - ニュース本文の URL は除去して正規化しています。
- 冪等性:
  - DuckDB へ保存する際は可能な限り ON CONFLICT を使い重複を排除します（ETL の安全性確保）。
- ロギング:
  - 各モジュールは logging を使用しています。環境変数 LOG_LEVEL でログレベルを制御できます。
- テスト性:
  - HTTP/ネットワークの呼び出し箇所はモック可能な構造になっており、単体テストや統合テストを行いやすく設計されています（例: news_collector._urlopen を差し替え可能）。

---

## 追加リソース / 今後の拡張

- strategy/ と execution/ は拡張ポイントです。具体的な戦略実装やブローカー連携（kabu ステーション等）をここに実装してください。
- monitoring/ パッケージは監視・アラート・Prometheus / Grafana 連携等の実装に利用できます。
- CI / CD、ユニットテスト、型チェック（mypy）や静的解析（ruff/flake8）の導入を推奨します。

---

README に不足している具体的なインストール要件（extras, setup.py/pyproject.toml での依存指定など）は、実際のプロジェクト運用に合わせて追記してください。追加したいサンプルやスクリプト（例: 日次 crontab ジョブ、Dockerfile、systemd ユニット）について要望があれば作成支援します。