# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ（未完成プロジェクト向けのコアモジュール群）

- バージョン: 0.1.0
- 説明: J-Quants API を用いた市場データ取得、DuckDB スキーマ定義・初期化、ETL パイプライン、データ品質チェック、監査ログ（発注フローのトレーサビリティ）など、アルゴリズム取引基盤の基礎機能を提供します。

---

目次
- プロジェクト概要
- 主な機能一覧
- 動作環境・依存関係
- セットアップ手順
- 環境変数（設定項目）
- 使い方（簡単なコード例）
- ディレクトリ構成
- 設計上の重要ポイント

---

プロジェクト概要
- J-Quants API から株価（OHLCV）、財務データ、JPX マーケットカレンダー等を取得し、DuckDB に冪等的に保存する機能を提供します。
- ETL（差分更新・バックフィル・品質チェック）を実行するパイプラインを備えます。
- シグナル → 発注 → 約定 のフローを監査ログとして記録するスキーマ群を提供します。
- 設定は環境変数（.env の自動読み込みを含む）で管理します。

主な機能一覧
- 環境設定管理
  - .env / .env.local からの自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - 必須値の検証とラッパー（settings オブジェクト）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日次株価、財務、マーケットカレンダーの取得（ページネーション対応）
  - レート制限（120 req/min）のクライアント側制御
  - リトライロジック（指数バックオフ、最大3回、特定ステータスでの再試行）
  - 401 時の自動トークンリフレッシュ（1 回のみ）
  - DuckDB への保存関数（冪等：ON CONFLICT DO UPDATE）
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブルを定義
  - インデックス定義、外部キーや制約を含む DDL を実行して初期化
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（DB の最終取得日に基づく自動算出）
  - バックフィル（日次 ETL 実行時に過去 n 日を再取得して後出し修正を吸収）
  - カレンダー先読み（デフォルト 90 日）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - ETL の結果を ETLResult データクラスで返却
- 監査ログ（kabusys.data.audit）
  - シグナル・発注要求・約定の監査テーブル群
  - 冪等キー（order_request_id 等）による追跡性
  - UTC タイムスタンプ運用を前提
- データ品質チェック（kabusys.data.quality）
  - 欠損（OHLC 欠如）、主キー重複、スパイク（前日比閾値）、日付整合性チェック
  - 各チェックは QualityIssue オブジェクトを返し、重大度（error/warning）を付与

動作環境・依存関係
- Python >= 3.10（型注釈に | を使用）
- 必須パッケージ:
  - duckdb
- 標準ライブラリのみで動作する部分が多いですが、実行時に duckdb パッケージが必要です。
- ネットワーク通信（J-Quants API）を行うためインターネット接続が必要。

セットアップ手順
1. リポジトリをクローン/配置
   - 例: git clone <repo-url>
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)
3. 依存パッケージのインストール
   - pip install duckdb
   - 将来的に requirements.txt がある場合は pip install -r requirements.txt
4. パッケージをインストール（編集可能な開発モード）
   - pip install -e .
   - （ソース直下に setup.cfg/pyproject.toml がある場合）
5. 環境変数を設定
   - プロジェクトルートに .env を配置すると自動読み込みされます（優先順位: OS 環境変数 > .env.local > .env）
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
6. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで schema.init_schema() を呼ぶ（下の「使い方」参照）

環境変数（主な設定項目）
- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API のパスワード
- KABU_API_BASE_URL (省略可): kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack Bot トークン（アラート通知等に使用）
- SLACK_CHANNEL_ID (必須): Slack チャンネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視 DB）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

使い方（簡単な例）
- 設定の利用:
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path などで取得できます。

- DuckDB スキーマ初期化:
  - from kabusys.data import schema
  - conn = schema.init_schema(settings.duckdb_path)
  - 既存 DB に接続だけしたい場合: conn = schema.get_connection(settings.duckdb_path)

- 監査ログ（独立で初期化したい場合）:
  - from kabusys.data import audit
  - audit_conn = audit.init_audit_db("data/audit.duckdb")
  - あるいは既存 conn に audit.init_audit_schema(conn)

- J-Quants API クライアントの利用:
  - from kabusys.data import jquants_client as jq
  - id_tok = jq.get_id_token()  # settings.jquants_refresh_token を使用して idToken を取得
  - records = jq.fetch_daily_quotes(id_token=id_tok, date_from=date(2023,1,1), date_to=date(2023,1,31))
  - saved = jq.save_daily_quotes(conn, records)

- 日次 ETL の実行（推奨フロー）:
  - from datetime import date
    from kabusys.data import pipeline, schema
    conn = schema.init_schema(settings.duckdb_path)
    result = pipeline.run_daily_etl(conn, target_date=date.today())
    # result は ETLResult オブジェクト。result.to_dict() で辞書化可能。

- 品質チェックのみ実行:
  - from kabusys.data import quality
    issues = quality.run_all_checks(conn, target_date=date(2023,1,1))
    for i in issues: print(i)

- 自動.env 読み込みを無効化（テスト時など）:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

設計上のポイント / 注意事項
- J-Quants API に対して 120 req/min の制限をクライアント側で守る実装（固定レートのスロットリング）を行っています。多量の並列リクエストをしないよう注意してください。
- リトライ: ネットワークエラーや 408/429/5xx に対して指数バックオフで最大 3 回リトライします。401 はトークンリフレッシュ後に 1 回だけ再試行します。
- データの「いつ知り得たか」を残すため、fetch 時刻（fetched_at）を UTC で保存します（Look-ahead Bias 対策）。
- DuckDB 側の保存は冪等性を担保するため ON CONFLICT DO UPDATE を利用しています（raw 層等）。
- ETL は Fail-Fast ではなく、できる限り各ステップを継続して実行し、結果（品質問題やエラー）を ETLResult にまとめて返す設計です。呼び出し側で停止判断や通知を実装してください。
- 監査ログは削除しない前提で設計され、order_request_id 等の冪等キーにより二重発注防止・追跡を行います。すべての TIMESTAMP は UTC で扱います。

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py                          # 環境変数管理（.env 自動ロード含む）
    - data/
      - __init__.py
      - jquants_client.py                # J-Quants API クライアント（取得 + 保存）
      - schema.py                        # DuckDB スキーマ定義・初期化
      - pipeline.py                      # ETL パイプライン（差分更新・品質チェック）
      - audit.py                         # 監査ログスキーマ（シグナル→発注→約定）
      - quality.py                       # データ品質チェック
      - pipeline.py
      - audit.py
      - quality.py
    - execution/
      - __init__.py                       # 発注関連のエントリポイント(未実装の余地あり)
    - strategy/
      - __init__.py                       # 戦略モジュール置き場（実装はプロジェクト固有）
    - monitoring/
      - __init__.py                       # 監視・メトリクス関連（拡張予定）

付録: よくある操作例
- DuckDB をメモリ上で初期化（テスト用）:
  - conn = schema.init_schema(":memory:")
- ETL をテスト的に実行（自動トークンリフレッシュを使う）:
  - result = pipeline.run_daily_etl(conn, target_date=date(2023,1,1))
- 取得した ID トークンを直接渡してページネーションを通す:
  - id_tok = jq.get_id_token()
    prices = jq.fetch_daily_quotes(id_token=id_tok, date_from=..., date_to=...)

ライセンスや貢献方法などはこの README に含まれていません。必要に応じてプロジェクトのポリシーを追加してください。

以上がこのコードベースの README.md（日本語）になります。必要であれば「実行例のスクリプトテンプレート」や「.env.example の雛形」を追記します。どちらを追加しますか？