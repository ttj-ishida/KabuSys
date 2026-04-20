# Changelog

すべての変更履歴は Keep a Changelog のフォーマットに従います。  
このファイルは、リポジトリの現状のコードから推測して作成した初期の変更履歴です。

全般的な注記
- バージョン情報は src/kabusys/__init__.py の __version__ = "0.1.0" に基づいています。
- 日付はコード解析時点（2026-04-20）を使用しています。
- 実装の挙動はソースコードの内容から推測して記載しています。

## [0.1.0] - 2026-04-20

### Added
- 初回リリース: KabuSys 自動売買システムの基盤機能群を追加。
- コアモジュール
  - portfolio: 銘柄選定・重み付け・ポジションサイズ計算・リスク調整を提供。
    - portfolio_builder: 候補選定（select_candidates）、等配分・スコア加重（calc_equal_weights / calc_score_weights）。
    - risk_adjustment: セクター上限適用（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）。
    - position_sizing: position size 計算（calc_position_sizes）—リスクベース、等配分、スコア配分をサポートし、単元株丸めや aggregate cap のスケーリングを実装。
  - research: factor_research モジュール（ファクター計算の骨子を実装、DuckDB を用いる設計）。
- 実行 / エンジン周り
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV による paper_trading 切替（MockBrokerClient を利用して paper 専用 DB に記録）をサポート。
  - 実行系コンポーネント（ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等）の組み立て処理を追加。
  - 停止制御: data/stop_requested.flag を監視し安全に停止する仕組み、実行用 PID ファイル（data/execution.pid）の管理。
- 監視周り
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を参照して起動。
  - monitoring_db 初期化ユーティリティ（init_monitoring_db）を起動時に実行。
  - 監視ループの例外をキャッチしてログに残し次回ポーリングに持ち越す実装。
- 設定・環境管理
  - config.Settings: 環境変数読み込み／検証を集約。DUCKDB/SQLite のパス、KABUSYS_ENV、ログレベル、Paper Trading 用設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）等をプロパティで提供。
  - .env 自動読み込み機能: プロジェクトルート（.git または pyproject.toml を探索）を基準に .env / .env.local を読み込み（既存 OS 環境を保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - 環境変数の行パーサを堅牢化（export 付き、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い等を考慮）。
  - config_setup.py: 対話式ウィザードで .env の初期作成・更新を支援。必須項目・任意項目・秘密項目の扱いをサポートし、保存前に確認ダイアログを表示。
  - validate_config.py: 起動前の設定検証 CLI を追加（必須 env の未設定検出、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml 存在・パース検査（PyYAML がない場合は警告））。--strict モードで警告を FAIL 扱いにできる。
- ロギング・ユーティリティ
  - utils.logging_setup.setup_logging: StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - ログレベル解決順序（引数 > 環境変数 LOG_LEVEL > デフォルト）を明確化。
- プロセス優先度ユーティリティ
  - utils.process_priority: cross-platform にプロセス優先度を設定（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）。CPU affinity 固定関数 set_cpu_affinity を提供。権限不足や未対応環境では警告を出して安全にスキップ。
  - 起動スクリプト（monitoring / execution）は開始時に優先度を "high" に設定するよう呼び出し。
- Paper Trading / 検証ツール
  - tools.paper_verification_report: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ等を集計して検証レポートを出力。P95 レイテンシ計算、閾値による PASS/FAIL 判定を実装。--from/--to/--db オプションで期間・DB 指定可能。
- DB 統合
  - DuckDB（duckdb.connect）と SQLite（sqlite3.connect）を併用する設計を採用。デフォルトパスは Settings で提供（data/kabusys.duckdb, data/monitoring.db）。
- ドキュメント的コメント
  - 各モジュールに動作説明、設計方針、注意事項（例: price の欠損時の将来対応や単元株の将来的拡張など）を詳細に記述。

### Changed
- 該当なし（初期リリースのため既存機能の変更履歴はなし）。

### Fixed
- 環境変数のパース・検証におけるフォールバックの整備:
  - MONITOR_POLL_INTERVAL に不正（非整数/0以下）が設定された場合は警告ログを出しデフォルト（60秒）にフォールバック。
  - PAPER_FILL_MODE の不正値は ValueError を送出し明示的に失敗させる検証を追加。
  - Settings.env / log_level の妥当性チェックで不正値は例外を投げる（早期検出）。
- ログディレクトリ作成失敗やファイルハンドラ生成失敗時に安全にフォールバックしてコンソールログのみで動作するよう改善。
- run_execution.py / run_monitoring.py の停止処理強化: stop フラグ検知で安全にスレッド/ループを終了し、最終的に DB 接続をクローズすることを保証。

### Security
- config_setup に注記: .env を絶対に Git にコミットしない旨の警告をファイルに記載。
- 環境変数読み込み時に OS 環境を保護する仕組み（protected set）を導入し、プロセス起動時の既存変数上書きを防止。

### Known limitations / Notes
- research.factor_research は部分実装（ファイル末尾が途中で切れている）で、完全なファクター計算ロジックは今後実装予定。
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄別単位をサポート予定）。
- apply_sector_cap は sector_map に "unknown" がある場合は上限適用をスキップする設計（将来的にフォールバック価格やマスタ拡張を検討）。
- 一部の外部依存（psutil, duckdb, PyYAML 等）への依存があるため、実行環境にこれらがない場合は機能が制限される（validate_config は PyYAML 不在時に警告を出す）。

---

今後の変更候補（提案）
- factor_research の完全実装と単体テスト整備。
- 各 CLI（config_setup, validate_config, paper_verification_report）に自動テストを追加。
- 銘柄ごとの lot_size マスタ導入、position_sizing の拡張。
- ロギング / モニタリングのメトリクス export（Prometheus など）対応。

（以上）