# KabuSys — 日本株自動売買プラットフォーム (README)

このリポジトリは日本株向けの自動売買プラットフォームのコアライブラリ群です。データ収集（J-Quants）、ETL、データ品質チェック、DuckDB スキーマ定義、監査ログ（発注→約定のトレーサビリティ）などを提供します。

主な用途は市場データの取得・永続化・品質管理および戦略／発注レイヤーへのデータ供給です。実際の売買 execution 層は拡張可能な設計になっています。

目次
- プロジェクト概要
- 機能一覧
- 要件
- セットアップ手順
- 使い方（簡易例）
- 環境変数（.env）と自動読み込み
- ディレクトリ構成

プロジェクト概要
- 名前: KabuSys
- 説明: J-Quants API などから日本株の市場データ・財務データ・市場カレンダーを取得し、DuckDB に冪等に保存。ETL パイプライン、品質チェック、監査ログ（order/exec）のスキーマを提供します。
- バージョン: 0.1.0（パッケージ定義内: src/kabusys/__init__.py）

機能一覧
- J-Quants API クライアント
  - 日次株価（OHLCV）取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
  - レート制限（120 req/min）に基づくスロットリング
  - 再試行（指数バックオフ、最大 3 回）、401 時のトークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で保存し、Look-ahead Bias を防止する設計
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル DDL を定義
  - インデックス定義、外部キー順序を考慮した初期化関数
  - 監査ログ用スキーマ（signal_events / order_requests / executions）を初期化するユーティリティ
- ETL パイプライン
  - 差分更新ロジック（最終取得日からの差分取得、バックフィル対応）
  - 市場カレンダーの先読み（デフォルト 90 日）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - ETL 実行結果を集約する ETLResult データクラス
- データ品質チェック
  - 欠損値検出（OHLC の欠損）
  - 主キー重複チェック
  - スパイク（前日比）検出
  - 日付整合性チェック（将来日付や非営業日のデータ）
  - 各チェックは QualityIssue を返し、severity（error/warning）で分類
- 設定管理
  - 環境変数および .env/.env.local による設定の自動読み込み
  - 必須設定の検証（存在しない場合は ValueError）
  - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL 検証
- 監視・通知用に Slack 設定を参照するプロパティを準備（実際の通知処理は拡張）

要件
- Python 3.10 以上（型注記に | を使用しているため）
- duckdb（DuckDB Python バインディング）
- ネットワークアクセス（J-Quants API など）

推奨パッケージ（最低限）
- duckdb

セットアップ手順

1. リポジトリをクローン
   - git clone ... （リポジトリ URL）

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存関係のインストール
   - pip install duckdb
   - （必要に応じて他のライブラリを追加）

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

4. 環境変数（.env）を準備
   - プロジェクトルートに .env または .env.local を置くと自動読み込みされます（src/kabusys/config.py）。
   - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

使い方（簡易例）

- 基本的な流れ
  1. DuckDB スキーマを初期化（初回）
  2. ETL を実行（run_daily_etl）
  3. 結果を確認・ログ出力

- Python スニペット（例）

  from pathlib import Path
  from datetime import date
  import duckdb

  # スキーマ初期化（ファイル DB）
  from kabusys.data import schema, pipeline
  db_path = Path("data/kabusys.duckdb")
  conn = schema.init_schema(db_path)  # ファイルがなければ親ディレクトリも作成されます

  # 日次 ETL 実行（今日分）
  result = pipeline.run_daily_etl(conn, target_date=date.today())

  # ETL 実行結果の確認
  print(result.to_dict())

- 監査ログ初期化（監査専用 DB）
  from kabusys.data import audit
  audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

- J-Quants クライアントを直接使う（ID トークン自動取得・キャッシュあり）
  from kabusys.data import jquants_client as jq
  records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))

環境変数（.env）と自動読み込み

- 自動読み込みルール（src/kabusys/config.py）
  - 読み込み優先順: OS 環境変数 > .env.local > .env
  - プロジェクトルートの検出: __file__ を起点に親ディレクトリで .git または pyproject.toml を探す
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
  - .env のパースは shell 形式に近いが、クォートやコメント処理を考慮した実装

