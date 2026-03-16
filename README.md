# KabuSys — 日本株自動売買基盤（README）

KabuSys は日本株のデータ取得・ETL、品質チェック、監査ログ、発注管理の基盤となる Python モジュール群です。本リポジトリはデータ層（DuckDB ベース）のスキーマ定義・初期化、J-Quants API クライアント、日次 ETL パイプライン、データ品質チェック、監査ログスキーマ等を提供します。

主な設計方針：
- データ取得は冪等（ON CONFLICT DO UPDATE）で安全に保存
- API レート制限・リトライ・トークン自動リフレッシュ対応
- Look-ahead bias を防ぐため取得時刻（UTC）を保存
- 品質チェックは全件収集型で、呼び出し元が重大度に応じて対応可能

---

## 機能一覧
- 環境設定読み込み（.env / 環境変数）
  - 自動ロードの挙動: OS 環境 > .env.local > .env（プロジェクトルート判定あり）
  - 自動ロード停止フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得
  - 120 req/min のレート制御、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - 取得データの fetched_at を UTC で記録
  - DuckDB へ冪等保存する save_* 関数群
- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブル群とインデックス定義
  - init_schema() / get_connection() を提供
- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新（最終取得日に基づく差分取得 + backfill）
  - 市場カレンダーの先読み、株価・財務の差分取得・保存
  - 品質チェック（check_missing_data, check_duplicates, check_spike, check_date_consistency）
  - 日次 ETL のエントリ: run_daily_etl()
- データ品質チェック（src/kabusys/data/quality.py）
  - 欠損、重複、スパイク、日付不整合を検出し QualityIssue を返す
- 監査ログ（src/kabusys/data/audit.py）
  - signal_events / order_requests / executions 等の監査テーブル初期化関数
  - 監査用のインデックスも作成
- 簡易モジュール構成（strategy / execution / monitoring のプレースホルダ）

---

## 要件（推奨）
- Python 3.10+
  - 理由: PEP 604 の union 型（X | Y）等を使用
- 依存パッケージ（最低限）
  - duckdb
- （任意）ロギング設定や Slack 通知などの外部連携ライブラリは別途追加可能

インストール（例）
- 仮想環境を作成してから:
  - pip install -U pip
  - pip install duckdb
  - またはリポジトリをパッケージとして使う場合:
    - pip install -e .

---

## 環境変数（必須 / 任意）
必須（アプリ起動時に必要）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード
- SLACK_BOT_TOKEN: Slack ボットトークン
- SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID

任意 / デフォルトあり
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動読み込みを無効化

.env ファイルの自動読み込みについて:
- プロジェクトルートは .git または pyproject.toml を起点に探索
- .env を読み込み、続けて .env.local を上書きで読み込む（OS 環境変数は保護）
- パースの互換性: export KEY=val, クォート、インラインコメント等に対応

---

## セットアップ手順（ローカル開発想定）
1. リポジトリをクローン
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. 依存ライブラリをインストール
   - pip install duckdb
   - （必要に応じて他ライブラリ）
4. 環境変数設定
   - プロジェクトルートに .env（および .env.local）を作成
   - .env.example があれば参照して必須値を設定
5. DuckDB スキーマ初期化（Python REPL またはスクリプトから）
   例:
   - python -c "from kabusys.data.schema import init_schema, get_connection; init_schema('data/kabusys.duckdb')"
   - または
     from kabusys.data.schema import init_schema
     conn = init_schema('data/kabusys.duckdb')
6. 監査ログテーブル初期化（任意）
   - from kabusys.data.audit import init_audit_schema
     conn = init_schema('data/kabusys.duckdb')
     init_audit_schema(conn)

---

## 使い方（主要ユースケース例）

- DuckDB スキーマの初期化
  - Python スクリプト例:
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")

- 日次 ETL を実行してデータを取得・保存する
  - 例: 今日を対象に実行（品質チェックあり）
    from kabusys.data.schema import init_schema
    from kabusys.data.pipeline import run_daily_etl
    conn = init_schema("data/kabusys.duckdb")
    result = run_daily_etl(conn)  # target_date を明示することも可能
    print(result.to_dict())

  - run_daily_etl の主な引数:
    - target_date: ETL の対象日（省略時は today）
    - id_token: J-Quants の id_token を注入（テスト用）
    - run_quality_checks: 品質チェックを実行するか（デフォルト True）
    - backfill_days: 最終取得日の何日前から再取得するか（デフォルト 3）
    - calendar_lookahead_days: カレンダー先読み日数（デフォルト 90）

- 個別 ETL ジョブ
  - run_prices_etl / run_financials_etl / run_calendar_etl を個別に呼べます。
  - これらは (fetched_count, saved_count) を返します。

- 品質チェックを単独実行
  - from kabusys.data.quality import run_all_checks
    issues = run_all_checks(conn, target_date=some_date)
    for i in issues: print(i)

- 監査ログの初期化（別 DB または同一 DB）
  - from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 重要な挙動・注意点
- J-Quants API のレート制御とリトライ:
  - 120 req/min に対応する内部スロットリングあり
  - HTTP 408/429/5xx は指数バックオフで最大 3 回リトライ
  - 401 は自動でリフレッシュを試みて 1 回だけリトライ
- データ保存は冪等性を保証:
  - save_* 関数は ON CONFLICT DO UPDATE を使い重複を排除
- 日次 ETL は「市場カレンダー取得 → 営業日調整 → 株価・財務取得 → 品質チェック」の順で実行
- 品質チェックは Fail-Fast ではなく全件収集し、重大な問題は caller が判断する方式
- DuckDB の接続は init_schema() で初期化してから使用することを推奨

---

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py  — 環境変数・設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
    - schema.py        — DuckDB スキーマ定義・初期化
    - pipeline.py      — ETL パイプライン（差分更新・品質チェック）
    - quality.py       — データ品質チェック
    - audit.py         — 監査ログ（signal/order/execution）スキーマ
    - pipeline.py, audit.py, quality.py 等はそれぞれの責務を分離
  - strategy/
    - __init__.py  — 戦略層（拡張・プラグイン用）
  - execution/
    - __init__.py  — 発注実行層（証券会社連携の実装を想定）
  - monitoring/
    - __init__.py  — 監視・メトリクス用（拡張用）

---

## 開発・拡張のヒント
- strategy / execution / monitoring モジュールはプレースホルダになっているため、
  実際の戦略ロジックやブローカー接続はここに実装してください。
- 単体テストでは settings の自動 .env ロードを無効化するために
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定できます。
- run_daily_etl は id_token を受け取れるため、テスト用モックトークンを注入して API 呼び出しを制御できます。

---

フィードバックや機能追加、ドキュメントの改善提案があればお知らせください。