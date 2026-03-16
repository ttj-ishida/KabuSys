CHANGELOG
=========

すべての注目すべき変更点を時系列で記録します。
このファイルは「Keep a Changelog」の慣習に準拠しています。

フォーマット
-----------
- バージョン見出しは "X.Y.Z - YYYY-MM-DD" 形式で記載しています。
- セクションは主に Added / Changed / Fixed / Removed / Security を使用します。

0.1.0 - 2026-03-16
------------------

Added
- 初期リリースとして基本機能群を実装。
  - パッケージ初期化
    - パッケージバージョンを __version__ = "0.1.0" として設定。
    - 公開モジュールとして data, strategy, execution, monitoring をエクスポート。

  - 設定（kabusys.config）
    - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を起点に探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
    - .env パーサー実装（export プレフィックス対応、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いを考慮）。
    - 環境変数上書き制御（.env と .env.local の読み込み順、既存 OS 環境変数を保護する protected オプション）。
    - Settings クラスを提供し、以下のプロパティ経由で設定値を取得可能:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト localhost）
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH
      - KABUSYS_ENV（development / paper_trading / live の検証）、LOG_LEVEL（DEBUG/INFO/... の検証）
      - is_live / is_paper / is_dev の便捷プロパティ

  - J-Quants API クライアント（kabusys.data.jquants_client）
    - レート制御（120 req/min）を固定間隔スロットリングで実装（RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回）。HTTP 408/429/5xx を再試行対象に設定。429 の場合は Retry-After ヘッダを尊重。
    - 401 Unauthorized を受けた場合、自動で refresh（id_token の再取得）して 1 回リトライする仕組み（無限再帰を防止）。
    - id_token のモジュールレベルキャッシュ（ページネーション間で共有）を実装。force_refresh に対応。
    - JSON デコードエラーやネットワークエラーに対する明示的な例外ラップ。
    - ページネーション対応のデータ取得関数:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（財務データ）
      - fetch_market_calendar（JPX マーケットカレンダー）
    - DuckDB へ保存する冪等的関数を提供（ON CONFLICT DO UPDATE を利用）:
      - save_daily_quotes, save_financial_statements, save_market_calendar
      - 保存時に fetched_at を UTC ISO8601 形式で記録し、Look-ahead Bias のトレーシングを容易にする。
    - データ変換ユーティリティ: 安全な _to_float / _to_int 実装（空値・不正値は None、"1.0" 等の float 文字列を int に変換するロジック等）。

  - DuckDB スキーマ定義・初期化（kabusys.data.schema）
    - DataSchema.md に準拠した多層スキーマを実装:
      - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
      - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature Layer: features, ai_scores
      - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 各テーブルに適切な型・チェック制約（CHECK, PRIMARY KEY, FOREIGN KEY 等）を付与。
    - 検索パフォーマンスを考慮したインデックス群を定義。
    - init_schema(db_path) によりデータベースファイルの親ディレクトリ自動作成、テーブルの冪等作成を実行（":memory:" サポート）。
    - get_connection(db_path) による既存 DB への接続関数を提供（初期化は行わない旨を明示）。

  - 監査ログ（kabusys.data.audit）
    - シグナルから約定に至るトレーサビリティ用の監査テーブルを実装:
      - signal_events（戦略が生成したシグナルをすべて記録。棄却やエラーも保存）
      - order_requests（発注要求、order_request_id を冪等キーとして扱う）
      - executions（証券会社の約定情報を保存、broker_execution_id をユニークとして冪等性確保）
    - UTC タイムゾーンでの TIMESTAMP 保存を前提（init_audit_schema は "SET TimeZone='UTC'" を実行）。
    - init_audit_schema(conn) により既存接続へ監査テーブルを追加、init_audit_db(db_path) による専用 DB 初期化を提供。
    - 監査用インデックスを多数定義して実用的な検索性能を確保。

  - データ品質チェック（kabusys.data.quality）
    - DataPlatform.md に基づく品質チェック群を実装:
      - 欠損データ検出 (check_missing_data): raw_prices の OHLC 欄の NULL を検出（volume は対象外）。
      - 異常値（スパイク）検出 (check_spike): 前日比の絶対変動率が閾値（デフォルト 50%）を超えるレコードを検出。
      - 重複チェック (check_duplicates): 主キー重複 (date, code) を検出。
      - 日付不整合チェック (check_date_consistency): 将来日付の検出、market_calendar と整合しない非営業日のデータ検出（market_calendar が存在する場合のみ）。
    - 各チェックは QualityIssue dataclass のリストを返す（severity: "error" | "warning"）。
    - run_all_checks で複数チェックをまとめて実行でき、エラー数/警告数をログ出力。

  - パッケージ構造の骨子
    - strategy, execution, monitoring のモジュール初期化子を作成（将来の戦略実装・発注処理・監視実装のための空シェル）。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Security
- 新規リリースのため該当なし。

Notes / 実装上の注意
- .env 自動ロードはプロジェクトルートを基準に行うため、配布後に CWD が変わっても動作するよう設計されています。ただしプロジェクトルートが特定できない場合は自動ロードをスキップします。
- J-Quants クライアントは外部 API のレート制限・一時的エラーに耐える設計です。アプリケーションは例外メッセージ／ログを見て運用判断してください。
- DuckDB スキーマの DDL には厳密な CHECK 制約や外部キーを多用しています。既存 DB に導入する際は互換性に注意してください（init_schema は冪等ですが、既存スキーマとの衝突は環境依存の影響を与える可能性があります）。
- 監査ログは削除しない前提で設計（外部キーは ON DELETE RESTRICT）。監査データの扱いに関する運用ポリシーを整備してください。

今後の予定（例）
- strategy / execution 層の具象実装（ポートフォリオ最適化、発注実行器の実装）。
- モニタリング（Slack 通知、メトリクスエクスポート）の実装強化。
- より詳細なテスト（ネットワークフォールト、トークン更新、DuckDB マイグレーション）および CI/CD 連携。

Acknowledgements
- 本 CHANGELOG はリポジトリ内のソースコードから機能を推測して作成しています。実装内容や運用ルールの詳細はソースコード内 docstring / コメントを参照してください。