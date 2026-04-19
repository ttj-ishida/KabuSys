# Changelog

すべての注目すべき変更はこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠します。

現在のパッケージバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-19

初回リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しました。主な追加内容は以下のとおりです。

### Added
- 基本パッケージ情報
  - パッケージメタ情報を追加（src/kabusys/__init__.py, __version__ = "0.1.0"）。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時は専用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離して動作する仕組みを実装。
    - BrokerClientFactory を用いたブローカークライアント生成（実稼働/モックの切替）。
    - エンジンはスレッドで起動し、data/stop_requested.flag の検知で安全に停止する仕組みを実装。
    - 実行時 PID ファイルの扱い（data/execution.pid）に対応。
    - RiskManager, OrderManager, Reconciler 等の組み立て処理を追加。RiskConfig にデフォルトパラメータを導入し、初期ポートフォリオ値は broker.get_available_cash() を参照して設定。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下の値は無効として警告しデフォルトにフォールバック。
    - 監視プロセスは KABUSYS_ENV にかかわらず本番用の sqlite_path を使用して監視データを一元管理。
    - 停止フラグ（data/stop_requested.flag）検知でループを正常終了。

- 環境設定 / 検証
  - config.py
    - .env 自動読み込み（.env → .env.local、OS 環境変数優先）を実装。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサ実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
    - Settings クラスで主要設定値（DB パス、API トークン、閾値、環境判定フラグ等）をプロパティとして提供。値検証・デフォルト解決を行う。
  - config_setup.py
    - 対話式ウィザードで .env を生成/更新する CLI を追加。シークレット値は表示をマスク。生成テンプレートで .env 書き込みを行う。
  - validate_config.py
    - 起動前の設定検証 CLI を追加（必須環境変数のチェック、KABUSYS_ENV 検証、LOG_LEVEL、DB パス、config/*.yaml の存在/パース検証、live 環境向け警告等）。
    - --strict モードで警告を失敗扱い（exit(1)）にできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一ログ初期化ユーティリティを追加。ルートロガーに stdout 出力（StreamHandler）と日次ローテートのファイル出力（TimedRotatingFileHandler）を設定。
    - ログディレクトリ作成失敗時はファイル出力を無効化してコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR の解決ロジックを実装。
  - utils/process_priority.py
    - psutil を使ったプロセス優先度設定（Windows と POSIX を吸収）。set_process_priority(level) / set_cpu_affinity(cpu_count) を提供。
    - アクセス権限等で設定に失敗した場合は警告を出してスキップ。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - シグナルの候補抽出（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装（スコアが全て 0 の場合に等金額へフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用（apply_sector_cap）を実装。既存保有のセクター別時価計算と上限超過セクターの除外ロジックを提供。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear）を実装。未知レジームは警告して 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に基づく株数計算を実装。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash を超える場合のスケーリング）および残差ロジックを実装。
    - cost_buffer（スリッページ・手数料見積り）を考慮した保守的評価を実装。

- リサーチ / ファクター基盤（骨組み）
  - research/factor_research.py
    - ファクター計算モジュールの骨組みを追加。Momentum, Value, Volatility, Liquidity 等の計算方針、DuckDB 経由での実装方針を文書化。momentum 計算関数 calc_momentum の実装を開始（ファイル末尾で未完の可能性あり）。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード結果を集計して検証レポートを出力するスクリプトを追加。
    - system_status/trade_logs/risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を算出し、しきい値（稼働率 99% 等）で PASS/FAIL 判定を行う。
    - CLI で期間指定（--from/--to）や DB パス指定（--db）が可能。

- DB / 分析
  - DuckDB と SQLite を併用する設計を反映（duckdb 接続を受け取る API を想定）。
  - init_monitoring_db を監視・実行起動時に呼び、監視用テーブルの存在を保証（冪等に初期化）。

### Changed
- ー（初回リリースのため既存機能の変更なし）

### Fixed
- ー（初回リリースのためバグ修正履歴なし）

### Notes / Implementation details
- run_monitoring は KABUSYS_ENV に関わらず Settings.sqlite_path（監視 DB）を使用します。開発時に監視 DB を切り分けたい場合は環境変数 SQLITE_PATH を変更してください。
- run_execution は paper_trading モードで専用 DB（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離します。paper_trading モードでは MockBrokerClient を用いる想定です（BrokerClientFactory により実環境/モックを切り替え）。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を基に行います。配布後やテストで自動ロードしたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- logging_setup は stdout を使用するため、cron 等で stdout/stderr を一本化してリダイレクトしている運用に適しています。
- process_priority はプラットフォーム差異を吸収しますが、権限不足や未実装 API の場合は警告を出して継続します。
- portfolio の計算関数は副作用なしの純粋関数として設計されており、単体テストしやすい構造です。
- research/factor_research.py の実装はまだ継続作業の可能性があり、完全実装前に API が変わる可能性があります。

### Migration / Usage
- 初期セットアップ:
  - python -m kabusys.config_setup で .env を生成
  - python -m kabusys.validate_config で設定を検証
- 監視起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能
- 実行起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定するとペーパートレード用 DB を使用
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - または PAPER_TRADING_SQLITE_PATH 環境変数/--db で DB を指定

もし特定の変更点について詳細（関数単位の振る舞い、設定のデフォルト値、CLI の挙動など）を出力してほしい場合は、どの部分を掘り下げるかを教えてください。