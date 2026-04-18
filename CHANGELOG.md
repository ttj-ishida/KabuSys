# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
  
※ 本 CHANGELOG はソースコードの内容から推測して作成しています。

## [Unreleased]

### Added
- 主要機能の初期実装（KabuSys 0.1.0 相当のまとめ）。
  - システム全体の起動スクリプト
    - run_execution.py: ExecutionEngine の起動フロー実装。環境に応じて paper_trading 用 DB を分離し、停止フラグ／PID 管理をサポート。
    - run_monitoring.py: SystemMonitor ポーリングループを実装。MONITOR_POLL_INTERVAL 環境変数で間隔上書き、停止フラグ検出で優雅に終了。
  - 設定管理・ユーティリティ
    - config.py: .env 自動ロード（.env / .env.local、OS 環境変数保護）、詳細な環境変数プロパティ（DB パス、API トークン、しきい値等）、値検証を実装。
    - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加。
    - validate_config.py: .env と config/*.yaml の起動前検証 CLI を追加（--strict オプションあり）。
    - validate_config は PyYAML 未インストール時のスキップ警告や本番時のガードも実装。
  - ロギング/プロセス管理
    - utils/logging_setup.py: stdout ストリームハンドラと日次ローテーションファイルハンドラをルートロガーに設定。ログディレクトリ自動作成と LOG_LEVEL 解決を実装。
    - utils/process_priority.py: Windows / POSIX の差分を吸収してプロセス優先度設定（および CPU affinity）を提供。権限不足時の安全なフォールバックあり。
  - ポートフォリオ構築モジュール（純粋関数群）
    - portfolio/portfolio_builder.py: 候補選定（スコア降順）と等分・スコア加重の重み計算を実装。スコアが全て 0 の場合は等分にフォールバック。
    - portfolio/risk_adjustment.py: セクター集中上限チェック（apply_sector_cap）と市場レジームに基づく資金乗数（calc_regime_multiplier）を実装。未知レジームはフォールバック。
    - portfolio/position_sizing.py: risk_based / equal / score ベースの株数決定ロジックを実装。単元株（lot_size）丸め、ポジション上限、aggregate cap（スケールダウン）および残差のロット配分ロジックを実装。コストバッファ考慮。
  - 研究・分析
    - research/factor_research.py: Momentum / Value / Volatility / Liquidity 等のファクター計算モジュールを設計（DuckDB 経由で prices_daily / raw_financials を参照）。（一部実装中）
  - ツール
    - tools/paper_verification_report.py: Paper Trading 用検証レポート生成。稼働率、注文成功率、送信率、レイテンシ（P95 等）を算出し PASS/FAIL 判定を行う。閾値を定義（例: uptime 99% など）。
  - DB 接続
    - SQLite（監視 DB / paper_trading DB）、DuckDB（分析 DB）への接続箇所を整備。監視用テーブル初期化のため init_monitoring_db 呼び出しを各起動スクリプトで行う（冪等）。

### Changed
- 初期リリースのため、各モジュールで堅牢性を重視した実装を採用。
  - .env のパースを強化（export プレフィックス、クォート／エスケープ、インラインコメントの取り扱い）。
  - ログは stdout を基軸にし、ファイル出力は日次ローテーションで保持（30 日）。
  - run_monitoring/run_execution は起動時にプロセス優先度を「high」に設定しようと試みる。

### Fixed
- 環境変数や設定値の不正入力時のフォールバック動作を明確化。
  - MONITOR_POLL_INTERVAL が不正な場合は警告してデフォルトに戻す。
  - PAPER_FILL_MODE の不正値検出と早期例外。
  - Settings.env / log_level の検証強化（無効値で ValueError）。
- process_priority の未対応 OS や権限不足時に例外を投げず警告してスキップするように安全化。

### Security
- .env を生成する際に注意書きを出力（.env を Git にコミットしない旨）。


## [0.1.0] - 2026-04-18

初回公開相当の実装をまとめてリリース。

### Added
- 上述の「Added」項目にあるすべての機能を初回リリースとして公開。
  - 起動スクリプト、設定管理、対話ウィザード、設定検証 CLI。
  - ログ設定・プロセス優先度ユーティリティ。
  - ポートフォリオ構築（選定・重み・ポジションサイズ・リスク調整）。
  - research/factor_research の初期設計と一部実装（Momentum 等、DuckDB ベース）。
  - Paper Trading 検証レポート生成ツール。
  - DuckDB / SQLite を用いた分析・監視基盤の統合。

### Notes
- run_monitoring はコメントにある通り「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用」する挙動を採用しています。運用時は意図した DB パス設定に注意してください。
- run_execution は paper_trading 環境で専用 DB（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離する設計です。
- research/factor_research は設計の残り（各ファクターの完全実装や境界条件の詳細化）が残っています。今後のリリースで拡充予定です。

### Breaking Changes
- 初回リリースのため該当なし。

もしこの CHANGELOG に追加してほしい点（例えば各ファイルごとのより詳細な変更ログ、履歴を遡った複数リリース分の仮想履歴、日付の変更など）があれば教えてください。コードの差分があればそれを元により正確な履歴を作成します。