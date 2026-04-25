# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このファイルは、与えられたコードベースの内容から推測して作成した変更履歴です。

## [Unreleased]

### Added
- 実行・監視用エントリポイントを追加
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。KABUSYS_ENV により paper_trading 用の MockBrokerClient と専用 SQLite（data/paper_trading.db）を使用する動作をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止は data/stop_requested.flag で制御。
- 設定管理・ウィザード・検証ツールを追加
  - config.py: 環境変数の読み込み・ラップ。.env/.env.local の自動読み込み、export 形式やクォート付き値、コメントの扱いに対応。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加（秘密値のマスク表示、デフォルト値・選択肢対応）。
  - validate_config.py: 起動前チェックツールを追加。必須環境変数やパス、config/*.yaml の存在・パース（PyYAML 利用可能時）を検証。--strict オプションをサポート。
- ロギング・プロセス管理ユーティリティを追加
  - utils/logging_setup.py: root ロガーを統一的に初期化するユーティリティを追加。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler、30日保持）を設定。LOG_DIR/LOG_LEVEL の優先解決を実装。ログディレクトリ作成失敗時はファイル出力をスキップして継続。
  - utils/process_priority.py: プロセス優先度（high/normal/low）および CPU affinity 設定用ユーティリティを追加。Windows と POSIX の差分吸収、権限不足時の警告ハンドリングを実装。
- ポートフォリオ構築ライブラリを追加（pure functions）
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等配分・スコア加重配分 (calc_equal_weights / calc_score_weights) を実装。スコア全てが 0 の場合のフォールバック警告を追加。
  - portfolio/position_sizing.py: ポジション株数計算ロジックを実装（risk_based / equal / score）。単元株（lot_size）丸め、1 銘柄上限・aggregate cap（availability に合わせたスケールダウン）、cost_buffer を考慮した安全な配分ロジック（端数配分処理含む）などを実装。
  - portfolio/risk_adjustment.py: セクター集中上限の適用（apply_sector_cap）、市場レジームに基づく乗数計算（calc_regime_multiplier）を実装。sell_codes を考慮した除外、unknown セクターの扱い、未知レジームでの警告フォールバックを備える。
  - portfolio/__init__.py: 上記関数群を公開。
- Paper Trading 検証レポートツールを追加
  - tools/paper_verification_report.py: Paper Trading 用 SQLite DB（PAPER_TRADING_SQLITE_PATH）から集計してレポートを生成するスクリプトを追加。稼働率（uptime）、注文成功率 (fill_rate)、送信率 (send_rate)、API レイテンシ（P95 等）を算出し PASS/FAIL 判定を出力。P95 算出や日付フィルタ指定、DB 存在チェックを実装。
- データ分析用の研究モジュールを追加（骨組み）
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨格を追加（モメンタム等の指標計算を想定）。関数 calc_momentum の実装開始（未完の箇所あり、以降のロジックは継続実装予定）。

### Changed
- データベース接続の振る舞い明確化
  - 監視(run_monitoring)は KABUSYS_ENV に関わらず本番用 sqlite_path を使用する（監視 DB は本番 DB を参照する設計）。
  - 実行(run_execution)は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を使用し、本番 DB と完全に分離する振る舞いを明確化。
- ログのデフォルト設定および出力先の取り扱いを統一
  - setup_logging によりアプリ名別ログファイル（logs/<app_name>.log）を日次ローテーションで出力するようにした。標準出力は stdout を使用（cron 等でのリダイレクトを想定）。
- .env のパースロジックを強化
  - export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いを適切に処理するよう改善。既存 OS 環境変数は保護される。

### Fixed
- 実行/監視プロセスの安定性向上
  - run_monitoring のポーリング中に check_once() が例外を投げてもループを継続し、例外をログ出力するようにしてサービス継続性を確保。
  - run_execution でスレッド終了監視と停止フラグ検出時の安全停止処理を実装（engine.stop() 呼び出し、タイムアウト付き join）。
- process_priority / set_cpu_affinity の例外ハンドリング強化
  - 権限不足や未対応プラットフォームで例外を握り潰して警告ログを出すようにし、起動失敗を回避。

### Documentation / UX
- config_setup.py が .env のテンプレートを生成・上書きする際に注意書き（.env を絶対に Git にコミットしない）を出力。
- validate_config.py が PyYAML 未インストール時に YAML 検証をスキップし警告を出すようにした。
- 各モジュールに docstring／コメントを充実させ、設計方針や TODO を明記（例: position_sizing の lot_size 将来拡張案、risk_adjustment の価格フォールバック TODO）。

## [0.1.0] - 2026-04-25

初回公開リリース。上記の機能セットをパッケージ化：
- 実行エンジン/run_execution、監視/run_monitoring、設定操作 (config_setup)、設定検証 (validate_config)、Paper Trading レポート、ポートフォリオ構築ロジック、プロセス/ロギングユーティリティを含む。
- DuckDB/SQLite を用いた分析＆監視基盤の基本を提供。

### Known issues / Notes
- research/factor_research.py は一部実装が未完（calc_momentum の続きが必要）。今後のリリースでファクター群の完全実装を予定。
- position_sizing の価格フォールバック（前日終値や取得原価を用いる）は未実装で TODO。price が欠損するとエクスポージャー算出に影響するため注意。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START の値に注意（デフォルト 0 推奨）。validate_config は本番時の追加チェック・警告を出す。
- PAPER_FILL_MODE の値は "instant" / "partial" / "never" / "reject" のいずれかでなければならない。

---

この CHANGELOG はソースコードの構造・コメント・定数・ログメッセージ等から推測して作成しています。実際の変更履歴／リリースノート作成時はコミット履歴や開発者コメントを参照してください。