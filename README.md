# KabuSys

KabuSys は日本株の自動売買・データ基盤ライブラリです。J-Quants API から市場データ・財務データ・マーケットカレンダーを取得して DuckDB に蓄積し、ニュース収集・品質チェック・ETL パイプライン・監査ログなどを提供します。発注・戦略・モニタリング用の骨組み（execution / strategy / monitoring）も含まれます。

バージョン: 0.1.0

---

## 主な機能

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）遵守、リトライ（指数バックオフ）、トークン自動更新
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead bias を防止
- DuckDB ベースのスキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - 監査ログ用スキーマ（signal / order_request / execution など）
- ETL パイプライン
  - 差分更新（最終取得日を参照）、バックフィル、品質チェックの実行
  - 日次 ETL エントリポイント（run_daily_etl）
- ニュース収集
  - RSS フィード収集、URL 正規化、記事 ID のハッシュ化、SSRF 対策、gzip 限度
  - raw_news / news_symbols への冪等保存（INSERT ... RETURNING）
- データ品質チェック
  - 欠損、重複、スパイク（前日比）、日付不整合などを検出
  - 問題は QualityIssue オブジェクトで集約
- カレンダー管理
  - market_calendar の差分更新、営業日判定（next/prev/get_trading_days 等）
- 監査ログ（audit）
  - 発生したシグナルから注文・約定までを UUID で連鎖してトレース可能にするスキーマ

セキュリティ・堅牢性面の特徴:
- .env 自動読み込み（プロジェクトルート検出）
- RSS パーサに defusedxml、SSRF リダイレクト検査、サイズ上限
- API 呼び出しでの retry / backoff / rate limiting
- DuckDB への保存は冪等（ON CONFLICT）設計

---

## 必要条件（依存パッケージ）

主な依存（プロジェクトに requirements.txt が無い場合の例）:
- Python 3.10+
- duckdb
- defusedxml

（実行環境に応じてその他標準ライブラリを使用）

インストール例:
```bash
pip install -e .        # editable install（パッケージが pip パッケージ構造なら）
pip install duckdb defusedxml
```

---

## 環境変数 / 設定

KabuSys は環境変数を通じて設定を取得します。プロジェクトルートに `.env` / `.env.local` がある場合、自動的に読み込まれます（自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須環境変数:
- JQUANTS_REFRESH_TOKEN - J-Quants の refresh token
- KABU_API_PASSWORD - kabuステーション API のパスワード
- SLACK_BOT_TOKEN - Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID - Slack チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV - "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL - "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"（デフォルト: INFO）
- DUCKDB_PATH - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH - SQLite（監視用等）パス（デフォルト: data/monitoring.db）

.env の例:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 環境を準備（venv 等）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   pip install -e .
   ```

3. 環境変数を設定（`.env` を作成）
   - 上記の必須項目を `.env` に記載するか、環境に直接設定します。

4. DuckDB スキーマを初期化
   Python インタプリタまたはスクリプトから:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")   # または ":memory:"
   conn.close()
   ```
   監査ログ用 DB を別途作る場合:
   ```python
   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   audit_conn.close()
   ```

---

## 使い方（主要 API）

以下は主要なモジュールと簡単な使用例です。

- J-Quants クライアント（データ取得）
  ```python
  from kabusys.data import jquants_client as jq
  # id_token は省略可能（内部で refresh_token から取得）
  daily = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
  financials = jq.fetch_financial_statements(code="7203")
  calendar = jq.fetch_market_calendar()
  ```

- DuckDB への保存（jquants_client が提供する保存関数を使用）
  ```python
  import duckdb
  from kabusys.data import jquants_client as jq, schema

  conn = schema.init_schema("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=..., date_to=...)
  saved = jq.save_daily_quotes(conn, records)
  ```

- ニュース収集
  ```python
  from kabusys.data import news_collector, schema
  conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB へ接続
  articles = news_collector.fetch_rss(
      "https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance"
  )
  new_ids = news_collector.save_raw_news(conn, articles)
  # 銘柄紐付け（known_codes は事前に取得して渡す）
  news_collector.save_news_symbols(conn, new_ids[0], ["7203", "6758"])
  ```

- 日次 ETL 実行
  ```python
  from kabusys.data import pipeline, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- データ品質チェック単体実行
  ```python
  from kabusys.data import quality, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  issues = quality.run_all_checks(conn)
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

---

## ETL を定期実行する（運用例）

- cron / systemd timer などで日次ジョブを回し、run_daily_etl を呼ぶスクリプトを実行します。
- 実行結果やエラーは Slack 等に通知する仕組みを別途実装してください（Slack トークンは環境変数で管理）。
- calendar は先読み（lookahead）を行うため、夜間に calendar_update_job を回すだけでも可。

簡単な実行スクリプト例（run_etl.py）:
```python
from kabusys.data import pipeline, schema

conn = schema.get_connection("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

---

## ディレクトリ構成（主なファイル）

プロジェクトの主要なファイルは以下の通りです（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py        # J-Quants API クライアント
    - news_collector.py       # RSS ニュース収集
    - schema.py               # DuckDB スキーマ定義・初期化
    - pipeline.py             # ETL パイプライン
    - calendar_management.py  # マーケットカレンダー管理
    - audit.py                # 監査ログ（トレーサビリティ）定義
    - quality.py              # データ品質チェック
  - strategy/
    - __init__.py
    # 戦略ロジックはここに追加
  - execution/
    - __init__.py
    # 発注・ブローカー接続ロジックを実装する場所
  - monitoring/
    - __init__.py
    # 監視・メトリクス周りを実装する場所

（上記以外にテストやドキュメント、CI 設定などがあることを想定）

---

## 注意事項 / 実装上のポイント

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を起点に行われます。テスト時や特殊環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを無効にできます。
- J-Quants API のレート制限（120 req/min）を尊重する実装になっています。大量取得を行う場合は間隔に注意してください。
- news_collector は SS R F、XML Bomb、巨大レスポンス等に配慮した実装（ホスト検証、サイズ制限、defusedxml 使用）になっています。
- DuckDB に対する DDL は冪等（IF NOT EXISTS）です。既存 DB へのマイグレーションは別途検討してください。
- すべてのタイムスタンプは UTC を基本に扱う方針です（監査ログは SET TimeZone='UTC' を実行）。

---

## 貢献・拡張

- strategy / execution / monitoring モジュールは骨組みとして用意されています。ここに戦略ロジック、オーダー送信処理（kabu API 連携）、モニタリングダッシュボード等を実装してください。
- テストを書いて、network 周りや DB 操作をモックして CI を整備することを推奨します。

---

必要であれば README を英語版にしたり、実際の運用手順（systemd ユニット / Docker / Kubernetes）向けのガイドを追加します。どの形式がよいか指示してください。