# Changelog

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-19

### Added
- 初回リリース: KabuSys 自動売買基盤の基本コンポーネント群を追加。
- 起動スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイントを追加。  
    - KABUSYS_ENV=paper_trading の場合に専用の Paper Trading 用 SQLite（data/paper_trading.db, 環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）を使用して本番 DB と完全分離する設計。  
    - ブローカークライアント生成を BrokerClientFactory に委譲。OrderRepository/OrderManager/RiskManager/Reconciler を組み立てて ExecutionEngine を起動する。  
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) を用いた停止制御を実装。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60 秒）。  
    - Monitoring は環境に依らず本番用 sqlite_path を使用する（監視情報は本番 DB に記録する意図）。
    - 停止フラグ (data/stop_requested.flag) によるループ終了および KeyboardInterrupt のハンドリングを実装。
- 設定管理
  - config.py: 環境変数/.env の読み込みと Settings クラスを追加。  
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）。  
    - .env/.env.local の自動ロード（OS 環境変数を保護、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。  
    - 値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）、各種パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）を Path として提供。
  - config_setup.py: .env を対話式に生成/更新するウィザードを追加。主要項目の説明・シークレットマスク・保存機能を提供。
  - validate_config.py: .env と config/*.yaml の事前検証 CLI を追加。必須環境変数のチェック、パスの親ディレクトリ存在チェック、YAML パース（PyYAML がインストールされている場合）や本番向けガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性）を実装。--strict オプションで警告を FAIL 扱いにできる。
- ログとプロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。  
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）によるファイル出力を設定。ログディレクトリは引数/環境変数/デフォルトの順で解決。ファイルハンドラ作成失敗時はコンソール出力のみで継続。30 日分保持。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度と CPU affinity 設定を追加。  
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(N) を提供。psutil の権限エラーや未サポート環境は警告を出して安全にスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: シグナルの候補選定 select_candidates、等重み calc_equal_weights、スコア重み calc_score_weights を実装。スコアが全て 0 の場合は等配分にフォールバックして警告。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap と市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装。未知レジームはフォールバック。
  - portfolio/position_sizing.py: 発注株数計算 calc_position_sizes を実装（allocation_method: "risk_based","equal","score" をサポート）。  
    - 単元株（lot_size）丸め、ポジション上限、aggregate cap（available_cash を超える場合のスケーリング）や cost_buffer を考慮した保守的見積りを行う。スケーリング後は残差に基づく追加配分ロジックを持つ。
- Research / ファクター計算
  - research/factor_research.py: DuckDB 接続を用いたモメンタム等のファクター計算モジュールを追加（設計骨子および定数を実装）。（ファイル末尾で calc_momentum の実装が始まるが一部省略あり。）
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。  
    - デフォルト DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。期間指定 (--from/--to) によるフィルタリング、稼働率・注文成功率・送信率・P95 レイテンシ等を集計して PASS/FAIL 判定を出力。  
    - 判定閾値: 稼働率 >= 99.0%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。
- パッケージ初期化
  - src/kabusys/__init__.py にバージョン情報 __version__ = "0.1.0" を追加し、主要サブパッケージを __all__ に定義。

### Changed
- —（初回リリースのため変更履歴は無し）

### Fixed
- —（初回リリースのため修正履歴は無し）

### Notes / 実装上の重要事項（ドキュメント的補足）
- run_monitoring は Monitoring 用 DB に本番 sqlite_path を常に使用する設計になっているため、開発環境で監視を分離したい場合は SQLITE_PATH を適切に設定するか挙動を理解しておくこと。
- .env の自動ロードはプロジェクトルート検出に依存するため、配布後や CWD 依存で動かす際は KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読込を無効化できる。
- process_priority および CPU affinity の設定は psutil を利用しているため、権限や OS により失敗する場合がある。失敗時は警告を出して処理を継続する安全設計。
- logging_setup はログディレクトリ作成に失敗するとファイル出力を行わず stdout のみで運用する。cron / systemd 等の環境で標準出力を収集する運用を想定。
- portfolio と position sizing の実装は「PortfolioConstruction.md」「StrategyModel.md」に準拠する設計思想をコメントで明示。将来的に銘柄別 lot_size などの拡張を想定した TODO を含む。
- research/factor_research.py は設計が整っているが一部実装が継続中（calc_momentum の実装が途中で切れている可能性あり）。大規模なファクター計算は DuckDB に依存。

### Security
- 環境変数やシークレット情報（J-Quants トークン、kabu API パスワード等）は .env に保存しない運用や適切なアクセス権管理を推奨。config_setup にて .env を生成する際に「絶対に Git にコミットしないこと」を明示。

---

開発/運用上の詳細な使い方は各モジュールのドキュメント（ソース内 docstring、CLI ヘルプ）を参照してください。必要であれば、リリースノートをより細かく分類（例えば Monitoring / Execution / Portfolio / Tools）して記載することも可能です。