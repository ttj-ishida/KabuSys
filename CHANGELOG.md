KEEP A CHANGELOG 準拠 — CHANGELOG.md

すべての重要な変更履歴をこのファイルに記載します。形式は「Keep a Changelog」に準拠しています。  
新しい変更は必ず「Added / Changed / Fixed / Removed / Security」などのセクションごとに記載してください。

Unreleased
- なし

0.1.0 - 2026-03-16
Added
- 初回リリース: KabuSys — 日本株自動売買システム（パッケージ: kabusys）
  - パッケージのエントリポイントを追加（src/kabusys/__init__.py）。
  - public API として data, strategy, execution, monitoring をエクスポート。

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local からの自動読み込みを実装（プロジェクトルートは .git または pyproject.toml を探索）。
  - export KEY=val 形式やクォート付き値、行末コメントなどを考慮した .env パーサを実装。
  - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD サポート。
  - Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル 等の取得・検証）。
  - 環境変数の必須チェック（未設定時は ValueError を送出）。

- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しラッパーを実装（JSON デコード、HTTP ヘッダ管理）。
  - レート制御: 固定間隔スロットリングによる 120 req/min 制限（RateLimiter）。
  - リトライロジック: 指数バックオフ（最大 3 回）、対象ステータス (408, 429, 5xx)。
  - 401 レスポンス時のトークン自動リフレッシュ（1 回のみ）を実装。
  - Retry-After ヘッダ優先の待機時間処理（429）。
  - ページネーション対応の取得関数:
    - fetch_daily_quotes（株価日足, OHLCV）
    - fetch_financial_statements（四半期財務）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存用関数（冪等設計、ON CONFLICT DO UPDATE）:
    - save_daily_quotes（raw_prices）
    - save_financial_statements（raw_financials）
    - save_market_calendar（market_calendar）
  - 取得時刻（fetched_at）を UTC（ISO 8601, Z）で記録。
  - 型変換ユーティリティ: _to_float / _to_int（厳密な変換ルールを適用）。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - 3層データモデルを実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）を付与。
  - インデックス群を定義（頻出クエリに最適化）。
  - init_schema(db_path) でデータベース・ディレクトリの自動作成とテーブル作成を行う（冪等）。
  - get_connection(db_path) による既存 DB 接続取得を提供。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 日次 ETL のエントリ run_daily_etl を実装。
    - 処理順: 市場カレンダー ETL → 株価日足 ETL → 財務データ ETL → 品質チェック
    - 各ステップは独立して例外処理され、1 ステップ失敗でも他は継続（エラー情報を収集）。
    - 差分更新ロジック: DB の最終取得日を基に自動算出、backfill_days による再取得（デフォルト 3 日）。
    - カレンダー先読み（デフォルト 90 日）と営業日調整機能。
    - fetch/save は jquants_client を利用（冪等保存）。
  - run_prices_etl / run_financials_etl / run_calendar_etl を個別に実行可能。
  - ETLResult データクラスを提供（品質問題・エラーの集約、to_dict でシリアライズ可能）。

- 監査ログ（トレーサビリティ）モジュール（src/kabusys/data/audit.py）
  - signal_events, order_requests, executions の監査テーブルを定義。
  - UUID ベースのトレーサビリティ階層と冪等キー設計（order_request_id）。
  - すべての TIMESTAMP を UTC で扱うよう init_audit_schema で SET TimeZone='UTC' 実行。
  - ステータス列と制約により発注・約定フローの完全な履歴を保存。
  - init_audit_db(db_path) で専用 DB の初期化・接続を提供。
  - 監査用インデックスを多数定義（検索パフォーマンス向上）。

- データ品質チェックモジュール（src/kabusys/data/quality.py）
  - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）。
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欠損検出（必須カラムの NULL 検出）。発見時は severity="error"。
    - check_spike: 前日比によるスパイク検出（LAG ウィンドウ関数を使用）。閾値はデフォルト 50%。
  - 各チェックは DuckDB 接続で SQL を実行し、サンプル行（最大 10 件）を返す設計。
  - Fail-Fast ではなく全件収集する方針（呼び出し側が重大度に応じて判断）。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Removed
- なし（初回リリース）

Security
- なし（初回リリース）

注意事項 / 補足
- settings.jquants_refresh_token 等の一部設定は必須で、未設定の場合は ValueError が発生します。デプロイ時は .env を正しく設定してください（.env.example を参照）。
- jquants_client のリクエストはネットワークや API のエラーに対してリトライを行いますが、API 側の仕様変更や認証方式の変更があれば追加対応が必要です。
- strategy, execution, monitoring パッケージはエントリポイントを備えていますが（__init__.py が存在）、実装の詳細は今後の開発対象です。
- DuckDB の ON CONFLICT / FOREIGN KEY の振る舞いはバージョン依存の差異があるため、運用環境の DuckDB バージョンでの検証を推奨します。

作成者
- コードベースの解析に基づき自動生成（CHANGELOG の内容はコードから推測した実装項目を記載しています）。実際のコミット単位の変更履歴とは差異がある可能性があります。必要であればコミットメッセージ・リポジトリ履歴に基づく正確な CHANGELOG 生成を支援します。