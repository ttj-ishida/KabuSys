# KabuSys

日本株向け自動売買基盤ライブラリ（KabuSys）のリポジトリ向け README。

このドキュメントはリポジトリ内のコードを元に、プロジェクト概要・機能・セットアップ方法・基本的な使い方・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォームのためのライブラリ群です。データ収集（J-Quants API / RSS ニュース）、ETL パイプライン、データ品質チェック、マーケットカレンダー管理、監査ログ（発注→約定のトレース）など、機械学習／戦略実行に必要な基盤機能を提供します。内部データベースには DuckDB を使用します。

設計上のポイント：
- API レートリミッティング、リトライ、トークン自動リフレッシュ
- データ取得時に fetched_at を記録して Look-ahead Bias を防止
- DuckDB への保存は冪等（ON CONFLICT）で重複を回避
- RSS ニュースはトラッキングパラメータ削除、SSRF や XML インジェクション対策済み
- 品質チェック（欠損・スパイク・重複・日付不整合）を備える
- 監査ログ（signal → order_request → execution）で完全トレーサビリティ

---

## 主な機能一覧

- 環境変数設定管理（.env 自動読み込み・検証）
- J-Quants API クライアント
  - 日次株価（OHLCV）、四半期財務、マーケットカレンダー取得
  - レート制御・再試行・トークン自動更新
  - DuckDB への冪等保存関数
- RSS ニュース収集（正規化・前処理・DB 保存・銘柄紐付け）
- DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログテーブル（signal / order_request / executions）初期化

---

## セットアップ手順

前提：
- Python 3.10 以上（型注釈で | を使用しているため）
- ネットワークアクセス（J-Quants / RSS）
- DuckDB（Python パッケージとして使用）

推奨インストール手順（プロジェクトルートで実行）：

1. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージをインストール
   最低限必要なパッケージ：
   ```
   pip install duckdb defusedxml
   ```
   （プロジェクトに pyproject.toml / requirements.txt がある場合はそちらを使用してください。editable install:
   ```
   pip install -e .
   ```）

3. 環境変数設定
   プロジェクトルートに `.env` と `.env.local`（任意）を作成できます。自動ロードの挙動：
   - OS 環境変数 > .env.local > .env の優先順位で読み込み（ただし OS 環境は上書き不可）
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（有効値）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

   注意：Settings プロパティ（kabusys.config.settings）からこれらを参照します。必須変数が未設定の場合は ValueError が発生します。

---

## 使い方（基本例）

以下はライブラリ API の代表的な利用例です。実行は Python スクリプトや REPL から可能です。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema

# デフォルトのファイルパスを使う場合
conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ
# conn = schema.init_schema(":memory:")
```

2) 日次 ETL を実行（J-Quants への認証トークンは settings 経由で自動取得）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定しないと today が使われます
print(result.to_dict())
```

3) ニュース収集ジョブを実行
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# known_codes を渡すと記事に含まれる銘柄コード抽出（重複除去・known_codes に基づく）
known_codes = {"7203", "6758", "9984"}  # 例
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: 新規保存数}
```

4) カレンダー更新バッチ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved calendar rows:", saved)
```

5) 監査ログテーブルの初期化（別 DB に分ける場合など）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

6) 設定（環境変数）参照
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.duckdb_path)  # Path オブジェクト
print(settings.env, settings.log_level)
```

ログ出力を有効にしたい場合は標準 logging を設定してください（LOG_LEVEL 環境変数でも制御可能）。

---

## よく使う API 要約

- kabusys.config.Settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.duckdb_path, settings.env など

- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)

- kabusys.data.jquants_client
  - get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()
  - save_daily_quotes(conn, records), save_financial_statements(...), save_market_calendar(...)

- kabusys.data.pipeline
  - run_daily_etl(conn, ...), run_prices_etl(...), run_financials_etl(...), run_calendar_etl(...)

- kabusys.data.news_collector
  - fetch_rss(url, source), save_raw_news(conn, articles), run_news_collection(conn, ...)

- kabusys.data.quality
  - run_all_checks(conn, ...), check_missing_data(...), check_spike(...)

- kabusys.data.calendar_management
  - is_trading_day(conn, d), next_trading_day(conn, d), prev_trading_day(conn, d), get_trading_days(...)

- kabusys.data.audit
  - init_audit_db(db_path), init_audit_schema(conn, transactional=False)

---

## 運用上の注意 / 実装上のポイント

- J-Quants の API レート制限（120 req/min）に合わせた内部 RateLimiter を持ちます。大量取得時は十分な時間を確保してください。
- API リトライや 401 時のトークン自動リフレッシュを備えていますが、適切なトークン（JQUANTS_REFRESH_TOKEN）を用意してください。
- RSS 取得は SS R F や XML 攻撃対策済みですが、外部フィードの信頼性や帯域に注意してください。
- DuckDB のファイルパスは settings.duckdb_path により制御できます。バックアップや排他制御を運用で考慮してください。
- ETL 実行後は quality.run_all_checks によりデータ品質を確認可能です。品質問題は Fail-Fast せずに収集され、呼び出し側で判断できます。

---

## ディレクトリ構成

本リポジトリ（src 配下）のおおまかな構成：

- src/
  - kabusys/
    - __init__.py
    - config.py                      # 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py            # J-Quants API クライアント + 保存ロジック
      - news_collector.py            # RSS ニュース収集・保存・銘柄抽出
      - schema.py                    # DuckDB スキーマ定義・初期化
      - pipeline.py                  # ETL パイプライン（差分更新・品質チェック）
      - calendar_management.py       # マーケットカレンダー管理
      - audit.py                     # 監査ログ（signal/order_request/executions）初期化
      - quality.py                   # データ品質チェック
    - strategy/                       # 戦略関連（未実装部分のプレースホルダ）
      - __init__.py
    - execution/                      # 発注/実行管理（未実装部分のプレースホルダ）
      - __init__.py
    - monitoring/                     # 監視（プレースホルダ）
      - __init__.py

（上記はコードベースから抽出した主要ファイルとモジュールです）

---

## トラブルシューティング

- 環境変数エラー: settings の必須プロパティ参照時に ValueError が出たら `.env` や環境変数を確認してください。
- DuckDB 接続エラー: パスの親ディレクトリが存在しない場合は init_schema が自動で作成しますが、書き込み権限を確認してください。
- ネットワーク / API エラー: jquants_client のリトライ機構はありますが、接続先・認証情報・API 利用制限を確認してください。
- RSS 取得が空になる: フィードの Content-Length 上限や gzip 解凍失敗、XML パースエラーの可能性があります。ログを確認してください。

---

## 開発・拡張

- strategy / execution / monitoring は拡張ポイントです。戦略と発注ロジック、監視アラートを実装するためのモジュールが用意されています。
- DuckDB のスキーマは schema.py にまとめられているため、新しいテーブルを追加する場合は同ファイルを編集し init_schema を用いて反映してください。
- テスト時は自動 .env ロードを無効化するために `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定できます。

---

この README はコード（src/kabusys 以下）に基づいて作成しています。実際の運用やデプロイ手順、CI 設定、より詳細な API ドキュメントは別途まとめることを推奨します。必要であればサンプルスクリプトやより細かい使い方（cron ジョブや Docker 化、Slack 通知の利用方法等）も追加できますので、希望があれば教えてください。