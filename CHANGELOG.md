CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。
主にコードベースの初期実装・機能追加を想定してまとめています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-19
--------------------

Added
- 初期リリース (0.1.0)
  - パッケージ情報
    - パッケージバージョンを __version__ = "0.1.0" として追加。
  - 実行スクリプト
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 停止はプロジェクト data/stop_requested.flag ファイルを検知して行う。
      - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して DB に接続。
      - duckdb 接続も作成し、監視用 DB 初期化処理 init_monitoring_db を呼び出す。
    - run_execution.py
      - ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離（MockBrokerClient の使用は BrokerFactory が担う）。
      - 起動時にプロセス優先度を "high" に設定し、PID ファイル管理、停止フラグ (data/stop_requested.flag) による安全停止を実装。
      - ExecutionEngine を別スレッドで実行し、停止フラグで engine.stop() を呼び出して安全に終了するロジックを追加。
  - 設定管理
    - config.py
      - .env 自動ロード機能を実装（プロジェクトルートは .git / pyproject.toml を探索して決定）。
      - .env / .env.local の読み込み順序を採用し、OS 環境変数は上書きされないよう保護。
      - .env 解析処理で export 形式、シングル/ダブルクォート値、エスケープ、行内コメントの取り扱いに対応。
      - Settings クラスを実装し、J-Quants / kabu API / LINE / DB / 監視閾値 / 環境値等のプロパティを提供。値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を行う。
      - settings = Settings() をデフォルトインスタンスとして公開。
    - config_setup.py
      - 対話式 .env 作成ウィザードを追加。既存 .env の読み込み、項目ごとの説明、選択肢・シークレット入力に対応。
      - 生成された設定を .env に書き込む機能を提供（書き込みテンプレートを定義）。
    - validate_config.py
      - CLI 検証ツールを追加。必須環境変数や KABUSYS_ENV 値、ログレベル、DB パス、config/*.yaml の存在・パース（PyYAML が利用可能な場合）等をチェック。
      - --strict オプションで警告を失敗扱いにできる。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py
      - 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
      - スコアが全て 0 の場合は等配分にフォールバックし警告を出す。
    - portfolio/risk_adjustment.py
      - セクター集中制限を行う apply_sector_cap を実装（売却予定銘柄除外、"unknown" セクターは除外対象外）。
      - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をマップし、未知値は 1.0 でフォールバックし警告）。
    - portfolio/position_sizing.py
      - position サイズ計算 calc_position_sizes を実装。
      - allocation_method に "risk_based"/"equal"/"score" をサポート。lot_size（単元株）、cost_buffer、max_position_pct、max_utilization、aggregate cap といった制約を反映。
      - キャッシュ不足時のスケールダウンと残差処理（lot 単位での再配分）を実装。
  - ユーティリティ
    - utils/logging_setup.py
      - 統一的なログ設定ユーティリティを追加。stdout 出力用 StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30 日保持）をルートロガーに設定。
      - LOG_LEVEL / LOG_DIR / 引数でのオーバーライドをサポート。既存ハンドラをクリアして再設定する。
      - ログディレクトリ作成失敗時はファイル出力をスキップし、コンソール出力のみで継続。
    - utils/process_priority.py
      - プロセス優先度設定ユーティリティを追加。Windows/Linux/mac の差分を吸収して set_process_priority(level) を提供（"high"/"normal"/"low"）。
      - psutil を用いて nice 値や Windows 優先度クラスを設定。設定失敗時には警告を出してスキップ。
      - set_cpu_affinity(cpu_count) により最初の N コアにプロセスを固定する機能を追加（権限不足等は警告でスキップ）。
  - 監視 DB 初期化
    - monitoring.monitoring_db.init_monitoring_db を run スクリプトから呼び出すことで監視テーブルの存在を保証（冪等）。
  - 実行エンジン周辺インフラ（参照）
    - execution パッケージの各種コンポーネント（BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等）を起動処理と連携する形で組み立て。
    - RiskConfig のデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit breaker 等）を Execution 起動時に設定。
  - ツール
    - tools/paper_verification_report.py
      - ペーパートレード DB を解析して検証レポートを生成する CLI を追加。
      - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）を集計して判定（PASS/FAIL）を行う。
      - 判定閾値（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）を定義。
      - --from/--to/--db オプションをサポート。デフォルト DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。
  - research/factor_research.py（ファクター計算基盤）
    - Momentum / Value / Volatility / Liquidity 等のファクタ計算を行う設計を追加。DuckDB を用いた prices_daily / raw_financials 参照を前提にした実装の開始。 （ファイル末尾で計算関数実装中の状態あり）

Changed
- 初期リリースのため該当なし（新規追加のみ）。

Fixed
- 初期リリースのため該当なし。

Deprecated
- なし

Removed
- なし

Security
- 環境変数やシークレット（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE のトークン等）は .env に平文で保存されることに注意。config_setup の README にて .env を Git にコミットしない注意書きを追加。

Notes / 備考
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップされるため、パッケージ配布後に CWD に依存しない振る舞いを想定しています。
- logging_setup はログディレクトリ作成に失敗した場合にコンソールのみで動作するようフォールバックします。CI や限定環境での利用時に有用です。
- process_priority と CPU affinity は権限や OS に依存するため、実行環境によっては設定がスキップされます（警告が出るのみ）。
- research/factor_research.py は設計方針・定数・インターフェースを定義しており、ファクター計算の実装を継続予定です。

作者
- KabuSys チーム

---