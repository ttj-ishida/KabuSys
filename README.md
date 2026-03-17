# KabuSys — 日本株自動売買プラットフォーム（README）

KabuSys は日本株向けの自動売買プラットフォーム用ライブラリ群です。J-Quants API からの市場データ取得、RSS ニュース収集、DuckDB ベースのデータスキーマ／ETL、品質チェック、マーケットカレンダー管理、監査ログ（発注→約定のトレーサビリティ）などを提供します。本リポジトリは「データ取得・保存・品質管理」〜「戦略・発注」までの基盤機能を実装することを目的としています。

主な特徴と設計方針：
- J-Quants API のレート制御（120 req/min）・再試行・トークン自動リフレッシュ
- DuckDB を用いた3層データレイヤ（Raw / Processed / Feature）と実行層
- ETL は差分更新・バックフィル対応・品質チェックを実施
- ニュース収集は SSRF/XML Bomb 対策・トラッキングパラメータ除去・冪等保存
- 監査ログでシグナル→発注→約定の追跡を保証

---

## 機能一覧

- 環境設定:
  - .env 自動読み込み（プロジェクトルートを探索）
  - 必須環境変数を Settings クラスで提供

- データ取得（kabusys.data.jquants_client）:
  - ID トークン取得・自動リフレッシュ
  - 日足（OHLCV）・財務（四半期）・JPX カレンダーのページネーション取得
  - レート制御、リトライ（指数バックオフ）、取得時刻（fetched_at）の記録
  - DuckDB への冪等保存（ON CONFLICT を利用）

- ニュース収集（kabusys.data.news_collector）:
  - RSS からの記事取得・前処理（URL除去・空白正規化）
  - URL 正規化（utm 等除去）→ SHA-256 ハッシュから記事ID生成（冪等）
  - SSRF 対策（スキームチェック、プライベートアドレスブロック、リダイレクト検査）
  - gzip サイズ制限、XML パースの安全化（defusedxml）
  - DuckDB へのバルク保存（INSERT ... RETURNING）

- スキーマ管理（kabusys.data.schema）:
  - Raw / Processed / Feature / Execution / Audit 向けテーブル DDL
  - init_schema(db_path) で初期化（冪等）
  - インデックス作成

- ETL パイプライン（kabusys.data.pipeline）:
  - 差分取得（最終取得日からの差分）、バックフィル、品質チェック
  - run_daily_etl を起点にカレンダー→株価→財務→品質チェックを実行

- カレンダー管理（kabusys.data.calendar_management）:
  - market_calendar の更新バッチ
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等

- データ品質（kabusys.data.quality）:
  - 欠損データ、スパイク（前日比閾値）、重複、日付整合性チェック
  - QualityIssue オブジェクトを返す。run_all_checks でまとめて実行可能

- 監査ログ（kabusys.data.audit）:
  - signal_events / order_requests / executions など監査用テーブル群
  - init_audit_db / init_audit_schema で監査テーブルを初期化

- 戦略／発注／監視層のプレースホルダ:
  - kabusys.strategy, kabusys.execution, kabusys.monitoring のパッケージプレースホルダあり

---

## セットアップ手順

前提:
- Python 3.10 以上（型注釈で `Path | None` 等を使用）
- pip が利用可能

1. リポジトリをチェックアウト／クローン

2. 依存パッケージをインストール
   - 本コードでは標準ライブラリの urllib を使用しますが、以下の追加パッケージが必要です。
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （将来的に requirements.txt / pyproject.toml がある場合はそちらを利用してください）

3. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。必要な環境変数:

     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN: Slack Bot トークン（必須）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
     - DUCKDB_PATH: DuckDB ファイルパス（任意、デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: SQLite モニタリング DB（任意、デフォルト data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live（任意、デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（任意、デフォルト INFO）

   - サンプル .env（作成例）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. データベース初期化
   - DuckDB スキーマを初期化する例（Python）:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     ```

   - 監査ログ DB 初期化（監査専用 DB を分ける場合）:
     ```python
     from kabusys.data import audit
     audit_conn = audit.init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（主要 API と実行例）

以下は最小限の利用例です。システム内の関数はテストやスクリプトから直接呼び出して利用します。

