Keep a Changelog
=================

すべての重要な変更点をこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]
-----------

- （現時点では未リリースの変更はありません）

[0.1.0] - 2026-04-24
--------------------

Added
- 全体
  - パッケージの初期リリース。バージョンは __version__ = "0.1.0"。
  - プロジェクト構成や各モジュールに豊富なドキュメント文字列を追加し、使い方や設計方針を明記。

- 環境設定 / 設定管理
  - kabusys.config.Settings を追加し、環境変数ベースの設定取得を体系化。
    - J-Quants / kabuAPI / LINE / DB / 監視 / システム設定など主要な設定プロパティを提供。
    - KABUSYS_ENV, LOG_LEVEL 等の値検証（有効な値チェック）を実装。
    - paper_trading 用に paper_sqlite_path、paper_fill_mode（instant / partial / never / reject）をサポート。
  - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env パーサーの実装: export プレフィックス対応、クォート文字・バックスラッシュエスケープ・インラインコメント処理などをサポート。

- 設定ウィザード / 検証 CLI
  - kabusys.config_setup: 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
    - secret フィールドのマスク表示、選択肢／デフォルト対応、保存前の確認ダイアログ等を実装。
  - kabusys.validate_config: 起動前チェック用 CLI を追加。
    - 必須/任意の環境変数チェック、KABUSYS_ENV や LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ存在チェック。
    - config/*.yaml の存在確認と PyYAML がある場合はパース検証。
    - KABUSYS_ENV=live のときの追加警告（LINE 通知や KILL_FLAG_CLEAR_ON_START 等）。
    - --strict オプションで警告を FAIL 扱いにできる。

- 起動スクリプト / 実行基盤
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite DB (data/paper_trading.db) を使用し、本番 DB と分離。
    - BrokerClientFactory を介したブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド実行と停止フラグ監視を実装。
    - 停止フラグファイル（data/stop_requested.flag）および実行 PID ファイル管理を想定。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境に関係なく本番用 sqlite_path を使用する仕様（監視 DB は一意）。
    - 停止フラグファイル検知でループ終了。KeyboardInterrupt ハンドリングと DB 接続クローズを備える。

- ロギング / プロセス管理ユーティリティ
  - kabusys.utils.logging_setup.setup_logging を追加。
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30 日保持）を設定。
    - LOG_LEVEL あるいは引数 level でログレベル解決、LOG_DIR / 引数 log_dir でログ出力先決定。ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみで継続。
  - kabusys.utils.process_priority を追加。
    - Windows / POSIX（Linux/macOS/FreeBSD）対応でプロセス優先度（high/normal/low）を設定。
    - psutil を使用した実装、権限不足や未対応 OS の場合は警告してスキップ。
    - set_cpu_affinity によりプロセスを最初の N コアに固定（オプション）。

- ポートフォリオ構築（Portfolio）
  - kabusys.portfolio.portfolio_builder: 候補選定と重み計算の純粋関数を追加。
    - select_candidates: スコア降順・タイブレークルールで上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（全スコア 0 の場合は等金額にフォールバック）。
  - kabusys.portfolio.risk_adjustment: セクター上限とレジーム乗数のロジックを追加。
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合、新規候補の除外処理（"unknown" セクターは除外適用外）。
    - calc_regime_multiplier: 'bull'/'neutral'/'bear' に対する投下資金乗数（未知のレジームは警告のうえ 1.0 フォールバック）。
  - kabusys.portfolio.position_sizing: 発注株数計算ロジックを追加。
    - allocation_method として "risk_based" / "equal" / "score" をサポート。
    - リスクベースの株数算出（risk_pct, stop_loss_pct を使用）、単元株（lot_size）で丸め、per-stock 上限と aggregate cap によるスケーリング、cost_buffer を加味した保守的見積り、残差処理による追加配分ロジックなどを実装。

- リサーチ / ツール
  - kabusys.research.factor_research: ファクター計算モジュールの骨組みを実装（Momentum / Value / Volatility / Liquidity を想定）。（一部関数は未完の箇所あり）
  - kabusys.tools.paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。
    - データベース（PAPER_TRADING_SQLITE_PATH）からシステム安定性、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）を集計。
    - デフォルト閾値による PASS/FAIL 判定（稼働率 99%／注文成功率 90%／送信率 95%／P95 レイテンシ 200ms）。
    - 日付範囲フィルタ、--db オプション、出力の整形（N/A 表示）をサポート。

Changed
- なし（初期リリースのため履歴は追加中心）

Fixed
- なし（初期リリース）

Notes / Implementation details
- .env の自動ロードはプロジェクトルートの検出に依存するため、パッケージ配布後は KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化することを推奨。
- run_monitoring は MONITOR_POLL_INTERVAL に不正な値が入っていた場合に警告してデフォルト値にフォールバックする設計。ゼロ以下の値は time.sleep と競合しうるため安全化している。
- run_execution は paper_trading 環境で本番 DB と完全に分離する設計を採用。paper_trading 用 DB のパスは PAPER_TRADING_SQLITE_PATH で上書き可能。
- ロギングは stdout とファイルの二重出力を行い、タスクスケジューラや cron からの運用を想定して stdout を使用する（stderr ではない）。
- process_priority / cpu_affinity は権限やプラットフォームに依存する箇所があるため、失敗時は警告で継続するフォールトトレラントな実装。

今後の課題（想定）
- factor_research の関数群（Momentum 等）の完全実装および単体テスト整備。
- ExecutionEngine / SystemMonitor の詳細なユニットテスト・統合テストの追加。
- 銘柄別 lot_size サポート（現在は全銘柄共通の lot_size）。
- 価格欠損時のフォールバック（前日終値や取得原価を用いた補完）や外部依存切り離しの強化。
- より詳細なエラーメトリクスとアラート（LINE 送信の成熟化）。

以上。必要であれば、各変更点についてさらに細かいチケットや実装ファイルごとの差分説明を作成します。