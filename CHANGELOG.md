# CHANGELOG

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

### Added
- 全体
  - パッケージ初期機能群を追加。自動売買システムのコアユーティリティ、実行・監視スクリプト、設定管理、ポートフォリオ構築、検証ツールなどを含む。
- CLI / 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度を "high" に設定して起動し、停止フラグ（data/stop_requested.flag）検知時に安全に停止する。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の専用 SQLite DB（data/paper_trading.db）にデータを分離する。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する仕様。
  - kabusys.validate_config: .env および config/*.yaml の起動前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや YAML ファイルの存在確認、--strict オプションで警告を FAIL 扱いにできる。
  - kabusys.config_setup: .env を対話式に作成・更新するウィザードを追加。既存 .env の読み込み、シークレット入力マスク、保存前の確認などを実装。
  - kabusys.tools.paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計し PASS/FAIL 判定を行う。コマンドラインで期間指定 (--from / --to)・DB 指定 (--db) が可能。
- 設定管理
  - kabusys.config: .env 自動読み込み（プロジェクトルート検出）、厳密な .env パース機能（クォート・エスケープ・コメント処理対応）、環境設定を表現する Settings クラスを追加。PAPER_FILL_MODE のバリデーションや env/log level の妥当性チェックなどを実装。
  - 自動ロードの挙動: OS 環境変数を保護しつつ .env / .env.local を適切な優先度でロード。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
- ロギング / プロセス制御
  - kabusys.utils.logging_setup: 統一ロギングセットアップを追加。console (stdout) と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続するフォールバックを実装。
  - kabusys.utils.process_priority: クロスプラットフォームでのプロセス優先度設定と CPU affinity 設定ユーティリティを追加。Windows と POSIX 系を吸収し、権限不足等の失敗は警告ログでスキップ。
- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio.portfolio_builder: 候補選定 select_candidates（スコア降順、タイブレーク）、等金額配分 calc_equal_weights、スコア重み配分 calc_score_weights（全スコア 0 の場合のフォールバック）を追加。
  - kabusys.portfolio.risk_adjustment: セクター集中制限 apply_sector_cap（当日売却予定を除外可能）、市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear 対応、未知レジームはフォールバック）を追加。
  - kabusys.portfolio.position_sizing: 複数の配分方式（risk_based / equal / score）に対応した株数計算 calc_position_sizes を追加。単元株丸め、1 銘柄上限・aggregate cap スケーリング（cost_buffer を考慮）、不足価格データ時のスキップロジックなどを実装。
- リサーチ
  - kabusys.research.factor_research: ファクター計算モジュールの骨格を追加（モメンタム/MA/ATR/流動性等の定数、calc_momentum 開始）。DuckDB を利用した prices_daily/raw_financials ベースでの計算を想定。

### Changed
- DB の取り扱い
  - 監視(run_monitoring)は KABUSYS_ENV にかかわらず常に本番用 sqlite_path を使用するよう仕様を明示（監視データを本番 DB に集約する意図）。
- ログ
  - StreamHandler を stdout に向ける方針を採用（cron/task scheduler との統合を考慮）。既存ハンドラは再設定時に flush/close してから削除するように変更。

### Fixed
- 環境変数パーサ
  - .env のパースにおけるクォートとバックスラッシュエスケープ、インラインコメントの扱いを改善。export キーワード付き行のサポートを追加。
- 実行停止ハンドリング
  - run_execution/run_monitoring で stop flag を検知して安全にシャットダウンする処理を追加。エンジンは別スレッドで動作し、停止フラグ検知後 engine.stop() を呼ぶ。

---

## [0.1.0] - 2026-04-19

初回公開リリース。上記 Unreleased の内容を含む初版リリース。

### Added
- パッケージメタデータ: __version__ = "0.1.0"
- 基本的なモジュール群（config, config_setup, validate_config, utils.logging_setup, utils.process_priority, portfolio, portfolio の各サブモジュール, execution/run_execution, monitoring/run_monitoring, tools.paper_verification_report, research.factor_research の初期実装）
- ExecutionEngine 起動フロー、監視ポーリングループ、Paper Trading 用検証レポートなど運用に必要な CLI/ツールを収録。

### Notes
- config/.env の取り扱いに際しては .env を絶対に Git にコミットしないことを README 等で明示することが推奨されます（config_setup にも注意書きを出力）。
- factor_research の一部（calc_momentum 以降の実装）は骨格が含まれるが、完全実装を要する箇所があります。実運用前に duckdb 給源のテーブル構成と計算ロジックを確認してください。

---

参考: 主要ファイル
- src/kabusys/config.py
- src/kabusys/config_setup.py
- src/kabusys/validate_config.py
- src/kabusys/run_execution.py
- src/kabusys/run_monitoring.py
- src/kabusys/utils/logging_setup.py
- src/kabusys/utils/process_priority.py
- src/kabusys/portfolio/*
- src/kabusys/tools/paper_verification_report.py
- src/kabusys/research/factor_research.py

（この CHANGELOG は提供されたコードベースから推測して生成しています。実際の変更履歴・コミットログと差異がある場合は、適宜調整してください。）