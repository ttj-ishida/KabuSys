# Changelog

すべての注目すべき変更は Keep a Changelog の形式に従って記載します。  
このファイルはコードベースから推測した変更点をまとめたものであり、実際のコミット履歴ではありません。

全般的な方針:
- 重大な追加は "Added" に、既存挙動の改善は "Changed" に、バグ回避や堅牢化は "Fixed" に分類しています。

## [Unreleased]

### Added
- 新規モジュール群を追加
  - 実行・監視の起動スクリプト:
    - run_execution.py: ExecutionEngine を起動する CLI 用スクリプトを追加。paper_trading 環境向けに MockBrokerClient と専用 SQLite DB を使用する分離を実装。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番用 sqlite_path を使用する仕様。
  - 環境設定関連:
    - config_setup.py: 対話式ウィザードで .env を初期作成 / 更新する CLI を追加。
    - validate_config.py: .env および config/*.yaml の起動前検証 CLI を追加（--strict オプションで警告を失敗扱いに可能）。
    - config.py: 環境変数読み込み・管理モジュールを追加。プロジェクトルート自動検出、.env / .env.local の自動読み込み、各種設定プロパティ（DB パス、KABUSYS_ENV 判定、paper_trading 切替等）を提供。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - ロギング・プロセス管理ユーティリティ:
    - utils/logging_setup.py: 標準化されたログ初期化ユーティリティ（stdout ストリーム + 日次ローテートファイル出力）。ログディレクトリ作成失敗時はファイル出力をスキップして安全にフォールバック。
    - utils/process_priority.py: Windows / POSIX に対応したプロセス優先度設定および CPU affinity 設定ユーティリティを追加。
  - ポートフォリオ構築（純粋関数群）:
    - portfolio/portfolio_builder.py: 候補選定(select_candidates)、等配分(calc_equal_weights)、スコア加重(calc_score_weights) を追加。
    - portfolio/risk_adjustment.py: セクター集中制限の apply_sector_cap、レジーム乗数 calc_regime_multiplier を追加。
    - portfolio/position_sizing.py: 発注株数算出ロジック calc_position_sizes を追加（risk_based / equal / score の割当方式、lot_size・コストバッファ・aggregate cap スケーリング等を実装）。
    - portfolio/__init__.py: 上記関数群をエクスポートするパッケージ初期化を追加。
  - 解析・検証ツール:
    - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ指標（平均/最大/P95）等を出力し PASS/FAIL 判定を行う。
  - 研究用モジュール（未完の実装を含む）:
    - research/factor_research.py: momentum 等のファクター計算モジュールの骨子を追加（DuckDB 接続を受け取り prices_daily 等のテーブルを参照する設計）。

### Changed
- 起動スクリプトの設計
  - run_execution と run_monitoring の両スクリプトは起動直後にプロセス優先度を "high" に設定するように統一。
  - run_execution は paper_trading 環境では専用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用するようにして、本番データと完全に分離。
  - run_monitoring は監視用 DB 初期化（init_monitoring_db）を行い、環境にかかわらず監視用 sqlite_path を使用する方針を明確化。
- 設定ローディングの優先度
  - config.py にて OS 環境変数 > .env.local > .env の優先順位を明示的に実装。
  - .env 読み込みは OS 環境変数を保護する仕組み（protected set）を採用し、上書き制御をサポート。
- ログ設定
  - logging_setup.py で stdout を使う設計（cron 等で stdout/stderr を一本化する運用を考慮）。日次ローテーションおよび 30 日分保持をデフォルトに設定。
- リスク管理パラメータ
  - run_execution 内で RiskManager のデフォルト設定値を導入（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker, max_drawdown など）および初期ポートフォリオ値に broker.get_available_cash() を使用する仕様に。

### Fixed / Robustness
- 環境変数パースの堅牢化
  - config._parse_env_line にて export プレフィックス、クォート文字のエスケープ、インラインコメントの扱いなどを考慮したパーサを実装。無効行はスキップ。
- ポーリング間隔の安全化
  - run_monitoring._get_poll_interval にて MONITOR_POLL_INTERVAL の不正値を検出し、0 以下や非整数はデフォルトへフォールバックして警告を出力するように。
- DB 初期化の冪等性
  - init_monitoring_db を起動時に呼ぶことで監視テーブルの存在を保証（既に存在しても問題なく動作）。
- process_priority / CPU affinity の失敗に対するフォールバックを追加
  - アクセス権限不足・未対応プラットフォーム時は警告ログを出力して処理を継続。
- position_sizing のスケーリング・端数処理の改善
  - aggregate cap 超過時のスケールダウン処理と残余キャッシュによる lot_size 単位での再配分ロジックを実装し、秩序だった端数処理を行うように。
- paper_verification_report の統計計算の堅牢化
  - 欠損テーブルやデータ不足時に sqlite3.OperationalError をハンドルして空結果にフォールバックする実装を追加。P95 計測・表示ロジックを実装。

---

## [0.1.0] - 2026-04-20

初期リリース想定のスナップショット。上記の主要機能を含む最初の公開バージョン。

### Added
- プロジェクトメタ
  - パッケージバージョンを __version__ = "0.1.0" に設定。
- コア機能
  - 設定管理（config.py）: 自動 .env ロード、各種設定プロパティ、環境判定ユーティリティ。
  - 環境設定ウィザード（config_setup.py）: 対話式で .env を生成・更新。
  - 設定検証 CLI（validate_config.py）: 必須環境変数や config/*.yaml の存在・パース検証。
  - 実行エンジン起動スクリプト（run_execution.py）: ExecutionEngine 起動フロー、paper_trading 分離、スレッド実行と停止フラグ監視。
  - 監視ループ起動スクリプト（run_monitoring.py）: SystemMonitor の定期実行、停止フラグ検知、ポーリング間隔設定。
  - ロギングユーティリティ（utils/logging_setup.py）: stdout と日次ローテートファイルの統一設定。
  - プロセス優先度ユーティリティ（utils/process_priority.py）: Windows / POSIX 対応の優先度設定・CPU affinity。
  - ポートフォリオ構築ライブラリ（portfolio/*）: 候補選定、重み付け、セクター制限、レジーム乗数、発注株数算出。
  - Paper Trading 検証ツール（tools/paper_verification_report.py）: 指標算出と PASS/FAIL 判定。
  - 研究用ファクター計算の骨子（research/factor_research.py）。

### Changed
- 起動・運用の安全策として、起動時にプロセス優先度を高く設定する手順を全スクリプトで共通化。
- paper_trading と本番 DB を明確に分離する設計方針を導入。

### Fixed
- .env パーサの強化により、クォート・エスケープ・コメント処理の誤解釈を回避。
- ログディレクトリ作成失敗時の安全なフォールバック処理を追加。

---

注記:
- 本 CHANGELOG はコードの構造・コメント・定数・docstring から推測して作成しています。実際のコミット単位の変更履歴や詳細な差分は Git の履歴をご参照ください。