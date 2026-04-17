# CHANGELOG

すべての重要な変更点を記録します。形式は「Keep a Changelog」に準拠しています。

全般
- バージョン管理: v0.1.0 を初回リリースとして記録しています（リリース日: 2026-04-17）。
- パッケージ説明: KabuSys — 日本株自動売買システム。

Unreleased
- （現在のコードベースは初回リリース相当の機能セットを含みます。以降の変更はここに追記してください。）

v0.1.0 - 2026-04-17
-------------------

Added
- 実行用スクリプトを追加
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。プロセス優先度を "high" に設定して起動する。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離する設計を導入。
    - BrokerClientFactory によるブローカークライアント生成処理を導入し、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動する。
    - Engine は別スレッドで run_session を実行し、 data/stop_requested.flag により安全に停止可能。
    - 実行中の PID を data/execution.pid に記録するための pid_file オプションをサポート。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60 秒）。0 以下や不正な値はデフォルトにフォールバックして警告を出力。
    - 監視は環境に関わらず本番用 sqlite_path を使用する仕様（監視データを運用 DB に集約する運用方針）。

- 設定管理・支援ツールを追加
  - config.py
    - .env の自動ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env/.env.local の読み込み順序（OS 環境変数 > .env.local > .env）と override/protected 機構を実装。
    - .env 行パーサーを実装（export 句対応、クォート/エスケープ処理、インラインコメント処理）。
    - Settings クラスを追加し、環境変数から各種設定値（DB パス、KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を安全に取得・検証するプロパティを提供。
    - PAPER_FILL_MODE の有効値検証（instant, partial, never, reject）を実装。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。シークレットは入力表示や確認時にマスクし、生成した .env に注意書きを含める。
    - デフォルト値や選択肢の提示、既存 .env の読み込み/再利用をサポート。

  - validate_config.py
    - 起動前の設定検証 CLI を追加。必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と YAML パース検証（PyYAML が存在する場合）を行う。
    - KABUSYS_ENV=live のときに注意喚起（LINE 設定・KILL_FLAG_CLEAR_ON_START の危険設定など）を行う。
    - --strict フラグで警告を FAIL 扱いにするオプションを実装。exit コードを適切に設定。

- ポートフォリオ構築ライブラリを追加
  - portfolio.portfolio_builder
    - 候補選定 select_candidates（スコア降順、同点は signal_rank でタイブレーク）。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコアが0の場合は等配分にフォールバックし警告）。

  - portfolio.risk_adjustment
    - セクター集中制限 apply_sector_cap（既存保有のセクター別時価を計算し上限超過セクターの新規候補を除外。unknown セクターは除外対象外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をマップ、未知レジームは警告と共に 1.0 にフォールバック）。

  - portfolio.position_sizing
    - 発注株数計算 calc_position_sizes を実装（allocation_method: risk_based / equal / score 対応）。
    - リスクベース計算（risk_pct, stop_loss_pct など）と単元株（lot_size）丸め、per-stock cap と aggregate cap のスケールダウンロジックを実装。
    - cost_buffer を用いた保守的コスト見積りと、残余キャッシュに基づく小数端数処理アルゴリズムを実装。

- 研究用モジュールを追加
  - research.factor_research
    - DuckDB 接続を使ったファクター計算（Momentum、Value、Volatility、Liquidity の計算方針を実装）。
    - モメンタム calc_momentum（1M/3M/6M リターン、MA200 乖離）。
    - ボラティリティ calc_volatility（ATR、平均売買代金、出来高比）等の計算を SQL + Python で実装。

- ユーティリティを追加
  - utils.process_priority
    - set_process_priority(level) で Windows と POSIX を吸収した優先度変更を実装（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）。
    - set_cpu_affinity(cpu_count) でプロセスの CPU affinity を設定するヘルパを実装。
    - 権限不足や未対応 OS の場合は警告を出力して安全にフォールバック。

- モニタリング・検証ツール
  - monitoring.monitoring_db の初期化呼び出しを各起動スクリプトが行うようにし、監視テーブルが存在することを保証（冪等）。
  - tools.paper_verification_report.py
    - Paper Trading 用検証レポート生成ツールを追加。SQLite から稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数を集計して PASS/FAIL を判定する。
    - CLI オプション --from/--to/--db をサポート。閾値はスクリプト上で定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 <= 200 ms）。

Changed
- なし（初回リリースのため既存からの変更はありません）。

Fixed
- .env パーシングの堅牢化
  - export 句、クォート文字とバックスラッシュエスケープ、インラインコメントルールを正しく扱うように改良。これにより複雑な値やコメントを含む .env の読み込みが安定。

- 設定読み込みの安全化
  - プロジェクトルート探索を __file__ から遡る方式にして CWD に依存しないようにしたため、パッケージ配布後の自動 env ロードが安定。

- 起動時の kill/stop フラグ処理
  - run_execution/run_monitoring で data/stop_requested.flag を監視して、安全にループ終了やエンジン停止を行うロジックを追加（強制終了前にエンジンの stop() を呼ぶ）。

- Logging / エラーハンドリング
  - check_once() や各種処理で例外を捕捉してログ出力し、ループ継続を保証（監視ループが単一例外で停止しないように防御）。

Security
- .env ファイルに関する注意喚起を config_setup のヘッダに明示（.env を Git にコミットしない旨を推奨）。

Removed / Deprecated
- なし（初回リリース）。

Notes / Implementation details
- Settings.is_paper / is_live / is_dev プロパティを提供し、起動スクリプト側で環境に応じた挙動分岐を行いやすくしている。
- RiskManager の初期設定で initial_portfolio_value に broker.get_available_cash() を使用することで、実行時のブローカー残高を反映したリスク計算が可能。
- portfolio モジュールの関数は DB を参照せず純粋関数（メモリ内計算）で設計され、ユニットテストが容易。
- 一部関数は将来的拡張を見越した TODO コメント（例: 銘柄ごとの lot_size 管理や価格フォールバックなど）を含む。

開発者向け
- パッケージバージョンは __init__.__version__ = "0.1.0"。
- 今後のリリースでは各機能の詳細（例: ExecutionEngine の内部動作、BrokerClient 実装の差分、Strategy モジュール）を個別に CHANGELOG に追加してください。

-- End of CHANGELOG --