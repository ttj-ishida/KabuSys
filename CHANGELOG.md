KEEP A CHANGELOG 準拠

すべての重要な変更はこのファイルに記録します。
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

Unreleased
- （現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-23
Added
- 初回リリース。KabuSys 日本株自動売買システムの基本機能を実装。
  - 実行系
    - src/kabusys/run_execution.py
      - ExecutionEngine を起動する CLI スクリプトを追加。スレッド実行と停止フラグ（data/execution.pid / data/stop_requested.flag）に対応。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
      - BrokerClientFactory によるブローカークライアントの切替え（モック含む）をサポート。
      - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を構成。
  - 監視系
    - src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。デフォルトポーリング間隔 60 秒、環境変数 MONITOR_POLL_INTERVAL で上書き可能。
      - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視用 DB の初期化を行う init_monitoring_db を呼び出す）。
  - 設定管理 / ユーティリティ
    - src/kabusys/config.py
      - 環境変数読み込み・管理モジュールを追加。プロジェクトルート検出（.git / pyproject.toml）に基づく .env 自動ロード（.env, .env.local）を実装。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - .env パースは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント（クォートなしのコメントは直前が空白の場合のみ）に対応する堅牢な実装。
      - 各種設定プロパティ（DB パス、ペーパートレード設定 PAPER_FILL_MODE、PID/kill flag パス、閾値設定、環境判定 is_live/is_paper 等）を提供。
    - src/kabusys/config_setup.py
      - 対話式ウィザードで .env を生成・更新する CLI を追加。デフォルト値、シークレット入力（マスク表示）、保存確認をサポート。
    - src/kabusys/validate_config.py
      - 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、config/*.yaml の存在・パース検証（PyYAML があれば内容も検査）などを行う。--strict オプションで警告も失敗扱いにできる。
    - src/kabusys/__init__.py
      - パッケージメタ情報（__version__ = "0.1.0"）を追加。
  - ポートフォリオ構築
    - src/kabusys/portfolio/
      - portfolio_builder.py: シグナル選定（スコア降順、タイブレークは signal_rank）、等金額/スコア重み計算を実装。
      - position_sizing.py: 発注株数計算ロジックを実装（risk_based / equal / score）。単元株（lot_size）丸め、max_position_pct、max_utilization、コストバッファ、aggregate cap によるスケールダウンと端数処理を実装。
      - risk_adjustment.py: セクター上限適用（既存ポジションのセクター比率に基づく候補除外）と市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知レジームはフォールバックで 1.0 を返す（警告ログ）。
  - 研究用・分析機能
    - src/kabusys/research/factor_research.py（ファクター計算基盤を追加）
      - DuckDB 接続を受け取り、prices_daily / raw_financials を元にモメンタム/Value/Volatility/Liquidity 等の定量ファクターを計算する方針を実装（モジュール構成と定数を用意、モメンタム計算関数 calc_momentum の骨組みを開始）。
    - DuckDB 統合: 各所で duckdb の接続（duckdb.connect）を使用して分析向け DB を利用。
  - 運用ツール
    - src/kabusys/tools/paper_verification_report.py
      - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）を解析して検証レポートを出力する CLI を追加。稼働率、注文成功率・送信率、リスク却下数、レイテンシ（avg/max/P95）を算出し、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL を判定する。
  - ロギング・プロセス管理ユーティリティ
    - src/kabusys/utils/logging_setup.py
      - ルートロガーに stdout ストリームハンドラと日次ローテートファイルハンドラ（TimedRotatingFileHandler）を設定するユーティリティを追加。ログディレクトリ自動作成、作成失敗時のフォールバック（コンソールのみ）に対応。保管日数 30 日。
    - src/kabusys/utils/process_priority.py
      - psutil を用いて Windows / POSIX を吸収するプロセス優先度設定（high/normal/low）と CPU affinity 設定を追加。権限不足やサポート外 OS の場合は警告を出してスキップする安全設計。

Changed
- （初回リリースのため変更履歴なし）

Fixed
- 設定・起動に関する堅牢性強化（初期化・例外抑止・フォールバックを多数実装）
  - .env 読み込み失敗時に警告を出してスキップ（warnings.warn）。
  - logging_setup: ログディレクトリ作成失敗時にファイルハンドラ作成をスキップしてコンソール出力のみで継続。
  - process_priority / set_cpu_affinity: 権限エラーや未実装メソッドに対して警告を出して失敗を回避。
  - run_monitoring / run_execution: 停止フラグを検知して安全に終了するロジック、例外時のログ出力を実装。

Security
- 環境変数取り扱いにおいて .env ファイルをデフォルトで Git 管理に含めないよう README 相当の注意書きを .env 書き込みロジックに追加（config_setup.py）。シークレット項目はウィザードでマスク表示。

Notes / Known limitations
- factor_research.calc_momentum の実装はファイルの末尾で未完（骨組みあり）。実際のファクター計算は今後の実装で完了予定。
- position_sizing の価格フォールバックが未実装（price が 0.0 の場合に過少見積りする可能性がある旨を TODO コメントで明示）。
- 一部機能は外部依存（psutil、duckdb、PyYAML）が必要。依存パッケージが無い場合は関連チェックでスキップまたは警告を行うが、実行に影響する場合あり。

開発者向けメモ
- 環境自動読み込みはプロジェクトルート特定に依存するため、配布後やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使用して挙動を制御可能。
- run_execution/run_monitoring 起動前に validate_config.py での検証を推奨。
- ログは既定で logs/<app_name>.log に出力され、日次ローテーションされる。ログ出力レベルは環境変数 LOG_LEVEL または引数で制御可能。

----------