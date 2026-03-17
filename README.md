# KabuSys

日本株向け自動売買／データ基盤ライブラリ

KabuSys は日本株のデータ収集・ETL・品質チェック・監査ログ・ニュース収集などを備えたライブラリ群です。J-Quants API を主なデータソースとして扱い、DuckDB を使った冪等（idempotent）なデータ保存や、ニュース RSS の安全な収集、マーケットカレンダー管理、ETL パイプライン、品質チェック、監査ログスキーマなどを提供します。

バージョン: 0.1.0

---

## 主な機能

- 環境変数／設定管理
  - .env/.env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定の取得とバリデーション（env/ログレベルなど）

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日次株価（OHLCV）取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）取得（ページネーション対応）
  - JPX マーケットカレンダー取得
  - API レート制御（120 req/min）、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事収集、前処理（URL除去・空白正規化）
  - 記事ID は正規化 URL の SHA-256（先頭32文字）で冪等性確保
  - defusedxml による XML 攻撃対策、SSRF 対策、受信サイズ制限
  - DuckDB へのバルク保存（INSERT ... RETURNING）と銘柄紐付け

- スキーマ管理（kabusys.data.schema / audit）
  - Raw / Processed / Feature / Execution / Audit 層の DuckDB テーブル定義と初期化
  - 監査ログ（signal, order_request, execution）スキーマ、UTC タイムスタンプ

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日 + バックフィル）によるデータ取得と保存
  - カレンダー先読み、品質チェックの組込み実行
  - run_daily_etl による日次パイプライン実行（結果は ETLResult）

- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定（is_trading_day / is_sq_day）・前後営業日検索（next/prev）
  - 夜間バッチ更新 job（calendar_update_job）

- 品質チェック（kabusys.data.quality）
  - 欠損、スパイク（前日比閾値）、重複、日付不整合などの検出
  - QualityIssue オブジェクトで詳細とサンプルを返す

- その他
  - settings 経由でのアプリ設定参照（J-Quants トークン、kabu API パスワード、Slack トークン等）
  - strategy / execution / monitoring 用のパッケージプレースホルダ

---

## 必要な環境・依存

- Python 3.10+ を想定（型アノテーションに依存）
- 主な依存パッケージ:
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API / RSS）

（パッケージ化/pyproject.toml がある想定で pip install -e . 等でインストールしてください）

---

## セットアップ手順（ローカル）

1. リポジトリをクローン
   ```bash
   git clone <リポジトリURL>
   cd <リポジトリ>
   ```

2. 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - pyproject.toml / requirements.txt がある場合はそれに従ってください。最小限は:
   ```bash
   pip install duckdb defusedxml
   ```
   - 開発用に編集可能インストール（プロジェクトがパッケージ化されていれば）:
   ```bash
   pip install -e .
   ```

4. 環境変数を準備
   - プロジェクトルート（.git または pyproject.toml を含む場所）に `.env` や `.env.local` を置くと自動で読み込まれます（auto-load はデフォルト有効）。
   - 自動ロードを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

   - 主に必要な環境変数（一例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN: Slack Bot トークン（必須）
     - SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID（必須）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: SQLite（監視）ファイルパス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: environment (development | paper_trading | live)、デフォルト development
     - LOG_LEVEL: ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)、デフォルト INFO

   例 .env（参考）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要な例）

以下は一般的な利用例です。Python スクリプトやジョブから呼び出して利用します。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")
  ```

- 監査ログテーブルを追加（既存接続へ）
  ```python
  from kabusys.data import audit
  audit.init_audit_schema(conn)
  ```

- J-Quants API を使った日次 ETL（全体パイプライン）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # デフォルトで今日の ETL を実行
  print(result.to_dict())
  ```

- 個別 ETL ジョブ（例: 株価のみ）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_prices_etl
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  ```

- ニュース収集（RSS 取得→保存→銘柄紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  known_codes = {"7203", "6758", "9984"}  # 有効銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)  # {source_name: 新規保存件数}
  ```

- カレンダー更新ジョブ（夜間バッチ）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- 品質チェックの実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn)
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

- 設定参照
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  db_path = settings.duckdb_path
  ```

---

## セキュリティ・設計上の注意

- J-Quants API 呼び出しはモジュール内でレート制御・リトライ・401 リフレッシュを行います。大量並列リクエストは避けてください。
- ニュース収集は defusedxml を用い、SSRF 対策や受信サイズ上限（10 MB）、gzip 解凍後サイズチェック等を行っています。外部 URL の扱いには常に注意してください。
- DuckDB への保存は多くの箇所で ON CONFLICT を使って冪等性を保っています。
- すべての監査ログタイムスタンプは UTC 保存を想定しています（audit.init_audit_schema は SET TimeZone='UTC' を実行）。

---

## ディレクトリ構成

（主要なファイル・モジュールを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py        # J-Quants API クライアント（取得・保存）
      - news_collector.py       # RSS ニュース収集・保存・銘柄抽出
      - schema.py               # DuckDB スキーマ定義・初期化
      - pipeline.py             # ETL パイプライン（日次ジョブ等）
      - calendar_management.py  # マーケットカレンダー管理・ジョブ
      - audit.py                # 監査ログスキーマ（signal/order/execution）
      - quality.py              # データ品質チェック
    - strategy/                 # 戦略関連（プレースホルダ）
      - __init__.py
    - execution/                # 発注実行関連（プレースホルダ）
      - __init__.py
    - monitoring/               # 監視機能（プレースホルダ）
      - __init__.py

---

## 開発・拡張メモ

- strategy/、execution/、monitoring/ パッケージはプレースホルダとして存在します。戦略ロジック、発注ラッパー、モニタリング統合はここに追加してください。
- ETL やニュース収集は外部ジョブ（cron / Airflow / Prefect 等）から呼び出す想定です。run_daily_etl や run_news_collection をラップしてログ・通知を追加してください。
- J-Quants の API rate limit（120 req/min）は jquants_client の内部 RateLimiter により制御されますが、複数プロセスで並列実行する場合は別途制御が必要です（トークン共有や分散レート制御）。

---

必要ならば README に記載するサンプル .env.example や CI 用の実行例、詳細な API 使用例（パラメータ説明）も作成します。どの部分をより詳細に記載しますか？