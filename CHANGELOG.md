Keep a Changelog
=================
すべての変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

[Unreleased]
------------

- なし（初回公開版のみを含むリリースノートを作成しています）

[0.1.0] - 2026-04-18
-------------------

Added
- 基本機能を実装した初回リリースを追加。
  - 実行／監視用エントリポイント
    - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
      - 起動時にプロセス優先度を "high" に設定。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を利用する（BrokerClientFactory による振り分け）。
      - 実行中は PID ファイル管理（data/execution.pid）および停止フラグ（data/stop_requested.flag）に対応。バックグラウンドスレッドでエンジンを実行し、停止フラグ検出時にエンジンを停止。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。不正値はデフォルトへフォールバックして警告。
      - Monitoring は環境にかかわらず本番用 sqlite_path を参照して監視テーブルを初期化。
      - 停止フラグ検知でループ終了。KeyboardInterrupt による終了をハンドリング。
  - 設定・環境読み込み
    - config.py: 環境変数と .env ファイルの読み込み・管理クラス（Settings）を実装。
      - プロジェクトルートの自動検出（.git または pyproject.toml）に基づいて .env 自動読み込みを行う（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
      - .env のパースは export プレフィックス、クォート内のエスケープ、インラインコメントの取り扱いに対応。
      - 各種プロパティを提供: duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, 各種しきい値や env/log_level 判定、paper_fill_mode の検証など。
  - 設定検証・ウィザード
    - validate_config.py: .env と config/*.yaml の起動前検証 CLI を実装。
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パス親ディレクトリ確認、YAML ファイルの存在とパース検証（PyYAML が無ければ警告）、本番環境向けの追加ガードを実装。
      - --strict オプションで警告も失敗とみなす振る舞いを提供。
    - config_setup.py: 対話式 .env 作成・更新ウィザードを提供。
      - 秘密値のマスク表示、選択肢/デフォルト表示、入力キャンセル時の取り扱い、ファイル書き出しテンプレートを実装。
  - ログ・プロセス管理ユーティリティ
    - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
      - stdout へ StreamHandler、日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定。
      - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
      - LOG_LEVEL / LOG_DIR の環境変数優先解決。
    - utils/process_priority.py: プロセス優先度（Windows・POSIX の差分吸収）および CPU affinity 設定を実装。
      - Windows: psutil の優先度クラスを利用（存在しない場合はフォールバック）。
      - POSIX: nice 値を調整。psutil.AccessDenied 等の例外は警告してスキップ。
      - set_cpu_affinity により最初の N コアへ固定可能（未サポート環境では警告）。
  - Execution 周辺コンポーネント（参照実装）
    - 実行系の組み立て例を含む（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み合わせ）。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec 等）および初期ポートフォリオ値を broker.get_available_cash() から取得。
  - ポートフォリオ構築（純粋関数）
    - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等重み（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコア全0時は等重みへフォールバックして警告。
    - portfolio/risk_adjustment.py: セクター上限適用（apply_sector_cap）、市場レジームに基づく乗数計算（calc_regime_multiplier）。未知レジーム時は 1.0 にフォールバックして警告。
    - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score をサポート）、単元株（lot_size）で丸め、aggregate cap によるスケーリング（残差配分ロジック含む）を実装。cost_buffer を考慮した保守的見積りをサポート。
  - 解析・検証ツール
    - tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツールを追加。
      - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）を集計し、閾値に基づいて PASS/FAIL を判定。
      - P95 計算関数、期間フィルタ、DB 存在チェックとエラーハンドリングを実装。
  - 研究用モジュール（骨格）
    - research/factor_research.py: Momentum/Value/Volatility/Liquidity の計算方針と定数を定義。DuckDB 接続を受け取る設計。モメンタム計算関数の骨子を実装開始（ファイル末尾で未完了の状態）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Known issues / Notes
- research/factor_research.py は途中で切れており実装が完了していない（calc_momentum の実装未完）。
- apply_sector_cap の価格欠損時のエクスポージャー過少見積りに関する TODO が記載されている（前日終値や取得原価でのフォールバック未実装）。
- .env の読み書きは簡易実装。非常に機密な運用では書き込みの原子性やファイルパーミッションを追加検討することを推奨。
- validate_config は PyYAML がない環境で YAML 内容検証をスキップして警告する。YAML 検証を有効にするには PyYAML をインストールすること。
- process_priority / set_cpu_affinity はプラットフォーム依存の権限により設定できない場合がある（警告してスキップ）。
- run_monitoring は監視 DB に常に sqlite_path（本番用）を使用する設計のため、テスト実行時の取り扱いに注意が必要。
- ログディレクトリ作成に失敗するとファイルローテーションが無効化され、標準出力のみでログが出力される。

Credits
- このリリースは KabuSys プロジェクトの初回パブリック実装を反映しています（モジュール群: config, utils, portfolio, execution 起動スクリプト, monitoring, tools, research）。

References
- Keep a Changelog: https://keepachangelog.com/en/1.0.0/