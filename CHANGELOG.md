# CHANGELOG

このプロジェクトは Keep a Changelog 準拠で変更履歴を記載します。  
フォーマット: https://keepachangelog.com/（日本語訳に準拠）

すべてのリリースはセマンティックバージョニングに従います。

## [Unreleased]
（現在の開発中の変更点はここに記載してください）

---

## [0.1.0] - 2026-04-19
初期リリース。日本株自動売買システム「KabuSys」の基本機能を実装。

### Added
- 基本パッケージ
  - kabusys パッケージを追加。__version__ を 0.1.0 に設定。
- 設定管理
  - robust な .env 読み込み機構を実装（kabusys.config）。
    - .git または pyproject.toml を基準にプロジェクトルートを自動検出して .env/.env.local をロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。
    - export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いなどに対応したパーサ実装。
    - 環境変数上書き制御（override / protected 機能）。
  - Settings クラスを導入し、環境変数から各種設定をプロパティとして取得可能に。
    - J-Quants / kabu API / LINE / DB パス / モニタ閾値 / 実行環境（development/paper_trading/live）などを提供。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等の paper_trading 用設定をサポート。
- 設定関連 CLI
  - 環境設定ウィザード: python -m kabusys.config_setup
    - 対話式で .env を初期作成・更新するウィザードを提供。
  - 設定検証ツール: python -m kabusys.validate_config
    - 必須環境変数や config/*.yaml の存在・パース検証を実行。--strict フラグで警告をエラー扱いに可能。
    - PyYAML 未インストール時は YAML 検証をスキップして警告を出力。
- 実行用スクリプト
  - 実行エンジン起動スクリプト: src/kabusys/run_execution.py
    - プロセス優先度を high に設定して実行。
    - paper_trading 環境では MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db）に分離して記録。
    - ExecutionEngine の起動／スレッド管理、停止フラグ（data/stop_requested.flag）検知のループを実装。
  - 監視ループ起動スクリプト: src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番 sqlite_path を使用して監視テーブルを初期化。
- ロギング / 実行ユーティリティ
  - 統一ログ設定ユーティリティ（kabusys.utils.logging_setup）
    - stdout への StreamHandler と日次ローテーションする TimedRotatingFileHandler（デフォルト logs/<app_name>.log）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップし、コンソール出力のみで継続。
    - LOG_LEVEL/LOG_DIR の解決順を明確化。
  - プロセス優先度・CPU affinity ユーティリティ（kabusys.utils.process_priority）
    - Windows / POSIX（Linux/macOS/FreeBSD）に対応した優先度設定（high/normal/low）と CPU affinity 設定を提供。
    - 権限不足や未対応 OS に対して安全に警告を出力してスキップする実装。
- ポートフォリオ構築（純粋関数）
  - portfolio.portfolio_builder
    - 候補選定 select_candidates、等配分 calc_equal_weights、スコア加重 calc_score_weights を実装。スコアが全て 0 の場合は等分配へフォールバック。
  - portfolio.risk_adjustment
    - セクター集中制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier を実装。
    - 未知のレジームは警告を出して 1.0 にフォールバック、"unknown" セクターはセクター上限の対象外などの挙動を定義。
  - portfolio.position_sizing
    - position sizing ロジック（risk_based / equal / score）を実装。単元株（lot_size）丸め、ポジション上限、aggregate cap（available_cash に合わせたスケールダウン）を考慮。
    - cost_buffer（スリッページ/手数料見積）対応、残差処理により lot 単位で追加配分する処理を実装。
- Research モジュール（骨格）
  - research.factor_research にてモメンタム等のファクター計算方針と定数を導入。DuckDB を用いた prices_daily / raw_financials 参照形式を想定（実装の一部がファイル末尾で継続）。
- Paper Trading 検証ツール
  - tools.paper_verification_report を実装。
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から各種指標を集計してレポートを出力。
    - 判定基準（閾値）を定義: 稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。
    - system_status / trade_logs / risk_logs テーブルを参照し、集計・P95 計算・Pass/Fail 判定を行う。
- 監視 DB 初期化ユーティリティ
  - monitoring.monitoring_db の init_monitoring_db を run スクリプトから利用して監視テーブルの存在を保証（冪等）。
- その他ユーティリティ
  - tools パッケージの初期化と各種 __all__ エクスポートを整備。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Notes / Implementation details
- 実行スクリプトは停止フラグファイル（data/stop_requested.flag）を用いた外部からの停止制御をサポート。
- run_execution/run_monitoring 両スクリプトは起動時にプロセス優先度を設定することで実行環境での安定性を高める設計。
- 設定検証ツールは本番環境（KABUSYS_ENV=live）に関連する追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険設定）をチェックして警告を出力。
- .env の自動読み込みは OS 環境変数を上書きしない既定動作を採用。必要に応じて .env.local で上書き可能。

---

（今後のリリースではバグ修正、テスト追加、factor_research の完了、Broker クライアント抽象化の強化、単体テスト・統合テストの追加などを追記してください。）