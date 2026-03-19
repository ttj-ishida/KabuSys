# KabuSys — 日本株自動売買基盤（README）

概要
----
KabuSys は日本株向けのデータ基盤・研究・戦略実装・発注監査までを想定した小規模な自動売買ライブラリ群です。本リポジトリにはデータ取得（J-Quants）、DuckDB スキーマ、ETL パイプライン、ニュース収集、ファクター計算・ファクター探索、監査ログ用スキーマなどが含まれます。モジュールは「本番口座への発注を行わない研究用途」でも使える設計方針（Look-ahead 防止、冪等処理、明示的な環境切替など）で実装されています。

主な設計方針・特徴
- DuckDB を中心とした軽量なローカル DB を利用（init_schema で初期化）
- J-Quants API クライアント（ページネーション・レート制御・自動トークンリフレッシュ・リトライ）
- RSS ベースのニュース収集（SSRF / XML 注入対策、トラッキングパラメータ除去、銘柄抽出）
- ETL：差分取得・バックフィル・品質チェック（欠損/重複/スパイク/日付不整合）
- 研究モジュール：ファクター計算（モメンタム/バリュー/ボラティリティ）、IC計算、前方リターン計算
- 監査ログスキーマ：シグナル→発注要求→約定のトレースをUUIDチェーンで保持

機能一覧
--------
- data/jquants_client.py
  - J-Quants API から株価日足・財務・マーケットカレンダーを取得
  - レート制御（120 req/min）、リトライ、401 自動リフレッシュ、ページネーション対応
  - DuckDB への冪等保存（save_* 関数）
- data/schema.py
  - DuckDB のテーブル定義（Raw / Processed / Feature / Execution 層）
  - init_schema()/get_connection()
- data/pipeline.py
  - 日次 ETL（run_daily_etl）：カレンダー → 株価 → 財務 → 品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl
- data/news_collector.py
  - RSS 取得・前処理・raw_news 保存・銘柄抽出・news_symbols 紐付け
  - SSRF / gzip/size-limit 対策
- data/quality.py
  - 欠損・重複・スパイク・日付不整合検出（QualityIssue を返す）
- data/calendar_management.py
  - market_calendar 管理、営業日判定・前後営業日の取得
- data/audit.py
  - 監査ログ用テーブル（signal_events / order_requests / executions 等）
  - init_audit_schema / init_audit_db
- research/factor_research.py, research/feature_exploration.py
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 前方リターン計算、IC（Spearman）計算、統計サマリー
- data/stats.py
  - zscore_normalize（クロスセクション Z スコア正規化）

前提・依存
-----------
主な実行環境・外部依存ライブラリ（抜粋）
- Python 3.10+ 推奨（型アノテーションに union 型等を利用）
- duckdb
- defusedxml
- 標準ライブラリ（urllib, datetime, logging など）

セットアップ手順
----------------
1. Python と pip の準備（3.10 以上推奨）
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\activate     (Windows)
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージ化されている場合）pip install -e .
4. 環境変数を設定（.env をプロジェクトルートに置くと自動ロードされます）
   - 必須（運用に必要な変数）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN: Slack 通知用ボットトークン（監視等に使用する場合）
     - SLACK_CHANNEL_ID: Slack チャンネル ID
     - KABU_API_PASSWORD: kabu API 連携用パスワード（発注を行う場合）
   - 任意
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/...（デフォルト INFO）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env 自動読み込みを無効化（テスト用）
   - 例 (.env)
     - JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - KABU_API_PASSWORD=your_password
     - DUCKDB_PATH=data/kabusys.duckdb
5. DuckDB スキーマ初期化
   - Python REPL / スクリプトで:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - 監査用 DB を別途作る場合:
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")

使い方（簡単な例）
-----------------

- 日次 ETL を実行する（J-Quants からデータを取得して DuckDB に保存、品質チェックを実施）
  - 例スクリプト:
    from kabusys.data.schema import init_schema
    from kabusys.data.pipeline import run_daily_etl
    conn = init_schema("data/kabusys.duckdb")
    result = run_daily_etl(conn)
    print(result.to_dict())

