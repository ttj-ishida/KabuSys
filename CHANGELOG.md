# Changelog

すべての変更は Keep a Changelog の慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/ より

## [Unreleased]

### Added
- run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ検出・例外時のロギング・SQLite / DuckDB 接続の初期化を含む。
- run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用のペーパートレード SQLite を使用し、MockBrokerClient を利用する挙動を想定。別スレッドでエンジンを実行し、停止フラグ / PID ファイル連携を行う。
- config.py: 環境変数読み込み・管理モジュールを追加。プロジェクトルート自動検出 (.git または pyproject.toml)、.env/.env.local の自動読み込み（OS 環境変数優先、上書き保護あり）を実装。各種設定プロパティ（DB パス、API トークン、Paper Trading 関連、監視閾値など）を提供。
- config_setup.py: 対話式 .env 設定ウィザードを追加。既存 .env 読み込み、入力プロンプト、シークレットマスク、確認後の .env 書き込み機能を実装。
- validate_config.py: 起動前設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在・パース検証、live 環境向けガードを実装。--strict モードをサポート。
- portfolio/*: ポートフォリオ構築用純関数群を追加（候補選定、等重/スコア重み、ポジションサイズ算出、セクター制限、レジーム乗数）。単元株（lot_size）丸め、コストバッファ、aggregate スケーリング／再配分ロジック等を備える。
- research/factor_research.py: DuckDB ベースのファクター計算モジュールを追加（Momentum / Volatility / Liquidity / Value 等の算出ロジック）。prices_daily テーブル参照で P&L 指標や移動平均、ATR 等を計算。
- tools/paper_verification_report.py: ペーパートレード検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）等を集計し PASS/FAIL 判定を行う。対象期間フィルタ、DB パス指定をサポート。
- utils/process_priority.py: クロスプラットフォームなプロセス優先度設定ユーティリティを追加。Windows / POSIX（Linux/Mac/FreeBSD）に対応し、nice 値・HIGH_PRIORITY_CLASS 等を扱う。CPU affinity 設定関数も追加。

### Changed
- 全体: DuckDB と SQLite を両方用いる設計を明確化。監視・実行それぞれの起動スクリプトで適切な DB パスを使用するよう分離（本番監視は常に sqlite_path を使用、ペーパートレードは paper_sqlite_path を使用）。
- config: .env 読み込みロジックを堅牢化（export プレフィックス、クォート付き値のエスケープ処理、インラインコメント処理、override/protected オプション）。自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
- position_sizing: allocation_method に "risk_based" と "equal"/"score" をサポート。コスト見積り (cost_buffer) を導入し aggregate cap 判定に反映。スケーリング後の再配分で残差（fractional remainder）考慮ロジックを追加して単元株単位で整合的に配分。
- risk_adjustment: セクター上限チェック（apply_sector_cap）で "unknown" セクターは上限対象外とする明示動作を採用。超過セクターの除外ログを追加。
- set_process_priority: 未対応 OS では警告を出しスキップする挙動に統一。アクセス権限不足や未実装 API に対して警告でフォールバック。

### Fixed
- paper_verification_report: データベース内のテーブル欠損やクエリ実行時の sqlite3.OperationalError を捕捉し、テーブルが存在しない場合でもレポート生成がクラッシュしないようにフォールバック（N/A 表示）を追加。
- config._parse_env_line: クォートあり／なし双方のケースでインラインコメントやバックスラッシュエスケープの扱いを明確化し、.env のパース誤動作を改善。

### Internal
- パッケージバージョンを __version__ = "0.1.0" に設定。
- モジュール間の import 順序・遅延インポート（noqa: E402）で循環や起動順問題を回避。
- ロギングを統一（basicConfig/INFO）して起動スクリプトでの起動メッセージを整備。

---

## [0.1.0] - 2026-04-17

初回リリース。上記の機能群を含む最初の公開バージョンです。

### Added
- 基本的な起動スクリプト:
  - run_execution.py (ExecutionEngine 起動、ペーパートレード分離、停止フラグ/PID 連携)
  - run_monitoring.py (SystemMonitor ポーリング)
- 環境設定・検証ツール:
  - config.py (自動 .env 読み込み、Settings)
  - config_setup.py (.env 対話ウィザード)
  - validate_config.py (設定検証 CLI)
- ポートフォリオ構築ライブラリ:
  - portfolio.portfolio_builder (候補選定、重み計算)
  - portfolio.position_sizing (株数計算、aggregate スケール)
  - portfolio.risk_adjustment (セクター制限、レジーム乗数)
- 研究用ファクター計算:
  - research.factor_research (Momentum / Volatility 等)
- 運用ツール:
  - tools.paper_verification_report (ペーパートレード検証レポート)
- ユーティリティ:
  - utils.process_priority (優先度・CPU affinity 設定)

### Changed
- DuckDB / SQLite を用途別に使い分ける設計を採用（分析用 DuckDB、監視/注文履歴用 SQLite）。
- .env パースと自動読み込みの仕様を明確化。

### Fixed
- データ欠損時の堅牢化（レポートやファクター計算での None 対応、SQLite テーブル未存在でのハンドリング等）。

---

注意:
- .env ファイルは機密情報を含むため Git 管理対象外としてください（config_setup.py のヘッダにも注意書きあり）。
- 本リリースは初期版のため、実運用（特に live 環境）では設定検証（validate_config）を必ず実行し、LINE 通知等のアラート経路を確認してください。