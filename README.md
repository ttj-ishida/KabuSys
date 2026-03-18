# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ / ツール群です。  
データ取得（J‑Quants）、ETL パイプライン、ニュース収集、マーケットカレンダー管理、監査ログ（発注→約定のトレース）など、運用に必要な基盤機能を提供します。

主な設計方針：
- DuckDB を用いたローカル DB（軽量・高速・SQL ベース）
- J‑Quants API のレート制御・リトライ・トークン自動リフレッシュ対応
- ニュース収集では SSRF/Gzip/XML Bomb 等への対策を実装
- ETL は差分取得・バックフィル・品質チェックを備え、冪等（ON CONFLICT）保存を行う
- 監査テーブルでシグナル→発注→約定のトレーサビリティを保持

---

## 機能一覧

- data/jquants_client.py
  - J‑Quants API からのデータ取得（株価日足、四半期財務、マーケットカレンダー）
  - レートリミッタ、リトライ、401 時のトークン自動リフレッシュ、fetched_at の記録
  - DuckDB への冪等保存（raw_prices / raw_financials / market_calendar）

- data/news_collector.py
  - RSS フィード収集 → 前処理（URL 除去など） → raw_news へ冪等保存
  - 記事 ID は正規化 URL の SHA‑256（先頭 32 文字）
  - SSRF / プライベート IP / gzip / XML 攻撃対策
  - 銘柄コード抽出と news_symbols への紐付け

- data/schema.py / audit.py
  - DuckDB 用のスキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema / init_audit_db によるテーブル作成（冪等）

- data/pipeline.py
  - 日次 ETL（run_daily_etl）：カレンダー → 株価 → 財務 → 品質チェック（quality）
  - 差分更新、バックフィル、品質チェックの集約（ETLResult を返す）

- data/calendar_management.py
  - market_calendar の夜間差分更新ジョブ
  - 営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）

- data/quality.py
  - 欠損・重複・スパイク（前日比）・日付不整合のチェック
  - QualityIssue オブジェクトで検出結果を返す

- config.py
  - .env 自動読み込み（プロジェクトルート検出: .git / pyproject.toml）
  - 必須環境変数取得（Settings クラス）
  - 自動読み込み無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD

---

## セットアップ手順

以下はローカルでライブラリを使うための例です。

1. Python 環境（3.9+ 推奨）を用意
   - 仮想環境の作成例：
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```

2. 依存パッケージをインストール
   - 本コードベースで直接参照される主な外部パッケージ：
     - duckdb
     - defusedxml
   - pip でインストール：
     ```
     pip install duckdb defusedxml
     ```

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使ってください）

3. 環境変数の設定 (.env)
   - プロジェクトルートに `.env`（および開発用に `.env.local`）を置くと自動で読み込まれます。
   - 必須環境変数（Settings から）：
     - JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API のパスワード
     - SLACK_BOT_TOKEN — Slack 通知に使う Bot トークン
     - SLACK_CHANNEL_ID — 通知先 Slack チャンネル ID
   - 任意 / デフォルト値:
     - KABUSYS_ENV — (development | paper_trading | live)（デフォルト: development）
     - LOG_LEVEL — (DEBUG|INFO|WARNING|ERROR|CRITICAL)（デフォルト: INFO）
     - KABU_API_BASE_URL — kabuAPI のベース（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

   - `.env` の自動ロードを無効にしたい場合：
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. データベース初期化
   - DuckDB スキーマを作成:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ専用 DB を作る（必要に応じて）:
     ```python
     from kabusys.data import audit
     audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（例）

- 日次 ETL を実行（J‑Quants から最新データ取得 → 保存 → 品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data import pipeline, schema

  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブを実行
  ```python
  from kabusys.data import news_collector, schema

  conn = schema.get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
  results = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: new_count, ...}
  ```

- カレンダー夜間更新ジョブ
  ```python
  from kabusys.data import calendar_management, schema

  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  print("saved:", saved)
  ```

- J‑Quants の ID トークンを手動で取得
  ```python
  from kabusys.data import jquants_client as jq
  token = jq.get_id_token()  # settings.jquants_refresh_token を使用して取得
  ```

- DuckDB 接続を直接取得（既存 DB へ接続）
  ```python
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")
  ```

ログは Python の logging 設定に従って出力されます。環境変数 LOG_LEVEL でログレベルを制御してください。

---

## ディレクトリ構成

（主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - calendar_management.py
    - audit.py
    - quality.py
  - strategy/
    - __init__.py
    (戦略用モジュールを配置)
  - execution/
    - __init__.py
    (発注とブローカー連携用を配置)
  - monitoring/
    - __init__.py
    (監視・メトリクス関連)

簡易ツリー（プロジェクトルートから）：
```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py
   ├─ data/
   │  ├─ __init__.py
   │  ├─ jquants_client.py
   │  ├─ news_collector.py
   │  ├─ schema.py
   │  ├─ pipeline.py
   │  ├─ calendar_management.py
   │  ├─ audit.py
   │  └─ quality.py
   ├─ strategy/
   │  └─ __init__.py
   ├─ execution/
   │  └─ __init__.py
   └─ monitoring/
      └─ __init__.py
```

---

## 環境変数一覧（主なもの）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID

- 任意 / デフォルト:
  - KABUSYS_ENV (development | paper_trading | live) — default: development
  - LOG_LEVEL — default: INFO
  - KABU_API_BASE_URL — default: http://localhost:18080/kabusapi
  - DUCKDB_PATH — default: data/kabusys.duckdb
  - SQLITE_PATH — default: data/monitoring.db
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — set to 1 to disable .env auto load

注意: Settings クラスは必須環境変数が未設定の場合 ValueError を投げます。

---

## 設計上の注意点 / 運用メモ

- J‑Quants API は 120 req/min のレート制限を意識しており、内部で固定間隔レートリミッタを使っています。
- HTTP エラーやネットワークエラーに対する指数バックオフのリトライと、401 時のトークン自動リフレッシュを実装しています。
- ニュース収集では外部から与えられる RSS に対して SSRF や XML 関連の攻撃対策を行っています。外部ソースを追加する際は URL の妥当性を確認してください。
- DuckDB のスキーマは冪等に作成されるため、既存 DB に対して繰り返し初期化ができます。
- ETL は Fail‑Fast ではなく、可能な限り他のデータ取得を継続する設計です。run_daily_etl の返却値（ETLResult）で品質問題や実行エラーを確認してください。
- 監査ログは削除前提ではないため、トレーサビリティを維持する目的でデータ保持方針を検討してください。

---

この README はコードベースの概要と基本的な使い方をまとめたものです。プロジェクト固有の運用手順（デプロイ、CI、運用監視、Slack 通知の実装など）は別途ドキュメント化してください。必要であれば README にサンプル .env.example や運用チェックリストも追加できます。