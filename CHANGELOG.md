CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠しています。

注記
----
- このログは提供されたコードベースの内容から推測して作成しています。実装の詳細や将来の変更により内容が変わる可能性があります。

Unreleased
----------
（なし）

v0.1.0 - 2026-04-19
------------------

Added
- 基本パッケージの初期実装を追加
  - パッケージのバージョンを `__version__ = "0.1.0"` として定義。

- 実行スクリプト / エントリポイントを追加
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトにフォールバックして警告を出力。
    - 停止制御はプロジェクト直下の data/stop_requested.flag ファイルで行う。
    - 監視は設定に関わらず本番用 sqlite_path を使用して初期化（init_monitoring_db）。
    - duckdb を分析用に利用。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB（data/paper_trading.db）を使用し、MockBrokerClient により本番 DB と分離して動作する設計を明記。
    - エンジンは別スレッドで実行し、stop フラグ検知で安全に停止するループを実装。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理・環境読み込み機能を追加
  - config.py
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env と .env.local の読み込み順序を実装（OS 環境変数は保護）。
    - .env 行のパーサを実装し、export プレフィックス、クォート、エスケープ、インラインコメント等をサポート。
    - Settings クラスを実装し、各種設定（DB パス、API トークン、監視閾値、環境判定メソッドなど）をプロパティで提供。
    - PAPER_FILL_MODE のバリデーションや環境（development/paper_trading/live）の検証などを実装。

- 設定ユーティリティ CLI を追加
  - config_setup.py
    - 対話式ウィザードで .env の作成・更新を支援。
    - デフォルト値、選択肢、シークレット入力対応、既存値のマスク表示、保存前の確認を実装。
    - .env の読み書きロジック（既存読み取り・ファイル書き出し）を提供。

  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV や LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ確認、config/*.yaml の存在と安全に YAML パース（PyYAML が無ければスキップ）を実施。
    - KABUSYS_ENV=live 向けの追加警告（LINE 通知設定未設定、KILL_FLAG_CLEAR_ON_START の危険性など）。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築ライブラリを追加（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等分配（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て 0 の場合は等分配へフォールバックし警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（既存ポジションのセクター暴露計算と候補フィルタ）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（"bull"/"neutral"/"bear" をサポート、未知のレジームは警告のうえ 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数算出 calc_position_sizes を実装。
    - allocation_method に "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、総投下上限（max_utilization）、手数料・スリッページ緩衝（cost_buffer）を考慮したスケーリングロジックを実装。
    - 価格欠損時のスキップ、aggregate cap 超過時のスケーリングと残差処理（lot 単位での追加配分）を実装。

- 監視関連の DB 初期化/監視実装を参照する機能を追加（初期化呼び出し）
  - monitoring.monitoring_db.init_monitoring_db を利用して監視テーブルの冪等な初期化を行う呼び出しを run_monitoring, run_execution 両方で実行。

- 実行関連の骨子を追加（参照のみ）
  - 実行系のコンポーネント（BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等）を参照する起動フローを実装済み（各コンポーネント本体は別モジュールとして存在する想定）。

- ユーティリティ群を追加
  - utils/logging_setup.py
    - ルートロガー設定ユーティリティを追加。Console (stdout) と 日次ローテーションファイル出力 (TimedRotatingFileHandler) を設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル・ログディレクトリの解決順を明記（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定（set_process_priority）を実装。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
    - 権限不足や未対応 OS 時は警告を出力してスキップする堅牢設計。

- ペーパートレード検証ツールを追加
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）を読み、期間フィルタで検証レポートを生成。
    - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）を算出。
    - P95 は独自のパーセンタイル実装を使用。
    - デフォルト閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義し PASS/FAIL 判定を出力。
    - DB 存在チェック・OperationalError に対する保護を実装。

- 研究用ファクター計算の骨格を追加
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity などの計算方針と定数を定義。DuckDB 接続を受け取り prices_daily/raw_financials を参照する設計。
    - モメンタム計算のための定数や関数骨格を追加（ファイル末尾は途中のため実装継続中）。

Changed
- N/A（初回リリース）

Fixed
- N/A（初回リリース）

Removed
- N/A（初回リリース）

Security
- N/A（初回リリース）

Notes / 備考
- .env の自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。自動ロードはプロジェクトルートが検出できる場合のみ行う。
- run_execution は paper_trading モードをサポートし、本番 DB と完全分離する設計。実際のブローカークライアントの選択は BrokerClientFactory に委ねられる。
- ログ設定は起動スクリプトから必ず setup_logging を呼ぶことで統一的なログ管理を行うことを想定。
- process_priority の呼び出しは起動直後に行う設計で、実行環境により権限が必要になる場合がある。

今後の TODO / 既知の改善余地（コードからの推測）
- research/factor_research.py のモメンタム計算の実装完了とテスト追加。
- position_sizing の価格欠損時のフォールバック（前日終値や取得原価の利用）を実装。
- テストカバレッジの整備（ユニットテスト / CI）。
- 実行コンポーネント（ExecutionEngine 等）の詳細実装に対する統合テストと運用監視強化。
- config/*.yaml の生成ヘルパーや例ファイルの追加（scripts/generate_config.py の存在が期待されている）。

--- 

（以降のリリースや細かな修正は実装の差分に応じて本 CHANGELOG に追記してください。）