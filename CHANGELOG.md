# CHANGELOG

すべての日付は ISO 形式（YYYY-MM-DD）。このファイルは Keep a Changelog のフォーマットに準拠しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-20

### Added
- 初回リリース: KabuSys 日本株自動売買システムの基盤機能群を追加。
- 起動スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite DB を使用して本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成（Mock/実ブローカーに対応）。
    - ExecutionEngine をスレッドで起動し、data/stop_requested.flag の検知で安全に停止可能。
    - PID ファイル（data/execution.pid）をサポート。
    - RiskManager 用の既定設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を組み立て。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番 sqlite_path を使用して起動（監視テーブル初期化処理を実行）。
    - stop フラグの検知、例外発生時のログ出力、KeyboardInterrupt のハンドリングを実装。
    - 起動時にプロセス優先度を high に設定。

- 設定／環境管理
  - config: 環境変数読み込み・設定取得モジュールを追加。
    - プロジェクトルート自動検出（.git / pyproject.toml を基準）により .env/.env.local を自動読み込み（OS 環境変数を保護）。
    - export KEY=val 形式、クォート付き値（バックスラッシュエスケープ対応）、インラインコメントの取り扱いなど堅牢な .env パーサを実装。
    - Settings クラスで各種設定プロパティを提供（DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE のバリデーション、KABUSYS_ENV/LOG_LEVEL の検証等）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用）。

- 設定ユーティリティ
  - config_setup: 対話式 .env 作成ウィザードを追加。
    - 複数項目（J-Quants トークン、kabu API パスワード、DB パス、ログレベル等）に対応。
    - 既存 .env 読込・既存値の再利用、保存確認、テンプレートでの .env 書き込み機能を実装。
  - validate_config: 起動前設定検証 CLI を追加。
    - 必須環境変数・KABUSYS_ENV の妥当性・DB パスの親ディレクトリ存在確認・config/*.yaml の存在と YAML パース（PyYAML 存在時）・本番向けガードをチェック。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング／プロセス管理ユーティリティ
  - utils.logging_setup: 統一的なログ設定ユーティリティを追加。
    - コンソール（stdout）向け StreamHandler と 日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成失敗時のフォールバック（コンソールのみ）や既存ハンドラのクリア処理を実装。
  - utils.process_priority: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定を追加。
    - Windows の優先度クラス、POSIX の nice 値に対応。実行権限不足時は警告でスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順・同点時 tie-break に基づく候補選択。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（全スコアが 0 の場合は等配分にフォールバックして警告）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター別上限（max_sector_pct）に基づいて新規候補を除外するロジック。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームはフォールバックで 1.0。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数計算を実装。
    - 単元（lot_size）丸め、per-position 上限、aggregate cap（利用可能資金を超える際のスケールダウン）、cost_buffer を考慮した保守的見積り、残差分配ロジックを実装。

- リサーチ／ファクター計算（骨組み）
  - research.factor_research: Momentum 等ファクター計算モジュールの骨組みを追加（DuckDB を利用、prices_daily/raw_financials を参照する設計）。calc_momentum 等の実装枠を用意。

- ツール
  - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH（または --db）からデータを読み、稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を算出して PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ（ISO8601 文字列化）、閾値定数を組み込み。

### Changed
- なし（初回リリースのため該当なし）。

### Fixed
- なし（初回リリースのため該当なし）。

### Security
- なし

### Breaking Changes
- なし

---

開発者向けメモ:
- .env の扱いや起動時の挙動（monitoring が常に本番 sqlite を見る等）は意図的な設計であり、環境変数やファイルパスの設定に注意してください。
- 今後の予定としては research モジュールの完全実装、単体テストの追加、銘柄ごとの単元情報導入（lot_size の銘柄別対応）などを想定しています。