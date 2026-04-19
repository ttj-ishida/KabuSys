# Changelog

すべての変更は "Keep a Changelog" の形式に準拠しています。  
慣例: 変更は区分 (Added / Changed / Fixed / Removed / Security) ごとに整理しています。

## [0.1.0] - 2026-04-19

初回リリース。KabuSys のコアユーティリティ、起動スクリプト、設定管理、ポートフォリオ構築・リスク調整ロジック、Paper Trading 検証ツールなどを含む最小実装を追加しました。

### Added
- 全体
  - 初期パッケージ・バージョンを 0.1.0 として公開。
  - パッケージ・エントリポイントとメタ情報を追加（src/kabusys/__init__.py）。
- 起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト内 data/stop_requested.flag ファイルの存在で検出。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視データを記録。
    - sqlite3 と DuckDB のコネクションを確立し、監視 DB 初期化を実行。
    - 予期しない例外はログに記録して次ポーリングへ継続。
  - run_execution: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 DB を使用（本番 DB と完全分離）。
    - BrokerClientFactory によるブローカークライアント生成（MockBroker を含む想定）。
    - ExecutionEngine をデーモンスレッドとして起動し、stop flag 検知で安全に停止。
    - 実行中の PID を data/execution.pid に格納する運用を想定。
- 設定管理
  - Settings クラス（src/kabusys/config.py）を追加。
    - .env の自動読み込み機能（プロジェクトルートの .env / .env.local を優先順で読み込み）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
    - 環境変数の厳密な取得 (必須変数チェック) と値検証（KABUSYS_ENV, LOG_LEVEL 等）。
    - 各種パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH 等）を Path 型で提供。
    - paper_fill_mode（ペーパートレードの約定モード）の検証と取得。
  - 設定ウィザード CLI（src/kabusys/config_setup.py）を追加。
    - 対話式で .env を新規作成 / 更新できるウィザード。
    - シークレット値はマスク表示、デフォルト値・選択肢のサポート。
    - .env の書き出しテンプレートを提供。
  - 設定検証 CLI（src/kabusys/validate_config.py）を追加。
    - 必須環境変数のチェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ検査、config/*.yaml の存在・パースチェック（PyYAML がある場合）。
    - --strict オプションで警告を fail 扱いにできる。
    - 本番 (live) 向けの追加ガード（LINE 通知設定や Kill Flag の自動クリア設定の警告）。
- ロギング & プロセス制御ユーティリティ
  - setup_logging（src/kabusys/utils/logging_setup.py）
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。
    - LOG_LEVEL / LOG_DIR / app_name を使った柔軟な設定。
    - 既存ハンドラをクリアして二重設定を防止。
  - process_priority（src/kabusys/utils/process_priority.py）
    - cross-platform（Windows / POSIX）でプロセス優先度を設定するユーティリティ（set_process_priority）。
    - CPU affinity を設定する set_cpu_affinity を追加。
    - psutil に依存し、権限不足・未対応環境では安全に警告を出してスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順で上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重の重み計算（スコア全零時は等分配にフォールバック）。
  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: セクター集中を検出し、既存セクター比率が上限を超える場合に新規候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは 1.0 でフォールバック。
  - position_sizing（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: 複数の allocation_method（risk_based / equal / score）に対応した発注株数計算。
    - lot_size（単元株）や cost_buffer（手数料・スリッページの保守見積もり）を考慮したスケール調整と切り捨て/再配分ロジックを実装。
    - aggregate cap（利用可能現金を超えた場合のスケールダウン）と残差処理を実装。
  - 上記関数群をパッケージ経由でエクスポート（src/kabusys/portfolio/__init__.py）。
- 研究・ファクター計算（開始）
  - research/factor_research.py を追加（DuckDB 経由でのファクター計算インターフェース）。
    - Momentum / MA200 / ATR / Liquidity 等の計算を想定した設計。関数 calc_momentum の骨子を実装（注: ファイルの末尾で未完の箇所あり）。
- ペーパートレード検証ツール
  - tools/paper_verification_report.py: Paper Trading の SQLite DB から検証レポートを生成する CLI を追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを計算して Pass/Fail 判定を出力。
    - --from / --to / --db オプションをサポート。環境変数 PAPER_TRADING_SQLITE_PATH を使用可能。
    - P95 計算、各種 SQL クエリを内蔵。
- 監視 DB 初期化ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db を使用する起動スクリプトへの組み込み（冪等に DB スキーマを準備）。
- Execution 関連の初期構成
  - ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等のインタフェースを参照する起動処理を追加（実運用ロジックは外部モジュールに依存）。

### Changed
- n/a（初回リリースのため過去の変更はありません）

### Fixed
- 環境変数パーサ（src/kabusys/config.py）
  - .env の行パースで以下のケースに対応:
    - export KEY=val 形式に対応。
    - クォート付き値のバックスラッシュエスケープ処理を考慮した正しいクォート解除。
    - クォートなし値における inline コメントの認識（直前が空白/タブの場合のみ # をコメント開始とみなす）。
  - MONITOR_POLL_INTERVAL の不正値検出とフォールバックを実装（run_monitoring 側）。
- logging_setup
  - StreamHandler を stdout に強制して Cron / Task Scheduler で stdout/stderr を統一して扱いやすくした。
  - ログディレクトリ作成失敗時のフォールバックを実装（ファイルハンドラのスキップと警告）。

### Removed
- n/a

### Security
- 環境変数取り扱い
  - シークレット値の扱いに注意する旨を .env テンプレートとウィザードに明記（.env を絶対に Git にコミットしないことを強調）。

### Notes / Known limitations
- research/factor_research.py の calc_momentum 関数はファイル末端で未完の行（start_da で切れている部分）があり、実装の続きが必要です。
- apply_sector_cap: price_map に価格が欠損 (0.0) の場合にエクスポージャーが過少見積りされる旨の TODO コメントあり。将来的にフォールバック価格（前日終値等）を使うことが検討されています。
- Process priority / CPU affinity の設定は psutil に依存し、権限不足や一部 OS では効果が無い場合があります。失敗時は警告ログによりスキップします。
- ExecutionEngine 等の具体的な実行ロジック・ブローカークライアント実装は別モジュールに依存します（本リリースは起動と依存注入の枠組みを提供）。

--- 

今後の予定: research モジュールの実装完了、ExecutionEngine の耐障害性強化、監視・アラートルールの充実、ユニットテストの追加等。