# KabuSys

バージョン: 0.1.0

KabuSys は日本株のデータプラットフォームと自動売買基盤のコアライブラリです。  
J-Quants API から市場データや財務データを取得し、DuckDB に格納・品質チェックを行う ETL、監査ログ（発注→約定のトレース）や実行/戦略層のための基盤モジュール群を提供します。

主な目的:
- J-Quants からの株価・財務・市場カレンダー取得（レート制限・リトライ・トークン自動更新対応）
- DuckDB によるスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- 差分ETL（バックフィル対応）とデータ品質チェック
- 監査ログ（トレーサビリティ）用テーブル群の初期化

---

## 機能一覧

- 環境設定管理
  - .env / .env.local をプロジェクトルートから自動読み込み（必要に応じて環境変数で上書き）
  - 必須設定の取得ヘルパー（不足時は例外）
  - 自動読み込みを無効化するフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD`

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）/ 財務（四半期 BS/PL）/ JPX マーケットカレンダーの取得
  - レートリミット（120 req/min）を守るスロットリング実装
  - リトライ（指数バックオフ、最大3回）、401 受信時はリフレッシュして再試行
  - 取得時刻（fetched_at）を UTC で記録

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - インデックス定義、FK 制約やチェック制約を含む DDL
  - init_schema() / get_connection() を提供

- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（DB の最終取得日を基に自動算出）とバックフィル
  - 市場カレンダー先読み（デフォルト 90 日）
  - 保存は冪等（ON CONFLICT DO UPDATE）
  - 品質チェックの統合（kabusys.data.quality）
  - ETL 実行結果を表す ETLResult

- データ品質チェック（kabusys.data.quality）
  - 欠損チェック（OHLC 欄など）
  - スパイク（前日比）検出
  - 主キー重複チェック
  - 将来日付 / 非営業日データの検出
  - 問題は QualityIssue オブジェクトに集約（severity: error|warning）

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブル定義
  - init_audit_schema()/init_audit_db() による初期化
  - 発注フローのトレーサビリティ確保（UUID 連鎖、冪等キー等）

---

## 動作環境・依存

- Python 3.10+
  - 型注釈に `Path | None` など Python 3.10 の表記を使用しています。
- 必須 Python パッケージ（例）
  - duckdb
- 標準ライブラリの urllib, logging などを使用

インストール例（プロジェクト配布・開発環境での一例）:
- 仮想環境を作成してから必要パッケージをインストールしてください:
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
  - pip install duckdb

（本リポジトリに requirements.txt がある場合はそれを使用してください。）

---

## 環境変数（主なもの）

以下はアプリが参照する主な環境変数です。必須項目は README の例に従って .env に設定してください。

必須:
- JQUANTS_REFRESH_TOKEN - J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD - kabu ステーション API パスワード（将来の実行モジュールで使用）
- SLACK_BOT_TOKEN - Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID - Slack チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV - {development, paper_trading, live}（デフォルト: development）
- LOG_LEVEL - {DEBUG, INFO, WARNING, ERROR, CRITICAL}（デフォルト: INFO）
- DUCKDB_PATH - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH - 監視用 SQLite（デフォルト: data/monitoring.db）

自動読み込み制御:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると .env 自動読み込みを無効化できます（テスト等で使用）。

例（.env）:
```
JQUANTS_REFRESH_TOKEN="your_refresh_token_here"
KABU_API_PASSWORD="your_kabu_password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"
DUCKDB_PATH="data/kabusys.duckdb"
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを取得
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate
3. 必要パッケージをインストール
   - pip install duckdb
   - （その他、将来の依存があれば追加でインストール）
4. プロジェクトルートに .env を作成（上記の必須変数を設定）
   - .env.example を参照して作成してください
5. DuckDB スキーマを初期化
   - Python インタプリタで init_schema() を実行（下記「使い方」を参照）

---

## 使い方（簡易ガイド）

