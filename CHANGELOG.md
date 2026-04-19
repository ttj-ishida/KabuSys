KEEP A CHANGELOG
=================

すべての重要な変更点をこのファイルに記録します。

次のフォーマットは "Keep a Changelog" に準拠しています。
リリース日付はリポジトリ内のコードや注釈を元に推測しています。

[Unreleased]
------------

- なし

0.1.0 - 2026-04-19
------------------

Added
- パッケージ初期リリース: KabuSys 自動売買フレームワーク（日本株想定）。
  - パッケージバージョンは src/kabusys/__init__.py にて __version__ = "0.1.0"。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトの data/stop_requested.flag ファイルを検出して行う。
    - 監視は KABUSYS_ENV に関わらず production 相当の sqlite_path を使用して監視 DB に接続。
    - DuckDB への接続も確立し、監視ループ中に monitor.check_once() を呼ぶ。例外はログに記録しループ継続。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を用いて data/paper_trading.db（または env 指定）を使用し、本番 DB と分離して動作。
    - 起動前に停止フラグ（data/stop_requested.flag）をチェックし、既に立っている場合は起動をスキップ。
    - 実行はデーモンスレッドで run_session を行い、停止フラグ検出で engine.stop() を呼び安全に停止。実行中は execution.pid を利用。
    - RiskManager/RiskConfig のデフォルトパラメータ（例: max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定し初期 portfolio value は broker.get_available_cash() から取得。

- 設定管理
  - config.py
    - Settings クラスを追加し、環境変数から設定を取得する統一 API を提供。
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。.env と .env.local の優先順処理をサポート。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env パースは引用符・エスケープ・インラインコメント等を考慮した独自実装。
    - 各種設定プロパティを提供（J-Quants トークン、kabu API 設定、DuckDB/SQLite パス、paper trading 用パス、PID/KILLフラグパス、閾値、環境種別検証 等）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）や KABUSYS_ENV の許容値検証を実装。

  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
    - J-Quants / kabu API 等の必須項目やログレベル、データベースパス、Kill Switch 振る舞いの設定などをサポート。
    - 現状値の読み込み、シークレットのマスク表示、保存前の確認、ファイル書き込みロジックを実装。

  - validate_config.py
    - .env および config/*.yaml の起動前検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パス親ディレクトリ存在チェック、config YAML の存在・パース検証（PyYAML が無ければ警告）を実行。
    - 本番環境向け追加チェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性）を実装。
    - --strict オプションで警告も失敗扱いに可能。

- ポートフォリオ構築ライブラリ (pure functions)
  - portfolio/portfolio_builder.py
    - 銘柄選定関数 select_candidates（スコア降順、同点は signal_rank でタイブレーク）。
    - 等配分 calc_equal_weights、スコア加重 calc_score_weights（全銘柄スコアが0 の場合は等配分にフォールバックして警告）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクターごとの既存エクスポージャーが閾値を超える場合に新規候補を除外する機能（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数（フォールバックと警告含む）。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に対応した株数決定ロジック実装。
    - risk_based: リスク許容率・損切り率に基づく株数計算。
    - equal/score: 重みと max_utilization を用いた配分。
    - 単元（lot_size）単位で丸め、単銘柄上限 max_position_pct、aggregate cap（available_cash）超過時のスケーリングと残差処理を実装。
    - cost_buffer により手数料・スリッページを保守的に見積もる挙動をサポート。
    - TODO: 将来的な銘柄別 lot_size の拡張を注記。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ログ初期化関数 setup_logging を提供。stdout 出力（StreamHandler）と日次ローテートファイル出力（TimedRotatingFileHandler、30日保持）をルートロガーに設定。
    - LOG_DIR/LOG_LEVEL 環境変数や引数での上書きに対応。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。

  - utils/process_priority.py
    - set_process_priority: Windows と POSIX を吸収して優先度（high/normal/low）を設定。psutil を利用し権限不足などは警告でスキップ。
    - set_cpu_affinity: 最初の N コアにプロセスを固定する機能を追加。未サポート環境や権限不足は警告でスキップ。

- 監視関連
  - monitoring_db の初期化呼び出しを run_monitoring/run_execution の起動時に行い、監視テーブルが存在することを保証（冪等）。
  - SystemMonitor / monitoring の基本的挙動（check_once の呼出し、例外ハンドリング）を導入。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード DB（デフォルト data/paper_trading.db）から検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime％）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）、リスク却下数 等を算出。
    - PASS/FAIL 判定の閾値（稼働率 99%、fill_rate 90%、send_rate 95%、P95 latency 200ms）を定義し、判定結果を標準出力に整形表示。
    - 日付フィルタ（--from/--to）と --db オプションに対応。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / Known issues / TODO
- portfolio.position_sizing: price が欠損 (0.0) の場合の取り扱いに関する注意と TODO。前日終値や取得原価等のフォールバックを検討すべき箇所あり。
- research/factor_research.py はファクター計算の骨子を用意しているが（モメンタム等）、実装途中の箇所（ファイルの末尾で途中切れ）や追加テストが必要な箇所がある。
- .env パーサーは独自実装（引用符やエスケープを考慮）だが、特殊ケースの完全網羅には追加テスト推奨。
- ログディレクトリ作成やプロセス優先度設定は実行環境の権限に依存するため、本番運用時は適切な権限設定を確認すること。
- validate_config の YAML 検証は PyYAML がインストールされている場合のみ内容検証を行う。未導入時は警告を出してスキップ。

ライセンス / その他
- 本 CHANGELOG はソースコード内のコメント・実装から推測して作成しています。実際の運用上の仕様やパラメータは README / ドキュメントや設定ファイルを参照してください。