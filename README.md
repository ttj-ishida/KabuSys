# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。データ取得（J-Quants）、ETLパイプライン、ニュース収集、DuckDBスキーマ、監査ログなどを提供し、戦略・発注・モニタリング層と連携できる基盤モジュール群です。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム開発に必要な基盤機能を集めた Python パッケージです。主に次を提供します。

- J-Quants API 経由の株価・財務・カレンダー取得（レート制限・リトライ・トークン自動更新対応）
- DuckDB を用いたスキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- RSS からのニュース収集と銘柄紐付け（SSRF対策、XML安全化、トラッキング除去、冪等保存）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 環境変数による設定管理（.env 自動ロード機能あり）

設計上のポイント:
- API レート・リトライ・トークン更新を備えた堅牢なデータ取得
- DuckDB への冪等保存（ON CONFLICT / DO UPDATE / DO NOTHING）
- 品質チェックでデータ品質を可視化（欠測・スパイク・重複・日付不整合）
- SSRF / XML Bomb / メモリ DoS 等を考慮した安全なニュース取得

---

## 機能一覧

- データ取得（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）／指数バックオフリトライ／401 時トークン自動リフレッシュ
  - 取得時刻（fetched_at）記録、DuckDB への冪等保存関数

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日を参照）・バックフィル・品質チェックを統合
  - run_daily_etl により市場カレンダー→株価→財務→品質チェックを実行

- DuckDB スキーマ（kabusys.data.schema）
  - Raw / Processed / Feature / Execution レイヤーのテーブル定義
  - インデックス・依存順を考慮した初期化関数 init_schema

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化（utm 等除去）、記事ID（SHA-256先頭32文字）生成
  - defusedxml による安全なパース、SSRF対策（リダイレクト検査・プライベートIP拒否）
  - raw_news への冪等保存、news_symbols への銘柄紐付け

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブル初期化
  - 発注トレーサビリティを確保するための DDL とインデックス

- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク（前日比閾値）、重複、日付不整合の検出
  - QualityIssue による詳細報告（severity: error | warning）

- 設定管理（kabusys.config）
  - .env ファイル（.env.local 上書き）および環境変数から設定を読み込み
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行う
  - 自動ロード無効化環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD

---

## 必要環境・依存パッケージ

推奨 Python バージョン: 3.10+

主な依存:
- duckdb
- defusedxml

（その他、標準ライブラリのみで動作する部分も多いです。実際の利用時は requirements.txt / pyproject.toml を参照してください。）

---

## セットアップ手順

1. リポジトリをクローン / パッケージをチェックアウト

2. 仮想環境を作成して依存をインストール
   - 例:
     python -m venv .venv
     source .venv/bin/activate
     pip install --upgrade pip
     pip install duckdb defusedxml

   - 開発インストール（プロジェクトに pyproject.toml / setup.py がある場合）:
     pip install -e .

3. 環境変数を設定
   必須の環境変数:
   - JQUANTS_REFRESH_TOKEN  (J-Quants のリフレッシュトークン)
   - KABU_API_PASSWORD      (kabuステーション API パスワード)
   - SLACK_BOT_TOKEN        (Slack 通知用 Bot トークン)
   - SLACK_CHANNEL_ID       (通知先チャンネルID)

   任意 / デフォルト値あり:
   - KABUSYS_ENV (development | paper_trading | live) - デフォルト: development
   - KABUSYS_DISABLE_AUTO_ENV_LOAD (1 をセットすると .env 自動ロードを無効化)
   - KABUSYS_BASE_URL 等 (必要に応じて)

   環境変数は .env / .env.local に記述できます（プロジェクトルートの .env が自動読み込みされます）。
   自動ロードの挙動:
   - 先に OS 環境変数が優先され、.env → .env.local（上書き） の順で読み込みます。
   - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. DuckDB スキーマ初期化
   - 例: Python REPL またはスクリプトで以下を実行
     from kabusys.data.schema import init_schema
     from kabusys.config import settings
     conn = init_schema(settings.duckdb_path)

---

## 使い方（主要操作例）

以下は利用例の抜粋です。実行前に環境変数を設定しておいてください。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)  # data/kabusys.duckdb（デフォルト）を作成・初期化
  ```

- 監査ログテーブル初期化（既に init_schema した conn を利用）
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)
  ```

- J-Quants API でデータを直接取得
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements

  quotes = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
  financials = fetch_financial_statements(code="7203")
  ```

- ETL（1日分・日次ETL）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)  # 既存ファイルへ接続（初回は init_schema を先に呼ぶ）
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- ニュース収集ジョブ実行
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection(settings.duckdb_path)
  known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット（抽出用）
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: 新規保存数, ...}
  ```

- 設定参照例
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  print(settings.env, settings.is_live)
  ```

ログ出力・レベルは環境変数 LOG_LEVEL で設定可能（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

---

## ディレクトリ構成

パッケージの主要ファイルと役割は次の通りです（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env 自動読み込み、Settings クラスを公開
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・リトライ・レート制御・保存関数）
    - pipeline.py
      - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
    - news_collector.py
      - RSS 取得・前処理・DB保存・銘柄抽出
    - schema.py
      - DuckDB スキーマ定義 / init_schema / get_connection
    - audit.py
      - 監査ログテーブル定義・初期化
    - quality.py
      - データ品質チェック（Missing / Spike / Duplicates / Date consistency）
  - strategy/
    - __init__.py
    - （戦略ロジックを実装するモジュールを配置予定）
  - execution/
    - __init__.py
    - （発注 / ブローカー連携ロジックを配置予定）
  - monitoring/
    - __init__.py
    - （監視・アラート関連を配置予定）

その他:
- .env/.env.local（プロジェクトルート、存在すれば自動で読み込まれる）
- pyproject.toml / setup.cfg 等（プロジェクト設定）

---

## 注意事項 / 補足

- .env のパースはシェルライク（export プレフィックス、クォート、コメント）に対応していますが、セキュリティ上重要なキーは OS 環境変数でセットすることを推奨します。
- J-Quants API 呼び出しはモジュール内でグローバルにトークンキャッシュを保持します。get_id_token はトークン再取得を行います。
- ニュース収集では外部から提供される RSS に対して SSRF / XML 攻撃対策を多層で実施しています。テスト時は news_collector._urlopen をモックして差し替え可能です。
- DuckDB の初期化は冪等です。既存テーブルがあればスキップされます。
- 品質チェックは Fail-Fast ではなく問題をすべて収集して返します。ETL の継続／停止判断は呼び出し元で実装してください。

---

## 貢献・開発

バグ報告、機能追加や改善の提案は Issue / Pull Request で受付けます。コードスタイル、テスト、CI などはリポジトリルールに従ってください。

---

この README はコードベース（src/kabusys）に基づいて作成しています。詳細な API 仕様や追加の使用例はソースコードの docstring を参照してください。