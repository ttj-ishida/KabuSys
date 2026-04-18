# Changelog

すべての重要な変更点はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  
  
注: 以下は与えられたコードベースの内容から推測して作成した変更履歴です。

## [Unreleased]

### Added
- CI / リリース前の検証ツール群を追加（設定検証・設定ウィザード・各種実行スクリプトを含む）。
- 実行スクリプト:
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じて paper_trading 用の専用 SQLite DB を使用し、MockBrokerClient の切替を行う。停止フラグの検出および PID ファイル管理、スレッド実行・安全停止処理を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能、停止フラグ検出機能を実装。
- 設定関連:
  - config.py: .env 自動読み込み機能（プロジェクトルート検出）、堅牢な .env パーサ（クォート、エスケープ、コメント解析対応）、環境設定を提供する Settings クラスを追加。
  - config_setup.py: 対話式 .env ウィザードを追加（シークレットマスク、既存 .env の読み込み・上書き、保存機能）。
  - validate_config.py: CLI による設定検証ツールを追加（必須環境変数チェック、KABUSYS_ENV 検証、DB パス確認、config/*.yaml 存在・パースチェック、--strict オプション）。
- ロギング・プロセス制御:
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。stdout 出力と日次ローテートファイル出力を設定、LOG_DIR/LOG_LEVEL に対応、ディレクトリ作成失敗時のフォールバックを実装。
  - utils/process_priority.py: プラットフォーム差を吸収したプロセス優先度および CPU affinity ユーティリティを追加（Windows / POSIX 対応、psutil ベース、権限不足時は警告してスキップ）。
- ポートフォリオ構築:
  - portfolio/portfolio_builder.py: 候補選定（スコア降順、同点時 signal_rank によるタイブレーク）、等金額／スコア加重配分ロジックを実装。スコア全0 の場合のフォールバック警告あり。
  - portfolio/risk_adjustment.py: セクター集中上限（apply_sector_cap）および市場レジームに基づく資金乗数（calc_regime_multiplier）を実装。未知レジーム時のフォールバック挙動を明示。
  - portfolio/position_sizing.py: 発注株数計算ロジックを実装（risk_based / equal / score）。単元株（lot_size）丸め、単銘柄上限・総投資上限（aggregate cap）スケーリング、cost_buffer による保守見積り、残差配分アルゴリズムを実装。
- ツール:
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツールを追加。稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）を算出し PASS/FAIL 判定を出力。閾値は定数化。
- 研究用:
  - research/factor_research.py: ファクター計算モジュール（Momentum / Value / Volatility / Liquidity）骨格を追加。DuckDB 接続経由で prices_daily / raw_financials を参照する設計。モメンタム計算関数の実装を開始（途中までの実装あり）。

### Changed
- 既存ライブラリ利用方針を明確化:
  - DuckDB を分析用 DB として統一的に利用（Execution/Monitoring/Research が duckdb_conn を受け取る）。
  - SQLite を監視・注文履歴用に利用。paper_trading 時は専用 SQLite（data/paper_trading.db）に分離。
- ロギングの出力先とローテーション方針を明確化（stdout を標準出力として使用、ファイルは日次ローテート・30日保持）。

### Fixed
- .env パーサの解釈を強化し、クォート内のエスケープや行内コメントの誤判定を修正（想定される入力形式に対して安全に読み込めるように改善）。
- process_priority のプラットフォーム差異による例外ハンドリングを追加（権限不足や未対応 OS の場合にワーニングでスキップ）。

## [0.1.0] - 2026-04-18

初回公開相当のまとめ（コードベースに含まれる主要機能を列挙）。

### Added
- 基本的な自動売買フレームワークを実装:
  - ExecutionEngine / OrderManager / OrderRepository / RiskManager / Reconciler（呼び出しの組み立ては run_execution.py に反映）。
  - SystemMonitor と監視ループ起動スクリプト（run_monitoring.py）。
- 設定関連ユーティリティ:
  - Settings クラスで環境変数を一元管理。多くの環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_LEVEL 等）をサポート。
  - .env 自動読み込み（.env / .env.local の優先度を実装）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプション。
- ポートフォリオ構築ロジック:
  - 候補選定・重み計算・ポジションサイズ決定（リスクベース・等分配等）。
  - セクターキャップおよびレジーム乗数の実装。
- 運用支援ツール:
  - 設定ウィザード CLI（config_setup.py）。
  - 設定検証 CLI（validate_config.py）。
  - Paper Trading 検証レポート出力ツール（tools/paper_verification_report.py）。
- ログ設定・プロセス制御ユーティリティ（utils.logging_setup, utils.process_priority）。

### Changed
- パッケージメタ:
  - パッケージバージョンを __version__ = "0.1.0" として設定。

### Removed
- （無し）

### Security
- 環境変数のシークレットは UI でマスク表示（config_setup.py）。ただし .env ファイル自体はローカル保存されるため、Git へコミットしない旨の注意を明記。

---

注記:
- research/factor_research.py の calc_momentum 実装は途中で切れているため、完全な実装は未完（追加実装・テストが必要）。
- 実稼働（KABUSYS_ENV=live）時は設定の慎重な確認が必要（validate_config の WARN が該当）。KILL_FLAG_CLEAR_ON_START や LINE 通知設定は本番運用での重要ポイント。