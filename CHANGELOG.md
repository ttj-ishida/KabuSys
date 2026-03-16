CHANGELOG
=========

すべての変更は「Keep a Changelog」フォーマットに準拠して記載しています。
タグ付けルール: バージョン - 日付（YYYY-MM-DD）

v0.1.0 - 2026-03-16
-------------------

Added
- パッケージ初期リリース。日本株自動売買システムの基盤機能を実装。
  - パッケージメタ情報
    - kabusys.__version__ = "0.1.0"
    - パッケージ公開 API に data, strategy, execution, monitoring を含む（strategy / execution / monitoring はプレースホルダ）。
  - 設定管理 (kabusys.config)
    - .env ファイルおよび環境変数からの自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
    - .env の行パーサー実装: export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いを考慮。
    - 環境変数取得ヘルパー _require と Settings クラスを提供（J-Quants, kabu API, Slack, DB パス等のプロパティ、値検証を含む）。
    - KABUSYS_ENV と LOG_LEVEL の値チェック（許容値バリデーション）。
  - J-Quants クライアント (kabusys.data.jquants_client)
    - API 呼び出しユーティリティ _request を実装：JSON デコード、タイムアウト、詳細なログ。
    - レート制限: 固定間隔スロットリングで 120 req/min を厳守する _RateLimiter を実装。
    - リトライロジック: 指数バックオフ（最大 3 回）、408/429/5xx の再試行、429 の Retry-After サポート。
    - 認証トークン取得と自動リフレッシュ: get_id_token、401 受信時の自動リフレッシュ（無限再帰回避）。
    - ページネーション対応のデータ取得関数を実装:
      - fetch_daily_quotes（株価日足: OHLCV）
      - fetch_financial_statements（財務データ: 四半期 BS/PL）
      - fetch_market_calendar（JPX カレンダー）
    - DuckDB への永続化関数（冪等）を実装:
      - save_daily_quotes, save_financial_statements, save_market_calendar
      - ON CONFLICT DO UPDATE による重複排除、fetched_at を UTC で記録
    - データ型変換ユーティリティ: _to_float, _to_int（入力の堅牢性を向上）
  - DuckDB スキーマ (kabusys.data.schema)
    - DataPlatform 設計に基づいた多層スキーマ定義を実装:
      - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
      - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature Layer: features, ai_scores
      - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 各テーブルに制約（PRIMARY KEY / CHECK / FOREIGN KEY 等）を定義。
    - パフォーマンス向けインデックス群を定義。
    - init_schema(db_path) による初期化 API、get_connection(db_path) を提供。親ディレクトリ自動作成、:memory: サポート。
  - ETL パイプライン (kabusys.data.pipeline)
    - 日次 ETL の実装:
      - run_daily_etl: 市場カレンダー → 株価 → 財務 → 品質チェック の順で実行（複数ステップの独立したエラーハンドリング）。
      - run_calendar_etl, run_prices_etl, run_financials_etl: 差分取得、バックフィル、lookahead をサポート。
    - 差分更新ロジック:
      - DB の最終取得日から backfill_days（デフォルト 3 日）分を遡って再取得することで API の後出し修正を吸収。
      - カレンダーは target_date + lookahead_days（デフォルト 90 日）まで先読み。
    - ETL 結果を表す ETLResult データクラスを実装（取得数／保存数／品質問題／エラー収集等、直列化サポート）。
    - 非営業日の調整ヘルパー _adjust_to_trading_day（market_calendar に基づいて過去方向に最も近い営業日に補正）。
    - DB 存在チェックと最終日取得ユーティリティ。
    - 各ステップで例外は捕捉されログに記録、処理は可能な限り継続する設計（Fail-Fast ではない）。
  - 監査ログ（トレーサビリティ） (kabusys.data.audit)
    - シグナル → 発注要求 → 約定 の一貫した監査テーブルを実装:
      - signal_events, order_requests, executions（各テーブルに UUID ベースの ID、ステータス、created_at/updated_at）。
    - order_request_id を冪等キーとして二重発注を防止する設計。
    - 全 TIMESTAMP を UTC で保存するため init_audit_schema は SET TimeZone='UTC' を実行。
    - init_audit_schema(conn) / init_audit_db(db_path) を提供（インデックス含む）。
  - データ品質チェック (kabusys.data.quality)
    - チェック設計と一部実装:
      - QualityIssue データクラス（check_name, table, severity, detail, rows）。
      - check_missing_data: raw_prices の OHLC 欠損検出（必須カラムの欠損を error として報告）。
      - check_spike: 前日比スパイク検出（LAG ウィンドウを用い、しきい値超過を検出）。
    - SQL パラメータバインドを利用しインジェクションリスクを低減。
    - 品質チェックは全件収集を行い、呼び出し元が重大度に応じて対応を決定する仕様。
  - ロギング・エラーハンドリング
    - 各モジュールで詳細な情報ログ・警告・例外ログを出力。失敗時も手元で原因追跡がしやすい設計。
  - テスト支援
    - id_token の注入や KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化等でユニットテストを容易化。

Changed
- 初版リリースのため該当なし。

Fixed
- 初版リリースのため該当なし。

Removed
- 初版リリースのため該当なし。

Deprecated
- 初版リリースのため該当なし。

Security
- 初版リリースのため該当なし。

注意事項 / 既知の制限
- strategy, execution, monitoring パッケージは存在するが初期状態では実装が未完成（プレースホルダ）。これらを用いた上位ロジックは別実装が必要。
- quality.run_all_checks の実装は pipeline.run_daily_etl から期待されるが、抜粋コードの範囲で全チェックの集約関数の有無は確認できないため、統合時に実装を確認してください。
- DuckDB の制約や UNIQUE/INDEX の動作はバージョン依存の挙動を含むため、運用環境での検証を推奨。
- ネットワーク / API のエラー処理は最大リトライ回数に達すると例外を投げる設計（呼び出し元での再試行方針は運用次第）。

今後の予定（例）
- strategy / execution 層の実装（戦略ロジック、注文送信・約定処理の実装）
- 監査ログと実取引ブローカー連携の検証（実運用の堅牢性確認）
- 品質チェックの拡充（ニュースデータ検査、統計的外れ値検出など）
- ドキュメント（DataSchema.md, DataPlatform.md の整備）および CLI / Makefile 等の運用ツール追加

--- 

（この CHANGELOG はソースコードの内容から推測してまとめたものであり、実際のリリースノートはプロジェクトの公式記録に従ってください。）