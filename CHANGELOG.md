CHANGELOG
=========

すべての重要な変更はこのファイルに記載します。フォーマットは Keep a Changelog に準拠します。

[0.1.0] - 2026-04-24
--------------------

Added
- 全体
  - 初回リリース (v0.1.0)。パッケージ名: KabuSys（日本株自動売買システム）。
  - パブリック API: kabusys パッケージのエントリポイントおよび __version__ を追加。

- 起動スクリプト
  - run_execution.py を追加:
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV が paper_trading の場合は専用の paper_trading DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離する挙動を実装。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine のデamon スレッド起動および停止フラグ処理を実装。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py を追加:
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出す。
    - Monitoring は環境にかかわらず本番用 sqlite_path を使用。
    - 停止フラグ (data/stop_requested.flag) の検出で graceful shutdown を実施。
    - 起動時にプロセス優先度を "high" に設定。

- 設定・構成
  - src/kabusys/config.py を追加:
    - .env ファイル（.env, .env.local）を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。プロジェクトルート検出は .git / pyproject.toml を基準に探索。
    - .env のパース機能を強化（export プレフィックス、シングル／ダブルクォート内のエスケープ、インラインコメントの扱いなどに対応）。
    - Settings クラスを提供し、J-Quants / kabuAPI / DB パス / Paper Trading 設定 / 監視しきい値 / 環境（development/paper_trading/live）/ログレベル等をプロパティで取得。PAPER_FILL_MODE のバリデーション等を実装。
    - settings インスタンスをデフォルトエクスポート。
  - src/kabusys/config_setup.py を追加:
    - 対話式の .env 作成・更新ウィザード。標準項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LINE 設定等）をサポート。
    - 既存 .env の読み込み・マスク表示・確認プロンプト・ファイル書き込みを実装。
  - src/kabusys/validate_config.py を追加:
    - 起動前チェック CLI。必須環境変数の存在確認、KABUSYS_ENV の妥当性チェック、ログレベルチェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および PyYAML によるパース検証（PyYAML 未インストール時はスキップ）を実装。
    - KABUSYS_ENV=live 時の追加警告（LINE 通知設定・KILL_FLAG_CLEAR_ON_START の危険性等）。
    - --strict オプションで警告を FAIL 扱いにできる。

- ログ・プロセス制御ユーティリティ
  - src/kabusys/utils/logging_setup.py を追加:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30世代）を一貫して設定するユーティリティ。
    - LOG_DIR / LOG_LEVEL の解決順、ディレクトリ作成失敗時のフォールバック、既存ハンドラのクリーンアップなどに対応。
  - src/kabusys/utils/process_priority.py を追加:
    - psutil を用いて Windows / POSIX（Linux/Mac/FreeBSD）を吸収したプロセス優先度設定 (high/normal/low) を提供。
    - CPU affinity 設定ユーティリティ（最初の N コアに固定）を追加。
    - 権限不足や未対応 OS での例外を捕捉し警告を出すよう頑健化。

- ポートフォリオ構築（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py を追加:
    - select_candidates: スコア降順で候補選定（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights: 重み計算。スコア合計が 0 の場合は等配分にフォールバック。
  - src/kabusys/portfolio/risk_adjustment.py を追加:
    - apply_sector_cap: 既存保有のセクター露出を計算し、max_sector_pct を超えるセクターの新規候補を除外するロジック。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジームは警告を出して 1.0 でフォールバック）。
  - src/kabusys/portfolio/position_sizing.py を追加:
    - calc_position_sizes: risk_based / equal / score の割当方式に対応した株数決定ロジック。
    - lot_size（単元）丸め、per-position 上限・aggregate cap、cost_buffer によるコスト保守見積り、スケーリング・端数配分ロジックを実装。

- 実行・監視関連 DB 初期化
  - 両起動スクリプトで init_monitoring_db を呼び出し、監視テーブル存在を保証（冪等）。

- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py を追加:
    - Paper Trading 用 SQLite DB（デフォルト: data/paper_trading.db）から集計を行い検証レポートを生成する CLI。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなどを集計し、閾値に基づいて PASS/FAIL を判定。
    - P95 算出ロジック、期間フィルタ（--from/--to）、DB パス解決 (--db or env) を実装。

- 研究用ファクター計算（骨組み）
  - src/kabusys/research/factor_research.py を追加:
    - DuckDB 接続を受け取り Momentum / Value / Volatility / Liquidity 等のファクターを計算するモジュールの骨組みを実装。モメンタム計算（calc_momentum）の実装を開始（営業日ベースの窓、MA200 乖離等の仕様記載）。（実装は一部で未完の箇所あり）

Changed
- パッケージ初期構成として、モジュール分割（execution, monitoring, portfolio, utils, research, tools）を整備し、テキストドキュメント（関数コメント・設計方針）を充実させた。

Fixed
- 起動スクリプトでの DB 接続後に finally ブロックで確実に接続を閉じるようにしてリソースリークを防止。

Notes / Implementation details
- .env の自動読み込みはプロジェクトルートが検出できない場合はスキップされるため、パッケージ配布後も安全に動作します。
- ログは stdout を基準に出力し、ファイルハンドラ作成に失敗した場合はコンソール出力のみで継続します（cron/task scheduler との併用を想定）。
- process_priority は権限がない場合に警告を出してスキップするため、一般ユーザーで実行しても致命的な失敗になりません。

Breaking Changes
- なし（初回リリースのため互換性に注意する変更はありません）。

Security
- なし（このリリースで扱っているのは主にローカル構成・処理ロジックであり、外部へのシークレット送信等は行いません。シークレットは .env に平文保存されるため、Git 管理に含めないよう注意してください）。

今後の予定（短期）
- research モジュールのファクター計算の完成（欠損処理・パフォーマンスチューニング）。
- ExecutionEngine / BrokerClient の統合テストと Paper Trading の挙動確認。
- config/*.yaml の雛形生成スクリプト（scripts/generate_config.py への言及あり）の提供。

---