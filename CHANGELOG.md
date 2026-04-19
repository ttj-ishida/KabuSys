CHANGELOG
=========

すべての注目すべき変更点は以下に記載します。フォーマットは「Keep a Changelog」に準拠しています。

[0.1.0] - 2026-04-19
-------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムのベース実装を追加。
- コア起動スクリプト
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。起動時にプロセス優先度を "high" に設定し、専用スレッドでエンジンを実行。停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) を利用した安全な起動/停止制御を実装。KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の SQLite（デフォルト: data/paper_trading.db）に記録する。
  - run_monitoring: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用し、停止フラグでループ終了を行う。

- 設定管理
  - config.Settings: 環境変数ベースの設定管理を追加。J-Quants / kabuステーション / LINE / DB / 監視閾値等のプロパティを備える。KABUSYS_ENV のバリデーションや paper_trading 用の paper_sqlite_path、PAPER_FILL_MODE のバリデーションなどを実装。
  - .env 自動読み込み: プロジェクトルート（.git または pyproject.toml を基準）を自動検出し、.env および .env.local を自動ロード。OS 環境変数は保護され、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサ: export 形式、シングル/ダブルクォート、エスケープ、インラインコメント等に対応する堅牢なパーサを実装。

- 設定補助 CLI / 検証
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新するツールを追加。各項目の説明・既存値の再利用・シークレットマスクを備える。
  - validate_config.py: 起動前検証ツールを追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在/パースチェック、live 環境向けのガード（LINE 通知、KILL_FLAG_CLEAR_ON_START の警告）などを行う。--strict モードで警告を FAIL 扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils.logging_setup.setup_logging: stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler、30日保持）をルートロガーに設定する共通ユーティリティを追加。ログディレクトリ作成失敗時はファイルハンドラをスキップして stdout のみで継続する。ログレベル・ログディレクトリの解決順を定義。
  - utils.process_priority: Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティを追加。権限不足や未対応環境では安全にフォールバックする。

- Execution コンポーネント（骨格）
  - ExecutionEngine／OrderManager／OrderRepository／Reconciler／RiskManager 等の組み立てを run_execution で行う。RiskManager のデフォルト RiskConfig（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定し、初期 portfolio value をブローカーから取得して初期化する。

- 監視（Monitoring）
  - monitoring の DB 初期化を保証する init_monitoring_db を起動時に呼び出し、SystemMonitor を sqlite + DuckDB 接続で初期化。監視ループはエラー発生時に例外をキャッチして次回ポーリングへ継続する。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: シグナル選定（select_candidates）と等金額・スコア加重の重み計算（calc_equal_weights / calc_score_weights）を追加。スコア全体が 0 の場合は等金額へフォールバック。
  - portfolio.risk_adjustment: セクター集中制限を行う apply_sector_cap（当日売却予定銘柄の除外対応、"unknown" セクターは制限除外）と市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear をマッピング、未知レジームは警告のうえ 1.0 でフォールバック）を追加。
  - portfolio.position_sizing: 複数の配分方式（risk_based / equal / score）に対応した株数計算を実装。ロット（lot_size）丸め、単銘柄上限、aggregate cap（available_cash を超える場合のスケーリングと余剰配分ロジック）、手数料・スリッページ見積り(cost_buffer) を考慮した安全な配分アルゴリズムを実装。

- DuckDB / 解析
  - DuckDB 接続を受け取り SQL + Python で処理する設計を採用。run_execution/run_monitoring で duckdb を開く。

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成ツールを追加。稼働率、注文成功率（Filled / Created）、送信率（Sent / Created）、P95 レイテンシ、リスク却下数などを算出し、閾値（稼働率 >=99%、成功率 >=90%、送信率 >=95%、P95 <=200ms）に基づき PASS/FAIL を判定。日付フィルタ（--from / --to）と DB パス指定が可能。P95 算出ロジックおよびデータ欠損時の耐性を実装。

- 研究用モジュール（骨格）
  - research.factor_research: Momentum / Value / Volatility / Liquidity 等のファクター計算を行うモジュールの骨格を追加。DuckDB の prices_daily / raw_financials を前提としており、Zスコア正規化等を想定。

Changed
- （初回リリースのため該当なし）

Fixed
- 環境変数パース・ロードの堅牢化: 不正な MONITOR_POLL_INTERVAL 値（0以下や非整数）を検出してデフォルトにフォールバックし警告を出す等、起動時の堅牢性を向上。
- ログディレクトリ作成失敗や権限不足時に、プロセスが停止せずコンソール出力のみで継続するように改善。

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 機密情報（トークン / パスワード）は .env に格納する想定。config_setup にてシークレット項目は入力時にマスク表示（出力時も **** 表示）。ログ内に secret を明示的に出力しない方針を採用。

Notes
- 本リリースは基盤機能（構成管理、起動スクリプト、ポートフォリオ構築ロジック、リスク制御ロジック、監視、レポート生成ツール）を提供する初期版です。各モジュール（ExecutionEngine、SystemMonitor、Broker クライアント実装、factor_research の詳細計算等）はさらに実装・テストが必要です。
- 設定ファイルテンプレート（config/*.yaml）は存在を想定しており、validate_config は PyYAML 未インストール時にパース検証をスキップして警告を出します。config/*.yaml の自動生成スクリプトがドキュメントや scripts に存在することを想定しています。

後続予定
- Engine / Monitor の統合テスト、Broker クライアントの実装拡充、銘柄別 lot_size 対応、価格フォールバックロジック（risk_apply 内の TODO）などを予定。