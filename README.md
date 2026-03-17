# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（KabuSys）。J-Quants や RSS 等から市場データ・ニュースを取得し、DuckDB に蓄積、品質チェック、監査ログ、ETL パイプライン、カレンダー管理など自動売買システムに必要な基盤機能を提供します。

以下はこのリポジトリの README.md（日本語）です。

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォーム向けに設計されたライブラリ群です。主な目的は：

- J-Quants API から株価・財務・マーケットカレンダーを安全に取得して保存
- RSS フィードからニュースを収集・前処理して保存し、銘柄との紐付けを支援
- DuckDB ベースのスキーマ・監査ログを提供してトレーサビリティを確保
- ETL（差分取得・バックフィル・品質チェック）パイプラインを提供
- 営業日判定やカレンダー更新ジョブを提供

設計上の特徴：
- API レート制限やリトライ、トークン自動リフレッシュ対応
- SSRF / XML Bomb 等の脅威対策（defusedxml、リダイレクト検査など）
- DuckDB への冪等保存（ON CONFLICT / RETURNING を活用）
- 品質チェックで欠損・スパイク・重複・日付不整合を検出
- 監査ログでシグナル→発注→約定の完全トレースを実現

---

## 機能一覧

- 設定管理
  - 環境変数 / .env 自動読み込み（プロジェクトルート検出）
  - 必須設定のバリデーション
- J-Quants クライアント（kabusys.data.jquants_client）
  - ID トークン取得（refresh token から）
  - 日次株価（OHLCV）取得（ページネーション対応）
  - 財務データ取得（四半期 BS/PL）
  - マーケットカレンダー取得
  - DuckDB への保存（冪等）
  - レートリミット・リトライ・401 時の自動リフレッシュ対応
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得（gzip 対応・サイズ上限）
  - URL 正規化・トラッキングパラメータ除去・記事ID 発行（SHA-256）
  - SSRF 対策（スキーム/ホスト検査、リダイレクト検査）
  - DuckDB への冪等保存・銘柄紐付け
- スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層の DuckDB スキーマ定義
  - init_schema(), get_connection()
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（最終日から backfill を含めた再取得）
  - prices / financials / calendar の個別 ETL
  - run_daily_etl()：一連の ETL と品質チェックを実行
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、next/prev 営業日、期間の営業日リスト
  - calendar_update_job() による夜間更新ジョブ
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等を初期化および管理
  - init_audit_schema(), init_audit_db()
- 品質チェック（kabusys.data.quality）
  - 欠損値、スパイク（前日比閾値）、重複、日付不整合の検出
  - run_all_checks()

---

## セットアップ手順

前提
- Python 3.10 以上（typing の | 演算子などを使用）
- pip が利用可能

1. リポジトリをクローン／チェックアウトしてください。

2. 必要パッケージをインストール（最低限）:

   pip install duckdb defusedxml

   （プロジェクトに requirements ファイルがある場合はそちらを使用してください）

3. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます。
   - 自動ロードが不要な場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須の環境変数（コードから参照される主要なもの）:
   - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注機能などで使用）
   - SLACK_BOT_TOKEN: Slack 通知に使う Bot トークン
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

   任意（デフォルトあり）:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視系で使う SQLite パス（デフォルト data/monitoring.db）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxx...
   KABU_API_PASSWORD=your_kabu_pass
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=./data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. スキーマ初期化
   Python REPL またはスクリプトで DuckDB スキーマを作成します：

   ```python
   from kabusys.config import settings
   from kabusys.data import schema

   conn = schema.init_schema(settings.duckdb_path)  # ファイルパス or ":memory:"
   ```

   監査ログ専用 DB を別途作る場合：
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（主要な API と例）

以下はよく使う API の簡単な使用例です。

- J-Quants トークン取得（内部で settings.jquants_refresh_token を使います）

  ```python
  from kabusys.data.jquants_client import get_id_token
  id_token = get_id_token()  # settings から refresh token を読み取って取得
  ```

- 日次 ETL 実行（run_daily_etl）

  ```python
  from kabusys.config import settings
  from kabusys.data import schema, pipeline

  conn = schema.get_connection(settings.duckdb_path)  # 既存 DB 接続
  result = pipeline.run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- 個別 ETL（株価のみ等）

  ```python
  from datetime import date
  from kabusys.data.pipeline import run_prices_etl

  fetched, saved = run_prices_etl(conn, target_date=date.today())
  ```

- ニュース収集ジョブ

  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  # known_codes は銘柄抽出を行う場合の有効な銘柄コード集合
  known_codes = {"6758", "7203", "9984"}
  stats = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(stats)  # {source_name: 新規保存件数}
  ```

- カレンダー夜間更新ジョブ

  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  ```

- 品質チェックのみ実行

  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

ノート：
- J-Quants の API 呼び出しはモジュール内部でレート制御（120 req/min）とリトライを行います。
- ニュース取得は RSS フィードの XML パースに失敗した場合は空リストを返して続行します。
- ETL は各ステップで失敗しても他ステップを継続する設計です（結果オブジェクトにエラー情報を格納）。

---

## ディレクトリ構成

リポジトリの主要ファイル/ディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                   # 環境変数・設定管理（.env 自動読み込み）
    - data/
      - __init__.py
      - jquants_client.py         # J-Quants API クライアント（取得・保存）
      - news_collector.py         # RSS ニュース収集・保存
      - schema.py                 # DuckDB スキーマ定義・初期化
      - pipeline.py               # ETL パイプライン（差分取得、品質チェック）
      - calendar_management.py    # マーケットカレンダー管理・営業日判定
      - audit.py                  # 監査ログ（signal/order/execution）
      - quality.py                # データ品質チェック
    - strategy/                    # 戦略関連（空のパッケージ：拡張用）
      - __init__.py
    - execution/                   # 実行（発注）関連（空のパッケージ：拡張用）
      - __init__.py
    - monitoring/                  # 監視関連（空のパッケージ：拡張用）

この README で示した API は主要なエントリポイントの一部です。各モジュール内の docstring に詳しい挙動や引数の説明がありますので参照してください。

---

## 注意事項 / ベストプラクティス

- 環境変数や API トークンは安全に管理してください。公開リポジトリに直書きしないでください。
- 本ライブラリは本番発注（live）環境とペーパートレード（paper_trading）環境を区別できる設定を用意しています。KABUSYS_ENV を適切に設定してください。
- DuckDB ファイルは定期的にバックアップを取ることを推奨します。
- ニュース収集や外部 URL 取得は SSRF の観点で厳密な検査を行っていますが、プロキシや企業ネットワーク下での挙動は実環境で必ずテストしてください。
- 大量データの取り扱い時はメモリ・I/O に注意し、適宜チャンク処理を行ってください（news_collector はチャンク挿入対応済み）。

---

README の補足・改善要望や、追加したい使用例（例: Slack 通知連携、kabuステーションとの発注サンプル等）があれば教えてください。README を利用目的に合わせてさらに詳しく作り込みます。