# Changelog

すべての重要な変更は Keep a Changelog の形式で記載します。  
このファイルはコードベースから推測して構成しています。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- セキュリティ (Security)

（注）日付は推測に基づき記載しています。

## [Unreleased]
- 特になし

## [0.1.0] - 2026-04-19
初回リリース（コードベースの現時点の機能を反映）。

### Added
- 基本ライブラリ・エントリポイント
  - パッケージ初期化: kabusys.__version__ = "0.1.0" を導入。

- 実行・監視用スクリプト
  - run_execution.py
    - ExecutionEngine 起動用エントリポイント。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント作成をサポート（Mock を含む実装想定）。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立て ExecutionEngine をスレッドで実行。
    - 停止制御: data/stop_requested.flag を検知すると engine.stop() を呼んで安全に終了。PID ファイルパス: data/execution.pid（デフォルト）。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を組み込み。initial_portfolio_value は broker.get_available_cash() から取得。

  - run_monitoring.py
    - SystemMonitor ポーリングループ起動用エントリポイント。
    - 起動時にプロセス優先度を "high" に設定。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値や 0 以下はデフォルトにフォールバックし警告を出力。
    - 監視は KABUSYS_ENV に関わらず production 相当の sqlite_path（デフォルト: data/monitoring.db）を使用する旨の注記。
    - 停止制御: data/stop_requested.flag を検知して監視ループを終了。

- 設定管理・ユーティリティ
  - config.py
    - 環境変数読み込み・ラッパを実装（Settings クラス）。
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を起点）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパーシングは export 形式、クォート、エスケープ、インラインコメントなどを考慮して堅牢に実装。
    - 多数の設定プロパティを提供（J-Quants / kabu API / LINE / DB / 監視閾値 / システム環境等）。
    - PAPER_FILL_MODE の有効値検証（instant, partial, never, reject）。
    - 環境 (KABUSYS_ENV) 検証（development, paper_trading, live）とログレベル検証。

  - config_setup.py
    - 対話式 .env 作成ウィザード。
    - デフォルト値、選択肢、シークレット入力扱い、既存 .env の読み込みと更新をサポート。
    - .env の書式化保存（.env に絶対コミットしない旨のヘッダを含む）。

  - validate_config.py
    - CLI ベースの設定検証ツール。
    - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）の存在確認。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック。
    - DUCKDB/SQLITE パスの親ディレクトリ存在チェック（自動作成の場合がある旨の警告）。
    - config/*.yaml の存在チェックと（PyYAML があれば）パース検証。
    - KABUSYS_ENV=live のときの追加ガード（LINE 未設定・KILL_FLAG_CLEAR_ON_START の危険設定など）。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - setup_logging() を提供。全起動スクリプトで共通のログ設定を行う。
    - stdout へ StreamHandler、日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log）を追加。バックアップ 30 日。
    - LOG_LEVEL / LOG_DIR の環境変数/引数優先順位に対応。
    - ログディレクトリ作成失敗時はファイル出力をスキップし stdout のみで継続。

  - utils/process_priority.py
    - set_process_priority(level) で Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収して優先度を設定。
    - set_cpu_affinity(cpu_count) で最初の N コアに固定する機能を提供（アクセス権限等により失敗した場合は警告でスキップ）。
    - 無効値や未対応 OS では安全にスキップして警告ログを出力。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates(): score 降順、同点は signal_rank 昇順で上位 N を選択。
    - calc_equal_weights(): 等金額配分（1/N）。
    - calc_score_weights(): スコア正規化配分。全銘柄スコアが 0 の場合は等配分にフォールバックし WARNING。

  - portfolio/risk_adjustment.py
    - apply_sector_cap(): セクター集中を計算し、既存ポジションで上限超過しているセクターの新規候補を除外。'unknown' セクターは除外対象外。sell_codes をエクスポージャー計算から除外。
    - calc_regime_multiplier(): market レジームに応じた資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3）、未知レジームは 1.0 にフォールバックして警告。

  - portfolio/position_sizing.py
    - calc_position_sizes(): allocation_method に応じた株数決定を実装（risk_based / equal / score）。
    - lot_size（単元）で丸め、1 銘柄上限（max_position_pct）、全体投下率（max_utilization）を考慮。
    - risk_based: risk_pct・stop_loss_pct に基づくポジションサイズ算出。
    - aggregate cap 超過時のスケールダウンと残余キャッシュによる lot 単位での再配分（端数処理の安定化ロジック）。

- リサーチ / ファクター計算（骨子）
  - research/factor_research.py
    - DuckDB 接続を受け prices_daily / raw_financials から Momentum / Value / Volatility / Liquidity の計算を行う設計（関数 calc_momentum 等の骨組み）。移動平均・ATR・複数期間のモメンタム等を想定。
    - 実装方針に関するコメントや定数（期間設定、スキャンバッファ等）を含む。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプト。
    - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH / data/paper_trading.db。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）、リスク却下数などを集計して PASS/FAIL 判定（閾値はソース内定義）。
    - コマンドライン引数: --from / --to / --db。

### Changed
- （初回リリースのため履歴上の変更はなし）

### Fixed
- （初回リリースのため修正履歴はなし）

### Security
- .env を生成する際に「.env を絶対に Git にコミットしないこと」と明示するヘッダを追加（config_setup.py）。
- 必須環境変数が未設定の場合に起動前チェックで検出可能（validate_config.py / config.Settings._require）。

### Notes / 動作上の重要な挙動（ユーザー向け）
- 環境変数読み込み順序
  - OS 環境変数 > .env.local > .env（自動ロードはプロジェクトルートが検出できない場合スキップ、無効化フラグあり）。
- Paper Trading の DB 分離
  - paper_trading 環境では発注関連ログ等を data/paper_trading.db に保存し、本番監視 DB（data/monitoring.db）と分離。
- 監視ループの停止方法
  - data/stop_requested.flag を作成することで監視/実行を安全に停止できる（実行中に検知して順次終了処理を行う）。
- ログ出力
  - コンソールは stdout、ファイルは日次ローテーション（30 日保持）。ログディレクトリ作成に失敗しても stdout 出力は保証。
- 環境変数の細かい仕様
  - PAPER_FILL_MODE の有効値制約、KILL_FLAG_CLEAR_ON_START の安全上の注意（validate_config のガード）。

---

将来的なリリースでは各モジュールの更なる詳細（ExecutionEngine 本体、SystemMonitor 実装、factore_research の完全実装、テスト、ドキュメント）に関する変更履歴を追加してください。