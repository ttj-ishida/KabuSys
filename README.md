# KabuSys

KabuSys は日本株の自動売買・データ基盤コンポーネント群です。  
J-Quants API や RSS フィードからデータを取得して DuckDB に保管し、ETL（差分更新・バックフィル）、データ品質チェック、マーケットカレンダー管理、ニュース収集、監査ログ（発注→約定トレース）などを行うためのライブラリ群を提供します。

主な設計方針：
- データ取得は冪等に（ON CONFLICT / DO UPDATE / DO NOTHING）
- API レート制限とリトライ（指数バックオフ、トークン自動リフレッシュ）に対応
- Look-ahead バイアス防止のため取得時刻（fetched_at）を保存
- ニュース収集はセキュリティ（SSRF、XML Bomb、Gzip Bomb）に配慮

バージョン: 0.1.0

---

## 機能一覧

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務四半期データ、JPX マーケットカレンダー取得
  - レート制限（120 req/min）管理、リトライ（408/429/5xx）、401 時のトークン自動リフレッシュ
  - ページネーション対応、取得時刻（fetched_at）を保存

- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution / Audit 層のテーブルを定義
  - インデックス・外部キーの作成

- ETL パイプライン
  - 差分更新（最終取得日からの差分のみ取得）
  - バックフィル（直近数日を再取得して後出し修正に対応）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）

- マーケットカレンダー管理
  - JPX カレンダーを夜間差分更新するジョブ
  - 営業日判定、前後の営業日取得、期間内の営業日列挙

- ニュース収集モジュール
  - RSS から記事収集、URL 正規化とトラッキングパラメータ除去、記事ID は URL の SHA-256（先頭32文字）
  - SSRF 回避のためスキーム・ホスト検査、受信サイズ上限、gzip 解凍検査
  - raw_news / news_symbols テーブルへの冪等保存

- 監査ログ（audit）
  - シグナル -> 発注要求 -> 約定 までトレースできる監査用テーブル群
  - order_request_id による冪等管理、UTC タイムスタンプ固定

---

## 必要条件

- Python 3.10 以上（型アノテーションで `X | None` を使用）
- 主要依存パッケージ（例）:
  - duckdb
  - defusedxml

（プロジェクトには requirements ファイルが同梱されている想定ですが、上記をインストールしてください）

例:
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install duckdb defusedxml
# 開発インストール（パッケージ化されている場合）
pip install -e .
```

---

## 環境変数（設定項目）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動ロードされます（自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション API パスワード（必須）
- KABU_API_BASE_URL : kabu API ベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN : Slack bot token（必須）
- SLACK_CHANNEL_ID : Slack channel ID（必須）
- DUCKDB_PATH : DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH : SQLite（monitoring 用）パス（省略時: data/monitoring.db）
- KABUSYS_ENV : execution 環境（development / paper_trading / live、省略時 development）
- LOG_LEVEL : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、省略時 INFO）

注意: `.env` をソース管理に含めないでください（機密情報含む）。

---

## セットアップ手順

1. リポジトリをクローン、仮想環境作成
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .  # パッケージ化されている場合
   pip install duckdb defusedxml
   ```

2. 環境変数を用意
   - プロジェクトルートに `.env` を作成するか、OS 環境変数として設定します。
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

3. DuckDB スキーマ初期化
   - Python REPL やスクリプトから init_schema を呼び出して DB とテーブルを作成します。
   - 例:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     # 監査ログだけ別に初期化する場合
     from kabusys.data import audit
     audit.init_audit_schema(conn)
     ```

---

## 使い方（簡単な例）

- 日次 ETL を実行する（株価・財務・カレンダー取得と品質チェック）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data import pipeline, schema

  conn = schema.init_schema("data/kabusys.duckdb")
  # J-Quants トークンは settings 経由で自動取得される（環境変数 JQUANTS_REFRESH_TOKEN）
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- マーケットカレンダー夜間更新ジョブ:
  ```python
  from kabusys.data import calendar_management, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  print("saved calendar rows:", saved)
  ```

- RSS ニュース収集と DB 保存:
  ```python
  from kabusys.data import news_collector, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  # ソース辞書を渡すかデフォルトを使用
  results = news_collector.run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
  print(results)  # {source_name: saved_count}
  ```

- J-Quants から直接データ取得（テスト／ユーティリティ）:
  ```python
  from kabusys.data import jquants_client as jq
  # トークンを直接渡すか settings から自動で取得される
  daily = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

---

## 主な API と関数一覧（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.duckdb_path, settings.env, settings.log_level など

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - save_news_symbols(conn, news_id, codes)
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=...)

- kabusys.data.calendar_management
  - is_trading_day(conn, d)
  - next_trading_day(conn, d)
  - prev_trading_day(conn, d)
  - get_trading_days(conn, start, end)
  - calendar_update_job(conn, lookahead_days=90)

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

---

## ディレクトリ構成

プロジェクトは src レイアウトで実装されています（主なファイルを抜粋）。

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数・設定読み込みロジック
    - data/
      - __init__.py
      - schema.py              # DuckDB スキーマ定義・初期化
      - jquants_client.py      # J-Quants API クライアント（取得・保存）
      - pipeline.py            # ETL パイプライン（差分更新・バックフィル・品質チェック）
      - news_collector.py      # RSS ニュース収集・保存・銘柄抽出
      - calendar_management.py # マーケットカレンダー管理
      - audit.py               # 監査ログ（発注→約定トレーサビリティ）
      - quality.py             # データ品質チェック
    - strategy/                 # 戦略関連（未実装: プレースホルダ）
      - __init__.py
    - execution/                # 発注・実行関連（未実装: プレースホルダ）
      - __init__.py
    - monitoring/               # モニタリング（未実装: プレースホルダ）

README に書かれている API の詳細は各モジュールの docstring（ソースコード内のコメント）を参照してください。

---

## セキュリティ・運用上の注意

- 秘密情報（API トークン・パスワード等）は `.env` を含めソース管理しないでください。
- news_collector は SSRF・XML Bomb・Gzip Bomb 等に対策済ですが、外部フィードの扱いには注意してください。
- J-Quants のレート制限や証券会社 API のルールを順守してください（運用環境では paper_trading モードで十分な検証を行ってから live に移行してください）。
- DuckDB のバックアップやファイル配置（権限）に注意してください。

---

## 貢献・拡張

- 戦略（strategy）や発注実装（execution）はプレースホルダになっているため、具体的なアルゴリズムやブローカー連携を実装して拡張してください。
- 品質チェックや監査スキーマは必要に応じてカスタマイズ可能です。
- バグ報告や機能追加は Issue / Pull Request を受け付けてください。

---

以上が KabuSys の概要・セットアップ・使い方の要約です。詳細は各モジュール（特に kabusys/data/*.py）内の docstring を参照してください。必要であれば README にサンプル .env.example や具体的な運用スクリプト例を追加できます。