以下は主要な操作例です。適宜スクリプト化して運用してください。

- DuckDB スキーマの初期化（ファイル DB）
```
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- DuckDB をインメモリで初期化（テスト用）
```
from kabusys.data.schema import init_schema
conn = init_schema(":memory:")
```

- 監査ログテーブルの追加初期化（既存接続へ）
```
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

- 日次 ETL の実行（デフォルトで当日を対象）
```
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)
print(result.to_dict())  # ETL の詳細結果を表示
```

- ETL をカスタムオプションで実行（バックフィルやスパイク閾値を指定）
```
result = run_daily_etl(
    conn,
    target_date=None,             # None = 今日
    run_quality_checks=True,
    spike_threshold=0.4,          # スパイク検出閾値(例: 40%)
    backfill_days=5,
)
```

- テスト時に環境変数自動読み込みを無効にする
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
# Windows PowerShell: $env:KABUSYS_DISABLE_AUTO_ENV_LOAD = "1"
```

注意点:
- J-Quants へアクセスする関数は内部で自動的にトークンを取得・キャッシュします。トークンの自動リフレッシュは 401 に対して1回のみ行われます。
- API レート制限（120 req/min）を守るためモジュール内でスロットリングを行います。
- save_* 関数は冪等（ON CONFLICT DO UPDATE）なので再実行で二重挿入されません。

---

## ディレクトリ構成（抜粋）

プロジェクト内の主要ファイルとディレクトリ構成例（この README に含まれるコードベースに基づく）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/
      - __init__.py
    - strategy/
      - __init__.py
    - monitoring/
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py     # J-Quants API クライアント（取得・保存）
      - schema.py             # DuckDB スキーマ定義・初期化
      - pipeline.py           # ETL 実装（差分更新・品質チェック統合）
      - audit.py              # 監査ログ（発注→約定トレース）スキーマ
      - quality.py            # データ品質チェック
- data/                      # デフォルトの DB 保存先 (例: data/kabusys.duckdb)
- .env, .env.local (任意)    # 環境変数ファイル（プロジェクトルートで自動読み込み）

---

## テーブル & 主要スキーマ（概要）

主要なテーブル（抜粋）:

- Raw 層:
  - raw_prices (date, code, open, high, low, close, volume, turnover, fetched_at)
  - raw_financials (code, report_date, period_type, revenue, ... , fetched_at)
  - raw_news, raw_executions

- Processed 層:
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols

- Feature 層:
  - features, ai_scores

- Execution 層:
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance

- 監査ログ:
  - signal_events, order_requests, executions

各テーブルは操作時の冪等性・データ整合性を確保するために PRIMARY KEY や CHECK 制約、ON CONFLICT 更新、インデックスが定義されています。

---

## 品質チェックの考え方

- 各チェックは fail-fast ではなく問題を収集して返します。呼び出し元は severity を見て停止/警告の判断を行います。
- 主なチェック:
  - 欠損（OHLC 欄の NULL）
  - 主キー重複
  - スパイク（前日比の絶対変動率が閾値を超える）
  - 日付不整合（将来日付、market_calendar で非営業日のデータ）
- check 関数群は DuckDB の SQL を使って効率的に実行します。

---

## 開発・テストのヒント

- 単体テストでは DuckDB のインメモリ DB を使用すると便利（init_schema(":memory:")）。
- .env の自動読み込みはプロジェクトルートの検出に .git または pyproject.toml を使います。CI 等で不要な自動読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- API コールはレート制限とリトライがあるため、テストでは外部通信をモックするか環境変数でテスト専用トークンを用意してください。

---

## ライセンス・貢献

（ここにライセンスやコントリビュート方法を追記してください）

---

README は以上です。必要であれば、セットアップスクリプト、.env.example、簡単な CLI ラッパー（ETL の定期実行用）、あるいはより詳細な DataSchema.md / DataPlatform.md を追記してドキュメントを拡張できます。どの部分を重点的に整備したいか教えてください。