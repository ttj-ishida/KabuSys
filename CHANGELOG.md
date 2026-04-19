# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の書式に準拠しています。  
本ファイルはコードベースから推測して生成した変更履歴です。

## [0.1.0] - 2026-04-19

### Added
- 初回リリース: KabuSys の基本コンポーネントを追加。
  - パッケージのバージョンを `__version__ = "0.1.0"` として定義。
- 実行用エントリスクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - BrokerClientFactory によるブローカークライアント生成をサポート（KABUSYS_ENV に応じて Mock を使用）。
    - Paper Trading 時は専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - ExecutionEngine を別スレッドで実行し、data/stop_requested.flag による安全停止を実装。
    - 実行時にプロセス優先度を "high" に設定する処理を追加。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数（デフォルト 60 秒）でポーリング間隔を上書き可能。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する仕様を採用。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止を実装。
- 設定関連
  - config.py
    - 環境変数・設定管理クラス `Settings` を追加。多くの設定値をプロパティとして提供（DB パス、API トークン、モード判定等）。
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。OS 環境変数を保護して .env/.env.local を読み込む実装。
    - .env 行パーサは `export KEY=val`、クォート（シングル/ダブル）とバックスラッシュエスケープ、インラインコメントの取り扱いに対応。
    - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等のバリデーションを実装。
  - config_setup.py
    - 対話式 .env 作成・更新ウィザードを追加（キー定義、既存値のマスク表示、保存処理）。
    - .env 書き込み時にテンプレートヘッダを付加し「.env を絶対に Git にコミットしない」旨を記載。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、DB パス存在確認、config/*.yaml の存在/パース検証（PyYAML が存在する場合）などを実行。
    - --strict モードで警告を失敗扱いにできる機能を提供。
- ロギング／プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに対し StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、既定 30 日保持）を統一的に設定するヘルパーを追加。
    - LOG_DIR の作成失敗やファイルハンドラ作成失敗時には警告を出してコンソール出力のみで継続する堅牢化。
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。
    - CPU affinity を最初の N コアに固定するヘルパ（set_cpu_affinity）を追加。
    - 権限不足などで設定できない場合は警告ログでスキップする実装。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等重み (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。全スコア 0 の場合は等重みへフォールバックして警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier) を実装。未知レジームは警告を出して 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - 株数算出ロジックを実装（risk_based / equal / score の配分方式）。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap スケーリング、cost_buffer（手数料・スリッページ見積り）を考慮した実装を提供。
    - スケールダウン時の残差配分アルゴリズムを実装し、再現性を確保するため安定ソートを採用。
- 研究用ファクターモジュール
  - research/factor_research.py（途中実装が含まれる）
    - DuckDB 接続を受け取り、momentum 等のファクター計算を行う設計。価格テーブル (prices_daily) と raw_financials を前提に計算を行う設計方針を採用。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を計算し、閾値判定により PASS/FAIL を出力。
    - --from / --to / --db オプションをサポート。デフォルト DB は data/paper_trading.db。
- DB 初期化ヘルパ
  - monitoring/monitoring_db.init_monitoring_db を各起動スクリプトから呼ぶことで監視テーブルの存在を保証（冪等）。

### Changed
- ログ出力先・振る舞い
  - StreamHandler を stdout に固定することで cron 等からの起動で stdout/stderr を一本化しやすくした。
  - ログディレクトリ作成失敗時はファイル出力をスキップしても動作継続するように堅牢化。
- 実行時のプロセス優先度
  - run_execution / run_monitoring の起動時に process priority を "high" に設定するフローを共通化。

### Fixed / Robustness
- .env パーサの堅牢化
  - export 前置、クォート内バックスラッシュエスケープ、インラインコメントルールに対応し、より実際の .env ファイルに耐性を持たせた。
- 設定読み込みの安全性
  - 自動 .env ロード時に OS 環境変数を保護する（.env の値が既存の OS 環境変数を上書きしない）挙動を導入。`.env.local` は上書きモードで読み込む設計。
- 環境変数/設定の検証強化
  - Settings の各プロパティで不正値を早期に検出して明確な例外を投げる（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL など）。
  - validate_config による事前チェックで起動前に設定ミスを検出しやすくした。
- 起動スクリプトの安全停止
  - data/stop_requested.flag の存在検知による安全停止、KeyboardInterrupt のハンドリング、DB 接続の確実なクローズを実装。
- DB パスやファイルの不存在時の扱いを明確化
  - validate_config にて DB 親ディレクトリの存在確認と警告を出すようにした。tools 側では DB が見つからない場合に明示的エラーメッセージを出力。

### Security
- .env 書き出しテンプレートに「.env を絶対に Git にコミットしないこと」を明記。
- 機密情報（J-Quants トークン、API パスワードなど）は対話ウィザードでマスク表示する。

### Notes / Implementation details
- DuckDB を分析用 DB（デフォルト data/kabusys.duckdb）として採用。多くの集計/研究処理が DuckDB 接続を前提としている。
- Paper Trading と Live の DB 分離を明確にし、paper_trading モード時は mock ブローカーと専用 SQLite を使用することで本番資産に影響を与えない設計。
- Position sizing, sector cap, regime multiplier 等は純粋関数群として実装しており、DB にアクセスしないためユニットテストやリサーチ用途に適している。
- いくつかのモジュール（research/factor_research.py 等）は実装途中または継続的拡張が想定される。

メジャーまたは重大な既知の破壊的変更やセキュリティ脆弱性はこのリリースでは報告されていません。将来的なリリースではユニットテスト、ドキュメント（PortfolioConstruction.md / StrategyModel.md 等）との整合性チェックを進める予定です。