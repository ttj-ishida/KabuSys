# Changelog

All notable changes to this project will be documented in this file.

フォーマットは「Keep a Changelog」に準拠しています。  
各項目はリリース単位で整理してあります。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-20

初回公開リリース。以下の主要コンポーネントと機能を実装しています。

### Added
- 基本パッケージ情報
  - パッケージ名: KabuSys、バージョン 0.1.0（src/kabusys/__init__.py）。
- 設定管理
  - 環境変数／.env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。（src/kabusys/config.py）
  - .env のパース機能（export 句、クォート、エスケープ、インラインコメント扱い等に対応）。必要環境変数未設定時に例外を出すヘルパ（_require）。各種設定プロパティ（DBパス、APIトークン、Paper Trading 設定など）を提供。
- 環境設定ウィザード CLI
  - 対話式ウィザードで .env を作成・更新するツールを実装（src/kabusys/config_setup.py）。既存値の読み込み、シークレットマスク、確認プロンプト、ファイル書き出しをサポート。
- 設定検証 CLI
  - .env と config/*.yaml の検証用 CLI を実装（src/kabusys/validate_config.py）。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、YAML パースチェック（PyYAML がある場合）、本番環境向けの追加ガードを提供。--strict オプションで警告を FAIL 扱いにできる。
- ロギングユーティリティ
  - 統一的なログ初期化関数を提供（setup_logging）。StreamHandler（stdout）と日次ローテーションする TimedRotatingFileHandler をルートロガーに設定し、ログディレクトリ自動作成と失敗時のフォールバックを行う。（src/kabusys/utils/logging_setup.py）
- プロセス優先度／CPU affinity ユーティリティ
  - Windows / POSIX を吸収する set_process_priority と set_cpu_affinity を実装。権限不足や未サポート環境は警告でスキップ。（src/kabusys/utils/process_priority.py）
- 実行系起動スクリプト
  - ExecutionEngine 起動用スクリプト（run_execution.py）を追加。
    - KABUSYS_ENV=paper_trading の場合は paper 用専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine の起動・停止処理、停止フラグ（data/stop_requested.flag）および実行 PID ファイル処理をサポート。
    - RiskManager のデフォルト設定（max_position_pct や max_drawdown 等）を提供。
- 監視系起動スクリプト
  - SystemMonitor ポーリングループ起動スクリプト（run_monitoring.py）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下の不正値はデフォルトにフォールバック。
    - 監視用 DB 初期化（init_monitoring_db）、duckdb 接続、停止フラグ検出、例外ハンドリングなどを実装。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
- ポートフォリオ構築モジュール（pure functions）
  - 候補選定、重み計算（等金額／スコア加重）を実装（portfolio_builder）。
    - スコアが全て 0 の場合は等金額にフォールバックして警告を出す。
  - セクター集中制限とレジーム乗数（apply_sector_cap, calc_regime_multiplier）を実装（risk_adjustment）。
    - セクター exposure 計算は現物価格（price_map）と既存保有から算出。unknown セクターは上限適用対象外。
    - レジーム乗数は bull/neutral/bear をサポート。未知レジームは 1.0 にフォールバックして警告。
  - 株数決定アルゴリズム（position_sizing）
    - allocation_method として "risk_based", "equal", "score" をサポート。
    - リスクベース方式ではポジションごとのリスク許容（risk_pct）とストップロス（stop_loss_pct）を用いて株数を計算。
    - 単元株（lot_size）で丸め、上限（max_position_pct）を考慮、aggregate cap を考慮したスケーリングおよび端数分配ロジックを実装。
    - cost_buffer（手数料・スリッページ見積り）を考慮してコスト見積りを保守的に行う。
- 研究・ファクター計算基盤
  - ファクター計算モジュールの骨子を実装（research/factor_research.py）。
    - Momentum、MA200乖離、ATR、出来高等の計算方針と定数を定義。DuckDB 経由で prices_daily / raw_financials を参照する設計。関数の記述は未完（以降の実装予定）。
- Paper Trading 検証ツール
  - Paper Trading の検証レポート生成スクリプト（tools/paper_verification_report.py）を実装。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）を集計し、PASS/FAIL 判定を行う。閾値を定義（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）。
    - 日付フィルタ、DB パス解決（引数・環境変数・デフォルト）をサポート。
- モニタリング DB 初期化ユーティリティへの参照（init_monitoring_db を複数箇所で呼び出し、監視テーブルの存在を保証）。
- 複数の CLI スクリプト（config_setup, validate_config, tools.paper_verification_report）および起動スクリプト（run_execution, run_monitoring）を package から直接実行可能に実装。

### Changed
- N/A（初回リリースのため変更履歴はなし）

### Fixed
- N/A（初回リリースのため修正履歴はなし）

### Security
- 環境変数のシークレット値取り扱いについて
  - config_setup の対話表示ではシークレット値をマスク表示（****）。.env は Git コミットしない旨を明記。

### Notes / Known limitations
- research/factor_research.py はファクター計算の骨組みまで記載されているものの、関数の一部（calc_momentum 等）の実装が途中で切れているため、完全なファクター計算は未完。
- apply_sector_cap の exposure 計算は price が 0 の場合に過小見積りとなる可能性がある旨の TODO コメントあり。将来的にフォールバック価格導入を検討。
- process priority / cpu affinity の設定は権限がない環境や未サポート OS ではスキップされる（警告ログのみ）。
- ログディレクトリ作成失敗時はファイルログをスキップしてコンソールのみで稼働する設計。
- Paper Trading 実行時は本番 DB と完全分離するように設計されているが、運用時の設定ミスによる DB 上書きに注意。

---

今後の予定（例）
- research/factor_research の完全実装（Momentum/Value/Volatility/Liquidity の詳細計算）
- ExecutionEngine / BrokerClient の実装詳細とユニットテスト追加
- モニタリング／アラート（LINE 通知等）の強化
- 単体テスト、CI 設定、ドキュメント整備

---
参考:
- この CHANGELOG はコード中のコメント・関数名・デフォルト値・CLI 実装などから推測して作成しています。実際のリリースノートとは差異がある場合があります。