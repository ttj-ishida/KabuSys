CHANGELOG
=========

すべてのリリースノートは "Keep a Changelog" の慣例に従って記載しています。
このファイルは主にコードベースの初期実装（v0.1.0）に基づいて推測して作成しています。

Unreleased
----------

- なし

0.1.0 - 2026-03-16
------------------

Added
- パッケージ初期実装を追加（kabusys v0.1.0）。
  - パッケージエクスポート: data, strategy, execution, monitoring を __all__ に定義。
- 環境設定管理モジュール (kabusys.config)
  - .env / .env.local ファイルおよび OS 環境変数から設定を読み込む自動読み込み機能を実装。
    - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - プロジェクトルート判定は .git または pyproject.toml を基準に行い、CWD に依存しない実装。
  - .env パーサを実装（export 形式、引用文字列、エスケープ、インラインコメント処理に対応）。
  - 環境変数取得ヘルパ（Settings クラス）を実装。
    - 必須設定の取得メソッド (_require) により未設定時は ValueError を投げる。
    - 検証を行うプロパティ: KABUSYS_ENV (development/paper_trading/live)、LOG_LEVEL（DEBUG/INFO/...）など。
    - 主要設定項目（例）:
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN（必須）
      - SLACK_CHANNEL_ID（必須）
      - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
      - SQLITE_PATH（デフォルト data/monitoring.db）
- J-Quants API クライアント (kabusys.data.jquants_client)
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得機能を実装。
  - 主要機能・設計:
    - API レート制限を守る固定間隔スロットリング（120 req/min を想定）を実装（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回）を実装。HTTP 408/429/5xx に対してリトライ。
    - 401 Unauthorized を受けた場合はリフレッシュトークンで id_token を自動リフレッシュして 1 回リトライ。
    - ページネーション対応（pagination_key を用いた連続取得）。
    - 取得時刻（fetched_at）を UTC 形式で記録し Look-ahead Bias の追跡を可能にする。
    - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で行う各 save_* 関数を実装:
      - save_daily_quotes -> raw_prices テーブルへ保存
      - save_financial_statements -> raw_financials テーブルへ保存
      - save_market_calendar -> market_calendar テーブルへ保存
    - 型安全な変換ユーティリティ _to_float / _to_int を提供（不正な値は None にする等の挙動）。
    - モジュールレベルの id_token キャッシュを保持し、ページネーション間で共有。
- DuckDB スキーマ定義・初期化モジュール (kabusys.data.schema)
  - データプラットフォーム用のスキーマを定義（3 層 + 実行層の設計に準拠）。
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルの制約（PRIMARY KEY, CHECK 等）を定義。
  - 検索パフォーマンス向けに主要なインデックスを定義。
  - init_schema(db_path) でディレクトリ作成 → 接続 → DDL 実行しテーブルを冪等に作成する API を提供。
  - get_connection(db_path) で既存 DB への接続を返す（スキーマ初期化は行わない）。
- ETL パイプライン (kabusys.data.pipeline)
  - 日次 ETL の主要フローを実装:
    - 差分更新（DB の最終取得日を参照し未取得分のみを取得）
    - backfill_days による数日前からの再取得（API 後出し修正の吸収）
    - 市場カレンダーは lookahead（デフォルト 90 日）で先読み
    - 保存は jquants_client の save_* を利用（冪等性を確保）
    - 品質チェックモジュール quality を呼び出すオプションを備える
  - run_prices_etl / run_financials_etl / run_calendar_etl を実装（各差分取得と保存を行う）。
  - run_daily_etl により、カレンダー取得 → 営業日調整 → 株価・財務 ETL → 品質チェック の順で実行し ETLResult を返す。
  - ETLResult データクラスにより、取得数・保存数・品質問題リスト・エラーを集約・報告可能。
  - DB の最終取得日取得ユーティリティ（get_last_price_date 等）や _adjust_to_trading_day を提供。
- 監査ログ（トレーサビリティ）モジュール (kabusys.data.audit)
  - シグナルから約定までの監査ログ用テーブルを実装:
    - signal_events（戦略が生成したシグナルの永続化）
    - order_requests（発注要求ログ、order_request_id を冪等キーとして利用）
    - executions（証券会社からの約定ログ、broker_execution_id を冪等キーとして扱う）
  - 監査用インデックス、FOREIGN KEY、CHECK 制約を定義。
  - init_audit_schema(conn) / init_audit_db(db_path) による初期化 API を提供。
  - すべての TIMESTAMP は UTC 保存を前提（接続時に SET TimeZone='UTC' を実行）。
- データ品質チェックモジュール (kabusys.data.quality)
  - 品質チェックフレームワークとチェック実装の一部を提供。
  - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）。
  - 実装済みチェック（少なくとも以下を提供）:
    - check_missing_data: raw_prices の OHLC 欠損検出（重大度: error）
    - check_spike: 前日比スパイク（急騰・急落）検出（デフォルト閾値 50%）
  - 各チェックは問題を全件収集して QualityIssue リストを返す設計（Fail-Fast ではない）。
  - DuckDB 上で SQL を直接実行することで効率的に検査を行い、パラメータバインドを使用。
- その他
  - data、strategy、execution パッケージの初期パッケージングを実施（将来的機能追加のための構成）。
  - ロギング箇所を要所に配置し、問題発見・運用時のトレースを容易にする。

Changed
- 新規リリースのため該当なし（初回実装）。

Fixed
- 新規リリースのため該当なし（初回実装）。

Notes / Implementation details
- J-Quants クライアントはレート制限（120 req/min）を守るために固定間隔スロットリングを採用しています。短時間に多数のリクエストを行う際は注意してください。
- HTTP リトライ時は指数バックオフを用い、429 の場合は Retry-After ヘッダを優先して待機します。
- DuckDB への保存は各テーブルの主キーに対して ON CONFLICT DO UPDATE を利用して冪等性を担保しています（ETL の再実行が安全）。
- 環境変数の自動読み込みはプロジェクトルートの検出に依存するため、パッケージ配布後やテスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD を使って挙動を制御できます。
- 品質チェックフレームワークは拡張しやすい設計になっており、追加のチェック（重複、将来日付、不整合など）を容易に実装可能です。
- 監査ログは削除しない前提の設計で、order_request_id / broker_execution_id を冪等キーとして二重発注や二重記録を防ぐ事を目的としています。

今後の TODO（想定）
- strategy / execution レイヤの具象実装（シグナル生成・ポートフォリオ最適化・ブローカー API 実装）。
- 品質チェックの追加（重複チェック、将来日付検出など）の完全実装と ETL への統合強化。
- テストカバレッジの拡充（ユニットテスト、統合テスト、モックを用いた API テスト）。
- モニタリング・アラート（Slack 通知等）の実装強化（Slack の設定は既に Settings に含まれる）。

参考
- この CHANGELOG はソースコードの実装コメント・ドキュメント文字列から推測して作成しています。実際のユーザー向けリリースノートとして公開する際は、実動作テスト結果や変更差分に基づいて適宜修正してください。