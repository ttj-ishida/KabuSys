# Keep a Changelog

すべての重要な変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

なお、このCHANGELOGはリポジトリ内のソースコードから実装内容を推測して生成しています（初回リリース相当）。

## [0.1.0] - 2026-03-16

### Added
- パッケージ初期リリース: kabusys 0.1.0
- パッケージのエントリポイントを追加
  - src/kabusys/__init__.py に __version__ = "0.1.0" と __all__ を定義。
- 環境設定管理モジュールを追加（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml を探索）。
  - .env のパース機能（コメント、export プレフィックス、クォート、エスケープ対応）を実装。
  - .env と .env.local の優先順位を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - Settings クラスでアプリ設定を取得するプロパティを提供（J-Quants トークン、kabu API 設定、Slack トークン/チャンネル、DB パス、環境モード、ログレベル判定など）。
  - 設定値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL の検証）および必須環境変数未設定時のエラーを実装。
- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーを取得する関数を提供。
  - レート制限制御（120 req/min）を満たす固定間隔スロットリング実装（RateLimiter）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx 対応）。
  - 401 受信時の自動トークンリフレッシュ（1 回）とトークンキャッシュの実装。ページネーション間でトークン共有。
  - ページネーション対応の fetch_* 系関数（pagination_key 処理）。
  - DuckDB へ冪等に保存する save_* 関数（INSERT ... ON CONFLICT DO UPDATE）を実装。
  - データ取得時の fetched_at を UTC ISO8601 形式で記録（Look-ahead Bias 対策）。
  - 型変換ユーティリティ（_to_float, _to_int）を追加（安全な変換・空値処理・小数検査）。
- DuckDB スキーマ定義・初期化モジュールを追加（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の多層データレイヤー向けテーブル定義を実装（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等多数）。
  - 制約（CHECK, PRIMARY KEY, FOREIGN KEY）と型を積極的に定義。
  - 使用頻度を考慮したインデックス群を定義。
  - init_schema(db_path) で親ディレクトリ自動作成・テーブル作成を行う初期化関数を提供。get_connection() も提供。
- ETL パイプラインを追加（src/kabusys/data/pipeline.py）
  - 差分更新（最終取得日からの差分計算）・バックフィル（デフォルト backfill_days=3）・カレンダー先読み（デフォルト 90 日）を備えた ETL ジョブを実装。
  - run_prices_etl / run_financials_etl / run_calendar_etl の個別ジョブと、日次統合 run_daily_etl を提供。
  - 各ステップは独立して例外処理され、1 ステップ失敗でも他ステップを継続する（Fail-Fast ではない運用を選択）。
  - ETLResult データクラスを追加し、取得件数・保存件数・品質問題・エラー一覧を集約・シリアライズ可能に。
  - market_calendar を先に取得して営業日に調整する _adjust_to_trading_day ロジックを実装。
  - id_token を注入可能にすることでテスト容易性を確保。
- 監査ログ（トレーサビリティ）モジュールを追加（src/kabusys/data/audit.py）
  - 戦略→シグナル→発注要求→証券会社受付→約定 までを UUID で連鎖してトレースするテーブル群を実装（signal_events, order_requests, executions）。
  - 冪等キー（order_request_id, broker_execution_id）・ステータス遷移・created_at/updated_at を備えた設計。
  - init_audit_schema(conn) / init_audit_db(db_path) による初期化関数を提供。すべての TIMESTAMP を UTC に固定（SET TimeZone='UTC'）。
  - 監査用のインデックスを多数定義（status 検索や ID 紐付け等）。
- データ品質チェックモジュールを追加（src/kabusys/data/quality.py）
  - 欠損データ検出（OHLC 欠損検出）、スパイク検出（前日比 > 閾値、デフォルト 50%）、重複チェック、日付不整合検出などのチェックを実装。
  - QualityIssue データクラスで問題を集約（チェック名、テーブル、重大度、サンプル行等）。
  - DuckDB 上の SQL を用いた効率的判定、Fail-Fast ではなく全件収集する設計。
  - check_missing_data(), check_spike() 等を実装。pipeline.run_daily_etl と組み合わせて品質チェックを実行可能。
- モジュール階層（data, strategy, execution, monitoring）のパッケージ初期化ファイルを整備（__init__.py）。

### Changed
- 初期リリースのため該当なし。

### Fixed
- 初期リリースのため該当なし。

### Security
- 初期リリースのため該当なし。

Notes（設計上の重要ポイント）
- J-Quants クライアントは API レート制限とリトライ、トークンリフレッシュを考慮して実装されており、実運用での安定性を重視しています。
- DuckDB スキーマは冪等性（ON CONFLICT）と整合性制約を重視して設計されており、監査ログは削除しない前提の設計（FK は ON DELETE RESTRICT）です。
- すべてのタイムスタンプは UTC を採用する方針が明示されています（監査モジュール等で SET TimeZone='UTC' を設定）。
- ETL は差分更新＋短いバックフィル（デフォルト 3 日）により API 後出し修正を吸収する方針です。

今後の予定（想定）
- strategy / execution 層の詳細実装（発注ドライバ、ポジション管理、リスク管理）
- 監視（monitoring）や Slack 通知等の運用機能追加
- 単体テスト / 統合テストの整備と CI 設定
- ドキュメント (DataSchema.md, DataPlatform.md 等) の整備と公開

---