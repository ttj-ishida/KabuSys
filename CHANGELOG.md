CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

[Unreleased]
------------

（現在の候補・開発中の変更はここに記載します）

[0.1.0] - 2026-04-18
-------------------

Added
- プロジェクト初回リリース。
- 実行スクリプトを追加:
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合はペーパートレード用の専用 SQLite（data/paper_trading.db）を使用し、MockBrokerClient による完全分離を行う。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。
- 設定管理関連:
  - config.py: .env の自動読み込み（プロジェクトルート検出）機能を追加。export プレフィックスやクォート・エスケープ、インラインコメントを考慮したパーサを実装。オーバーライド動作や OS 環境変数保護もサポート。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化も可能。
  - config_setup.py: 対話式 .env ウィザードを追加（.env の初期作成 / 更新支援）。
  - validate_config.py: 起動前の設定検証 CLI を追加（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス確認、config/*.yaml 存在・パースチェック等）。--strict モードで警告を失敗扱いにできる。
- ポートフォリオ構築関連モジュール:
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。スコアが全て 0 の場合は等分配にフォールバック。
  - portfolio.position_sizing: position sizing ロジックを追加。allocation_method（risk_based / equal / score）をサポート。単元株（lot_size）丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap スケーリング、残余の切り上げ配分ロジックを実装。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。unknown セクターは上限適用対象外。レジーム乗数は bull/neutral/bear を想定しフォールバックを実装。
- ユーティリティ:
  - utils/logging_setup.py: 統一的なロギングセットアップを提供。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。LOG_LEVEL / LOG_DIR の解決順を実装し、ファイル出力失敗時はコンソール出力へフォールバック。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定関数を実装。アクセス権限不足や未対応 OS では警告を出してスキップする安全設計。
- 監視・解析:
  - monitoring 側の DB 初期化ユーティリティ（init_monitoring_db）を呼び出す起動フローを追加（監視テーブルが必ず存在することを保証）。
  - duckdb を分析用（ローカル分析） DB として採用。実行および監視スクリプトで duckdb 接続を開くように統一。
- ツール:
  - tools/paper_verification_report.py: Paper Trading 向けの検証レポート生成ツールを追加。稼働率、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等の指標を集計し PASS/FAIL 判定を行う。期間指定（--from / --to）や DB パス指定（--db）をサポート。
- リサーチ:
  - research/factor_research.py: ファクター計算モジュールを追加（モメンタム / Value / Volatility / Liquidity 等を想定した設計）。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する方針を採用。

Changed
- ログ出力の標準化: すべての起動スクリプトから setup_logging を呼ぶことで、ログ形式・ローテーションを統一。
- .env 読み込み順を明確化: OS 環境変数 > .env.local > .env の順で解決。既存の OS 環境変数は保護（上書きされない）。

Fixed
- .env パーサの堅牢化: export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、コメントの扱い（クォート無しの '#' は直前が空白の場合にコメントと解釈）などに対応して、実運用での .env 設定ミスを低減。
- ExecutionEngine 起動フローの安全化: 起動時に停止フラグ（data/stop_requested.flag）が既に存在する場合は起動をスキップ、稼働中に停止フラグを検知したら安全に停止する仕組みを追加。

Security
- 機密値取り扱い: config_setup のウィザードでシークレット項目はマスク表示。README 等には .env を絶対にコミットしない旨を出力するテンプレートを生成。

Notes / Implementation details
- Paper Trading 分離: paper_trading 環境では SQLite を別ファイルに分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）して、本番 DB への影響を防止。
- デフォルト値・閾値はコード内に明示（例: MONITOR_POLL_INTERVAL=60 秒、ログローテーション保持 30 日、paper verification の各閾値など）。
- process_priority.set_process_priority は権限不足等により失敗しても起動を中断せず警告ログでフォールバックする。
- validate_config は PyYAML 未インストール時に YAML 検証をスキップし警告を出す。config/*.yaml のテンプレート生成スクリプト（scripts/generate_config.py）を想定。

Deprecated
- なし

Removed
- なし

Acknowledgements
- 初期設計は PortfolioConstruction.md / StrategyModel.md 等の設計文書に基づいて実装しています（コード内コメント参照）。

（以降のバージョンでは、各モジュールの単体テスト追加、factor_research の完全実装、パフォーマンス改善・エラーハンドリング強化等を予定しています。）