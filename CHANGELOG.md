CHANGELOG
=========

すべての重要な変更は「Keep a Changelog」フォーマットに従って記載しています。  
このファイルはコードベースから推測して作成した変更履歴（初期リリース）です。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-18
--------------------

Added
- 基本アプリケーション初期実装を追加。
  - パッケージメタ情報:
    - kabusys.__version__ = "0.1.0"
- 起動スクリプト / CLI を追加:
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを提供。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトの data/stop_requested.flag ファイルで検知。
    - 監視は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを提供。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db 等）を使用し、本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）検知および PID ファイル管理（data/execution.pid）。
  - config_setup.py
    - .env の対話式ウィザード。初期 .env の作成・更新を支援。
    - 機密値はマスク表示、保存前に確認を行う。保存後は .env を出力（Git へコミットしないよう注意喚起）。
  - validate_config.py
    - .env と config/*.yaml の事前検証 CLI。
    - --strict を指定すると警告も失敗 (exit 1) として扱う。
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを提供。
    - CLI 引数で期間指定 (--from, --to) と DB パス指定 (--db) が可能。
    - 検証基準（稼働率・注文成功率・送信率・P95 レイテンシ等）を定義し PASS/FAIL 判定を出力。
- 設定管理と自動読み込み:
  - config.py
    - Settings クラスを導入し、環境変数取得・検証ロジックを提供。
    - .env 自動読み込み機能（プロジェクトルートが検出できる場合）を実装。読み込み順は OS 環境 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - 環境変数のパース処理は引用符・エスケープ・コメント処理に対応。
    - 各種設定プロパティ（duckdb/sqlite パス、paper_trading 用パス、PID/kill flag パス、しきい値など）を提供。
    - PAPER_FILL_MODE 値の検証（"instant","partial","never","reject"）。
- ポートフォリオ構築モジュール（純粋関数）:
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
    - スコアが全て 0 の場合は等配分へフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。
    - 未知レジームは警告を出し 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - ポジションサイズ計算（risk_based / equal / score）。
    - 単元株（lot_size）丸め、aggregate cap（利用可能現金に応じたスケーリング）、cost_buffer による保守的見積り、残余配分ロジックを実装。
    - いくつかのパラメータ（risk_pct, stop_loss_pct, max_position_pct, max_utilization 等）を受け取る。
- ユーティリティ:
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを提供。StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）をルートロガーへ設定。
    - LOG_DIR 環境変数や引数でログディレクトリを指定可能。ディレクトリ作成に失敗した場合はファイル出力をスキップしコンソールのみで継続。
  - utils/process_priority.py
    - プロセス優先度設定（set_process_priority）および CPU affinity 設定（set_cpu_affinity）を提供。
    - Windows / POSIX の差異を吸収し、psutil 利用時に権限エラー等をハンドリングして安全にフォールバック。
- Execution コンポーネントの組立て（run_execution 内の推定構成）:
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等を統合する起動フローを実装（ファクトリ利用・依存注入を想定）。
  - RiskManager にデフォルト RiskConfig 値を設定（max_position_pct=0.20 等）、initial_portfolio_value を broker.get_available_cash() から初期化。
- 監視 DB 初期化:
  - monitoring.monitoring_db.init_monitoring_db を利用して監視用テーブルの存在を保証（冪等）。
- Paper Trading の評価・検証:
  - tools/paper_verification_report.py にて P95 計算、各種集計クエリ、閾値判定を実装。

Changed
- 新規リリースのための初期設計・API 契約を確定（ファイル配置、デフォルトパス、環境変数名、ログ出力ポリシー等）。

Fixed
- 該当なし（初期実装）。

Deprecated
- 該当なし。

Removed
- 該当なし。

Security
- 機密値（トークン・パスワード）は .env に保存する設計。ただし .env を Git にコミットしないよう明記している。

Notes / Known issues / TODO
- position_sizing.calc_position_sizes:
  - TODO: 将来的に銘柄別の lot_size を stocks マスタで管理するため拡張予定（現状は全銘柄共通 lot_size を想定）。
- risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少評価される可能性があり、前日終値などを使ったフォールバックを検討中（コード内に TODO コメントあり）。
- research/factor_research.py:
  - ファイル末尾が途中で切れているように見え、実装が未完または抜粋の可能性あり。実際のリリースでは完全実装とテストが必要。
- .env 自動読み込み:
  - 自動ロードを行う際、OS 環境変数は保護される（.env が既存 OS 環境を上書きしない / .env.local は上書き可能だが保護対象キーは除外）。
- プロセス優先度 / CPU affinity:
  - 実行環境によっては権限不足で設定に失敗する可能性があるが、エラーは警告で扱い処理を継続する設計。
- ログ出力:
  - コンソール出力は stdout を使用（cron 等からのリダイレクトを想定）。ログファイル出力に失敗してもプロセスは継続。

Acknowledgements
- この変更履歴は提供されたソースコードから推測して作成しています。実際のリリースノートでは、コミット単位の変更履歴や担当者・チケット番号などの追加情報を含めることを推奨します。