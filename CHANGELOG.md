# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングを使用します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-17

### Added
- 基本アプリケーション構成・バージョン
  - パッケージ初期バージョンを追加（kabusys.__version__ = "0.1.0"）。

- 実行用スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックして警告を出力。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を利用）。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化する。
    - データディレクトリに配置された停止フラグファイル（data/stop_requested.flag）検出で安全終了。
    - DuckDB 接続を併用（分析用 DB）。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - Paper Trading (`KABUSYS_ENV=paper_trading`) 時は MockBrokerClient を使用し、専用 SQLite（デフォルト: data/paper_trading.db）で本番 DB と完全分離。
    - Broker クライアント生成（BrokerClientFactory）と OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - ExecutionEngine を別スレッドで起動。停止フラグ（data/stop_requested.flag）を検知すると安全にエンジン停止を試みる。
    - 実行 PID ファイル path をサポート（data/execution.pid）。

- 設定管理
  - config.py
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）に基づく .env 自動読み込み機能を追加（環境変数で無効化可: KABUSYS_DISABLE_AUTO_ENV_LOAD）。
    - .env パーサーはコメント、export プレフィックス、シングル/ダブルクォート、エスケープシーケンス、インラインコメントに対応。
    - .env 読み込み時に OS 環境変数を保護するための protected 上書き制御を実装。
    - Settings クラスを導入し、J-Quants / kabu API / LINE / DB / 監視 / システム関連の設定をプロパティとして提供。
    - PAPER_FILL_MODE の値検証（instant/partial/never/reject）や PAPER_TRADING_SQLITE_PATH のサポート。
    - 各種閾値（CPU/MEM/DISK）や PID/KILL フラグ設定をプロパティ化。
    - 環境種別検証（development / paper_trading / live）とログレベル検証を実装。

- 設定ユーティリティ / CLI
  - config_setup.py
    - .env 初期作成・更新の対話式ウィザードを追加。デフォルト値、選択肢、シークレット入力、保存確認をサポート。
    - 生成された .env のテンプレートヘッダにはコミット禁止の注意書きを含む。
  - validate_config.py
    - 起動前に .env と config/*.yaml の基本的整合性をチェックする CLI を追加。
    - 必須環境変数の未設定検出、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在およびパース検証（PyYAML がある場合）などを実装。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告を FAIL 扱いにできる。

- モニタリング / レポート
  - monitoring_db 初期化ユーティリティ（init_monitoring_db）を利用して監視テーブルの存在を保証（冪等）。
  - tools/paper_verification_report.py
    - ペーパートレード用検証レポート生成スクリプトを追加。期間指定（--from / --to）と DB 指定（--db）をサポート。
    - 稼働率（uptime）、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を算出し PASS/FAIL を判定する閾値を定義。
    - P95 計算、NULL/データ不足への安全なハンドリング、SQLite の存在チェックとエラーメッセージを実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で並べ上位 N を選択（同点時は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分を実装。
    - calc_score_weights: スコア正規化配分を実装。全スコアが 0 の場合は等分配へフォールバックし警告を出力。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター別エクスポージャに基づき、セクター上限を超えたセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に基づく資金乗数を返す。未知レジームは警告の上 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じた発注株数計算を実装。
    - risk_based: 損切り幅とリスク許容率から個別株数を算出。
    - equal/score: weight に基づく配分と per-position / aggregate の上限を考慮。
    - 単元株（lot_size）丸め、cost_buffer（手数料・スリッページ見積り）考慮、aggregate cap を越えた場合のスケールダウンと残差の配分ロジックを実装。
    - 価格欠損時のスキップとログ出力に対応。

- リサーチ / ファクター計算
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュールを追加（prices_daily / raw_financials を参照）。
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（ATR20）、流動性（20日平均売買代金 / 出来高比率）等の計算を実装。
    - データ不足に対する安全な None 返却、計算範囲のバッファ設定を実装。

- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度設定ユーティリティを追加。Windows（psutil の priority constants）と POSIX 系（nice 値）を吸収しプラットフォーム非依存の呼び出しを提供。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。権限不足や未対応環境時には警告を出力してフォールバック。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

---

Notes / 注意事項:
- .env ファイルは絶対にリポジトリにコミットしないでください（config_setup のヘッダにも警告あり）。
- run_monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用します。開発・テスト環境で監視データを分離したい場合は sqlite_path を別途指定してください。
- Paper Trading 用の DB はデフォルトで data/paper_trading.db に保存され、本番データと分離されています（run_execution の挙動）。
- 一部の機能（YAML 検証など）は外部ライブラリ（PyYAML 等）がインストールされていることを前提とします。存在しない場合は該当チェックをスキップして警告を出力します。