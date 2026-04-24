# Changelog

すべての notable な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に準拠します。  
リリースバージョンはパッケージの __version__（src/kabusys/__init__.py）を参照してください。

## [Unreleased]

## [0.1.0] - 2026-04-24
初期リリース。自動売買システム「KabuSys」のコアユーティリティ、実行/監視スクリプト、設定ツール、ポートフォリオ構築ロジック、Paper Trading 検証ツールなどを追加。

### Added
- 全体
  - パッケージ初期バージョンを追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。
  - DuckDB/SQLite を利用する分析・監視基盤を想定したデータパス設定を導入（Settings.duckdb_path / Settings.sqlite_path / Settings.paper_sqlite_path）。
  - 環境変数自動読み込み機能を実装（.env, .env.local の優先順位処理。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応）。
  - .env パーサーの実装（クォート、エスケープ、`export` プレフィックス、インラインコメント処理をサポート）。

- 実行 / 監視スクリプト
  - run_execution: 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 専用 SQLite（data/paper_trading.db 等）を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - エンジンは別スレッドで実行され、data/stop_requested.flag による安全停止をサポート。起動 PID を data/execution.pid に記録する想定。
    - RiskManager のデフォルト設定を明示（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - run_monitoring: システム監視ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、負の値など不正値はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して安定的に監視データを蓄積。
    - stop フラグ（data/stop_requested.flag）検知でループを終了。
    - 各ポーリング時に SystemMonitor.check_once() を呼び、例外はログに捕捉して次回ポーリングへ継続。

- 設定関連 CLI / ユーティリティ
  - Settings クラスによる環境設定管理を追加（src/kabusys/config.py）。
    - 必須環境変数取得ヘルパ（_require）や env/log level のバリデーション、paper_trading 用設定を含む。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）を実装。
  - config_setup: 対話式 .env 作成ウィザードを追加（src/kabusys/config_setup.py）。
    - 主要設定項目の対話入力、既存 .env の読み込み、.env ファイル生成ロジックを提供。
  - validate_config: 起動前の設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数の未設定チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML がある場合）。
    - --strict オプションで警告をエラー扱いにする機能を追加。

- ロギング / プロセス制御ユーティリティ
  - setup_logging: 統一的なロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決、ログディレクトリ作成失敗時のフォールバックを実装。
    - 既存ハンドラのクリア処理（多重登録防止）。
  - process_priority: プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX を抽象化して set_process_priority("high"|"normal"|"low") を提供。
    - set_cpu_affinity により最初の N コアに固定可能。権限不足や未対応環境では警告を出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder: 銘柄選定・等重/スコア加重重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
    - スコアが全て 0 の場合は等金額配分へフォールバック（警告ログ）。
  - risk_adjustment: セクター集中制限（apply_sector_cap）・レジーム乗数計算（calc_regime_multiplier）。
    - apply_sector_cap は既存保有のセクター比率を計算し、過剰セクターの新規候補を除外。unknown セクターは制限適用外。
    - calc_regime_multiplier は "bull"/"neutral"/"bear" に対応、未知レジームは警告の上フォールバック値 1.0。
  - position_sizing: 発注株数計算（calc_position_sizes）。
    - allocation_method に "risk_based"/"equal"/"score" をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）に基づくスケーリング、cost_buffer（手数料・スリッページ見積り）を考慮。
    - スケールダウン時は fractional remainder に基づく追加配分ロジックを実装して安定性と再現性を確保。

- Paper Trading / 検証ツール
  - tools/paper_verification_report: Paper Trading 用レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）を集計してレポート出力。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 <= 200 ms）に基づく PASS/FAIL 判定を出力。
    - --from / --to / --db オプションで期間・DBパス指定が可能。DB が存在しない場合のエラーメッセージを用意。

- 監視 DB 初期化フック
  - monitoring.monitoring_db.init_monitoring_db を呼び出して監視用テーブルの存在を保証する処理を run_monitoring と run_execution から呼び出す（冪等化）。

### Changed
- なし（初期リリースのため既存コードの変更履歴はなし）。

### Fixed
- なし（初期リリース）。

### Deprecated
- なし。

### Removed
- なし。

### Security
- 環境変数を直接ファイルに書き込む .env ファイルについて、config_setup の README コメントで「.env は絶対に Git にコミットしないこと」を明記。

---

注記 / 実装上の留意点（コードから推測）
- run_monitoring はモニタリングに常に本番 sqlite_path を使うため、監視データは環境に依存せず一元管理される設計になっています。意図的な動作のため運用時は注意してください。
- run_execution は paper_trading 環境向けに DB を分離していますが、BrokerClientFactory の実装次第でさらに Mock 実行が制御されます。
- .env パーサーは多くのケース（シングル/ダブルクォート、バックスラッシュエスケープ、export プレフィックス、コメント）に対応していますが、極端な入力ケースは未網羅の可能性があります。
- research/factor_research モジュールはファクター計算の骨格（モメンタム等）を含みますが、一部実装が未完（ファイル末尾で切れている）です。今後のリリースで完成が期待されます。
- プロセス優先度・CPU affinity の操作は OS 権限に依存するため、権限不足時は警告で済ます設計になっています。

もし CHANGELOG の粒度（より詳細なコミット単位、日付の調整、将来の Unreleased エントリ追加など）について希望があれば教えてください。