# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはコードベースの内容から推測して作成した変更履歴です。

## [Unreleased]

### Added
- 監視/実行の起動スクリプトを追加
  - run_monitoring.py：SystemMonitor を定期ポーリングで実行。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能。停止はプロジェクト直下の data/stop_requested.flag による。
  - run_execution.py：ExecutionEngine を起動するデーモンスレッド管理。停止フラグ・PID ファイル対応、Paper Trading 時の専用 DB を使用する分離ロジックを実装。

- 環境設定関連の CLI を追加
  - config_setup.py：対話式ウィザードで .env を作成・更新するツール（シークレットのマスク表示、デフォルトの提示、保存確認）。
  - validate_config.py：起動前に .env と config/*.yaml の妥当性を検証する CLI（--strict オプションで警告を失敗扱いにできる）。

- 設定管理モジュールを強化
  - config.py：.env 自動読み込み（プロジェクトルート検出、.env と .env.local の優先度処理）、複雑な行のパース（export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの取り扱い）、必須項目チェック、設定プロパティ（duckdb/sqlite パス、PID パス、各種閾値、KABUSYS_ENV 検証等）を追加。

- 実行関連ユーティリティを追加
  - utils/logging_setup.py：StreamHandler（stdout）と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定する共通ユーティリティ。ログディレクトリ作成失敗時はフォールバックする。
  - utils/process_priority.py：クロスプラットフォームのプロセス優先度設定と CPU affinity 設定ユーティリティ。Windows / POSIX の差分吸収と例外に対するフォールバックを実装。

- ポートフォリオ構築モジュールを追加
  - portfolio/portfolio_builder.py：買い候補の選定（スコア降順、タイブレーク）、等金額・スコア加重の重み計算（スコア全0の際のフォールバックを含む）。
  - portfolio/position_sizing.py：複数配分方式（risk_based / equal / score）に対応した株数計算。単元株丸め、per-position 上限、aggregate cap のスケーリング、cost_buffer を考慮した保守的見積り、端数処理の安定化ロジックを実装。
  - portfolio/risk_adjustment.py：セクター集中制限（既存保有のセクター別エクスポージャ計算と候補除外）、市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（未知レジームは警告してフォールバック）。

- Paper Trading 用検証ツールを追加
  - tools/paper_verification_report.py：Paper Trading の検証レポート生成ツール。稼働率（uptime）、注文成立率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出し PASS/FAIL 判定を出力。DB が欠けている場合でも OperationalError を捕捉して安全に動作。

- 研究用ファクター計算基盤を追加（進捗あり）
  - research/factor_research.py：DuckDB を利用したモメンタム等のファクター計算モジュールの骨格（関数定義、定数、設計方針）。（実装途中の関数あり）

### Changed
- デフォルト設定および挙動の明確化
  - 監視は KABUSYS_ENV に関係なく本番 sqlite_path を使用する旨を明確化（run_monitoring）。
  - 実行エンジンは Paper Trading の場合に専用の PAPER_TRADING_SQLITE_PATH を使用して本番 DB と分離（run_execution）。
  - logging_setup: stdout を StreamHandler に利用し、ファイルハンドラ作成に失敗した場合はコンソール出力のみで継続する安全設計。

### Fixed
- 環境変数読み込みの堅牢化
  - .env パースの改良（export 接頭辞、シングル/ダブルクォート内のエスケープ、インラインコメント処理）により誤読を軽減。
  - .env の自動ロード時に OS 環境変数を上書きしない（protected set）仕組みを追加。

- 実行中のリソースクリーンアップ強化
  - run_monitoring / run_execution の finally で SQLite / DuckDB 接続を確実に閉じるように修正。

- 安全な環境検証
  - validate_config.py: PyYAML 未インストール時に YAML 検証をスキップして警告する処理を追加、KABUSYS_ENV/LOG_LEVEL の不正値チェックと適切な警告/エラー出力を実装。

- 数値計算の安全化
  - paper_verification_report の P95 算出や各種割合計算でゼロ除算や空データを安全に扱うように修正（N/A 表示）。

### Documentation
- 各モジュールに docstring と使用例を充実化（setup_logging, run_monitoring, run_execution, config_setup, validate_config, portfolio, tools/paper_verification_report など）。
- .env 関連の注意（.env を Git にコミットしない旨）を config_setup の出力に追加。

### Security
- シークレット値の CLI 表示をマスク（config_setup の確認表示など）。

---

## [0.1.0] - 2026-04-20

初回リリース想定。上記の機能群が含まれるリリース。

### Added
- 基本アーキテクチャと主要コンポーネントを実装
  - ExecutionEngine 周りの骨格（EngineConfig, ExecutionEngine 起動フロー、OrderManager/OrderRepository/Reconciler/RiskManager の組み立て）
  - SystemMonitor を用いた監視ループ
  - 設定管理（Settings クラス）と自動 .env ロード
  - ロギングとプロセス優先度のユーティリティ
  - ポートフォリオ構築・サイズ決定・リスク調整ロジック
  - Paper Trading の検証レポート生成ツール
  - 設定ウィザード（config_setup）と事前検証ツール（validate_config）
  - パッケージバージョン __version__ = "0.1.0"

### Changed
- 初期設計としての各モジュール API を確定（上記参照）。

### Fixed
- 初期実装段階で想定される環境変数読み込みやファイルハンドリングの脆弱性に対処。

---

注記:
- 本 CHANGELOG はコードの現状から推測して作成したものであり、実際のコミット履歴ではありません。将来的なリリースでは各変更を実際のコミット/チケットに基づいて細分化し、日付・著者情報を付与してください。