# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。データ取得・ETL・データ品質チェック・ニュース収集・監査ログ等の基盤機能を提供します。

主な設計方針：
- J-Quants API など外部データソースからの差分取得（差分ETL）
- DuckDB を用いたローカルデータレイク（冪等な保存：ON CONFLICT）
- API レート制御とリトライ/トークン自動リフレッシュ
- ニュース収集における SSRF / XML 攻撃対策、トラッキング除去
- 監査ログによるシグナル→発注→約定のトレーサビリティ

---

## 機能一覧

- 環境設定管理
  - .env / 環境変数から設定を自動読み込み（プロジェクトルート検出）
  - 必須パラメータ取得 API（例: settings.jquants_refresh_token）
- J-Quants API クライアント（data/jquants_client.py）
  - 日足（OHLCV）・財務（四半期）・マーケットカレンダー取得
  - レート制御（120 req/min）・リトライ（指数バックオフ）・401 時のトークン自動更新
  - DuckDB への冪等保存（save_... 関数）
- ETL パイプライン（data/pipeline.py）
  - 差分更新ロジック（最終取得日からの差分 / backfill）
  - 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
- データ品質チェック（data/quality.py）
  - 欠損、重複、前日比スパイク、日付不整合チェック
  - QualityIssue オブジェクトで問題を収集
- ニュース収集（data/news_collector.py）
  - RSS から記事収集・前処理・記事ID生成（正規化URL の SHA-256 先頭32文字）
  - SSRF 対策、gzip 上限チェック、defusedxml による XML 攻撃対策
  - DuckDB への冪等保存・銘柄抽出（4桁コード）
- スキーマ定義・初期化（data/schema.py、data/audit.py）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - 監査ログ（signal_events / order_requests / executions）とインデックス
  - init_schema / init_audit_schema を提供
- マーケットカレンダー管理（data/calendar_management.py）
  - 営業日判定、前後営業日計算、カレンダーの夜間更新ジョブ
- そのほか：strategy、execution、monitoring の名前空間（実装の拡張余地あり）

---

## 必要条件

- Python 3.10+
- 主な依存ライブラリ（最低限）
  - duckdb
  - defusedxml

推奨：プロジェクトの pyproject.toml / requirements.txt がある場合はそちらを利用してください。最低限のインストール例は下記を参照。

---

## セットアップ手順（クイックスタート）

1. リポジトリを取得
   - git clone <リポジトリURL>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. パッケージをインストール
   - 開発パッケージが pyproject.toml にある場合:
     - pip install -e .
   - 最低限の依存を直接インストールする場合:
     - pip install duckdb defusedxml

   （Slack 通知などを使う場合は slack-sdk 等の追加パッケージが必要となる可能性があります）

4. 環境変数 / .env を用意
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと自動で読み込まれます（テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須キー（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
   - 任意 / デフォルト:
     - KABUSYS_ENV=development|paper_trading|live  (default: development)
     - LOG_LEVEL=INFO|DEBUG|...
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1  (自動読み込みを無効化)
     - DUCKDB_PATH=data/kabusys.duckdb  (デフォルト)
     - SQLITE_PATH=data/monitoring.db  (デフォルト)

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. データベーススキーマを初期化
   - Python REPL またはスクリプトで DuckDB スキーマを作成します。
   - 例:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)  # settings.duckdb_path は Path を返します
     ```

   - 監査ログスキーマ（必要な場合）:
     ```python
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)
     ```

---

## 使い方（代表的な例）

- 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）を実行する例：
  ```python
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  # DB 初期化（初回のみ）
  conn = init_schema(settings.duckdb_path)

  # 日次ETL を実行（戻り値は ETLResult）
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- ニュース収集を実行する例：
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection

  conn = init_schema("data/kabusys.duckdb")
  results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  print(results)  # {source_name: 新規保存件数}
  ```

- J-Quants から日足を直接取得して保存する例：
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  records = fetch_daily_quotes(code="7203", date_from=..., date_to=...)
  saved = save_daily_quotes(conn, records)
  ```

- カレンダー更新夜間ジョブを呼ぶ例：
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  ```

- 品質チェックだけを実行する例：
  ```python
  from kabusys.data.quality import run_all_checks
  conn = get_connection("data/kabusys.duckdb")
  issues = run_all_checks(conn)
  for issue in issues:
      print(issue)
  ```

---

## 環境変数の注意点

- 自動で .env を読み込む仕組みがあります（プロジェクトルートにある `.env` / `.env.local`）。環境変数を優先します。
- テスト時や明示的に読み込みを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- settings で必須値を取得し、未設定の場合は ValueError を投げます（例: settings.jquants_refresh_token）。

---

## 実装上の主要な設計・運用上の注意

- J-Quants API 周り
  - 120 req/min のレート制御に従う（モジュールの RateLimiter）。
  - リトライ：408/429/5xx, 最大 3 回、429 の場合は Retry-After を尊重。
  - 401 が来たらリフレッシュトークンから id_token を自動更新して 1 回だけ再試行。
  - 取得したデータには fetched_at（UTC）を付与して、いつこのデータが取得されたかをトレース可能にしています（Look-ahead Bias 対策）。
- ニュース収集
  - URL 正規化・トラッキングパラメータ除去を行い、同一記事の二重登録を防止。
  - XML パーサは defusedxml を使用（XML Bomb 対策）。
  - リダイレクト時や最終 URL に対してプライベートアドレス判定を行い SSRF を防止。
  - レスポンスサイズを上限（デフォルト 10MB）で検査してメモリ DoS を防ぐ。
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE / DO NOTHING）を基本としています。
- 監査ログ（audit）では UTC タイムスタンプ、冪等キー（order_request_id / broker_execution_id）など運用に必要な要素を備えています。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py  -- パッケージ定義（バージョン等）
  - config.py    -- 環境変数・設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py       -- J-Quants API クライアント（fetch/save）
    - news_collector.py      -- RSS ニュース収集と保存ロジック
    - schema.py              -- DuckDB スキーマ定義・初期化（init_schema）
    - pipeline.py            -- ETL（差分更新 / run_daily_etl）
    - calendar_management.py -- 市場カレンダー管理（営業日判定等）
    - audit.py               -- 監査ログスキーマ（signal/order/execution）
    - quality.py             -- データ品質チェック
  - strategy/
    - __init__.py            -- 戦略モジュールの名前空間（拡張用）
  - execution/
    - __init__.py            -- 発注／ブローカー接続等（拡張用）
  - monitoring/
    - __init__.py            -- 監視用モジュール（拡張用）

---

## よくある質問 / トラブルシューティング

- .env が読み込まれない
  - プロジェクトルート検出は src/kabusys/config.py の __file__ を基準に親ディレクトリで `.git` または `pyproject.toml` を探します。該当ファイルがない場合は自動ロードをスキップします。
  - 自動ロードを無効にしているか（KABUSYS_DISABLE_AUTO_ENV_LOAD）を確認してください。
- DuckDB の初期化エラー
  - パスの親ディレクトリが存在しない場合は init_schema が自動作成しますが、権限やファイルロック等に注意してください。
- J-Quants のレート制限に引っかかる
  - 本クライアントは 120 req/min に合わせた最小間隔で待機しますが、連続大量取得を行うと429 が返ることがあります。429 の場合は Retry-After を尊重して再試行します。

---

この README はライブラリの利用開始のための基本情報をまとめたものです。各モジュール内の docstring に詳細な利用方法や設計意図が書かれていますので、実装や拡張を行う際は該当ファイルを参照してください。必要であればサンプルスクリプトや CLI を追加して運用しやすくすることを推奨します。