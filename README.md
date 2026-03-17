KabuSys
=======

日本株向けの自動売買プラットフォーム向けライブラリ（KabuSys）のリポジトリです。  
データ取得・ETL・品質チェック・ニュース収集・DuckDBスキーマ管理・監査ログなど、トレーディング基盤に必要な共通機能を提供します。

主な設計方針
- J-Quants API を用いた市場データ・財務データ・マーケットカレンダーの取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いた3層データレイヤ（Raw / Processed / Feature）および Execution / Audit レイヤのスキーマ定義
- ニュース（RSS）収集で SSRF・XML Bomb・トラッキングパラメータ除去などセキュリティ対策を実装
- ETL は差分更新・バックフィルを行い、品質チェックで欠損・スパイク・重複・日付不整合を検出
- 冪等性を重視（DB 保存は ON CONFLICT で安全に上書き / スキップ）

機能一覧
- 環境設定の読み込み（.env / OS 環境変数、自動ロード / 無効化オプション）
- J-Quants クライアント
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務（四半期 BS/PL）取得（ページネーション対応）
  - JPX マーケットカレンダー取得
  - トークン取得・自動リフレッシュ、レートリミット、リトライ
- DuckDB スキーマ定義・初期化（data.schema）
  - raw / processed / feature / execution 層のテーブル群
  - 監査ログ（audit）テーブルの初期化
- ETL パイプライン（data.pipeline）
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新・バックフィル機能
- ニュース収集（data.news_collector）
  - RSS フィード取得、前処理、記事の冪等保存、銘柄コード抽出と紐付け
  - SSRF 対策・受信サイズ制限・gzip 解凍の安全処理
- データ品質チェック（data.quality）
  - 欠損、スパイク、重複、日付不整合の検出
- マーケットカレンダー管理（data.calendar_management）
  - 営業日判定、next/prev 営業日、期間内の営業日取得、夜間カレンダー更新ジョブ

前提
- Python 3.10 以上（コード内で | を使った型ヒント等を使用）
- 主要依存ライブラリ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード等）

セットアップ手順（ローカル開発向け）
1. リポジトリをクローンし作業ディレクトリへ移動
   - git clone … && cd <repo>

2. 仮想環境の作成（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - pip install --upgrade pip
   - pip install duckdb defusedxml

   （このリポジトリがパッケージ化されている場合は pip install -e . も可）

4. 環境変数設定
   - プロジェクトルートに .env または .env.local を作成すると自動で読み込まれます（優先度: OS 環境 > .env.local > .env）。
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   例 (.env)
   ```
   JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
   KABU_API_PASSWORD=あなたの_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマの初期化
   - Python REPL またはスクリプトから初期化できます。例:
     ```
     from kabusys.data.schema import init_schema
     init_schema("data/kabusys.duckdb")
     ```
   - 監査ログのみ別 DB にしたい場合:
     ```
     from kabusys.data.audit import init_audit_db
     init_audit_db("data/audit.duckdb")
     ```

使い方（主なユースケース例）
- 日次 ETL を実行して DuckDB にデータを取り込む:
  ```
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")  # 存在しなければ作成
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブを走らせる:
  ```
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: 新規保存件数}
  ```

- J-Quants の生データを直接取得する（テストやデバッグ用）:
  ```
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()  # settings から refresh token を参照して取得
  records = fetch_daily_quotes(id_token=token, code="7203", date_from=..., date_to=...)
  ```

- 品質チェックを個別に実行する:
  ```
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

設定（Settings）
- 設定は kabusys.config.settings プロパティ経由で取得します。主な必須環境変数:
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
  - KABU_API_PASSWORD     : kabu API のパスワード（必須）
  - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
  - SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
- 任意/デフォルト:
  - KABUSYS_ENV (development | paper_trading | live) — default: development
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — default: INFO
  - DUCKDB_PATH — default: data/kabusys.duckdb
  - SQLITE_PATH — default: data/monitoring.db
- 自動 .env ロードはパッケージ読み込み時にプロジェクトルート（.git または pyproject.toml を元に探索）から行われます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

重要な注意事項
- J-Quants API のレート制限（120 req/min）を順守するため内部でスロットリングを行っています。大量の取得時は適切に間隔やバッチを調整してください。
- トークンが 401 となった場合は自動でリフレッシュして 1 回再試行します。
- news_collector は RSS の XML パースに defusedxml を使い、SSRF・XML Bomb 対策を行っていますが、外部 URL の取り扱いは十分に注意してください。
- DuckDB の SQL 実行はプレースホルダを利用しますが、外部から受け取った SQL 文字列を直接実行するような拡張を行う場合はインジェクションに注意してください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                      : 環境変数・Settings 管理（.env 自動読み込み等）
  - data/
    - __init__.py
    - jquants_client.py            : J-Quants API クライアント（取得＋保存ユーティリティ）
    - news_collector.py           : RSS ニュース収集・前処理・DB保存
    - schema.py                   : DuckDB スキーマ定義・初期化
    - pipeline.py                 : ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py      : マーケットカレンダー関連ユーティリティと更新ジョブ
    - audit.py                    : 監査ログ（signal / order_request / executions）定義・初期化
    - quality.py                  : データ品質チェック（欠損・スパイク・重複・日付）
  - strategy/
    - __init__.py                  : 戦略関連モジュール（拡張想定）
  - execution/
    - __init__.py                  : 発注・約定連携関連（拡張想定）
  - monitoring/
    - __init__.py                  : 監視用モジュール（拡張想定）

拡張・運用メモ
- strategy / execution / monitoring モジュールは骨格が用意されており、実際の戦略ロジックやブローカー API 統合は各プロジェクトで実装してください。
- ETL は日次バッチ向けに設計されています。CI やスケジューラ（cron / Airflow / Prefect 等）から run_daily_etl を呼ぶのが標準的です。
- 監査ログ（audit）はトレーサビリティを保証するため削除せず蓄積する方針です。監査 DB の運用（バックアップ・保管方針）を事前に設計してください。

ライセンス・貢献
- 本リポジトリに含まれるライセンスやコントリビュート規約がある場合はプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（このコードダンプには含まれていません）。

お問い合わせ
- 実装や挙動に関する質問・改善提案があれば、リポジトリの Issue を作成してください。

以上。README に含めてほしい追加項目（例: サンプル .env.example、パッケージ化手順、CI 設定、より具体的なコマンド等）があれば教えてください。必要に応じて追記します。