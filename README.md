# KabuSys

KabuSys は日本株向けの自動売買プラットフォームのコアライブラリです。  
データ収集（J-Quants / RSS）、ETL パイプライン、データ品質チェック、監査ログ（発注→約定のトレーサビリティ）など、戦略実行に必要な基盤機能を提供します。

主な設計方針:
- API レート制御・リトライ・トークン自動更新対応
- DuckDB を用いた冪等な永続化（ON CONFLICT / RETURNING を活用）
- ニュース収集での SSRF / XML 攻撃対策、サイズ制限
- 品質チェックを行い問題を集約して返す（Fail-Fast ではない）
- 監査ログによりシグナルから約定までを UUID で追跡可能

---

## 機能一覧
- 環境設定管理（.env の自動読み込み・検証、必須環境変数チェック）
  - 自動ロードはプロジェクトルート（.git / pyproject.toml）を起点に行う
  - 自動ロード無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- J-Quants API クライアント
  - 日足（OHLCV）、財務データ、マーケットカレンダー取得
  - レートリミット（120 req/min）、指数バックオフによるリトライ
  - 401 時の自動トークンリフレッシュ（1 回）
  - 取得時刻（fetched_at）を UTC で記録
- ニュース収集（RSS）
  - RSS フィード取得、前処理（URL 除去・空白正規化）
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）で冪等保証
  - SSRF 対策（スキーム検証、プライベートアドレス拒否、リダイレクト検査）
  - レスポンスサイズ上限（デフォルト 10 MB）と Gzip 展開後サイズ検査
  - DuckDB への冪等保存（INSERT ... RETURNING / ON CONFLICT DO NOTHING）
  - 銘柄コード抽出（4桁数字）と news_symbols 保存
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - 監査ログ（signal_events, order_requests, executions）の分離初期化
- ETL パイプライン
  - 差分更新（DB の最終取得日をもとに backfill を実施）
  - カレンダー先読み（デフォルト 90 日）
  - 品質チェック（欠損、重複、スパイク、日付不整合）
  - 結果は ETLResult オブジェクトで集約（品質問題リスト & エラー）
- データ品質チェック（QualityIssue 構造で問題を返却）
- 監視／実行（骨格モジュール: strategy, execution, monitoring のプレースホルダ）

---

## セットアップ手順

前提:
- Python 3.10 以上（PEP 604 の `X | Y` 型表記を使用）
- pip が利用可能

1. リポジトリをクローンしてインストール（開発モード推奨）
   ```
   git clone <repo-url>
   cd <repo-root>
   pip install -e ".[dev]"  # requirements を setup.cfg/pyproject.toml で用意している想定
   ```
   ※ 実プロジェクトでは `pyproject.toml` / `setup.cfg` に依存パッケージ（例: duckdb, defusedxml）を定義してください。
   必要最小限のライブラリ例:
   ```
   pip install duckdb defusedxml
   ```

2. 環境変数 (.env) を準備
   プロジェクトルートに `.env` または `.env.local` を配置すると、自動的に読み込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

   必須（例）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=xxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   ```
   任意:
   ```
   KABUSYS_ENV=development          # development | paper_trading | live
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb  # デフォルト
   SQLITE_PATH=data/monitoring.db   # 監視用 sqlite（optional）
   KABUSYS_DISABLE_AUTO_ENV_LOAD=   # 自動ロード抑止（テスト用）
   ```

3. DuckDB スキーマ初期化
   Python REPL またはスクリプトから:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")  # ファイルを自動作成
   ```
   監査ログを分離して初期化する場合:
   ```python
   from kabusys.data import audit
   audit.init_audit_schema(conn)  # 既存 conn に監査テーブルを追加
   ```
   または専用 DB:
   ```python
   conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（主要 API の例）

- 設定読み取り
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  db_path = settings.duckdb_path
  ```

- J-Quants: トークン取得 / データ取得
  ```python
  from kabusys.data import jquants_client as jq
  id_token = jq.get_id_token()  # settings.jquants_refresh_token を使って取得
  records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

- DuckDB に保存（冪等）
  ```python
  import duckdb
  from kabusys.data import jquants_client as jq

  conn = duckdb.connect("data/kabusys.duckdb")
  saved = jq.save_daily_quotes(conn, records)
  ```

- ニュース収集（RSS）と保存
  ```python
  from kabusys.data import news_collector as nc
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")  # スキーマ初期化済みを想定

  articles = nc.fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  new_ids = nc.save_raw_news(conn, articles)

  # 銘柄紐付け（既存の known_codes を渡す）
  known_codes = {"7203", "6758", "9984"}
  for nid in new_ids:
      # extract_stock_codes を使ってコードを取り、save_news_symbols を呼ぶ等
      pass
  ```

- ETL の日次実行（全体）
  ```python
  from datetime import date
  from kabusys.data import schema, pipeline

  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())  # ETL の結果概要（品質問題・エラーを含む）
  ```

- 品質チェック単体実行
  ```python
  from kabusys.data import quality
  issues = quality.run_all_checks(conn, target_date=None)
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

注意点（運用上のポイント）:
- J-Quants のレート制限（120 req/min）をライブラリが内部で制御しますが、バッチ運用時はAPI使用量に注意してください。
- ETL は差分更新を行います。初回ロードはかなりの量になる可能性があるため、_MIN_DATA_DATE（デフォルト 2017-01-01）を適宜設定してください。
- 自動 .env 読み込みはプロジェクトルートを基準に行います。CI/テストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定して明示的に環境を注入することを推奨します。

---

## ディレクトリ構成

主要なファイル/モジュール構成（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py      # RSS ニュース収集・保存・銘柄抽出
    - schema.py              # DuckDB スキーマ定義と初期化
    - pipeline.py            # ETL パイプライン（差分取得・保存・品質チェック）
    - audit.py               # 監査ログ（signal/order/execution）定義と初期化
    - quality.py             # データ品質チェック
  - strategy/
    - __init__.py            # 戦略モジュールのプレースホルダ（拡張ポイント）
  - execution/
    - __init__.py            # 発注・約定処理のプレースホルダ（ブローカー接続等）
  - monitoring/
    - __init__.py            # 監視・メトリクス収集（プレースホルダ）

---

## 追加メモ / 運用ガイド
- ログレベルは環境変数 `LOG_LEVEL` で制御（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- 実運用（ライブ注文）とペーパートレードは `KABUSYS_ENV` で切り分け（development / paper_trading / live）。
- DuckDB を単一ファイルで運用する場合はバックアップと排他制御（複数プロセス同時書き込み）に注意してください。
- ニュース収集の既知銘柄（known_codes）は別途銘柄マスタを用意して渡すことを推奨します。

---

この README はコードベースの主要な利用方法と設計意図をまとめたものです。詳細な API ドキュメント（引数の挙動、戻り値の型など）は各モジュールの docstring を参照してください。追加で「導入手順をスクリプト化する」「CI 用の初期化手順」を追記したい場合は仕様に合わせてサンプルを作成します。必要であれば教えてください。