# Changelog

すべての重要な変更はここに記録します。本ファイルは Keep a Changelog の形式に準拠します。  
タグ付けは semver を使用します。

- リリースノートの対象はソースツリーの現状から推測して作成しています（実装/挙動の要点を抜粋）。
- 日付は本ファイル作成日です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

### Added
- パッケージ初期リリース。
- 実行系 / 監視系起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - プロセス優先度を "high" に設定して起動（utils.process_priority を利用）。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（paper/trading では MockBrokerClient 想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、スレッドで ExecutionEngine.run_session を実行。停止フラグ（data/stop_requested.flag）検知で安全に停止する仕組みを導入。
    - PID ファイル管理（data/execution.pid）対応。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用して初期化（init_monitoring_db）。
    - 停止フラグによりループを終了、KeyboardInterrupt による終了もハンドリング。
    - duckdb 連携（分析用 DB パスを利用）。
- 環境設定 / 構成関連
  - config.py
    - .env（および .env.local）自動ロード機能を追加（プロジェクトルートを .git or pyproject.toml で検出）。自動ロードを無効にする環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。
    - .env の堅牢なパーサを実装（export 句対応、クォート内のエスケープ処理、インラインコメントの扱い等）。
    - Settings クラスを実装し、各種設定値（J-Quants / kabuAPI / DBパス / PID/kill flag パス / モニタ閾値 / env 判定 / paper_trading 用設定等）をプロパティ経由で取得できるようにした。必須項目は _require() で検査し未設定時は例外を送出。
    - PAPER_FILL_MODE のバリデーション（有効値: instant/partial/never/reject）を実装。
  - config_setup.py
    - 対話式 .env 作成ウィザードを追加（項目の説明、既存 .env の読み込み、シークレット入力、保存確認など）。
  - validate_config.py
    - 起動前設定検証 CLI を追加。必須環境変数、KABUSYS_ENV や LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境向けの追加ガード（LINE 設定、KILL_FLAG_CLEAR_ON_START の注意）を行う。--strict オプションで警告も FAIL 扱いにできる。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等分配（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。全スコアが 0 の場合は等分配にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（既存保有と当日売却予定を考慮）。unknown セクターは上限適用対象外。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear マッピング、未知の場合は 1.0 でフォールバックして警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes を実装。allocation_method に応じて (risk_based | equal | score) の株数を計算。
    - lot_size（単元）で丸め、1 銘柄上限・aggregate cap（available_cash）・cost_buffer（手数料・スリッページ見積）を考慮したスケーリングを実装。
    - price 欠損や 0 の場合のスキップ、スケーリング後の端数処理（fractional remainders を考慮して lot 単位で追加配分）を行う。
- ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。ログディレクトリ作成失敗時はファイルハンドラを回避してコンソール出力のみで継続。
    - ログレベル/ログディレクトリの解決順を明示。
  - utils/process_priority.py
    - set_process_priority, set_cpu_affinity を実装。Windows と POSIX（Linux, macOS 等）で差分を吸収する実装。psutil を用いて優先度設定・CPU affinity を行い、権限不足等のエラーは警告でスキップ。
- 分析 / レポート
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。system_status / trade_logs / risk_logs を参照して稼働率・注文成功率・送信率・レイテンシ（P95）等を算出し、閾値（稼働率 99%、成立率 90% 等）に基づいて PASS/FAIL 判定を行う。--from/--to/--db オプションを提供。PAPER_TRADING_SQLITE_PATH 環境変数を参照可能。
- 研究用（着手）
  - research/factor_research.py
    - ファクター計算モジュールを追加。Momentum/Value/Volatility/Liquidity 等を想定。calc_momentum のインターフェースと定数を定義。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計。実装は継続中（スキャン範囲や指標定義を含む）。
- その他
  - パッケージメタ情報を追加（kabusys/__init__.py の __version__ = "0.1.0"）。
  - duckdb と sqlite3 の両方を分析/運用で併用する設計を採用（各モジュールが接続を受け取る形）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- 本番環境（KABUSYS_ENV=live）向けに注意喚起を実装:
  - validate_config で LINE 通知設定や KILL_FLAG_CLEAR_ON_START の設定をチェックして警告を出すようにした。

### Migration / Usage notes
- .env 自動ロード
  - デフォルトでリポジトリルート（.git または pyproject.toml を基準）にある .env/.env.local を自動でロードします。テストなどで自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須環境変数
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須です。Settings._require() により未設定時は ValueError を送出します。validate_config を使って起動前に検証することを推奨します。
- Paper Trading と本番 DB
  - paper_trading 実行時は settings.is_paper により paper_sqlite_path（デフォルト: data/paper_trading.db）を使用します。本番データベースとデータ分離されています。
- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60 秒）。1 未満や数値以外を指定するとデフォルトにフォールバックし警告が出ます。
- Kill/Stop フラグ
  - 起動スクリプトは data/stop_requested.flag（または Settings 経由で指定したパス）を監視して安全に停止します。KILL_FLAG_CLEAR_ON_START を 1 に設定すると起動時に自動クリアされる挙動に注意（本番では 0 推奨）。
- ログ
  - ログはデフォルトで logs/<app_name>.log に日次ローテートで保存されます。ログディレクトリの作成に失敗した場合はコンソール（stdout）出力のみとなります。
- 既知の制約 / TODO
  - research/factor_research の実装は継続中で、いくつかの関数は未完（このリリースではインターフェース定義と定数が中心）。
  - position_sizing の価格欠損（price が 0.0）の扱いに TODO コメントあり（将来的に前日終値や取得原価でフォールバックする検討）。
  - .env パーサは多くのケースを扱うが、極端な複雑な引用・エスケープを含むケースでの互換性は十分に検証する必要あり。

---

（必要に応じて、今後のリリースでは各ファイル単位の変更点やバグ修正、パフォーマンス改善などを追記してください。）