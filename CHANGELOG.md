# CHANGELOG

すべての注目に値する変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-04-17

### Added
- 基本アプリケーションパッケージを追加（kabusys v0.1.0）。
  - パッケージメタ情報: __version__ = "0.1.0"。

- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - プロセス起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を使ったブローカークライアント生成に対応（Mock/実ブローカーの切り替え想定）。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み合わせて ExecutionEngine を構築。
    - RiskConfig のデフォルト値を定義（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。
    - 起動前に data/stop_requested.flag（プロジェクトルート/data/stop_requested.flag）をチェックし、フラグが立っていれば起動を中止。
    - 実行はデーモンスレッドで行い、停止フラグ検知時に engine.stop() を呼び出してシャットダウンする。PID ファイル（data/execution.pid）を使用。

  - run_monitoring.py
    - SystemMonitor ポーリングループのエントリポイントを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - Monitoring は KABUSYS_ENV に関わらず（本番）sqlite_path を使用して監視 DB を操作。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 終了はプロジェクト上位の data/stop_requested.flag による検知で行う。KeyboardInterrupt にも対応。
    - SQLite と DuckDB の接続を開き、監視スキーマの初期化を行う（init_monitoring_db）。

- 設定・環境管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートに .git または pyproject.toml を基準に探索）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env の各エントリのパースを堅牢化（コメント、クォート、export プレフィックス等に対応）。
    - Settings クラスを提供し、環境変数から型安全に設定値を取得する API を実装。
      - J-Quants / kabu ステーション / LINE / DB / 監視閾値などのプロパティを提供。
      - KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE のバリデーションを実装。
      - paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）や pid/kill flag パス等を取得可能。

  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加（python -m kabusys.config_setup）。
    - .env の既存値取り込み、シークレットはマスク表示、選択肢・デフォルト対応。
    - .env ファイルを書き出すロジックを実装（テンプレートとヘッダコメント付き）。

  - validate_config.py
    - 起動前の設定検証 CLI を追加（python -m kabusys.validate_config）。
    - 必須環境変数の未設定チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と YAML パース検証（PyYAML がインストールされている場合）。
    - KABUSYS_ENV=live 時の追加警告（LINE 通知設定や Kill Switch 設定など）。
    - --strict モードで警告を FAIL 扱いにするオプションを提供。

- ポートフォリオ構築（純関数ライブラリ）
  - portfolio/portfolio_builder.py
    - 候補銘柄選定 select_candidates（スコア降順、タイブレークに signal_rank）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全てのスコアが 0 の場合は等金額でフォールバック、警告ログ）。

  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有のセクター別時価から上限超過セクターの新規候補を除外）。
    - レジーム乗数 calc_regime_multiplier（"bull"/"neutral"/"bear" に基づく乗数。未知レジームは 1.0 でフォールバック）。
    - セクターが "unknown" の場合は上限適用をスキップする設計。

  - portfolio/position_sizing.py
    - 各銘柄の発注株数を計算する calc_position_sizes（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）に基づくスケーリングを実装。
    - cost_buffer を使った保守的コスト見積り、スケール後の残差に対する lot 単位での再配分ロジック。
    - 将来拡張用の TODO（銘柄別 lot_size 等）を記載。

- 研究（ファクター計算）
  - research/factor_research.py
    - DuckDB 接続を利用したファクター計算モジュールを追加。
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を DuckDB SQL ウィンドウ関数で計算。
    - calc_volatility: ATR（20日）、相対 ATR、平均売買代金、出来高比率などを計算するクエリ基盤を追加。
    - 入力は prices_daily テーブル、出力は date, code をキーとした dict のリスト。

- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）のプロセス優先度制御を実装（psutil ベース）。
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未対応 OS の場合は警告ログでスキップする堅牢性。

- 監視関連・レポート
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成 CLI を追加（python -m kabusys.tools.paper_verification_report）。
    - 指標: 稼働率 (uptime)、注文成功率 (fill_rate)、送信率 (send_rate)、P95 レイテンシ等を計算。
    - デフォルト閾値を定義（稼働率 >= 99.0%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms）。
    - --from / --to / --db オプションで期間と DB を指定可能。PAPER_TRADING_SQLITE_PATH 環境変数も参照。
    - SQLite のテーブルが存在しない場合に例外をハンドリングして N/A 扱いにする耐性を実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Known issues / Notes
- config._find_project_root() は .git または pyproject.toml を基準にプロジェクトルートを探索するため、配布形態や特殊環境下では自動 .env 読み込みがスキップされる可能性がある点に注意。
- risk_adjustment.apply_sector_cap:
  - price_map に価格が存在しない（0.0）場合、エクスポージャーが過小評価される可能性があり、将来的に前日終値などのフォールバックを検討する旨の TODO コメントあり。
- position_sizing:
  - 銘柄別の lot_size をサポートする拡張は未実装（TODO）。
- process_priority / set_cpu_affinity:
  - 実行環境で権限がない場合は設定に失敗し、警告を出して処理を継続する設計。
- Paper Trading の検証レポートは trade_logs / system_status / risk_logs 等のテーブル構造に依存する。テーブルが存在しない DB に対しては N/A やゼロ扱いで出力する仕様。
- run_monitoring は Monitoring 用 DB として Settings.sqlite_path（デフォルト: data/monitoring.db）を常に使用する設計のため、環境により挙動を分けたい場合は設定を調整する必要がある。

---

このリリースは主に以下を提供します:
- 本番運用向けの監視/実行エントリポイント、
- 環境設定のための対話ウィザードと検証ツール、
- ポートフォリオ構築・リスク調整・ポジションサイズ計算の純関数群、
- DuckDB を用いたファクター計算基盤、
- Paper Trading の検証レポート作成ツール、
- プロセス優先度や CPU affinity のユーティリティ。

引き続き、設定例や config/*.yaml のテンプレート生成スクリプト、ブローカークライアント実装や ExecutionEngine の詳細実装・テスト整備などを進めていく予定です。