- 重要な環境変数（README に記載しておくべき最低限の例）

  JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  KABU_API_PASSWORD=your_kabu_api_password
  KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C01234567
  DUCKDB_PATH=data/kabusys.duckdb
  SQLITE_PATH=data/monitoring.db
  KABUSYS_ENV=development  # development | paper_trading | live
  LOG_LEVEL=INFO

  - settings（kabusys.config.settings）が上記変数をプロパティとして提供します。
  - 必須キーが未設定の場合は ValueError を送出します（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）。

主要 API（概要）
- kabusys.config.Settings
  - settings.jquants_refresh_token / kabu_api_password / slack_bot_token / slack_channel_id
  - settings.duckdb_path / settings.sqlite_path
  - settings.env / settings.log_level / settings.is_live / is_paper / is_dev

- kabusys.data.jquants_client
  - get_id_token(refresh_token: str | None) -> str
  - fetch_daily_quotes(id_token: None|str, code: None|str, date_from: None|date, date_to: None|date) -> list[dict]
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records) -> int
  - save_financial_statements(conn, records) -> int
  - save_market_calendar(conn, records) -> int

  特徴: レートリミット、リトライ、401 自動リフレッシュ、fetched_at 記録、DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- kabusys.data.schema
  - init_schema(db_path) -> duckdb.Connection
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date: date | None, id_token: None|str, run_quality_checks: bool = True, ...) -> ETLResult
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - get_last_price_date / get_last_financial_date / get_last_calendar_date

- kabusys.data.quality
  - run_all_checks(conn, target_date: None|date, reference_date: None|date, spike_threshold: float) -> list[QualityIssue]
  - check_missing_data / check_spike / check_duplicates / check_date_consistency

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py                      # 環境変数・設定管理（.env 自動読み込み）
    - data/
      - __init__.py
      - jquants_client.py            # J-Quants API クライアント + DuckDB 保存ユーティリティ
      - schema.py                    # DuckDB スキーマ定義・初期化
      - pipeline.py                  # ETL パイプライン（差分更新・品質チェック）
      - audit.py                     # 監査ログ（発注→約定トレーサビリティ）スキーマ
      - quality.py                   # 品質チェックロジック
      - (others)
    - strategy/
      - __init__.py                  # 戦略層（拡張用）
    - execution/
      - __init__.py                  # 発注・ブローカー連携（拡張用）
    - monitoring/
      - __init__.py                  # 監視／メトリクス（拡張用）

注意事項・運用上のポイント
- J-Quants API 利用時は API レート制限（120 req/min）に注意してください。クライアントは内部で制御しますが、外部から複数プロセスで同時実行すると制限に抵触する可能性があります。
- DuckDB の初期化は init_schema を使ってください。既存テーブルがあればスキップ（冪等）。
- ETL はバックフィル（デフォルト 3 日）で最終取得日の一部を再取得し、API 後出し修正を吸収するよう設計されています。
- 品質チェックはエラー・警告を収集して返却します。ETL は基本的に Fail-Fast ではなく、呼び出し側が結果に応じた対応（停止・通知など）を判断します。
- 実運用（実際の売買）では KABUSYS_ENV を live に設定し、適切な安全対策（サンドボックスでのテスト、order_request の冪等運用、監査ログの監視）を行ってください。
- セキュリティ上の理由でトークン等の秘密値は Git に保存しないで下さい。.env はリポジトリ外に管理することを推奨します。

拡張ポイント（アイデア）
- Slack や監視システムへの通知（ETL 結果や品質エラー）
- strategy レイヤーでの特徴量利用（features / ai_scores テーブル）
- execution レイヤーで kabu ステーション API への送信および注文監視
- 分散実行やジョブキュー（Airflow / Dagster）との統合

ライセンス・貢献
- 本 README はコードベースを元にしたドキュメントです。実際のライセンス表記や貢献フローはリポジトリの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

問題報告・質問
- バグや改善提案があれば Issue を作成してください。使い方の質問は README に追記します。

以上。必要であれば README にサンプル .env.example、より詳しい API 使用例、運用チェックリスト（本番移行チェックリスト）などを追記します。どの部分を詳しく載せたいか教えてください。