- ニュース収集ジョブを実行する
  - 例:
    from kabusys.data.schema import init_schema
    from kabusys.data.news_collector import run_news_collection
    conn = init_schema("data/kabusys.duckdb")
    known_codes = {"7203", "6758", "9984"}  # 事前に有効銘柄リストを用意
    stats = run_news_collection(conn, known_codes=known_codes)
    print(stats)

- ファクターを計算して Z スコア正規化する（研究用）
  - 例:
    from kabusys.data.schema import get_connection
    from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize
    conn = get_connection("data/kabusys.duckdb")
    target_date = date(2024, 1, 31)
    mom = calc_momentum(conn, target_date)
    vol = calc_volatility(conn, target_date)
    val = calc_value(conn, target_date)
    normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])

- J-Quants トークン取得（内部では自動で行われますが手動取得も可能）
  - 例:
    from kabusys.data.jquants_client import get_id_token
    token = get_id_token()  # settings.jquants_refresh_token を使用

- カレンダー更新ジョブ
    from kabusys.data.calendar_management import calendar_update_job
    conn = init_schema("data/kabusys.duckdb")
    saved = calendar_update_job(conn)

環境変数の自動ロードについて
-----------------------------
- kabusys.config はプロジェクトルート（.git または pyproject.toml を探索）を基準に .env と .env.local を自動読み込みします。
- 読み込み順序: OS 環境変数 > .env.local > .env
- OS 環境変数は保護され、.env によって上書きされません（.env.local は override=True で上書き）。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト向け）。

注意事項・安全性
----------------
- J-Quants の API レート制限（120 req/min）を厳守するため、クライアントは内部でスロットリング・リトライ処理を行います。
- news_collector は SSRF・XML BOM / Gzip bomb 対策を実装していますが、外部フィードの取り扱いには注意してください。
- データの「将来日付」や「非営業日のデータ」は品質チェックで検出されます。ETL 実行後は結果（ETLResult）や quality.run_all_checks の出力を確認してください。
- 本リポジトリは発注機能の一部（schema や audit スキーマ等）を含みますが、実際の証券会社 API 連携・本番発注を行う際は十分なテストと安全バリデーションを行ってください（KABUSYS_ENV を適切に設定して本番と板寄せを区別すること）。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py
  - news_collector.py
  - schema.py
  - stats.py
  - pipeline.py
  - features.py
  - calendar_management.py
  - audit.py
  - etl.py
  - quality.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- strategy/
  - __init__.py
- execution/
  - __init__.py
- monitoring/
  - __init__.py

代表 API（抜粋）
----------------
- kabusys.data.schema.init_schema(db_path)
- kabusys.data.schema.get_connection(db_path)
- kabusys.data.pipeline.run_daily_etl(conn, target_date=None, ...)
- kabusys.data.jquants_client.fetch_daily_quotes(...)
- kabusys.data.jquants_client.save_daily_quotes(conn, records)
- kabusys.data.news_collector.run_news_collection(conn, sources=None, known_codes=None)
- kabusys.data.news_collector.save_raw_news(conn, articles)
- kabusys.data.quality.run_all_checks(conn, target_date=None, reference_date=None)
- kabusys.research.calc_momentum(conn, target_date)
- kabusys.research.calc_volatility(conn, target_date)
- kabusys.research.calc_value(conn, target_date)
- kabusys.data.stats.zscore_normalize(records, columns)
- kabusys.data.audit.init_audit_db(path)

ライセンス・貢献
----------------
本 README ではライセンス欄は省略しています。実際のリポジトリでは LICENSE ファイルを配置してください。貢献する際は issue / pull request を通じて設計方針（安全性・冪等性・Look-ahead 防止）を尊重してください。

最後に
------
この README はコードベースの主要な用途・操作方法をまとめた簡易ドキュメントです。各モジュールは docstring（関数説明）を充実させてあるため、実装の詳細や引数仕様は該当モジュールの docstring を参照してください。追加の使い方や運用手順を README に追記したい場合は、目的（ETL スケジューリング、監視、Slack通知など）を教えてください。詳細な例や運用ガイド（systemd / cron / Airflow など）を作成します。