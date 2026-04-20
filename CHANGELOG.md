# CHANGELOG

すべての notable な変更は Keep a Changelog の形式に従って記載しています。  
リリースポリシー: バージョンはパッケージ内部の __version__ と同期しています。

## [0.1.0] - 2026-04-20

初回公開リリース。

### Added
- 基本アプリケーション設定管理を追加（kabusys.config）。
  - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - .env のパース機能を強化（export プレフィックス、クォート内のバックスラッシュエスケープ、行内コメント処理）。
  - Settings クラスで環境変数をラップ（J-Quants、kabu API、DB パス、Paper Trading 周り、監視閾値、実行環境判定など）。
- 環境設定ウィザード CLI を追加（kabusys.config_setup）。
  - 対話式で .env の生成／更新が可能。出力は .env ファイル（Git にコミットしない注意喚起を含む）。
- 設定検証 CLI を追加（kabusys.validate_config）。
  - 必須環境変数やパス、config/*.yaml の存在と YAML パース（PyYAML がある場合）をチェック。
  - `--strict` オプションで警告をエラー扱いにする機能を追加。
- 実行エンジン起動スクリプトを追加（kabusys.run_execution）。
  - ExecutionEngine の起動フロー、依存コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler）を組み立てて実行。
  - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用して本番 DB と分離（PAPER_TRADING_SQLITE_PATH で上書き可）。
  - 停止フラグ（data/stop_requested.flag）検出で安全に停止。PID ファイル管理。
- 監視ループ起動スクリプトを追加（kabusys.run_monitoring）。
  - SystemMonitor のポーリングループを提供。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
  - 監視は環境にかかわらず本番 sqlite_path を参照して監視テーブルを初期化。
  - 起動時にプロセス優先度を High に設定。
- ロギング設定ユーティリティを追加（kabusys.utils.logging_setup）。
  - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、デフォルト logs/<app>.log）を統一的に設定。
  - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - ログレベル解決順と LOG_DIR / LOG_LEVEL 環境変数のサポート。
- プロセス優先度 / CPU affinity ユーティリティを追加（kabusys.utils.process_priority）。
  - Windows / POSIX の差分を吸収して set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
  - アクセス権限不足など失敗時は警告ログを出してスキップする堅牢性を持たせた実装。
- Portfolio 構築関連の純粋関数群を追加（kabusys.portfolio）。
  - portfolio_builder: シグナル選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。同点時のタイブレークやスコア全0時のフォールバック等の挙動を明記。
  - risk_adjustment: セクター集中上限適用 (apply_sector_cap)、市場レジームに応じた乗数計算 (calc_regime_multiplier)。未知レジームは警告してフォールバック。
  - position_sizing: 発注株数計算 (calc_position_sizes)。risk_based / equal / score の方式、単元株丸め（lot_size）、コストバッファ・aggregate cap によるスケーリング処理を実装。
- Paper Trading 検証レポート生成ツールを追加（kabusys.tools.paper_verification_report）。
  - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ等を集計して PASS/FAIL 判定する CLI を提供。
  - P95 計算、日付フィルタ（--from/--to）対応、閾値はソース内定義（稼働率 99%、注文成功率 90% 等）。
- research/factor_research の骨組みを追加（DuckDB 接続を受けてファクター計算を行う設計）。モメンタム等の計算仕様をコメントで定義（実装は一部）。

### Changed
- ログ出力ポリシーを統一:
  - すべての起動スクリプトが setup_logging を利用する想定により、標準出力とファイル出力の挙動を統一。
- .env 自動ロードの挙動:
  - OS 環境変数は保護され、.env.local は .env より優先して上書きされる（ただし OS 環境変数は上書きされない）。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

### Fixed
- 環境変数パースの堅牢化:
  - クォート内のエスケープ処理や行内コメント解釈を改善し、より現実的な .env 内容に対応。
- ポーリング間隔の安全化:
  - MONITOR_POLL_INTERVAL で 0 や負値を指定した場合に time.sleep が ValueError を投げないよう、無効値はデフォルトにフォールバックして警告を出すようにした。

### Deprecated
- （該当なし）

### Removed
- （該当なし）

### Security
- 機密値の取り扱い:
  - config_setup の表示や保存でシークレット項目はマスク表示（対話中）および .env に平文で保存される旨をドキュメントに明記。運用上の注意喚起（.env を絶対に Git にコミットしない）を追加。

--- 

注意・移行メモ
- Paper Trading と本番 DB は分離されています。Paper Trading を使う場合は KABUSYS_ENV=paper_trading を設定し、PAPER_TRADING_SQLITE_PATH を必要に応じて指定してください。run_execution は paper_trading の場合に専用 sqlite を使用します。
- 監視プロセスは MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（秒）。不正な値はデフォルト 60 秒にフォールバックします。
- ログはデフォルトで logs/<app_name>.log に日次ローテートで出力されます。LOG_DIR 環境変数や setup_logging の引数で変更可能です。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。
- 実運用（KABUSYS_ENV=live）の場合は validate_config による事前チェックを強く推奨します（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値等のガードを含む）。

もし CHANGELOG の形式や記載粒度（より詳細なファイル単位の変更一覧など）を変更したい場合は指示してください。