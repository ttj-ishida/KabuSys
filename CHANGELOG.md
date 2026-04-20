Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

0.1.0 - 2026-04-20
------------------

Added
- 初期リリース: KabuSys 自動売買フレームワークの基本コンポーネントを追加。
  - パッケージメタ情報:
    - バージョン: `0.1.0` (src/kabusys/__init__.py)
- 起動スクリプト:
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト直下の data/stop_requested.flag によるフラグ検出で行う。
    - Monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する設計。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は専用のペーパートレード用 SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離。
    - 停止フラグ検出による安全停止、実行用 PID ファイル（data/execution.pid）を扱う。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderManager / RiskManager / Reconciler と連携して ExecutionEngine を実行。
- 設定・環境管理:
  - config.py:
    - .env 自動読み込み機能（プロジェクトルートの判定: `.git` または `pyproject.toml`）を実装。OS 環境変数保護機構あり。
    - `.env` の行パーサを独自実装（`export` プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの扱い等に対応）。
    - Settings クラスを提供し、環境変数をプロパティとして安全に取得（必須値チェック、値検証）。
    - Paper Trading 用設定: `PAPER_FILL_MODE` の検証（有効値: `"instant" | "partial" | "never" | "reject"`）、`PAPER_TRADING_SQLITE_PATH` をサポート。
    - 各種監視閾値・ファイルパス（PID/KILL フラグ等）をプロパティで提供。
    - 自動 .env ロードの無効化には `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使用可能。
  - config_setup: 対話式ウィザードで `.env` を初期生成/更新する CLI を追加。
    - 複数項目の定義とマスク入力（シークレット）をサポート。書き込み前の確認プロンプトあり。
    - デフォルトパスや説明文を含むテンプレートで `.env` を生成。
  - validate_config: 起動前に .env や config/*.yaml の基本的妥当性を検証する CLI を追加。
    - 必須/任意の環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック。
    - PyYAML があれば config/*.yaml のパース検証を行い、未導入時は警告を出す。
    - `--strict` モードで警告を FAIL 扱いにできる。
- ロギング・プロセス管理ユーティリティ:
  - logging_setup:
    - ルートロガーに StreamHandler（stdout）と日次ローテーションの TimedRotatingFileHandler を設定する共通ユーティリティを提供。
    - ログレベル解決順: 引数 > 環境変数 `LOG_LEVEL` > デフォルト `INFO`。
    - ログディレクトリ解決順: 引数 > 環境変数 `LOG_DIR` > `logs/`。ディレクトリ作成失敗時はファイルハンドラをスキップして stdout のみで継続。
    - 日次ローテーションで 30 世代保持。
  - process_priority:
    - Windows と POSIX (Linux/macOS/FreeBSD) に対応したプロセス優先度設定ユーティリティ（`set_process_priority("high"|"normal"|"low")`）。
    - CPU affinity を最初 N コアに固定する `set_cpu_affinity` を提供（権限不足等を捕捉して警告）。
    - psutil を利用し、権限不足や未対応 OS は警告を出して安全にスキップ。
- ポートフォリオ構築（純粋関数群、DB 非依存）:
  - portfolio.portfolio_builder:
    - 候補選定 `select_candidates`（スコア降順、同点は signal_rank 昇順）、等金額/スコア加重重み `calc_equal_weights`, `calc_score_weights`（スコア全0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment:
    - セクター集中制限 `apply_sector_cap`（既存保有のセクター別時価を計算し、上限超過セクターの新規候補を除外。unknown セクターは制限適用せず）。
    - レジーム乗数 `calc_regime_multiplier`（"bull"=1.0, "neutral"=0.7, "bear"=0.3。未知レジームは警告を吐いて 1.0 でフォールバック）。
  - portfolio.position_sizing:
    - 発注株数計算 `calc_position_sizes` の実装。
      - allocation_method: `"risk_based" | "equal" | "score"` をサポート。
      - リスクベース算出、1銘柄上限/max_utilization/lot_size（単元株丸め）/cost_buffer（手数料・スリッページ概算）を考慮。
      - aggregate cap 超過時はスケールダウンし、lot_size 単位で端数配分（残差の大小順）を行う。
      - 価格欠損時のスキップやデバッグログ出力を実装。
- 研究・ファクター計算:
  - research.factor_research: モメンタム等のファクター計算モジュールの初期実装開始（DuckDB 経由で prices_daily / raw_financials を参照する設計、日数・ウィンドウ等の定数定義あり）。（実装途中）
- ツール:
  - tools.paper_verification_report: ペーパートレード検証レポート生成 CLI を追加。
    - デフォルト DB パスは `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`。
    - CLI オプション `--from`, `--to`, `--db` をサポート。
    - システム稼働率、注文成功率（fill rate）、送信率、リスク却下数、API レイテンシ（avg/max/P95）を集計して PASS/FAIL 判定を行う。既定の閾値を設定（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。
    - P95 計算、期間フィルタ、DB が無い場合のエラーメッセージなどを実装。

Changed
- （初回リリースのため「変更」は無し）

Fixed
- （初回リリースのため「修正」は無し）

Notes / Important details
- monitoring の SQLite は環境にかかわらず Settings.sqlite_path（本番用監視 DB）を使用するため、環境設定に注意すること。
- run_execution は paper_trading モード時に専用 DB を使用するため、本番 DB とデータが混在しない設計。
- .env の自動ロードはプロジェクトルートが特定できない場合はスキップされる。テスト等で自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定する。
- logging_setup は stdout を利用する設計（cron 等で stdout/stderr のリダイレクトを想定）。ログディレクトリ作成に失敗してもプロセス自体は継続する。
- process_priority / set_cpu_affinity は権限や OS の差異により実行できない場合がある。その際は警告ログを出してスキップする。

Acknowledgements / Future
- research.factor_research は計算ロジックの実装が続いており、今後のリリースで完了予定。
- 今後の改善候補: 銘柄別 lot_size 対応、価格欠損時のフォールバック価格導入、より詳細な監視メトリクスおよびリトライ戦略など。

-----