# KabuSys

日本株自動売買プラットフォーム向けのユーティリティ群（データ収集・ETL・スキーマ・監査ログ等）を提供する Python パッケージです。

> このリポジトリは「J-Quants API」や RSS フィードを介したデータ収集、DuckDB を用いたローカルデータベース管理、データ品質チェック、監査ログ（発注〜約定のトレーサビリティ）を主な目的としています。

---

目次
- プロジェクト概要
- 主な機能
- 必須環境変数 / 設定
- セットアップ手順
- 使い方（コード例）
- ディレクトリ構成
- 開発・運用上の注意点

---

## プロジェクト概要

KabuSys は日本株向け自動売買システムのデータ基盤部分を支えるライブラリ群です。  
主に次を目的としています。

- J-Quants API から株価（OHLCV）、四半期財務、JPX カレンダーを取得
- RSS からニュース記事を収集して DuckDB に保存（記事と銘柄の紐付け）
- DuckDB 上でスキーマの初期化（Raw / Processed / Feature / Execution / Audit レイヤ）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定、前後営業日の取得）
- 監査ログ（signal → order_request → execution をトレース）

設計上のポイントとして、API レート制御、堅牢なリトライロジック、冪等性確保（ON CONFLICT）、SSRF 対策、XML 脆弱性対策（defusedxml）などに配慮しています。

---

## 主な機能

- data.jquants_client
  - J-Quants API 用クライアント（レートリミット制御・リトライ・トークン自動リフレッシュ）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への保存（save_daily_quotes / save_financial_statements / save_market_calendar）

- data.news_collector
  - RSS フィード取得・前処理（URL除去・空白正規化）
  - 記事IDを正規化URLの SHA-256（先頭32文字）で生成して冪等保存
  - SSRF 対策、gzip／サイズ制限、defusedxml による XML セキュリティ対策
  - save_raw_news / save_news_symbols / run_news_collection

- data.schema / data.audit
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema(db_path) / init_audit_db(db_path) による初期化

- data.pipeline
  - 日次 ETL 実行（run_daily_etl）
  - 差分更新（最終取得日計算、バックフィルの考慮）
  - 品質チェック（data.quality 連携）

- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job によるカレンダー差分更新

- data.quality
  - 欠損検出 / 重複検出 / スパイク検出 / 日付不整合検出
  - QualityIssue 型で問題を列挙し、ETL に情報を返却

---

## 必須環境変数 / 設定

KabuSys は .env（および .env.local）またはシステム環境変数から設定を読み込みます。自動読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を基に行われます。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数:

- JQUANTS_REFRESH_TOKEN（必須）
  - J-Quants のリフレッシュトークン。get_id_token により ID トークンを取得します。

- KABU_API_PASSWORD（必須）
  - kabuステーション API 用のパスワード（実行/発注モジュールで利用）。

- KABU_API_BASE_URL（任意、デフォルト: http://localhost:18080/kabusapi）
  - kabuステーション API のベース URL。

- SLACK_BOT_TOKEN（必須）
  - Slack 通知用ボットトークン。

- SLACK_CHANNEL_ID（必須）
  - Slack チャンネル ID。

- DUCKDB_PATH（任意、デフォルト: data/kabusys.duckdb）
  - DuckDB の DB ファイルパス。":memory:" も使用可能。

- SQLITE_PATH（任意、デフォルト: data/monitoring.db）
  - 監視系で使用する SQLite パス（プロジェクト固有の用途）。

- KABUSYS_ENV（任意、デフォルト: development）
  - 有効値: development / paper_trading / live

- LOG_LEVEL（任意、デフォルト: INFO）
  - 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL

注意: .env.local は .env を上書きします（優先度: OS 環境変数 > .env.local > .env）。OS 環境変数は保護され上書きされません。

---

## セットアップ手順

前提: Python 3.10 以上を推奨（型ヒントに | 演算子を使用）。

1. リポジトリをクローンして作業ディレクトリに移動

   git clone <repo-url>
   cd <repo>

2. 仮想環境を作成・有効化（任意）

   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 依存ライブラリをインストール

   pip install duckdb defusedxml

   （将来的には requirements.txt / pyproject.toml を用意している前提です。開発用に追加パッケージがある場合はそれらもインストールしてください。）

