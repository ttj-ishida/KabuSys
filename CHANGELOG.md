# CHANGELOG

すべての注目すべき変更を一元管理します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-03-16

初回公開リリース。日本株自動売買システム "KabuSys" の基盤機能を実装します。

### Added
- パッケージ基盤
  - パッケージルート定義とバージョン: kabusys v0.1.0 を追加（src/kabusys/__init__.py）。
  - モジュール分割: data, strategy, execution, monitoring 用のパッケージ構成を用意。

- 環境設定・読み込み機能（src/kabusys/config.py）
  - .env ファイルと環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサーの強化:
    - export KEY=val フォーマット対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - インラインコメントの扱い（スペース/タブに依存するコメント認識）。
  - Settings クラスで型付きプロパティを提供（J-Quants/カブAPI/Slack/DBパス/環境切替/ログレベル等）。
  - 必須環境変数未設定時は明示的な ValueError を発生させる _require 関数。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 株価日足、財務（四半期 BS/PL）、JPX マーケットカレンダー取得エンドポイントを実装。
  - レート制限の厳守: 固定間隔スロットリングで 120 req/min を実現する RateLimiter を実装。
  - 再試行と指数バックオフ: ネットワーク系エラーや 408/429/5xx に対して最大3回のリトライ（Retry-After ヘッダ優先）。
  - 401 が返った場合はリフレッシュトークンから自動で id_token を再取得して 1 回リトライ（無限再帰防止）。
  - ページネーション対応（pagination_key）をサポートし、ページ間で id_token を共有するキャッシュを実装。
  - 取得時刻（fetched_at）を UTC ISO8601 形式で記録（Look-ahead Bias 対策）。
  - DuckDB への保存関数は冪等に実行（INSERT ... ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar を提供。
  - 保存前に主キー欠損行をスキップし、スキップ件数をログ出力。

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - 3層データモデルに対応するテーブル定義を提供:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - データ品質や検索を考慮したインデックス定義を多数追加。
  - init_schema(db_path) で DB ファイルの親ディレクトリ自動作成と DDL 実行（冪等）。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 日次 ETL 処理の統合エントリ run_daily_etl を実装:
    - 市場カレンダー取得 → 株価差分取得（backfill 対応）→ 財務差分取得 → 品質チェック の順で実行。
  - 差分更新ロジック: DB の最終取得日から backfill_days（日）分さかのぼって再取得するデフォルト動作（backfill_days default = 3）。
  - 市場カレンダーは lookahead（デフォルト 90 日）で先読み。
  - ETLResult dataclass により取得件数、保存件数、品質問題、エラーの集約を提供。
  - 各ステップは独立して例外処理され、あるステップが失敗しても他ステップは継続（全件収集指向）。

- 監査ログ（audit）機能（src/kabusys/data/audit.py）
  - シグナル生成・発注要求・約定を追跡する監査用スキーマを追加:
    - signal_events, order_requests, executions テーブル。
  - 冪等キー（order_request_id）、broker_execution_id のユニーク性、制約・チェック・FK を設計。
  - UTC タイムゾーン強制（SET TimeZone='UTC'）でタイムスタンプ記録。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供。

- データ品質チェック（src/kabusys/data/quality.py）
  - QualityIssue dataclass を導入し、各チェックの結果を構造化して返却。
  - 実装済みチェック:
    - 欠損データ検出（raw_prices の OHLC 欄）
    - 異常値（スパイク）検出：前日比の絶対変化率が閾値（デフォルト 50%）超過
    - （将来的に）重複・日付不整合チェックを想定した設計
  - 各チェックは全件を収集して報告する方式（Fail-Fast ではない）。
  - DuckDB SQL による効率的な実装とパラメータバインドを採用。

- ユーティリティ
  - 安全な型変換ヘルパー: _to_float / _to_int の実装（空値や不正値の扱いを定義）。
  - パイプライン、クライアント共通でのログ出力と警告メッセージの整備。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 認証トークン処理での自動リフレッシュは安全対策（allow_refresh フラグ）を持ち、無限再帰を回避。
- .env の読み込みは OS 環境変数を保護する仕組み（protected set）を採用。

Notes / 備考
- DuckDB への INSERT 文は ON CONFLICT による更新を行うため、同一主キーでの重複挿入に対して冪等性が確保されています。
- ETL の品質チェックは発見した問題を ETLResult.quality_issues に格納します。呼び出し側で重大度に応じた運用判断（停止・アラート等）を行ってください。
- 今後の予定: ニュース取得 / シグナル生成の戦略実装、発注連携（kabuステーション等）と監視・通知機能の追加。

もっと詳しい変更点（関数名や挙動）を含めた差分が必要であれば、対象ファイル・関数を指定してください。