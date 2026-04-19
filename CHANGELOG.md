# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
日付は本コードベースのスナップショット（リリース v0.1.0）を基にしています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-19

### 追加
- 初回公開リリース v0.1.0。
- 実行用スクリプト
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。起動時にプロセス優先度を上げ、SQLite / DuckDB に接続し、Broker クライアントや OrderManager / RiskManager / Reconciler を組み立ててエンジンを別スレッドで実行。停止は data/stop_requested.flag によるフラグ検知で行う。
  - run_monitoring: SystemMonitor ポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視用 DB 初期化（init_monitoring_db）と duckdb 接続を行う。
- 設定関連ツール
  - config_setup: 対話式ウィザードで .env を生成・更新する CLI を追加（シークレットのマスク表示、選択肢/デフォルト対応）。
  - validate_config: .env と config/*.yaml に対する事前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、YAML パース検証（PyYAML が存在する場合）や本番用の追加警告を提供。--strict モードで警告を失敗扱いにできる。
- 環境設定管理
  - Settings クラスを追加。環境変数のラップとバリデーションを提供（J-Quants、kabu API、DB パス、paper_trading 用設定、監視閾値など）。
  - .env 自動ロード機能を実装（プロジェクトルートの検出: .git or pyproject.toml を探索）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。読み込みは OS 環境変数を保護しつつ `.env` → `.env.local` の順で適用。
  - .env パースの強化: export 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱い等を実装。
- Paper Trading 対応
  - 実行時に KABUSYS_ENV が `paper_trading` の場合、paper 用専用 SQLite（data/paper_trading.db）を使用する仕組みを実装（本番 DB と分離）。PAPER_FILL_MODE 環境変数により MockBroker の fill 動作を制御（有効値: "instant", "partial", "never", "reject"）。
  - tools/paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率・送信率、リスク却下数、レイテンシ指標（平均/最大/P95）等を集計して標準出力に出力。閾値による PASS/FAIL 判定を行う。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
  - portfolio.risk_adjustment: セクター集中制限 apply_sector_cap、および市場レジームに応じた投下資金乗数 calc_regime_multiplier（"bull"/"neutral"/"bear" 対応、未知レジームはフォールバック）。
  - portfolio.position_sizing: 各配分法（"risk_based", "equal", "score"）に基づく株数計算 calc_position_sizes。単元株丸め、per-position / aggregate 上限、コストバッファ考慮、スケーリング／端数補正ロジックを実装。
- ユーティリティ
  - utils/logging_setup: ルートロガー設定ユーティリティを追加。コンソール(stdout) と日次ローテーション (TimedRotatingFileHandler、30日保持) を設定。LOG_LEVEL / LOG_DIR の解決順を実装し、ディレクトリ作成失敗時はファイル出力を無効化してコンソールのみで継続。
  - utils/process_priority: psutil を用いたプロセス優先度設定と CPU affinity 設定を追加。Windows / POSIX(Mac/Linux/FreeBSD) を吸収する実装。アクセス権限不足時は警告を出してスキップ。

### 変更
- パッケージメタ情報にバージョンを追加: __version__ = "0.1.0"。

### 修正（エラーハンドリング・フォールバック）
- run_monitoring: MONITOR_POLL_INTERVAL が不正（負数や非整数）の場合にデフォルト値にフォールバックし、警告を出す。
- logging_setup: ログディレクトリの作成に失敗した場合にファイルハンドラ作成をスキップし、コンソール出力のみで継続するように修正（例外耐性の向上）。
- process_priority: プラットフォーム非対応や権限エラー発生時に警告を出して処理をスキップする安全装置を追加。
- run_execution / run_monitoring: 両スクリプトで初期にプロセス優先度を High に設定する処理を追加（性能想定の最適化）。また起動前に停止フラグ（data/stop_requested.flag）を確認して即時終了する挙動を実装。

### 既知の注意点（ドキュメント的注記）
- run_monitoring の挙動: ドキュメントどおり「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」点に注意してください（監視データは production DB を想定）。
- PAPER_FILL_MODE: 環境変数は指定された列挙値のみ有効。誤った値を与えると Settings.paper_fill_mode が ValueError を送出します。
- .env 自動ロードはプロジェクトルートの検出に依存するため、配布後やインストール後にプロジェクトルートが見つからないと自動ロードをスキップします（この挙動は意図的）。
- portfolio.position_sizing の price フォールバック: open_prices に価格が欠損（0.0 や None）の場合は候補をスキップするため、前処理で価格データの整備が必要です（TODO コメントあり）。
- research/factor_research モジュールはモメンタム等の計算ロジックを含むが、スナップショット内で実装が途中になっている箇所が存在します（今後の実装継続が必要）。

### セキュリティ
- .env ファイルは生成時に明示的に「Git にコミットしない」旨をヘッダに記載。秘匿情報は .env に保存される点に注意。

---

注: 本 CHANGELOG は提供されたコードベースの内容から推測して作成したものであり、実際のコミット履歴や変更履歴に基づくものではありません。必要に応じてプロジェクトの実際の git log と照合して調整してください。