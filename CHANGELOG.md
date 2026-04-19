# CHANGELOG

すべての重要な変更点をこのファイルに記録します。形式は Keep a Changelog に準拠します。  
リリースポリシー: 破壊的変更はメジャー、機能追加はマイナー、バグ修正はパッチに記載します。

すべてのバージョン履歴

## [0.1.0] - 2026-04-19
初回公開リリース。

### 追加
- 実行エントリ・監視エントリ
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 SQLite（data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）および MockBrokerClient を使用して本番 DB と完全分離して実行可能。
    - 起動時にプロセス優先度を "high" に設定し、停止フラグファイル (data/stop_requested.flag) と実行 pid ファイル (data/execution.pid) を用いて安全に停止制御を行う。
    - ExecutionEngine の依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler 等）を組み立ててスレッドで run_session を実行し、停止フラグ検知で安全に停止する仕組みを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化する（init_monitoring_db）。
    - 停止フラグ (data/stop_requested.flag) によるループ終了と KeyboardInterrupt のハンドリングを実装。

- 設定管理・初期化ツール
  - config.py: 環境変数 / .env 自動ロードと Settings クラスを追加。
    - プロジェクトルート (.git または pyproject.toml を探索) を基準に .env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
    - 環境変数のパースロジックでクォート / エスケープ / 行内コメントに対応。
    - 各種設定値（JQUANTS_REFRESH_TOKEN、KABU_API_*、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID/KILL フラグ関連、閾値等）をプロパティとして提供。
    - env 検証（KABUSYS_ENV / LOG_LEVEL の妥当性チェック）と is_live / is_paper / is_dev ヘルパーを実装。
  - config_setup.py: 対話式 .env ウィザードを追加。
    - 対話入力で .env を生成/更新し、秘密値はマスク表示、デフォルト／既存値の再利用に対応。
    - 出力は .env ファイルに書き込み（注意書きとテンプレート付き）。
  - validate_config.py: 起動前に設定不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ存在確認、config/*.yaml の存在および PyYAML があればパース検証を実行。
    - --strict を指定すると警告も失敗扱い（exit(1)）にできる。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を返す。
    - calc_equal_weights: 等金額配分 (1/N) を提供。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等金額へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限を適用し、既存ポジションのセクター比率が閾値を超える場合に同セクターの新規候補を除外。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた資金乗数を返す（未知レジームは警告を出して 1.0 でフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づいて発注株数を決定。
      - リスクベース（risk_pct, stop_loss_pct）方式と、等配分・スコア配分方式をサポート。
      - 単元（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）、cost_buffer（手数料・スリッページ見積り）などを考慮した安全な丸めと再配分ロジックを実装。

- ユーティリティ
  - utils/logging_setup.py:
    - すべての起動スクリプトで共通利用できるロギング設定ユーティリティを追加。
    - stdout への StreamHandler + 日次ローテーション (TimedRotatingFileHandler) によるファイル出力（デフォルト logs/<app_name>.log）。
    - LOG_DIR 環境変数や引数でログディレクトリを指定可能。ディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py:
    - プラットフォーム差分を吸収するプロセス優先度設定機能を追加（Windows: HIGH_PRIORITY_CLASS 等 / POSIX: nice 値）。
    - CPU affinity 固定機能（set_cpu_affinity）を追加。権限制約や未対応 OS では警告でスキップ。

- ツール
  - tools/paper_verification_report.py:
    - ペーパートレード用 SQLite を解析して検証レポートを生成するスクリプトを追加。
    - 指標: 稼働率 (uptime)、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ、リスク却下数 等。
    - CLI オプション: --from / --to で期間指定、--db で DB パス指定（環境変数 PAPER_TRADING_SQLITE_PATH も使用可）。
    - デフォルトの合格基準（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200 ms）を定義し PASS/FAIL を判定。

- 研究用モジュール
  - research/factor_research.py（モメンタム等のファクター計算を提供するモジュールの実装を追加）。
    - DuckDB 接続を受け prices_daily / raw_financials を参照して Momentum / Value / Volatility / Liquidity 等のファクターを計算する方針と一部定数（期間等）を実装。  

### 変更
- パッケージメタ
  - __init__.py に __version__ = "0.1.0" を設定。
  - パッケージの __all__ に主要モジュールを追加（data, strategy, execution, monitoring）。

### 既知の挙動・注意点
- .env 自動ロード:
  - プロジェクトルートが検出できない場合は自動ロードをスキップする。
  - OS 環境変数はデフォルトで保護され、.env の上書きを防ぐ（.env.local は明示的に上書き可能）。
  - テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- run_monitoring は監視用 DB の初期化（init_monitoring_db）を行うが、監視は常に settings.sqlite_path（本番監視 DB）を使用する。
- run_execution は paper_trading モードのとき paper_sqlite_path を使用してデータ分離を行う。
- process_priority / CPU affinity の設定は権限や OS に依存し、失敗した場合は警告を出して処理を続行する（例: AccessDenied）。
- position_sizing や risk_adjustment は現状 DB 参照を行わない純粋関数群として設計。将来的に lot_size の銘柄別対応や price フォールバック（前日終値等）などの拡張を想定している（TODO コメントあり）。

### 既知の制限 / TODO
- research/factor_research.py は設計方針と定数を実装しているが、ファイル末尾での計算関数実装が途中で切れている（現状は作成中の可能性あり）。
- position_sizing の lot_size は全銘柄共通で扱う実装。銘柄別単元対応は将来の拡張予定。
- sector exposure 計算で price が欠損（0.0）の場合に過小評価される可能性があり、将来的に価格フォールバックの実装を予定。

以上が初回リリース (0.1.0) の主要変更点です。今後のリリースでは API の安定化、欠損データ処理の強化、テストカバレッジ拡充、設定検証の強化などを行う予定です。