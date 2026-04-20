# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

（次回リリースに向けた未リリースの変更点をここに記載してください）

---

## [0.1.0] - 2026-04-20

最初の安定版リリース。システム全体の起動スクリプト、設定管理、検証ツール、ポートフォリオ構築ロジック、ユーティリティ群、および Paper Trading 向けレポートを含む一連の機能を追加しました。

### Added
- 実行/監視ランナー
  - run_execution.py: ExecutionEngine を起動するエントリポイント。  
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を使用することで本番 DB と完全分離。  
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine の起動処理を実装。  
    - data/execution.pid を PID ファイルとして利用し、data/stop_requested.flag による外部停止フラグ検知に対応。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。  
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。  
    - 監視は環境にかかわらず本番 sqlite_path（監視 DB）を使用する仕様。停止フラグ（data/stop_requested.flag）検知でループ終了。  
    - 起動時にプロセス優先度を上げる処理を実行。

- 設定管理
  - config.py: 環境変数読み込み・ラッパー Settings を実装。  
    - 自動でプロジェクトルート（.git または pyproject.toml）を探索し、`.env` / `.env.local` を読み込む（OS 環境変数優先）。自動読み込みを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。  
    - 必須値取得ヘルパー、env の妥当性検証（KABUSYS_ENV/LOG_LEVEL など）、Paper Trading 関連設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）、監視閾値（CPU/MEM/DISK）などのプロパティを提供。  
  - config_setup.py: 対話式ウィザードで `.env` を生成・更新する CLI を追加。秘密項目はマスク表示、既存値の読み込み／デフォルト適用、保存前の確認を実装。

- 設定検証ツール
  - validate_config.py: .env と config/*.yaml の検証 CLI を追加。  
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML パース検証（PyYAML がインストールされている場合）、本番環境用のガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の警告）などを実装。  
    - `--strict` オプションで警告を FAIL 扱いにできる。

- Paper Trading 検証・分析ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite から検証レポートを生成する CLI。  
    - 稼働率（uptime）、注文成功率（filled/created）、送信率（sent/created）、リスク却下数、API レイテンシ（平均・最大・P95）を計算して PASS/FAIL 判定を出力。  
    - 日付レンジ指定（--from / --to）と DB パスの上書き（--db / 環境変数）に対応。  
    - P95 の計算、データ欠落時のフォールバックを実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選定と重み計算（select_candidates, calc_equal_weights, calc_score_weights）。  
    - スコアが全て 0 の場合は等金額配分にフォールバック（警告出力）。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）。  
    - セクター上限を超える既存エクスポージャーに対する候補除外ロジック、レジーム（bull/neutral/bear）に応じた投下資金乗数を提供。
  - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score）。  
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケーリング、コストバッファ（手数料/スリッページ見積）を考慮した配分ロジックを実装。残差処理で lot 単位での追加配分を行う。

- 研究用ファクター計算（基盤）
  - research/factor_research.py（未完の箇所あり）: DuckDB を用いたファクター計算基盤を追加。モメンタム、MA200 乖離、ATR、流動性等の計算を想定。

- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。  
    - StreamHandler を stdout に出力、TimedRotatingFileHandler による日次ローテーション（デフォルト logs/、保持 30 日）を設定。既存ハンドラの二重登録防止やログディレクトリ作成失敗時のフォールバックを実装。  
  - utils/process_priority.py: Windows/Linux/macOS 向けのプロセス優先度設定と CPU affinity 設定ユーティリティを追加。  
    - 標準的な優先度レベル（high/normal/low）を提供し、権限不足時は警告を出してスキップする。

- パッケージ基礎
  - パッケージ初期化 (kabusys.__init__.py) にバージョン "0.1.0" を追加。

### Changed
- （初回リリースのためなし）

### Fixed
- （初回リリースのためなし）

### Notes / Usage hints
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須。validate_config で事前検査できます。
- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml 基準）を発見すると .env および .env.local を自動読み込みします（既存 OS 環境変数は上書きされません）。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。
- Paper Trading 分離:
  - 実行エンジンはペーパートレード時にデータベースを分離して動作するよう設計されています（デフォルト: data/paper_trading.db）。
- 監視ループ:
  - run_monitoring は監視 DB（sqlite_path）を環境にかかわらず使用します。ポーリング間隔は `MONITOR_POLL_INTERVAL` で上書き可能（1 秒以上の整数）。
- ログ:
  - デフォルトのログディレクトリは `logs/`。LOG_DIR 環境変数または setup_logging の引数で変更可能。ファイル出力に失敗した場合でもコンソール出力は継続します。
- プロセス優先度/CPU affinity:
  - 起動スクリプトは初動でプロセス優先度を "high" に設定しようとします。実行環境や権限によっては設定に失敗して警告が出ます。

---

（以降のリリースでは Unreleased セクションの内容を移し、日付を更新してください）