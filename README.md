# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買に向けたデータ収集・ETL・監査基盤の軽量ライブラリです。J-Quants API と連携して株価・財務・マーケットカレンダー・ニュースを取得し、DuckDB に冪等的に保存します。品質チェック、カレンダー管理、ニュース収集、監査ログ初期化などの機能を備え、戦略層・実行層と組み合わせて自動売買システムを構築するための基盤を提供します。

## 主な機能

- J-Quants API クライアント
  - 日足（OHLCV）、四半期財務諸表、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）・リトライ・トークン自動リフレッシュ対応
  - ページネーション対応および取得時刻（fetched_at）記録
- DuckDB スキーマ定義 / 初期化
  - Raw / Processed / Feature / Execution 層のテーブル群を定義
  - インデックス作成、外部キー制約、冪等的な初期化
- ETL パイプライン
  - 差分取得（最終取得日からの差分）＋バックフィル（API の後出し修正吸収）
  - 日次 ETL（カレンダー → 日足 → 財務 → 品質チェック）
- データ品質チェック
  - 欠損、重複、スパイク（前日比急変）、日付不整合の検出
  - QualityIssue オブジェクトで詳細を収集
- ニュース収集（RSS）
  - RSS 取得、XML の安全パース（defusedxml）、URL 正規化、記事ID のハッシュ化
  - SSRF 対策、受信サイズ制限、DB への冪等保存（INSERT ... RETURNING）
  - 記事と銘柄コードの紐付け（news_symbols）
- マーケットカレンダー管理
  - 営業日判定、前後営業日の検索、夜間カレンダー更新ジョブ
  - DB データがない場合は曜日ベースのフォールバック
- 監査ログ（Audit）
  - signal → order_request → execution のトレース用テーブル群の初期化
  - タイムゾーンを UTC に固定して監査証跡を保証

## 要求環境

- Python 3.10+
  - 型注釈に `X | None` などの構文を使用しているため Python 3.10 以上を推奨
- PostgreSQL 等は不要（デフォルトは DuckDB）
- 主な依存パッケージ
  - duckdb
  - defusedxml

（実際のパッケージ要件はプロジェクトの requirements.txt / pyproject.toml を参照してください）

## セットアップ手順

1. リポジトリをクローン、もしくはプロジェクト配布を取得

2. 仮想環境を作成して有効化（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（例）
   ```bash
   pip install duckdb defusedxml
   # またはプロジェクトに requirements.txt があれば
   # pip install -r requirements.txt
   ```

4. 環境変数の設定
   - プロジェクトルートの `.env` / `.env.local` を自動読み込みします（デフォルト）。
   - 自動読み込みを無効にする場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須環境変数（主なもの）
     - JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API のパスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - オプション（デフォルト値あり）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG / INFO / ...
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 で自動 .env ロード無効化
     - DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
     - SQLITE_PATH: デフォルト "data/monitoring.db"
   - 例 `.env`:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

## 使い方（API / 実行例）

以下は代表的な利用例です。モジュールはすべて Python からインポートして利用できます。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（J-Quants トークンは settings.jquants_refresh_token を利用）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- 市場カレンダーの夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"market_calendar に保存された行数: {saved}")
  ```

- ニュース収集ジョブ（RSS）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # known_codes は銘柄コードセット（例: {'7203', '6758', ...}）
  result = run_news_collection(conn, known_codes={'7203', '6758'})
  print(result)
  ```

- 監査ログスキーマの初期化
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

- データ品質チェックを個別に実行
  ```python
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

## 重要な設計上の注意点

- J-Quants のレート上限（120 req/min）に合わせた内部 RateLimiter、リトライ、トークンリフレッシュが実装されています。ライブラリを利用する際はこの挙動を尊重してください。
- DuckDB へは冪等性を担保した INSERT（ON CONFLICT）やトランザクション管理を行っていますが、外部からの直接操作やスキーマ変更には注意してください。
- RSS の取得は SSRF / XML Bomb / 大容量応答対策を講じています。外部 URL を使用する場合でも安全性を考慮してください。
- すべてのタイムスタンプは UTC を原則としています（監査ログ初期化時に TimeZone を UTC に固定）。

## ディレクトリ構成

（抜粋 — 実際のリポジトリに合わせて調整してください）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得・保存）
    - news_collector.py            — RSS ニュース収集・保存・紐付け
    - schema.py                    — DuckDB スキーマ定義・初期化
    - pipeline.py                  — ETL パイプライン（差分取得 / 日次 ETL）
    - calendar_management.py       — マーケットカレンダー管理（営業日ロジック）
    - audit.py                     — 監査ログスキーマ初期化
    - quality.py                   — データ品質チェック
  - strategy/
    - __init__.py                  — 戦略用モジュール（拡張領域）
  - execution/
    - __init__.py                  — 発注・実行関連（拡張領域）
  - monitoring/
    - __init__.py                  — 監視関連（拡張領域）

## 開発 / テスト時のヒント

- 自動で .env をプロジェクトルートから読み込みます。テストで環境変数を明示的に指定したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- テスト用に DuckDB のインメモリ DB を使う場合は db_path に `":memory:"` を指定できます。
- HTTP / ネットワーク呼び出しはモジュールレベルで分離されているため、ユニットテストでは urllib / _urlopen / get_id_token などをモックすることを推奨します。

---

何か特定の機能の詳しい使い方（例: ETL パラメータ調整、ニュースソースの追加、監査スキーマの詳細など）が必要であれば教えてください。README をプロジェクト実行スクリプトや CI 用手順に合わせて拡張できます。