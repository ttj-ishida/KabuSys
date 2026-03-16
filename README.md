# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（プロトタイプ）です。  
データ取得（J-Quants）、ETL / 品質チェック、DuckDB スキーマ定義、監査ログ（発注→約定のトレーサビリティ）など、システムのデータプラットフォーム周りを提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 動作要件 / 依存関係
- セットアップ手順
- 使い方（基本例）
- 環境変数（.env）例
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築における「データプラットフォーム」「監査」「ETL」「品質チェック」を担うモジュール群です。  
主に以下を提供します。

- J-Quants API からの市場データ取得（株価日足 / 財務 / JPX マーケットカレンダー）
- DuckDB を使った永続化用スキーマ（Raw / Processed / Feature / Execution 層）
- ETL パイプライン：差分取得、バックフィル、先読みカレンダー、品質チェック
- 監査ログ（signal → order_request → execution）用スキーマと初期化
- 環境変数管理（.env 自動読み込み・保護）

設計上のポイントとして、API レート制御、リトライ（指数バックオフ）、トークン自動リフレッシュ、取得時刻の記録（look-ahead bias 対策）、DuckDB への冪等保存（ON CONFLICT DO UPDATE）を重視しています。

---

## 主な機能一覧

- config
  - .env ファイルまたは OS 環境変数から設定を読み込む（プロジェクトルート検出）
  - 必須キーは取得時に検証
- data.jquants_client
  - get_id_token（リフレッシュトークンから idToken を取得）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
  - レートリミッタ（120 req/min）・リトライ（408/429/5xx、最大 3 回）・401 時のトークン自動リフレッシュ
  - DuckDB へ保存する save_* 関数（冪等）
- data.schema
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema(), get_connection()
- data.pipeline
  - 差分 ETL 実装（run_prices_etl / run_financials_etl / run_calendar_etl）
  - run_daily_etl：市場カレンダー取得 → 株価 ETL → 財務 ETL → 品質チェック（オプション）
  - ETL 実行結果を ETLResult にまとめる
- data.quality
  - 欠損チェック / スパイク検出（前日比）/ 主キー重複 / 日付不整合（未来日・非営業日）等
  - run_all_checks でまとめて実行、QualityIssue を返す
- data.audit
  - signal_events / order_requests / executions を含む監査ログスキーマ
  - init_audit_schema(), init_audit_db()

注：strategy、execution、monitoring のトップパッケージは存在しますが、個別実装はこのコードベースでは最小限（プレースホルダ）です。

---

## 動作要件 / 依存関係

- Python 3.10+
  - Union 型の `X | Y` 構文を使用しているため 3.10 以上が必要です
- 必須 Python パッケージ
  - duckdb
- 標準ライブラリで HTTP は urllib を使用（requests は必須ではありません）

インストール例:
- pip で duckdb を追加
  - pip install duckdb

パッケージとして利用する場合はプロジェクトルートで:
- pip install -e .

（実運用では追加の依存（Slack クライアント、証券会社 API クライアント等）が必要になる場合があります）

---

## セットアップ手順

1. Python 3.10+ を用意する
2. リポジトリをクローン / 取得
3. 依存パッケージをインストール
   - pip install duckdb
   - （開発用）pip install -e .
4. プロジェクトルートに .env を配置（下に例あり）
   - KabuSys は起動時に .env / .env.local を自動読み込みします（OS 環境変数を保護）
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
5. DuckDB スキーマ初期化
   - Python から data.schema.init_schema() を呼んで DB を作成します（親ディレクトリがなければ自動作成）

---

## 使い方（基本例）

以下は最小限の ETL 実行例です。run_daily_etl を実行すると市場カレンダー → 株価 → 財務 → 品質チェックが順に実行されます。

例: ETL スクリプト（example_run_etl.py）
```python
from datetime import date
from kabusys.data import schema, pipeline
from kabusys.config import settings

# デフォルトでは settings.duckdb_path に保存される（例: data/kabusys.duckdb）
db_path = settings.duckdb_path

# DB とスキーマ初期化（1 回だけ実行）
conn = schema.init_schema(db_path)

# 日次 ETL を実行（target_date を省略すると今日）
result = pipeline.run_daily_etl(conn, target_date=date.today())

# 結果の確認
print(result.to_dict())
```

API クライアントの直接利用例:
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings

# id_token はモジュールでキャッシュされ自動リフレッシュされます
quotes = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
print(len(quotes))
```

監査スキーマ初期化（監査テーブルを別 DB に作る例）:
```python
from kabusys.data import audit
conn = audit.init_audit_db("data/audit.duckdb")
```

ログ出力や環境の切り替え:
- 環境変数 `KABUSYS_ENV` により動作モードを変えられます（development / paper_trading / live）
- `LOG_LEVEL` によりログレベルを制御します（DEBUG/INFO/...）

---

## 環境変数（.env）例

主要な環境変数（必須は README 内で明示）:

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン（get_id_token に使用）

- KABU_API_PASSWORD (必須)  
  kabuステーション API 用パスワード（将来の execution モジュールで使用）

- KABU_API_BASE_URL  
  kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）

- SLACK_BOT_TOKEN (必須)  
  Slack 通知用 Bot トークン（将来の通知機能で使用）

- SLACK_CHANNEL_ID (必須)  
  Slack チャンネル ID

- DUCKDB_PATH  
  DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）

- SQLITE_PATH  
  監視（monitoring）用 SQLite パス（デフォルト: data/monitoring.db）

- KABUSYS_ENV  
  環境: development / paper_trading / live（デフォルト: development）

- LOG_LEVEL  
  ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL

例 (.env):
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- パッケージ起動時にプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索して .env を自動読み込みします。
- OS 環境変数は上書きされないよう保護されます。`.env.local` は上書き優先で読み込まれます。

---

## ディレクトリ構成

リポジトリの主要ファイル / ディレクトリ（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み / Settings クラス
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ロジック）
    - schema.py
      - DuckDB スキーマ定義 / init_schema / get_connection
    - pipeline.py
      - ETL 実装（run_daily_etl 等）
    - quality.py
      - データ品質チェック（欠損、スパイク、重複、日付不整合）
    - audit.py
      - 監査ログ（signal / order_request / executions）スキーマの初期化
  - strategy/
    - __init__.py
    - （戦略関連の実装を置く場所、現状はプレースホルダ）
  - execution/
    - __init__.py
    - （証券会社発注ロジック等を置く場所、現状はプレースホルダ）
  - monitoring/
    - __init__.py
    - （監視・可観測性関連の実装を置く場所、現状はプレースホルダ）

上記のスキーマは以下のレイヤーを含みます：
- Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer: features, ai_scores
- Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
- Audit: signal_events, order_requests, executions（監査目的）

---

## 開発 / 貢献

- 新しい機能（strategy / execution / monitoring）を追加する際は、既存の schema に合わせてスキーマ設計を検討してください。
- ETL は冪等性とトレーサビリティを重視しています。外部 API の呼び出しは jquants_client の RateLimiter / リトライロジックを活用してください。
- 品質チェック（quality）で検出された問題は ETL を強制停止せず収集する設計です。呼び出し元で重大度に応じた処理を行ってください。

---

必要であれば README に以下の内容も追加できます：
- CI / テストの実行方法
- ローカル開発環境の Docker 化手順
- 監視アラート / Slack 通知のサンプル
- 各テーブルの詳しい列説明（DataSchema.md に相当するドキュメントの抜粋）

追加してほしい項目があれば教えてください。