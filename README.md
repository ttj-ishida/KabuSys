# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買・データ基盤を想定したライブラリ群です。J-Quants API や RSS フィードから市場データ・ニュースを収集し、DuckDB に冪等に保存、ETL／品質チェック、マーケットカレンダー管理、監査ログ（発注〜約定のトレース）などを提供します。

---

## 主な特徴（機能一覧）

- J-Quants API クライアント
  - 日次株価（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レート制御（120 req/min 固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を防止

- ニュース収集（RSS）
  - RSS から記事を収集して `raw_news` に保存（記事ID は正規化 URL の SHA-256 先頭32文字）
  - SSRF 対策、レスポンスサイズ制限（デフォルト 10 MB）、gzip サポート、XML パースの安全化（defusedxml）
  - 記事 → 銘柄コードの抽出（既知コードセットに基づく 4 桁抽出）と紐付け（`news_symbols`）

- データベース（DuckDB）スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - 冪等なスキーマ初期化関数（`init_schema` / `init_audit_db`）

- ETL パイプライン
  - 差分更新（最終取得日からの差分取得）、バックフィル（デフォルト 3 日）
  - カレンダー先読み（デフォルト 90 日）
  - 品質チェック（欠損、重複、スパイク、日付不整合）

- 品質チェック（quality モジュール）
  - 欠損（OHLC）、主キー重複、前日比スパイク（デフォルト 50% 閾値）、未来日付／非営業日データなど
  - 問題は QualityIssue オブジェクトとして集約して返す（エラー／警告の区別）

- 監査ログ（audit モジュール）
  - シグナル→発注要求→約定までのトレース用テーブル（冪等・ステータス管理）
  - すべてのタイムスタンプは UTC 保存

---

## セットアップ手順

前提: Python 3.9+（タイプアノテーションに Path | None 等を使用しているため少なくとも 3.10 を想定する実装も含まれます）。実行環境に合わせて適宜調整してください。

1. リポジトリをクローン／配置
   - 例: git clone ... （既にコードがあるものとして進めます）

2. 仮想環境を作成してアクティベート（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\activate     (Windows)

3. 依存ライブラリをインストール
   - 必要最低限（サンプル）:
     - duckdb
     - defusedxml
   - pip を使ってインストール例:
     ```
     pip install duckdb defusedxml
     ```
   - 実際には追加で urllib, logging など標準ライブラリのみで済みますが、プロジェクトで別の依存があれば requirements.txt を参照してください。

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（自動ロードはデフォルトで有効）。
   - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   重要な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN – J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD – kabu API のパスワード（必須）
   - SLACK_BOT_TOKEN – Slack 通知用 bot トークン（必須）
   - SLACK_CHANNEL_ID – Slack チャネル ID（必須）

   オプション
   - KABU_API_BASE_URL – kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH – DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH – SQLite パス（モニタリング用、デフォルト: data/monitoring.db）
   - KABUSYS_ENV – environment (development|paper_trading|live)（デフォルト: development）
   - LOG_LEVEL – ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡単なコード例）

以下はライブラリの主要機能を Python スクリプト／REPL から利用する例です。

- DuckDB スキーマ初期化（すべてのテーブルを作成）
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

- 監査ログ専用 DB 初期化
```python
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

- 日次 ETL 実行（株価、財務、カレンダー取得 + 品質チェック）
```python
from kabusys.data import pipeline
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")  # 既に init_schema を実行済みの想定
result = pipeline.run_daily_etl(conn)  # 引数で target_date や id_token を渡せます
print(result.to_dict())
```

- ニュース収集ジョブ（RSS → raw_news / news_symbols）
```python
from kabusys.data import news_collector
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")

# 既知の銘柄コードセットを用意しておく（例: 全上場コードリスト）
known_codes = {"7203", "6758", "9984", ...}

# デフォルトソースを使う場合
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

- 市場カレンダーの夜間更新ジョブ
```python
from kabusys.data import calendar_management
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print(f"saved calendar rows: {saved}")
```

- J-Quants の日足を直接フェッチして保存（テストや部分取得）
```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
```

- 品質チェック単体実行
```python
from kabusys.data import quality
issues = quality.run_all_checks(conn)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

注意点:
- news_collector.fetch_rss は SSRF 等を防ぐためスキームやホストの検証を行います。RSS URL は http/https のみ。
- jquants_client は API レート制限を内部で制御します（120 req/min）。テストで自動ロードを抑止する際は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## 主な API / エントリポイント（参考）

- kabusys.config
  - settings: 環境変数から各種設定を取得（例: settings.jquants_refresh_token）
  - 自動 .env ロード機能（プロジェクトルート検出: .git または pyproject.toml）

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
  - run_prices_etl, run_financials_etl, run_calendar_etl

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - run_news_collection(conn, sources=None, known_codes=None)

- kabusys.data.calendar_management
  - is_trading_day(conn, d)
  - next_trading_day(conn, d)
  - prev_trading_day(conn, d)
  - get_trading_days(conn, start, end)
  - calendar_update_job(conn, lookahead_days=90)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)

- kabusys.data.audit
  - init_audit_db(db_path)
  - init_audit_schema(conn, transactional=False)

---

## ディレクトリ構成

プロジェクト内の主なファイル構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数 / 設定読み込みロジック
  - data/
    - __init__.py
    - schema.py              -- DuckDB スキーマ定義 / init_schema
    - jquants_client.py      -- J-Quants API クライアント（取得・保存）
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - news_collector.py      -- RSS ニュース収集／保存ロジック
    - calendar_management.py -- マーケットカレンダー管理（営業日判定 等）
    - audit.py               -- 監査ログテーブル定義／init
    - quality.py             -- データ品質チェック
  - strategy/
    - __init__.py            -- 戦略関連 (将来的に拡張)
  - execution/
    - __init__.py            -- 発注・実行関連 (将来的に拡張)
  - monitoring/
    - __init__.py            -- 監視／モニタリング関連 (将来的に拡張)

---

## 運用上の注意 / 設計上のポイント

- J-Quants API に対するレート制限（120 req/min）を厳守するため、クライアント側でのスロットリングを実装しています。
- API エラー時のリトライ設計:
  - ネットワーク系エラー（URLError/Timeout 等）や 408/429/5xx は指数バックオフで最大 3 回リトライ。
  - 401 は自動で ID トークンをリフレッシュして 1 回リトライ（無限ループ防止）。
- データ保存は冪等（INSERT ... ON CONFLICT DO UPDATE / DO NOTHING）で重複や再実行に耐えられる設計です。
- ニュース収集は SSRF、XML Bomb、巨大レスポンス対策（サイズ制限・defusedxml）を実装しています。
- 品質チェックは Fail-Fast にせず、すべてのチェックを実行して結果を集める方針です。呼び出し側が重大度に応じた対処を行います。
- 監査ログは削除せず永続化する方針（FK は ON DELETE RESTRICT 等で保護）。

---

## ライセンス / 貢献

この README はコードベースの内容を要約したものであり、実運用時は API キーやパスワードの管理、セキュリティポリシー、さらに詳細な監査・ロギング設定を適切に行ってください。貢献や改善提案は Pull Request / Issue を通じて歓迎します。

---

必要であれば、README に加えるサンプル .env.example やより詳細なデプロイ手順（systemd / Cron / Airflow 等のジョブ設定）、テスト方法や CI 設定のテンプレートも作成できます。どの情報を追加しますか？