# CHANGELOG

すべての変更は「Keep a Changelog」仕様に準拠して記載されています。  
このリポジトリはセマンティックバージョニングを使用します。

## [Unreleased]

（現在なし）

## [0.1.0] - 2026-04-18

初期リリース。自動売買システム「KabuSys」の基本機能群を実装しました。主な追加点は以下のとおりです。

### Added
- 全体
  - パッケージの初期バージョンを設定（__version__ = "0.1.0"）。
  - ログ、プロセス管理、設定、実行・監視スクリプト、ポートフォリオ構築、リサーチ・ツール類を含む基本モジュール群を追加。

- 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能（プロジェクトルートを .git / pyproject.toml で探索）を実装。
  - .env の優先順位: OS 環境変数 > .env.local > .env。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DBパス / 監視閾値 / 実行環境判定など）。
  - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
  - 環境値の必須チェックで未設定時に ValueError を投げる _require() を導入。

- 設定検証 CLI（src/kabusys/validate_config.py）
  - .env と config/*.yaml の事前検証を行う CLI を追加。
  - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL、DBパス、YAML の存在とパース検証、ライブ環境向け追加警告などを実装。
  - --strict オプションで警告を FAIL 扱いにできる。

- 設定ウィザード CLI（src/kabusys/config_setup.py）
  - 対話式ウィザードで .env を作成・更新するツールを追加。
  - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE*, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START）を備える。
  - 既存 .env の読み込み、シークレットマスク表示、保存確認を実装。

- 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
  - ExecutionEngine を起動するエントリポイントを追加。
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（デフォルト: data/paper_trading.db）で本番 DB と完全分離。
  - Execution 用の PID ファイル、停止フラグ（data/stop_requested.flag）による安全停止サポート。
  - 依存コンポーネントの組み立て（BrokerFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine）の初期化ロジックを実装。
  - RiskManager 初期設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を含む。

- 監視ポーリングスクリプト（src/kabusys/run_monitoring.py）
  - SystemMonitor をポーリングで実行する起動スクリプトを追加。
  - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒、0 以下はデフォルトにフォールバックして警告）。
  - 監視は環境にかかわらず本番 sqlite_path を使用する設計。停止フラグで安全に終了。

- ツール: Paper Trading 検証レポート（src/kabusys/tools/paper_verification_report.py）
  - ペーパートレード履歴から稼働率・注文成功率・送信率・レイテンシ等を集計してレポート出力する CLI を実装。
  - デフォルト DB パスは PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。
  - P95 計算、期間フィルタ、閾値による PASS/FAIL 判定（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を実装。

- ポートフォリオ構築（src/kabusys/portfolio/*.py）
  - 銘柄選定と重み算出（select_candidates, calc_equal_weights, calc_score_weights）。
    - calc_score_weights は全銘柄スコアが 0 の場合に等金額配分へフォールバックして警告を出力。
  - リスク調整（apply_sector_cap, calc_regime_multiplier）。
    - セクター集中上限 (max_sector_pct) を超えたセクターの新規候補を除外する apply_sector_cap。
    - 不明セクター ("unknown") は除外対象としない。
    - レジーム乗数: bull=1.0, neutral=0.7, bear=0.3、未知は 1.0 にフォールバックして警告。
  - 発注株数算出（calc_position_sizes）
    - risk_based / equal / score の配分方式をサポート。
    - 単元株（lot_size）で丸め、1銘柄上限・aggregate cap・コストバッファを考慮したスケーリングロジックを実装。
    - 価格欠損時のスキップ、利用可能現金に応じたスケールダウン、余りの繰り上げ配分ロジックなどを備える。

- ユーティリティ
  - ロギング設定（src/kabusys/utils/logging_setup.py）
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - ログレベルとログディレクトリ解決順を実装。ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールのみで継続。
  - プロセス優先度 / CPU affinity（src/kabusys/utils/process_priority.py）
    - Windows と POSIX を吸収した優先度設定（high/normal/low）を実装。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity() を実装。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- リサーチ（src/kabusys/research/factor_research.py）
  - ファクター計算モジュールを追加（モメンタム・MA200乖離・ATR・出来高系の計算方針を記述）。
  - DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。関数 calc_momentum の骨子を含む（将来的な実装拡張のための定数・方針を定義）。

### Changed
- （初期リリースのため、履歴上の変更なし）

### Fixed
- （初期リリースのため、履歴上の修正なし）

### Security
- （該当なし）

---

注:
- 各 CLI ツールはコマンドラインから直接実行可能（python -m kabusys.validate_config 等）。
- .env ファイルは機密情報を含むため絶対にリポジトリにコミットしないでください（config_setup.py のヘッダにも注意喚起あり）。
- 今後のリリースでは ExecutionEngine / SystemMonitor / リサーチ計算の具体実装（外部依存の注入、ユニットテスト追加、エラー処理の強化など）を順次追記予定です。