# KabuSys

日本株向けの自動売買（データ基盤＋ETL＋監査ログ）ライブラリです。  
J-Quants や RSS 等からデータを取得し、DuckDB に整形・保存、品質チェックや監査ログを提供します。戦略・実行・モニタリング層の骨組みを含む設計です。

---

## 主な機能（概要）
- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得
  - レート制限（120 req/min）対応、リトライ（指数バックオフ）、トークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を防止
  - DuckDB への冪等保存（ON CONFLICT ... DO UPDATE）
- ニュース収集
  - RSS 収集、XML セキュリティ対策（defusedxml）、SSRF 対策、受信サイズ制限
  - 記事IDを正規化 URL の SHA-256 先頭 32 文字で生成し冪等性を確保
  - raw_news, news_symbols テーブルへの保存（バルク挿入、INSERT ... RETURNING）
  - テキスト前処理、銘柄コード抽出（4 桁数字）
- ETL パイプライン
  - 差分更新（最終取得日を元に差分取得 + バックフィル）
  - 市場カレンダー先読み、品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次 ETL エントリ（run_daily_etl）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化（init_schema）
  - 監査ログ用スキーマ（signal / order_request / executions 等）と初期化（init_audit_schema / init_audit_db）
- データ品質チェック（quality モジュール）
  - 欠損、スパイク、重複、未来日付／非営業日データの検出

---

## 必要環境
- Python 3.9+
- 必要なパッケージ（DuckDB, defusedxml など）: pyproject.toml / requirements.txt に従ってインストールしてください。

（プロジェクトに pyproject.toml がある想定です。pip install -e . / poetry install 等でセットアップしてください）

---

## セットアップ手順

1. リポジトリをクローン／取得
2. 依存パッケージをインストール
   - pip の場合（パッケージ配布設定がある場合）:
     pip install -e .
   - または requirements.txt / poetry に従ってインストール

3. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env` / `.env.local` を配置すると自動で読み込まれます。
   - 自動読み込みを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. DuckDB スキーマ初期化（例）
   - デフォルトの DuckDB パスは data/kabusys.duckdb（settings.duckdb_path）
   - Python REPL / スクリプトで:
     from kabusys.config import settings
     from kabusys.data.schema import init_schema
     conn = init_schema(settings.duckdb_path)

---

## 環境変数（主要）
以下はコード内で参照される主な環境変数です。必須項目は README の用途に応じて設定してください。

必須（実運用で必要）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意 / デフォルトあり
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

.env の自動読み込みはプロジェクトルートの `.env` と `.env.local` を対象に、OS 環境変数より下位の設定を読み込みます（.env.local は .env を上書き）。テスト等で自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

簡単な .env 例:
JQUANTS_REFRESH_TOKEN=your_refresh_token
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（クイックスタート）

以下は代表的な操作例です。スクリプトやジョブ管理ツールから呼び出して使います。

1) スキーマ初期化 / 接続取得
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# 初回: テーブルを作成して接続を返す
conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL の実行（市場カレンダー / 株価 / 財務 / 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
# ETLResult オブジェクト: fetched/saved 件数、品質チェック結果やエラーメッセージを含む
```

3) ニュース収集（RSS → raw_news、news_symbols）
```python
from kabusys.data.news_collector import run_news_collection

# known_codes を渡すと記事中の銘柄コード抽出→news_symbols に保存する
known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

4) 監査スキーマの初期化（audit テーブル群）
```python
from kabusys.data.audit import init_audit_schema

# 既存の DuckDB 接続に監査テーブルを追加
init_audit_schema(conn, transactional=True)
```

5) J-Quants の ID トークンを明示的に取得
```python
from kabusys.data.jquants_client import get_id_token

token = get_id_token()  # settings.jquants_refresh_token を用いて取得
```

---

## 主要 API（抜粋）
- kabusys.config.settings: 環境設定アクセス（settings.jquants_refresh_token 等）
- kabusys.data.schema.init_schema(db_path)
- kabusys.data.schema.get_connection(db_path)
- kabusys.data.jquants_client.fetch_daily_quotes(...)
- kabusys.data.jquants_client.fetch_financial_statements(...)
- kabusys.data.jquants_client.fetch_market_calendar(...)
- kabusys.data.jquants_client.save_daily_quotes(conn, records)
- kabusys.data.news_collector.fetch_rss(url, source)
- kabusys.data.news_collector.save_raw_news(conn, articles)
- kabusys.data.news_collector.run_news_collection(conn, sources, known_codes)
- kabusys.data.pipeline.run_daily_etl(...)
- kabusys.data.audit.init_audit_schema(conn)
- kabusys.data.audit.init_audit_db(db_path)
- kabusys.data.quality.run_all_checks(conn, target_date, reference_date, spike_threshold)
- kabusys.data.calendar_management.calendar_update_job(conn, lookahead_days)
（各関数の詳細はコード内 docstring を参照してください）

---

## ディレクトリ構成（主要ファイル）
プロジェクトのルートに src/kabusys 配下として実装されています。主要ファイルは以下の通りです。

- src/kabusys/
  - __init__.py
  - config.py                 - 環境変数・設定管理（.env 自動ロード等）
  - data/
    - __init__.py
    - jquants_client.py       - J-Quants API クライアント（取得 + 保存）
    - news_collector.py       - RSS 収集・前処理・保存ロジック
    - schema.py               - DuckDB スキーマ定義と init/get_connection
    - pipeline.py             - ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py  - マーケットカレンダー管理（営業日判定等）
    - audit.py                - 監査ログ（signal/order_request/executions）初期化
    - quality.py              - データ品質チェック
  - strategy/
    - __init__.py             - 戦略モジュール（拡張ポイント）
  - execution/
    - __init__.py             - 発注/約定処理（拡張ポイント）
  - monitoring/
    - __init__.py             - モニタリング（拡張ポイント）

---

## 実運用上の注意点 / 設計上のポイント
- J-Quants API: 120 req/min のレート制限を厳守しています（モジュール内 RateLimiter）。
- 認証: 401 受信時は自動的に refresh して1回だけリトライします（無限再帰防止設計）。
- DuckDB への書き込みは可能な限り冪等（ON CONFLICT）を採用。ETL は差分更新＋バックフィルで API の後出し修正を吸収します。
- NewsCollector: SSRF、XML Bomb、Gzip bomb、大きすぎるレスポンスなどに対する防御を実装しています。
- 品質チェックは Fail-Fast ではなく全チェックを実行し、呼び出し元が停止/警告を判断する設計です。
- .env の自動読み込みはプロジェクトルートを .git / pyproject.toml で探索します。パッケージ配布後も動くように CWD に依存しない実装です。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化してください。

---

## 開発者向け
- モジュールは型アノテーション・docstring を充実させています。ユニットテストから個別関数（例: news_collector._urlopen）をモックして動作検証が行いやすい設計です。
- ETL の単体実行や局所テストは DuckDB の ":memory:" パスを使ってインメモリ DB で行えます。
- 監査テーブルの初期化は transactional=True にできるため、初期セットアップで原子的に作成できます（ただし DuckDB のトランザクション制限に注意）。

---

必要であれば「運用用の systemd ジョブ例」「Airflow DAG のサンプル」「より詳しい .env.example」や「よく使う CLI スクリプト案」などの README セクションを追加できます。どの情報を優先して追記しましょうか？