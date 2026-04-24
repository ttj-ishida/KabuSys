CHANGELOG
=========

すべての注目すべき変更を記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。

フォーマット:
- 追加(Added)、変更(Changed)、修正(Fixed)、削除(Removed)、セキュリティ(Security) のカテゴリで整理しています。

0.1.0 - 2026-04-24
-----------------

初回リリース（ベースライン）。主にシステム全体のコア機能・ユーティリティ・CLI を実装しました。

Added
- コアパッケージとバージョンを追加
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止検出はプロジェクトの data/stop_requested.flag ファイルを監視。
    - 監視用 DB 接続には Settings.sqlite_path（監視は環境にかかわらず本番 sqlite_path を使用）と DuckDB を使用。
    - プロセス優先度を起動時に高に設定する処理を含む。
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB（data/paper_trading.db）を使用し、Mock ブローカークライアントを用いる運用に対応（BrokerClientFactory による分岐）。
    - エンジン用 PID ファイルと停止フラグ（data/execution.pid / data/stop_requested.flag）を取り扱い、別スレッドでエンジンを実行・監視。
    - 起動時にプロセス優先度を高に設定。
- 設定管理
  - config.py: 環境変数読み込み・管理クラス Settings を追加。
    - .env 自動読み込み機能（プロジェクトルート探索: .git または pyproject.toml を基準）。
    - .env の読み込み順序: OS 環境 > .env.local > .env。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD に対応。
    - .env パース/クォート/コメント処理の詳細な実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメント等）。
    - 必須環境変数取得用の _require() 実装。
    - 各種設定プロパティを提供（J-Quants/Kabu API/LINE/DB パス/監視閾値/環境種別等）。
    - PAPER_FILL_MODE の検証ロジック（有効値チェック）や paper_sqlite_path、pid/kill flag 等。
- 設定ユーティリティ
  - config_setup.py: 対話型ウィザードで .env を作成・更新する CLI を追加。
    - 複数の設定項目を対話的に入力でき、シークレット項目はマスク表示。保存前に確認を行う。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パス、config/*.yaml の存在・パース（PyYAML があれば内容検証）をチェック。
    - --strict オプションで警告をエラー扱いにできる。
    - production 用の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の注意喚起）。
- ロギングユーティリティ
  - utils/logging_setup.py: 統一されたログ設定ユーティリティを追加。
    - コンソール出力は stdout を使用。
    - 日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）実装、デフォルト logs/<app_name>.log、30 日分保持。
    - LOG_DIR や引数でログディレクトリ/レベルをオーバーライド可能。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
- プロセス優先度 / CPU affinity ユーティリティ
  - utils/process_priority.py: クロスプラットフォームでプロセス優先度を設定するヘルパーを追加。
    - Windows と POSIX(Linux/Mac/FreeBSD) の違いを吸収。失敗時は警告を出してスキップ。
    - set_cpu_affinity() で最初 N コアにピン留めする機能を実装。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py:
    - select_candidates(): BUY シグナルのスコア降順選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights(): 等金額配分の重み計算。
    - calc_score_weights(): スコア加重配分（全スコアが 0 の場合は等金額配分にフォールバックし WARN を出す）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap(): セクター集中上限に基づき候補を除外するロジック（unknown セクターは除外対象外）。
    - calc_regime_multiplier(): market レジームに応じた投下資金乗数を返す（"bull"/"neutral"/"bear" マップ、未知レジームは警告のうえ 1.0 でフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes(): allocation_method ("risk_based", "equal", "score") に基づき発注株数を計算する包括的ロジック。
      - risk_based: ポジションごとのリスクベース計算（risk_pct, stop_loss_pct）。
      - equal/score: 重みと max_utilization に基づく配分。
      - lot_size（単元株）を考慮した丸め処理、aggregate cap 超過時のスケーリングと残余配分ロジック、cost_buffer を用いた保守的なコスト見積り。
- Execution 周りの組み立て例
  - run_execution から組み立てられるコンポーネント群に関する実装が存在:
    - BrokerClientFactory（ブローカークライアントの生成）
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine（起動時のデフォルト RiskConfig を含む）
    - RiskConfig のデフォルト値（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）
    - ExecutionEngine は pid_file, duckdb_conn, target_date 等を受け取る設計。
- 監視 / 検証ツール
  - monitoring.monitoring_db との連携（init_monitoring_db 呼び出し）により監視用テーブルの存在を保障する仕組みを導入（冪等）。
- ペーパートレード検証レポート
  - tools/paper_verification_report.py: ペーパートレード結果を集計・判定する CLI を追加。
    - デフォルト DB: data/paper_trading.db （PAPER_TRADING_SQLITE_PATH 環境変数で上書き可）。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数。
    - P95 の計算、各種クエリの実装、閾値による PASS/FAIL 判定（デフォルト閾値: 稼働率 99%, 成立率 90%, 送信率 95%, P95 レイテンシ 200 ms）。
    - 日付フィルタ (--from/--to) に対応。
- 研究用モジュール（factor_research）
  - research/factor_research.py: ファクター計算の骨格（モメンタム/MA/ATR/流動性等）を実装する設計。DuckDB を用いた prices_daily/raw_financials 参照での処理を想定。モジュール内に定数と calc_momentum の骨組みを追加（詳細は実装継続中）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 環境設定ウィザードと .env 作成において、.env を絶対に Git にコミットしないよう注意書きを追加（config_setup.py）。機密情報はシークレット表示で扱う。

Notes / 補足
- 各ユーティリティは失敗に対して堅牢に設計されており、ファイル/ディレクトリ作成失敗や OS 権限不足時は警告を出して代替動作（例: ログのファイル出力のスキップやプロセス優先度設定のスキップ）を行います。
- run_monitoring は監視用 DB を常に production sqlite_path として扱う点に注意してください（コードコメントの通り）。
- run_execution は paper_trading 環境と本番環境（live）を分離する設計になっており、Paper 環境では専用の SQLite（デフォルト data/paper_trading.db）へ記録されます。
- 一部のモジュール（研究系や ExecutionEngine の内部等）はこのリリースで基本的な骨格・API を提供しており、今後のリリースで細部や最適化、追加のエラーハンドリングが予定されています。

今後の予定（例）
- factor_research の完全実装（Momentum/Value/Volatility/Liquidity などのファクター計算完遂）
- ExecutionEngine 周りの追加テスト・耐障害性強化
- モニタリング・アラート（LINE 連携）の拡張と運用向けドキュメント追加

---------------
この CHANGELOG はコードベースの現状をコードから推測して作成した概要です。詳細な変更点や設計方針は各モジュールのドキュメント・ソースコードのコメントを参照してください。