# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）の README。  
本リポジトリはデータ収集・ETL・スキーマ管理・品質チェック・監査ログ基盤などの基礎機能を提供します。

主な設計方針のポイント:
- J-Quants API を利用した株価・財務・マーケットカレンダー取得（レート制限/リトライ/トークン自動リフレッシュ対応）
- DuckDB を用いた三層（Raw / Processed / Feature）スキーマの定義と冪等保存
- RSS ベースのニュース収集（SSRF対策・サイズ制限・トラッキングパラメータ除去）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注〜約定フローの監査ログスキーマ（トレース性重視）
- 設定は環境変数または .env ファイルから読み込み（自動ロード機能あり）

---

## 機能一覧

- 環境変数/設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定の取得（未設定時はエラー）
- J-Quants クライアント（kabusys.data.jquants_client）
  - 日次株価（OHLCV）、財務データ、マーケットカレンダーの取得
  - API レート制御（120 req/min）、リトライ、401 の自動トークンリフレッシュ
  - DuckDB への冪等保存（ON CONFLICT 対応）
- ニュース収集（kabusys.data.news_collector）
  - RSS から記事取得、前処理、記事ID生成（正規化URL→SHA-256）および DuckDB 保存
  - SSRF / XML Bomb / レスポンスサイズ制限などの堅牢性対策
  - 銘柄コード抽出と news_symbols への紐付け
- スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - インデックス作成、init_schema() / get_connection()
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日を確認して新しいデータのみ取得）
  - 日次 ETL 実行（market calendar → prices → financials → 品質チェック）
  - 各ステップは独立してエラーハンドリング（1ステップの失敗で全体停止させない）
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定 / 次営業日/前営業日取得 / カレンダー夜間更新ジョブ
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions など監査用テーブル初期化
  - UTC タイムゾーン固定、冪等キーによる二重発注防止
- 品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合を検出して QualityIssue を返却

（strategy、execution、monitoring モジュールはパッケージの骨組みとして存在します）

---

## セットアップ手順

前提
- Python 3.10 以上（typing における "|" 演算子などを使用）
- DuckDB を使用するのでネイティブ依存が必要ないが pip パッケージをインストールしてください

1. 仮想環境作成と有効化（例）
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

2. 必要な Python パッケージをインストール
   - 最低限:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （プロジェクトに requirements.txt がある場合はそれを利用してください）

3. 開発モードでインストール（任意）
   - pip install -e .

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に `.env` / `.env.local` が自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数（kabusys.config.Settings による）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD     : kabuステーション API パスワード
     - SLACK_BOT_TOKEN       : Slack Bot トークン（通知等に使用）
     - SLACK_CHANNEL_ID      : Slack チャンネル ID
   - 任意 / デフォルト:
     - KABUSYS_ENV （development / paper_trading / live、デフォルト: development）
     - LOG_LEVEL （DEBUG/INFO/...、デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD （1 を設定すると自動 .env ロードをスキップ）
     - DUCKDB_PATH （デフォルト data/kabusys.duckdb）
     - SQLITE_PATH （デフォルト data/monitoring.db）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡単な例）

以下は基本的な操作例です。実行前に .env を準備してください。

- DuckDB スキーマ初期化
  - Python REPL やスクリプトから:
    ```python
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")
    # conn は duckdb connection オブジェクト
    ```

- 監査ログ用 DB 初期化（分離して管理したい場合）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

- 日次 ETL 実行（run_daily_etl を使用）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

  - run_daily_etl は市場カレンダー取得 → 株価取得 → 財務取得 → 品質チェック の順で処理します。
  - 結果は ETLResult（to_dict で明示的な出力）で返ります。

- ニュース収集ジョブ実行
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9432"}  # 例: 有効な銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: 新規保存件数}
  ```

- カレンダー夜間更新ジョブ（calendar_update_job）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- 個別 ETL（価格のみ等）
  ```python
  from kabusys.data.pipeline import run_prices_etl
  from datetime import date
  conn = init_schema("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  ```

- 品質チェックを個別に実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

注意点:
- 環境変数が未設定のままだと Settings のプロパティで ValueError が発生します。
- J-Quants API のレートやエラーに対して内部で待機/リトライを行いますが、大量取得時は注意してください。
- DuckDB の接続はスレッドセーフではないため並列処理時は接続管理に注意してください。

---

## 代表的 API（概要）

- kabusys.config
  - settings: 環境変数から設定値を取得する Settings インスタンス
  - 自動 .env 読み込み機能（プロジェクトルート検出）

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - save_news_symbols(conn, news_id, codes)
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30)

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_prices_etl(conn, target_date, ...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
  - run_daily_etl(...)

- kabusys.data.calendar_management
  - is_trading_day(conn, d)
  - next_trading_day(conn, d)
  - prev_trading_day(conn, d)
  - get_trading_days(conn, start, end)
  - calendar_update_job(conn, lookahead_days=90)

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)
  - 各種個別チェック (check_missing_data / check_spike / check_duplicates / check_date_consistency)

---

## ディレクトリ構成

リポジトリの主要なファイル/ディレクトリ（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数／設定管理
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント + DuckDB 保存
    - news_collector.py             — RSS ニュース収集・保存・銘柄抽出
    - schema.py                     — DuckDB スキーマ定義と初期化
    - pipeline.py                   — ETL パイプライン（差分更新 / run_daily_etl）
    - calendar_management.py        — マーケットカレンダー管理 / 営業日判定
    - audit.py                      — 監査ログ（シグナル→注文→約定のトレース用）
    - quality.py                    — データ品質チェック
  - strategy/
    - __init__.py                   — 戦略パッケージ（拡張ポイント）
  - execution/
    - __init__.py                   — 発注/ブローカ連携パッケージ（拡張ポイント）
  - monitoring/
    - __init__.py                   — 監視・メトリクス用（将来的な拡張）

---

## トラブルシューティング

- .env が読み込まれない
  - プロジェクトルート（.git or pyproject.toml）から .env を探します。実行場所（CWD）に依存しない設計です。
  - 自動読み込みを無効にした場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が設定されています。テスト環境等で無効化されていないか確認してください。

- 環境変数未設定エラー
  - settings.jquants_refresh_token 等の必須プロパティを参照すると未設定時に ValueError を送出します。.env.example を参考に .env を作成してください。

- API レートや 429 エラー
  - jquants_client は 120 req/min の制限を守るためスロットリングします。429 返却時は Retry-After を優先して待機します。

- DuckDB 関連
  - デフォルトのパスは data/kabusys.duckdb です。パスの親ディレクトリが存在しない場合、init_schema が自動作成します。

---

## 今後の拡張ポイント

- strategy/ 以下に実戦的なトレード戦略を実装し signals を生成
- execution/ に証券会社 API（kabu/stub 等）との連携実装
- monitoring/ に Prometheus / メトリクス・アラート統合
- Slack 通知やジョブスケジューラ (cron / Airflow) 統合

---

この README はコードの現状（モジュール、関数の意図）を元に作成しています。実行環境や外部依存（J-Quants / kabu API）の利用には各サービスの利用規約・認証情報の管理に注意してください。