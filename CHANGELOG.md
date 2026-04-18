# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

(現時点では未リリースの変更はありません)

## [0.1.0] - 2026-04-18

初回リリース。以下は、本リポジトリに含まれる主な機能・改善点・補助ツールの要約です（コードベースから推測して記載）。

### Added
- 実行用エントリスクリプト
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite DB（data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）を使用し、MockBrokerClient を利用する設計をサポート。
    - プロセス優先度を起動時に "high" に設定する処理を追加（utils.process_priority）。
    - PID ファイル管理、停止フラグ（data/stop_requested.flag）検出による安全停止処理を実装。
    - ExecutionEngine 起動前に監視用テーブルを初期化（init_monitoring_db）して冪等性を確保。
    - RiskManager, OrderManager, Reconciler 等の組み立てとデフォルト設定値（例: max_position_pct, max_utilization 等）を組み込んだ起動フロー。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - デフォルトポーリング間隔 60 秒、環境変数 MONITOR_POLL_INTERVAL で上書き可能（不正値はデフォルトにフォールバックし警告を出力）。
    - 監視は実行環境に依らず本番 sqlite_path を使用する挙動を明示。
    - 停止フラグ（data/stop_requested.flag）や KeyboardInterrupt によるクリーンな終了処理を実装。

- 設定関連
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を探索）。
    - .env/.env.local の読み込み順と上書きルールを実装（OS 環境変数保護）。
    - 独自の .env パーサを実装し、export プレフィックス、引用符、エスケープ、インラインコメント等に対応。
    - Settings クラスを提供し、アプリケーション設定（パス、閾値、API トークン、環境判定 etc.）をプロパティ経由で取得。値の妥当性チェックを実装（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の検証）。
    - settings = Settings() のインスタンスをモジュールレベルでエクスポート。

  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を追加。
    - デフォルト値、選択肢、シークレット入力マスク、既存 .env の読み込みと再利用をサポート。
    - 保存前の確認と .env ファイルに対するテンプレート的な出力フォーマットを提供。

  - validate_config.py
    - 起動前に環境変数や config/*.yaml の基本チェックを行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性確認、ログレベル、DB パスの親ディレクトリ存在チェック、YAML パース検証（PyYAML があれば）などを実施。
    - `--strict` オプションで警告をエラー扱いにできる機能を追加。
    - 本番環境（KABUSYS_ENV=live）に対する追加警告（LINE 通知未設定、KILL_FLAG_CLEAR_ON_START の危険設定等）を実装。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/
    - portfolio_builder.py
      - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。
      - スコアが全て 0 の場合のフォールバック等をハンドリング。
    - risk_adjustment.py
      - セクター集中制限を適用する apply_sector_cap を追加（既存保有や売却予定の考慮、"unknown" セクターは除外しない挙動）。
      - 市場レジームに応じた資金乗数 calc_regime_multiplier を追加（bull/neutral/bear に対するマッピングと未知レジームの警告）。
    - position_sizing.py
      - ポジションサイズ計算 calc_position_sizes を実装。
      - allocation_method（"risk_based" / "equal" / "score"）に対応し、損切り率・リスクパーセント・最大ポジション比率・利用可能現金・単元株（lot_size）・手数料/スリッページ用バッファ(cost_buffer) を考慮した丸め・スケーリングロジックを備える。
      - aggregate cap（全銘柄合計が available_cash を超えた際のスケールダウン）と残差を考慮した再配分を実装。

- ユーティリティ
  - utils/logging_setup.py
    - アプリ全体で共通利用可能なログ設定ユーティリティを追加（StreamHandler を stdout、TimedRotatingFileHandler による日次ローテーション）。
    - ログレベル・ログディレクトリの解決ルール、既存ハンドラのクリーンアップ、30 日分のログ保持設定を提供。
    - ファイル出力できない場合にフォールバックしてコンソールのみにする堅牢設計。
  - utils/process_priority.py
    - Windows と POSIX（Linux/Mac/FreeBSD）を吸収するプロセス優先度設定機能を追加（nice / Windows priority クラスを利用）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加。権限エラーや非実装環境は警告でスキップ。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を算出し PASS/FAIL を判定する機能を実装。
    - デフォルト DB は data/paper_trading.db、コマンドライン引数で期間（--from/--to）・DB パス（--db）を指定可能。
    - P95 計算、欠損データの柔軟な扱い、閾値による判定ロジックを備える。

- 研究用モジュール
  - research/factor_research.py
    - モメンタムやボラティリティ等のファクター計算を行うための雛形を追加（DuckDB 接続を受けて prices_daily / raw_financials を参照する設計）。
    - 定数や計算方針（1M/3M/6M リターン、MA200 乖離、ATR、出来高指標等）を定義。ファイルは途中まで実装（calc_momentum の導入部分まで）。

- パッケージメタ情報
  - kabusys/__init__.py にバージョン情報 __version__ = "0.1.0" を追加。

### Changed
- なし（初回リリースのため既存機能の変更無し）。ただし、各モジュールに安全性やバリデーションを強化する実装が含まれている（設定値検証、例外ハンドリング、フォールバック動作）。

### Fixed
- なし（初回リリース）。コード内に多くの警告ログや例外処理が組み込まれており、実行時の堅牢性が向上している。

### Deprecated
- なし

### Removed
- なし

### Security
- 環境変数読み込み周りでは OS 環境変数を保護する設計（.env の上書き制御）を導入。
- .env テンプレート生成時に「絶対に Git にコミットしないこと」を明記。

---

Notes / 備考
- run_monitoring / run_execution はそれぞれ停止フラグ（data/stop_requested.flag）を監視して安全にシャットダウンする仕組みを持ちます。運用時は stop フラグや PID ファイル等の取り扱いに注意してください。
- config.py の自動 .env ロードはプロジェクトルート検出に依存します。配布後やテスト時に不要な場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- position_sizing 等の関数は純粋関数（副作用なし）として設計されており、ユニットテストが書きやすくなっています。
- research/factor_research.py は実装途中（ファイル末尾が切れている）なので、フル実装・テストが必要です。

今後のリリースでは、テストカバレッジの追加・ドキュメントの拡充・strategy/execution 実行フローの実稼働検証ログの整備などが想定されます。