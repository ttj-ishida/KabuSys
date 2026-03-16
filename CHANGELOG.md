# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

全般:
- 本リリースはパッケージ初期公開相当の内容を含みます（バージョン 0.1.0）。
- 日付: 2026-03-16

## [0.1.0] - 2026-03-16

### Added
- パッケージ基盤を追加
  - kabusys パッケージの初期モジュール群を追加（data, strategy, execution, monitoring を公開）。
  - パッケージバージョンを 0.1.0 に設定。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを追加。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を探索）。
  - .env のパース機能を実装（export プレフィックス対応、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント扱いの制御）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 環境変数保護（OS環境変数を上書きしない）や .env.local による上書き優先度を実装。
  - Settings クラスを実装し、J-Quants リフレッシュトークン、kabu API パスワード、Slack トークン/チャンネル、データベースパス等のプロパティを提供。
  - KABUSYS_ENV と LOG_LEVEL の値検証（有効値チェック）と便利な is_live / is_paper / is_dev プロパティを追加。

- J-Quants クライアント (kabusys.data.jquants_client)
  - J-Quants API からのデータ取得機能を実装:
    - 株価日足（fetch_daily_quotes）
    - 財務データ（fetch_financial_statements）
    - JPX マーケットカレンダー（fetch_market_calendar）
  - 認証補助: リフレッシュトークンからの id_token 取得（get_id_token）とモジュールレベルの id_token キャッシュ実装。
  - HTTP レイヤーに以下の堅牢化を実装:
    - レートリミッタ（120 req/min 固定間隔スロットリング）
    - リトライ（指数バックオフ、最大 3 回、408/429/5xx に対応）
    - 401 を受けた場合のトークン自動リフレッシュ（1 回のみリトライ）
    - 429 の Retry-After ヘッダ優先処理
    - JSON デコード失敗時の明示的エラー
  - ページネーション対応（pagination_key を用いた継続取得）を実装。
  - DuckDB へ保存する idempotent な保存関数を実装:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - 各関数は fetched_at を UTC タイムスタンプで保存し、ON CONFLICT DO UPDATE を用いて冪等性を確保。
  - データ変換ユーティリティ（_to_float, _to_int）を提供し、不正値や空文字列を安全に扱う処理を実装。

- DuckDB スキーマ定義 (kabusys.data.schema)
  - 3 層（Raw / Processed / Feature）と Execution 層を含むスキーマ DDL を実装。
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw レイヤー。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed レイヤー。
  - features, ai_scores 等の Feature レイヤー。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution レイヤー。
  - パフォーマンスを考慮したインデックスを多数定義。
  - init_schema(db_path) でディスク上の DB を初期化（親ディレクトリ自動作成、:memory: 対応）、get_connection() を提供。

- ETL パイプライン (kabusys.data.pipeline)
  - 日次 ETL 実装:
    - run_prices_etl, run_financials_etl, run_calendar_etl（差分取得・バックフィル・保存）
    - run_daily_etl: 市場カレンダー取得 → 営業日調整 → 株価・財務の差分 ETL → 品質チェック（オプション）の統合フロー
  - 差分ロジック:
    - DB の最終取得日からの差分取得、自動的な date_from 算出
    - デフォルトのバックフィル日数を 3 日とし、API の後出し修正に対応
    - カレンダーはデフォルトで先読み 90 日
  - ETLResult データクラスを導入し、取得数、保存数、品質問題、エラー一覧を集約。
  - トレードオフとして、各ステップは独立してエラーハンドリングされ、1 ステップ失敗でも他ステップは継続（Fail-Fast ではない）。

- 品質チェック (kabusys.data.quality)
  - QualityIssue データクラスを導入（check_name, table, severity, detail, rows）。
  - 少なくとも以下のチェックを実装/提供:
    - 欠損データ検出（check_missing_data: raw_prices の OHLC 欠損検出、サンプル行取得、件数報告）
    - 異常値（スパイク）検出（check_spike: 前日比で閾値超の急騰/急落を検出、サンプル取得）
  - 各チェックは全件収集を行い、呼び出し側が重大度に応じて判断できる設計。

- 監査ログ（トレーサビリティ） (kabusys.data.audit)
  - シグナル→発注要求→約定までの監査テーブルを定義:
    - signal_events（戦略が生成したシグナルの記録）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ）
    - executions（証券会社からの約定ログ、broker_execution_id をユニークキーとして冪等性担保）
  - init_audit_schema(conn) / init_audit_db(db_path) を提供（UTC タイムゾーン適用、インデックス定義含む）。
  - 発注種別ごとの整合性チェック（limit/stop/market の価格必須制約等）やステータス遷移をモデル化。

### Changed
- 初期リリースのため該当なし。

### Fixed
- 初期リリースのため該当なし。

### Security
- 認証情報（リフレッシュトークン等）は Settings 経由で環境変数から読み込み、.env の自動上書きは OS 環境変数を保護する仕組みを導入。

### Notes / Implementation details
- J-Quants API クライアントはレート制限・リトライ・トークンリフレッシュを備え、ページネーションをサポートしています。テスト時の利便性のため、id_token を引数で注入可能です。
- DuckDB 初期化は冪等であり、既存のテーブルがあればスキップします。:memory: を指定して単体テスト用のインメモリ DB を利用可能です。
- run_daily_etl は市場カレンダー取得→営業日調整を行うことで、営業日判定に基づいた差分取得を行います。
- quality モジュールは SQL ベースで効率的に品質チェックを行い、複数の問題を一括して検出・報告します。

### Breaking Changes
- 初期リリースのため該当なし。

---

今後の予定（非公式）
- data.quality に重複チェック・日付不整合検出の具象実装を追加
- strategy / execution / monitoring モジュールの実装補完（現在はパッケージのみ存在）
- より細かなエラーハンドリングやメトリクス出力の強化

贡献者:
- 初期実装チーム（コードベースから推測して記載）