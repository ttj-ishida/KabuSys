# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けデータ基盤および ETL / 収集 / 監査ユーティリティ群です。  
J-Quants API からの市場データ取得、RSS ベースのニュース収集、DuckDB によるスキーマ管理、データ品質チェック、監査ログ（オーダー/約定のトレース）などを提供します。

バージョン: 0.1.0

---

## 主要機能

- 環境変数 / .env 自動読み込み（プロジェクトルート検出）と型付けされた設定アクセス
- J-Quants API クライアント
  - 日足（OHLCV）、四半期財務、マーケットカレンダー取得
  - レートリミット順守（120 req/min）、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
  - フェッチ時刻（fetched_at）を UTC で記録して Look‑ahead Bias を抑制
  - DuckDB への冪等保存（ON CONFLICT ... DO UPDATE）
- ニュース収集モジュール（RSS）
  - URL 正規化／トラッキングパラメータ除去、記事 ID は正規化 URL の SHA-256（先頭32文字）
  - SSRF/リダイレクト対策、受信サイズ上限（Gzip 含む）、defusedxml を利用した安全な XML パース
  - raw_news / news_symbols へ冪等保存（INSERT ... RETURNING を利用して新規挿入を検出）
- DuckDB スキーマ定義
  - Raw / Processed / Feature / Execution / Audit の多層スキーマ定義と初期化ユーティリティ
- ETL パイプライン
  - 差分取得（最終取得日を基に自動算出）、バックフィル、品質チェックの実行（欠損・スパイク・重複・日付不整合）
  - 日次 ETL の統合エントリポイント（run_daily_etl）
- カレンダー管理（営業日判定 / next/prev / 範囲取得 / 夜間カレンダー更新ジョブ）
- 監査ログ（signal_events / order_requests / executions）の初期化ユーティリティ
- データ品質チェックモジュール（QualityIssue を返す方式）

---

## 前提・依存関係

- Python 3.10+
- 必要パッケージ（最低限）
  - duckdb
  - defusedxml

（プロジェクトに合わせて追加で logging や Slack 用ライブラリ等を利用する場合があります）

例: pip によるインストール
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# またはプロジェクト化されていれば: pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成して依存をインストールします。
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   ```

2. 環境変数を用意します（.env をプロジェクトルートに置けます）。
   - 自動ロード: パッケージの config モジュールはプロジェクトルート（.git または pyproject.toml）を探索し `.env` / `.env.local` を自動で読み込みます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

3. 主要な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN — Slack 通知に使うボットトークン（必須）
   - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
   - 任意 / デフォルト:
     - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - KABUSYS_ENV: development | paper_trading | live（default: development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（default: INFO）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマを初期化します（data/schema.py のユーティリティを利用）。
   Python REPL かスクリプトで:
   ```
   python - <<'PY'
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")
   print("DuckDB schema initialized.")
   PY
   ```

5. 監査ログ用 DB を初期化する（必要に応じて独立 DB を使用）。
   ```
   python - <<'PY'
   from kabusys.data.audit import init_audit_db
   init_audit_db("data/audit.duckdb")
   print("Audit DB initialized.")
   PY
   ```

---

## 使い方（主要ワークフロー例）

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
  ```
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")  # 既に初期化済みなら get_connection でも可
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

  - 引数で target_date / id_token / run_quality_checks / backfill_days 等を制御可能です。

- ニュース収集ジョブの実行
  ```
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 必要に応じて銘柄コードセットを用意
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- J-Quants の ID トークン取得（テスト用など）
  ```
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用して自動で取得
  print(token)
  ```

- カレンダー更新ジョブ（夜間バッチ想定）
  ```
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- 監査スキーマの初期化（既存接続へ追加）
  ```
  from kabusys.data.schema import init_schema
  from kabusys.data.audit import init_audit_schema

  conn = init_schema("data/kabusys.duckdb")
  init_audit_schema(conn)  # transactional=True を必要に応じて指定
  ```

---

## 設計上のポイント / 注意事項

- J-Quants API:
  - レート制御は固定間隔スロットリング（120 req/min）で行います。大量リクエストをかけると遅延が発生します。
  - 408 / 429 / 5xx やネットワークエラー時に指数バックオフで最大 3 回リトライします。
  - 401 受信時は refresh token から id_token を再取得して 1 回だけリトライします。
- ニュース収集:
  - URL 正規化・トラッキング除去により冪等的に記事を識別します。
  - SSRF 対策（スキームチェック、ホストがプライベートかどうかの検証、リダイレクト時の検査）を実装しています。
  - レスポンスサイズに上限を設け、Gzip 解凍後もサイズチェックを行います（Gzip・XML bomb 対策）。
- データベース:
  - DuckDB を利用。スキーマは init_schema() で冪等に作成されます。
  - raw レイヤの保存関数は ON CONFLICT を利用して冪等性を担保します。
- 品質チェック:
  - 欠損（OHLC 欠損はエラー）、主キー重複（エラー）、スパイク（警告）、将来日付や非営業日のデータ（警告/エラー）を検出します。
  - チェックはすべての問題を収集し、呼び出し元で重大度に応じた対応を決定できます。

---

## トラブルシューティング

- .env が読み込まれない
  - config モジュールはプロジェクトルート（.git または pyproject.toml）を基準に .env を読み込みます。テスト実行やパスが異なる場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自前で環境変数を設定してください。
- J-Quants で 401 が返る / トークン取得に失敗する
  - settings.jquants_refresh_token を確認してください。get_id_token は指定されたリフレッシュトークンから id_token を取得します。
- DuckDB のスキーマが作られない
  - init_schema() を実行した接続でエラーが出ていないかログを確認してください。親ディレクトリが存在しない場合は自動で作成します。

---

## ディレクトリ構成（主要ファイル）

README はリポジトリルートに置く想定です。ソースは `src/kabusys` 配下にあります。主要ファイル/モジュールは以下の通りです。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 管理（Settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得 / 保存ユーティリティ）
    - news_collector.py      — RSS ニュース収集・保存ロジック
    - schema.py              — DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py            — ETL パイプライン（run_daily_etl, 個別 ETL）
    - calendar_management.py — カレンダー管理・営業日ロジック・update_job
    - audit.py               — 監査ログ（signal / order / execution）定義と初期化
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py            — 戦略層のプレースホルダ
  - execution/
    - __init__.py            — 発注実行層のプレースホルダ
  - monitoring/
    - __init__.py            — 監視用プレースホルダ

---

## 開発者向けメモ

- 型注釈に Python 3.10 の新しい union 型（|）を使用しています。実行環境は Python 3.10 以上推奨です。
- ユニットテストを行う際は、環境変数の自動ロードを無効化するか（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）、テスト用の .env を用意してください。
- HTTP 周り（news_collector._urlopen 等）はモックしやすい設計（内部関数差し替え）になっています。

---

必要に応じて README の追加項目（CI / デプロイ手順、Slack 連携サンプル、kabuステーション実行例、より詳細な運用手順など）を作成できます。どの部分を詳細化したいか教えてください。