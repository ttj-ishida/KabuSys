KEEP A CHANGELOG 準拠 — 変更履歴 (日本語)
======================================

すべての変更は https://keepachangelog.com/ja/ に準拠して記載しています。

[Unreleased]
-------------

0.1.0 - 2026-04-18
------------------

Added
- 初期リリース。パッケージバージョン: `kabusys.__version__ = "0.1.0"`.
- 実行用スクリプト:
  - run_execution.py: ExecutionEngine 起動スクリプトを実装。  
    - KABUSYS_ENV による paper_trading モード対応（MockBrokerClient を使用、paper_trading 用 SQLite DB に記録して本番 DB と分離）。
    - プロセス優先度を起動時に "high" に設定。
    - 停止フラグ (data/stop_requested.flag) と PID 管理 (data/execution.pid) をサポート。
    - ExecutionEngine, OrderManager, OrderRepository, RiskManager, Reconciler 等の組み立てロジックを配置。
    - RiskManager のデフォルトパラメータ（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を定義し、初期資金を broker.get_available_cash() で取得。
  - run_monitoring.py: SystemMonitor 起動スクリプトを実装。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用する挙動を明示。
    - プロセス優先度を "high" に設定、停止フラグでループ終了、例外発生時にログ出力のうえ継続。
- 設定管理:
  - config.py:
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env と .env.local のロード順（OS 環境変数が優先）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
    - .env パースの強化（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの処理）。
    - Settings クラスを導入し、各種環境変数へのアクセサ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、PID/kill flag、閾値設定、PAPER_FILL_MODE の検証など）を提供。
    - PAPER_TRADING_SQLITE_PATH / PAPER_FILL_MODE 等、paper_trading 向け設定を追加。
- 設定ツール:
  - config_setup.py: .env を対話式に作成・更新するウィザードを実装（秘密値マスク、デフォルト・選択肢対応、保存確認）。
  - validate_config.py: 起動前に .env と config/*.yaml の整合性・必須項目を検証する CLI を実装。--strict オプションで警告も失敗扱いにできる。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性チェック、本番用ガード（LINE 設定チェック、KILL_FLAG_CLEAR_ON_START の警告）等を実施。
- 分析・検証ツール:
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、API レイテンシ（P95）などを算出して PASS/FAIL 判定を出力。
    - デフォルト DB は data/paper_trading.db。期間フィルタ (--from / --to) と --db オプションをサポート。
- ポートフォリオ構築モジュール:
  - portfolio.portfolio_builder:
    - 銘柄選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコアが全て 0 の場合は等分配にフォールバックして警告を出力。
  - portfolio.risk_adjustment:
    - セクター集中制限 (apply_sector_cap) とレジーム乗数 (calc_regime_multiplier) を実装。未知レジームのフォールバックやログ出力あり。
  - portfolio.position_sizing:
    - position サイズ決定の純粋関数 calc_position_sizes を実装（risk_based / equal / score の配分方式、lot_size 単位丸め、max position / aggregate cap、cost_buffer による保守的見積り、スケーリングロジック）。
  - portfolio パッケージで上記関数をエクスポート。
- ユーティリティ:
  - utils.logging_setup:
    - 統一的なロギング設定関数 setup_logging を実装。stdout への StreamHandler と日次ローテーション (TimedRotatingFileHandler) を設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils.process_priority:
    - set_process_priority / set_cpu_affinity を実装。Windows/Linux/macOS の違いを吸収し、psutil を利用して優先度（high/normal/low）と CPU affinity を設定。権限不足などの失敗は警告でスキップ。
- リサーチ:
  - research.factor_research: モメンタム等のファクター計算モジュール骨格を追加（DuckDB 接続を想定、モメンタム、MA200、ATR、出来高統計等の計算を想定する設計）。※実装途中の箇所あり（ファイル末尾で切れている）。

Changed
- なし（初期リリースのため「追加」が中心）。

Fixed
- なし（初期リリース）。

Security
- なし（初期リリース）。

Notes / 備考
- データベースの取り扱い:
  - 監視用 monitoring は環境にかかわらず settings.sqlite_path（デフォルト data/monitoring.db）を使用する旨が明記されています。paper_trading モードでは paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離します。
- 環境変数ロード:
  - .env 自動ロードはプロジェクトルートが特定できる場合にのみ行われ、OS 環境変数は上書きされません（.env.local は上書き可能）。
- ログ:
  - デフォルトログディレクトリは logs/、ファイルは日次ローテーションで 30 日分保持。
- 実運用上の注意:
  - KABUSYS_ENV=live では本番向けの追加警告が出るため、LINE 通知設定などを適切に行ってください。
  - run_monitoring/run_execution は起動時にプロセス優先度を上げます。権限が不足する環境では警告が出ますが起動自体は継続します。
  - PAPER_FILL_MODE は "instant" / "partial" / "never" / "reject" のいずれかである必要があります。

開発者向け
- 既知の未実装 / TODO:
  - research.factor_research の一部実装が途中で終わっています（ファイル末尾に "start_da" 等の断片が存在）。このモジュールは今後の修正で完成予定です。
  - position_sizing の price 欠損時のフォールバック（前日終値など）に関する TODO を記載済み。
- テスト:
  - .env 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストでの利用を想定）。

以上。必要であればリリースノートの英語版、あるいはセクションごとの詳細（ファイル別変更点）を追記します。