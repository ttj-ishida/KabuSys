# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

※このファイルはコードベースから推測して作成した変更履歴です（実装内容・コメントを元に要約しています）。

## [Unreleased]

## [0.1.0] - 2026-04-20
初期リリース。システム全体のコア機能（設定管理、実行エンジン起動、監視、ポートフォリオ構築、ユーティリティ群、ペーパートレード検証ツール等）を実装。

### Added
- 全体
  - パッケージ初期化とバージョン設定（__version__ = "0.1.0"）。
  - モジュール群を提供：config, execution, monitoring, portfolio, utils, research, tools など。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - プロセス優先度を "high" に設定（set_process_priority を使用）。
    - KABUSYS_ENV によって Paper Trading 用 DB を分離（デフォルト: data/paper_trading.db）。paper_trading 環境では MockBrokerClient を使用する設計。
    - BrokerClientFactory、OrderRepository、OrderManager、RiskManager（デフォルトパラメータ含む）、Reconciler を組み立てて ExecutionEngine を起動。
    - ストップフラグ（data/stop_requested.flag）検知で安全に停止。PID ファイル管理（data/execution.pid）対応。
    - SQLite / DuckDB の接続初期化とクローズを行う。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
    - プロセス優先度を "high" に設定、停止フラグ検知でループ終了、check_once() の例外をログに記録してポーリング継続。
    - SQLite / DuckDB の接続初期化とクローズを行う。

- 設定関連
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml 基準）。優先順位は OS 環境 > .env.local > .env。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
    - .env パースの堅牢化（export に対応、クォート・エスケープ、インラインコメント扱い等）。
    - Settings クラスを提供し、環境変数アクセスをラップ（必須の _require()、各種プロパティ: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス、PID/kill flag、監視閾値、PAPER_FILL_MODE 検証など）。
    - KABUSYS_ENV の有効値検証（development / paper_trading / live）と LOG_LEVEL 検証。

  - config_setup.py
    - .env を対話式に生成・更新するウィザードを追加。
    - 主要設定項目（実行環境、API トークン、DB パス、ログレベル、Kill Switch 設定等）を順にプロンプトして .env を出力。
    - 既存 .env の読み込みおよび値のマスク表示、保存確認を実装。出力 .env は Git にコミットしないよう注意喚起を含むテンプレート。

  - validate_config.py
    - 起動前に .env および config/*.yaml の設定を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 値チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml 存在確認・パース検証（PyYAML 未インストール時は警告）などを実施。
    - --strict オプションで警告も FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順ソートと上位 N 選定。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア加重配分。全スコアが 0 の場合は等分配にフォールバックして警告を出力。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中を抑えるため、既存ポジション比率が閾値を超えるセクターの新規候補を除外するロジックを実装（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数を返す（bull/neutral/bear に対応、未知レジームはフォールバック）。

  - portfolio/position_sizing.py
    - calc_position_sizes: 重み・候補・レジーム等を基に個別銘柄の発注株数を算出するロジックを実装。
      - allocation_method: "risk_based" / "equal" / "score" をサポート。
      - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）適用、aggregate cap（available_cash）を超えた場合のスケールダウンと残差配分アルゴリズムを実装。
      - cost_buffer による保守的見積りをサポート。
      - TODO コメント: 将来的な銘柄別 lot_size 対応のための拡張案を記載。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。
    - ログレベルとログディレクトリの解決順を明示（引数 / 環境変数 / デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続するフェールセーフを実装。

  - utils/process_priority.py
    - cross-platform（Windows / POSIX）でのプロセス優先度設定を実装（psutil ベース）。優先度レベル: high / normal / low。
    - CPU affinity 設定関数 set_cpu_affinity を実装（最初の N コアに固定）。
    - アクセス権限不足や未対応 OS に対する例外ハンドリングと警告出力を実装。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード DB（デフォルト: data/paper_trading.db）を読み、稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）などを集計して検証レポートを出力する CLI を追加。
    - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を用いた PASS/FAIL 判定を実装。
    - 日付フィルタ（--from / --to）と DB パス指定オプションをサポート。

- リサーチ（スケルトン）
  - research/factor_research.py
    - ファクター計算モジュールの骨組みを追加（モメンタム、MA200 乖離、ATR、出来高等の計算仕様と定数を定義）。
    - DuckDB 接続を受け取り prices_daily 等のテーブルを参照してファクターを算出する設計（関数 calc_momentum の実装途中の痕跡あり）。

### Changed
- N/A（初期リリースのため変更履歴はありません）

### Fixed
- N/A（初期リリース）

### Security
- 環境変数・シークレットは .env に保存する前提。config_setup にて .env を Git にコミットしない旨を明記。

### Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN（J-Quants API）
  - KABU_API_PASSWORD（kabuステーション API）
  これらが未設定だと実行時にエラーを発生させる箇所があります（Settings._require）。
- 実行環境:
  - KABUSYS_ENV は development / paper_trading / live のいずれか。paper_trading は発注を分離して専用 DB を使用（PAPER_TRADING_SQLITE_PATH で上書き可能）。
- ログ:
  - デフォルトは logs/ ディレクトリにアプリケーション別ログファイルを出力。LOG_DIR で変更可。作成失敗時はコンソール出力のみ。
- 監視:
  - run_monitoring で MONITOR_POLL_INTERVAL を設定可能（秒）。0以下や非数はデフォルト 60 秒にフォールバック。
- 注意点 / 既知の制約:
  - position_sizing の価格欠損時の挙動に関する TODO（欠損価格のフォールバック戦略は未実装）。
  - research/factor_research.py は一部実装が途中（calc_momentum の実装が途中で終了しているように見える）。
  - validate_config は PyYAML がない場合に YAML 内容検証をスキップする（警告を出す）。
  - process_priority / set_cpu_affinity は権限不足や未対応プラットフォームでスキップして警告を出す設計。

---

（この CHANGELOG はソースコード内の docstring、コメント、関数/クラスの実装を基に作成しています。実際のリリースノートとして使用する場合は運用者による確認・追記を推奨します。）