1. Settings（環境設定）利用例:
   ```python
   from kabusys.config import settings
   print(settings.jquants_refresh_token)
   print(settings.duckdb_path)  # Path オブジェクト
   ```

2. DuckDB スキーマ初期化（再掲）:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema(settings.duckdb_path)
   ```

3. J-Quants データ取得（手動）:
   ```python
   from kabusys.data import jquants_client as jq
   id_token = jq.get_id_token()  # settings に基づき自動で取得
   daily = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
   jq.save_daily_quotes(conn, daily)
   ```

   - ポイント:
     - fetch_* はページネーション対応
     - save_* は DuckDB へ冪等保存（ON CONFLICT DO UPDATE）

4. 日次 ETL 実行:
   ```python
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)  # target_date を省略すると今日が対象
   print(result.to_dict())
   ```

   - オプションで id_token、backfill_days、run_quality_checks を指定可能。

5. ニュース収集:
   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import get_connection
   conn = get_connection("data/kabusys.duckdb")

   # 既知の銘柄コードセットを DB から生成する例
   rows = conn.execute("SELECT DISTINCT code FROM raw_prices").fetchall()
   known_codes = {r[0] for r in rows}

   results = run_news_collection(conn, sources=None, known_codes=known_codes)
   print(results)  # source 名ごとの新規保存数
   ```

6. 品質チェック（単体）:
   ```python
   from kabusys.data.quality import run_all_checks
   issues = run_all_checks(conn)
   for issue in issues:
       print(issue)
   ```

7. カレンダー操作例:
   ```python
   from kabusys.data.calendar_management import is_trading_day, next_trading_day
   from datetime import date
   print(is_trading_day(conn, date(2024,1,1)))
   print(next_trading_day(conn, date.today()))
   ```

8. 監査スキーマの初期化:
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn, transactional=False)
   ```

---

## 設計上の注意点 / 運用上のヒント

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を起点）を探索して行います。テストや一時的に無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API のレート制限に留意（120 req/min）。jquants_client は固定間隔スロットリングと再試行を実装していますが、大量取得を行うバッチ運用では並列化に注意してください。
- DuckDB ファイルのバックアップを定期的に行ってください（ファイルベースDBのため障害対策が必要）。
- news_collector は外部ネットワークからデータを取得するため、SSRF／XML 関連の防御を組み込んでいます。テストでは _urlopen をモックして外部エンドポイントにアクセスしないようにできます。
- Audit（監査）スキーマには UTC タイムゾーン固定を行います（init_audit_schema 実行時に SET TimeZone='UTC'）。

---

## ディレクトリ構成

リポジトリの主要なファイル／モジュール:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み・Settings クラス定義
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ロジック、レート制御、リトライ）
    - news_collector.py
      - RSS 収集、前処理、SSRF/サイズ制限、DuckDB保存
    - schema.py
      - DuckDB スキーマ DDL と init_schema/get_connection
    - pipeline.py
      - ETL（差分更新・バックフィル・品質チェック）
    - calendar_management.py
      - 市場カレンダーの更新／営業日判定ユーティリティ
    - audit.py
      - 監査ログテーブル DDL（signal_events, order_requests, executions）と初期化
    - quality.py
      - データ品質チェック群（欠損・重複・スパイク・日付不整合）
  - strategy/
    - __init__.py （戦略層のプレースホルダ）
  - execution/
    - __init__.py （発注・ブローカー連携のプレースホルダ）
  - monitoring/
    - __init__.py （監視／アラート関連プレースホルダ）

---

## 今後の拡張案 / TODO（参考）

- strategy / execution モジュールの具象実装（ポートフォリオ構築、注文送信ラッパー）
- Slack 通知や監視ダッシュボードの実装（monitoring）
- pyproject.toml / requirements.txt の整備と CI ワークフロー
- 単体テスト、統合テスト用のテストデータとモック化ユーティリティ
- 大規模データ処理時のパフォーマンス改善（チャンク処理の最適化等）

---

本 README はコードベース（src/kabusys 以下）に基づいて作成しています。追加で使用例や API ドキュメントを生成したい場合は、どの機能を詳細化したいかを教えてください。