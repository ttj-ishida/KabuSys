CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

現在のバージョン: 0.1.0

Unreleased
----------

（なし）

0.1.0 - 2026-04-18
------------------

初回リリース — コードベースから推測した主要な機能・挙動を記載します。

Added
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動するメインスクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper_trading SQLite DB を使用して本番 DB と完全分離。
    - 起動時にプロセス優先度を "high" に設定する仕組みを導入。
    - エンジンはデーモンスレッドで実行され、data/stop_requested.flag による外部停止をサポート。
    - 実行中の PID を data/execution.pid に記録する想定（pid_file サポート）。
- 監視スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番の sqlite_path を使用する設計（監視データの一元化を想定）。
    - 停止フラグ検知によりループを終了する処理を実装。
- 設定・環境管理
  - config.py: Settings クラスを実装。
    - .env / .env.local の自動ロード機能（プロジェクトルートの検出: .git または pyproject.toml）。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD フラグをサポート。
    - .env パースは export 形式、クォート、エスケープ、行内コメントなどに対応。
    - 各種設定プロパティ（J-Quants トークン、kabu API、DB パス、Paper Trading 設定、監視閾値、ログレベル等）を提供。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
- 設定ユーティリティ / 検証ツール
  - config_setup.py: 対話式ウィザードで .env を作成/更新する CLI を追加。
    - 秘匿項目は表示時にマスク。
    - 保存前に内容確認を行う。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および（PyYAML があれば）パース検証を行う。
    - --strict モードで警告をエラー扱いにできる。
    - live 環境用の追加ガードチェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性指摘）。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で選抜。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を提供（スコア全て 0 の場合は等分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中の上限チェック（既存保有のセクター比率に応じて候補をフィルタ）。
    - calc_regime_multiplier: 相場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数計算を実装。
    - 単元株（lot_size）で丸め、ポジション上限・aggregate cap（available_cash）を考慮したスケーリング、cost_buffer（手数料・スリッページ見積り）を反映。
- ログ／プロセスユーティリティ
  - utils.logging_setup: 共通ログ設定ユーティリティを追加。
    - stdout 出力（StreamHandler）と日次ローテートのファイル出力（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル・ログディレクトリは引数 → 環境変数 → デフォルトの順で決定。
    - stdout を利用することでタスクスケジューラ起動時のリダイレクト運用を想定。
  - utils.process_priority: プロセス優先度と CPU affinity の設定ユーティリティを提供。
    - Windows / POSIX (Linux, Darwin, FreeBSD) を吸収する実装。
    - 権限不足等で失敗しても警告を出して安全にスキップ。
- 実行関連コンポーネント（配置の痕跡）
  - execution.*: BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager（RiskConfig）などの組み立てコードを run_execution で利用。デフォルトの RiskConfig 値（max_position_pct 等）が含まれる。
  - monitoring.monitoring_db:init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。
  - duckdb と sqlite3 の併用（DuckDB を分析用、SQLite を監視/履歴用に想定）。
- ツール
  - tools.paper_verification_report: ペーパートレード検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を行う。
    - デフォルト DB は data/paper_trading.db。PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションで指定可能。
    - P95 の独自実装、期間フィルタ機能を持つ。
- パッケージメタ
  - パッケージバージョンを __version__ = "0.1.0" に設定。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （該当なし）

Notes / 注意事項
- 監視（run_monitoring）は「環境にかかわらず本番 sqlite_path を使用」する設計になっています。監視用データを分離したい場合は設定を見直してください。
- config の自動ロードはプロジェクトルートの検出に依存します。パッケージ配布後やテスト環境で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- run_execution は KABUSYS_ENV が paper_trading の場合に paper_trading 用 DB を使うため、本番 DB とデータが混在しないよう配慮されています。
- process_priority や CPU affinity の設定は権限不足や未対応プラットフォームで失敗する可能性があり、その場合は警告を出してスキップします。
- research/factor_research.py はファクター計算の設計と一部実装（定数群、関数定義の骨組み）を含みますが、ファイル末尾が不完全に見える（未実装部分の存在）ため追加実装が必要です。

今後の予定（推測）
- factor_research の完成（Momentum / Value / Volatility / Liquidity の計算ロジック）。
- ExecutionEngine 周りのさらなるテストと安定化（リスク管理・再実行ロジック等）。
- 監視アラートの LINE 通知連携と本番向けガード強化。
- 単体テスト・CI の整備、ドキュメント（README, API docs）の拡充。

----------------------------------------
この CHANGELOG はソースコードから推測して作成しています。実際の変更履歴やリリースノートはリポジトリのコミット履歴・メンテナ情報に基づいて正式に作成してください。