4. 環境変数を設定

   プロジェクトルートに .env を作成するか、OS 環境変数に設定してください。

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化

   Python から初期化します（親ディレクトリが無ければ自動で作成されます）:

   python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

   監査ログ専用 DB を別に用意する場合:

   python -c "from kabusys.data.audit import init_audit_db; init_audit_db('data/kabusys_audit.duckdb')"

---

## 使い方（コード例）

以下は主要なユーティリティの簡単な利用例です。実行前に .env 等で必要な環境変数を設定してください。

- DuckDB の初期化と日次 ETL 実行

  python - <<'PY'
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  conn = init_schema('data/kabusys.duckdb')
  result = run_daily_etl(conn)  # デフォルトは本日をターゲットに実行
  print(result.to_dict())
  PY

- ニュース収集ジョブ実行（RSS → raw_news 保存、既存記事はスキップ）

  python - <<'PY'
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  conn = init_schema('data/kabusys.duckdb')
  # known_codes を与えると記事本文から銘柄コードを抽出して news_symbols に紐付ける
  known_codes = {'7203', '6758'}  # 実運用では銘柄マスター等から生成
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  PY

- J-Quants から株価取得（プログラム内で id_token を明示的に渡す例）

  python - <<'PY'
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()  # settings.jquants_refresh_token から取得
  records = fetch_daily_quotes(id_token=token, date_from=None, date_to=None)  # パラメータで絞る
  print(len(records))
  PY

- 監査スキーマの追加（既存の DuckDB 接続に監査テーブルを追加）

  python - <<'PY'
  from kabusys.data.schema import init_schema
  from kabusys.data.audit import init_audit_schema
  conn = init_schema('data/kabusys.duckdb')
  init_audit_schema(conn, transactional=True)
  PY

---

## ディレクトリ構成

（リポジトリ内の主要ファイル構成）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数/設定管理（Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（rate limit / retry / save_*）
    - news_collector.py              — RSS ニュース収集・前処理・DB 保存
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - schema.py                      — DuckDB スキーマ定義 & init_schema
    - calendar_management.py         — カレンダー管理（営業日判定・calendar_update_job）
    - audit.py                       — 監査ログ（signal / order_request / executions）
    - quality.py                     — データ品質チェック
  - strategy/
    - __init__.py                    — 戦略関連（拡張ポイント）
  - execution/
    - __init__.py                    — 発注/約定関連（拡張ポイント）
  - monitoring/
    - __init__.py                    — 監視／メトリクス（拡張ポイント）

注: strategy / execution / monitoring は拡張領域として準備されています（実装はこのコードベースのスニペットに依存）。

---

## 開発・運用上の注意点

- Python バージョン: 型ヒントで Python 3.10 の構文を利用しているため、3.10 以上を推奨します。
- 依存: duckdb（データ保存）、defusedxml（安全な XML パーサ）、標準 urllib を使用。
- 環境変数の自動ロード:
  - .env と .env.local をプロジェクトルートから自動読み込みします。
  - テスト等で自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API:
  - レート制限（120 req/min）を守るために固定間隔レートリミッタが実装されています。
  - ネットワークエラー・一部ステータスコードに対して指数バックオフでリトライします。
  - 401 を受けた場合はリフレッシュトークンから ID トークンを再取得して 1 回リトライする仕組みがあります。
- セキュリティ:
  - RSS 取得時に SSRF 対策（リダイレクト先の検査、プライベートアドレスの拒否）、Content-Length と読み取り上限、gzip の解凍サイズ検査を実装しています。
  - XML パースは defusedxml を使用し XML Bomb 等への耐性を高めています。
- 冪等性:
  - 多くの保存関数は ON CONFLICT（DuckDB のサポートの範囲で）による上書き/スキップを行い、再実行可能に設計されています。
- 品質チェック:
  - ETL の最後に品質チェック（欠損・重複・スパイク・日付不整合）を実行し、問題は QualityIssue リストとして返却されます。重大度に応じた運用アクションは上位（運用）で判断してください。

---

必要に応じて README を更新します。追加したいサンプルや運用手順（cron / Airflow / systemd での運用例、Slack 通知フロー等）があれば教えてください。