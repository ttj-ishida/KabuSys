# Changelog

すべての変更は Keep a Changelog のフォーマットに従います。  
このファイルはリポジトリの現時点（バージョン 0.1.0）をコードベースから推測してまとめた初期リリース記録です。

## [Unreleased]

## [0.1.0] - 2026-04-17
### Added
- 基本パッケージ初期実装（バージョン: 0.1.0）。
  - パッケージメタ情報を追加（src/kabusys/__init__.py）。
- 環境設定/管理
  - 環境変数自動ロード機能を実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から検出して .env / .env.local を読み込む。
    - OS 環境変数を保護しつつ .env.local で上書き可能。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - 複雑な .env 行のパース（export プレフィックス、クォート文字列、バックスラッシュエスケープ、インラインコメント処理）を実装。
  - Settings クラスを実装し、各種設定値（J-Quants / kabu / DB パス / PID / Kill Switch /閾値など）を環境変数から取得する API を提供。
    - KABUSYS_ENV のバリデーション（development / paper_trading / live）。
    - PAPER_FILL_MODE のバリデーション（instant / partial / never / reject）。
    - paper_trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）のサポート。
- 設定支援 CLI
  - 対話式 .env 作成ウィザードを実装（src/kabusys/config_setup.py）。
    - 各設定項目の説明・デフォルト提示・シークレットマスク表示。
    - .env ファイルの読み書きロジック（既存値の再利用、保存時のテンプレート整形）。
    - 起動例: python -m kabusys.config_setup
- 設定検証 CLI
  - バリデーションツールを実装（src/kabusys/validate_config.py）。
    - 必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および（PyYAML があれば）パース検証、KABUSYS_ENV=live 時のガードチェック。
    - --strict モードで警告を FAIL 扱いにできる。
    - 起動例: python -m kabusys.validate_config
- 実行系 / 監視系プロセス起動スクリプト
  - ExecutionEngine 起動用スクリプトを追加（src/kabusys/run_execution.py）。
    - プロセス優先度を最初に "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite に分離して接続（データベースの完全分離）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。スレッドで実行し stop フラグで停止可能。
    - 実行中 PID ファイル（data/execution.pid）を管理。
  - SystemMonitor のポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下・不正値はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して DB を初期化／接続。
    - 停止検出は data/stop_requested.flag ファイルの存在で行う。
- モニタリング DB 初期化フックの呼び出し（init_monitoring_db を両起動スクリプトで呼ぶことで監視テーブルの存在を保証）。
- 実運用ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティを実装（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX（Linux / macOS / FreeBSD）に対応する優先度マッピングを実装。
    - set_process_priority(level) で高・通常・低を指定可能。権限不足や未対応 OS 時は警告ログを出してスキップ。
    - set_cpu_affinity(cpu_count) による CPU ピン留め機能（未指定は全コア）。
- ポートフォリオ構成ロジック（純粋関数群、DB 非依存）
  - 候補選定および重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順、同点は signal_rank 昇順でタイブレーク。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア合計が 0 の場合は等金額にフォールバックして警告。
  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター比率が上限を超える場合に新規候補を除外。unknown セクターは上限適用対象外。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数（1.0 / 0.7 / 0.3）。未知レジームは 1.0 でフォールバック。
  - 発注株数決定（src/kabusys/portfolio/position_sizing.py）
    - allocation_method に応じた株数計算（"risk_based" / "equal" / "score"）。
    - risk_based: risk_pct, stop_loss_pct からポジションサイズを決定。
    - lot_size（単元株）で丸め、max_position_pct（銘柄上限）や max_utilization（投下上限）を考慮。
    - aggregate cap: 全銘柄合計が available_cash を超える場合にスケーリングして、端数は lot_size 単位で再配分するロジックを実装。
    - cost_buffer により手数料・スリッページ分を保守的に見積もる。
- リサーチ / ファクター計算
  - Factor 計算モジュールを実装（src/kabusys/research/factor_research.py）。
    - DuckDB 接続を受け prices_daily / raw_financials を参照してモメンタム（1M/3M/6M/MA200乖離）、ボラティリティ（ATR20 等）、流動性指標を計算する関数を提供。
    - 計算は SQL ウィンドウ関数を多用して効率的に実行。
- Paper Trading 検証レポートツール
  - paper_verification_report スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - PAPER_TRADING_SQLITE_PATH / --db で DB を指定して、以下を集計・判定して標準出力にレポートを出力:
      - 稼働率（system_status）、注文成功率・送信率（trade_logs）、リスク却下数（risk_logs）、API レイテンシ（P95 等）。
    - デフォルトの Pass/Fail 基準を設定（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200ms）。
    - 起動例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- tools パッケージの作成（src/kabusys/tools/__init__.py）。

### Changed
- 設計決定（監視/実行の DB 取り扱い）
  - 監視（run_monitoring）は KABUSYS_ENV にかかわらず Settings.sqlite_path（運用用 monitoring DB）を使用する実装になっている。これは監視情報を常に本番 DB に記録する意図のため（paper_trading と分離しない仕様）。
  - 一方、ExecutionEngine（run_execution）は paper_trading 環境時に PAPER_TRADING_SQLITE_PATH（data/paper_trading.db デフォルト）を使用して発注ログ等を本番 DB と分離する仕様を採用。
- .env 処理の堅牢化
  - 複雑な .env の値（クォート、バックスラッシュ、インラインコメント）に対応することで、実運用でありがちな誤設定を減らす設計。

### Fixed
- 不正な MONITOR_POLL_INTERVAL（0以下、非数）時に time.sleep に渡して例外が発生するのを防ぐため、入力値チェックとフォールバックを追加（src/kabusys/run_monitoring.py）。

### Internal / Notes
- 多くの機能は純粋関数で実装され DB 依存を最小化しているため、単体テストが容易な設計になっている（portfolio / research モジュール等）。
- 一部の TODO コメント（例: position_sizing の銘柄別 lot_size サポート、price のフォールバック価格）を残している。
- 実際のブローカークライアントや ExecutionEngine の詳細実装は別モジュールに委譲されている（broker_factory / execution_engine / order_manager 等）。これらは起動スクリプトから組み合わせて使用される。

### Security
- .env ファイルは生成時に「絶対に Git にコミットしないこと」と明示している（config_setup のテンプレートコメント）。

---

注: 上記は公開されているソースコードから推測して作成した CHANGELOG です。リリースノートには実際の変更差分やコミットログに基づく詳細（バグ修正番号や貢献者一覧など）を追加することを推奨します。