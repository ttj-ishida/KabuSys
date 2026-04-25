# Changelog

すべての注目すべき変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-25

初回公開リリース。日本株自動売買システム KabuSys の基本機能を実装しました（設定管理、起動スクリプト、ログ設定、プロセス優先度制御、ポートフォリオ構築ユーティリティ、実行/監視エンジンの起動補助、ペーパートレード検証ツールなど）。

### Added
- パッケージバージョンを設定
  - src/kabusys/__init__.py にて __version__ = "0.1.0" を追加。

- 設定管理
  - src/kabusys/config.py
    - プロジェクトルートを自動検出して .env/.env.local を自動ロードする仕組みを実装（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - .env の行パースを堅牢化（export プレフィックス、シングル/ダブルクォート、エスケープ、コメント処理に対応）。
    - Settings クラスを導入し、J-Quants / kabu API / DB パス /監視閾値 / 実行環境情報などのプロパティを提供。
    - Paper Trading 用設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）をサポート。
    - env 値や LOG_LEVEL の妥当性チェックを組み込む。

- 設定検証 CLI
  - src/kabusys/validate_config.py
    - .env や config/*.yaml の設定を起動前に検証する CLI を追加（--strict オプションで警告を失敗扱いにできる）。
    - 必須環境変数チェック、KABUSYS_ENV の値チェック、DB パスの親ディレクトリ存在チェック、YAML のパースチェック（PyYAML 任意）などを実施。

- 設定ウィザード CLI
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を初期作成・更新するユーティリティを追加。
    - 入力補助、既存値の再利用、マスク表示（シークレット項目）等をサポート。

- ログ設定ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 全起動スクリプトから共通で使用できる logging のセットアップ関数を追加。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/、30日保持）を設定。
    - ファイル出力用ディレクトリ作成に失敗した場合はファイルハンドラをスキップしコンソール出力のみで継続するフェイルセーフ処理を実装。
    - LOG_DIR / LOG_LEVEL の解決順を明確化。

- プロセス優先度・CPU affinity ユーティリティ
  - src/kabusys/utils/process_priority.py
    - Windows / POSIX の差分を吸収してカレントプロセスの優先度を設定する set_process_priority を実装（"high" / "normal" / "low"）。
    - set_cpu_affinity でプロセスを最初の N コアにピン止めする機能を追加。
    - 許可エラー時に安全にスキップするハンドリングを導入。

- 起動スクリプト
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。無効値は警告を出してデフォルトにフォールバック。
    - 停止フラグファイル (data/stop_requested.flag) 検知でループ終了。
    - 監視は環境に関わらず本番用 sqlite_path を使用する旨を明示。
    - duckdb 接続も確立して SystemMonitor に渡す。

  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番DBと分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み立て、ExecutionEngine を別スレッドで実行。
    - 停止フラグ (data/stop_requested.flag) 検知でエンジンを安全に停止・終了。PID ファイル管理をサポート。

- 監視 DB 初期化
  - src/kabusys/monitoring/monitoring_db.py (参照されている) を起動時に呼び出して監視テーブルの存在を保証（冪等）。

- ポートフォリオ構築ライブラリ
  - src/kabusys/portfolio/*
    - portfolio_builder.py
      - select_candidates: BUY シグナルのスコア降順フィルタを実装。
      - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を実装。スコアが全て 0 の場合は等分にフォールバックして警告を出力。
    - risk_adjustment.py
      - apply_sector_cap: セクター集中を抑えるため、既存保有のセクター比率が閾値を超える場合に候補を除外するロジックを実装（unknown セクターは除外対象外）。
      - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた資金乗数を返す。
    - position_sizing.py
      - calc_position_sizes: weight / candidates / リスクパラメータに基づき発注株数を算出。単元株丸め、1銘柄上限、aggregate cap（available_cash）に基づくスケーリング、残余キャッシュを用いた端数配分ロジックを実装。
    - パッケージエクスポートを提供 (src/kabusys/portfolio/__init__.py)。

- ペーパー検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - ペーパートレード用 SQLite DB を集計して検証レポートを生成する CLI を追加。
    - 稼働率、注文成立率、送信率、P95 レイテンシなどを算出し PASS/FAIL 判定を行う。
    - デフォルト閾値を定義（稼働率 >= 99%, 成立率 >= 90% 等）。
    - --from/--to/--db オプションで期間・DBパスを指定可能。

- 研究用ファクタ計算（基盤）
  - src/kabusys/research/factor_research.py
    - モメンタム／ボラティリティ／流動性等のファクター設計と定数を実装。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
    - calc_momentum の実装開始（ファイル末尾にて実装途中の箇所が存在）。

### Changed
- ログの挙動を統一
  - すべての起動スクリプトが setup_logging を使うことを想定して実装。ログ出力は stdout を優先し、ファイル出力はフォールバック可能。

- DB 接続挙動
  - 監視用スクリプトは環境に左右されず本番 sqlite_path を使用する明確な挙動を採用。Execution は paper_trading の場合専用 DB を使用して分離。

### Fixed
- .env 読み込みの堅牢化
  - export プレフィックスやクォート内のエスケープ、インラインコメント扱いの改善で .env の多様な形式に対応。

- プロセス優先度設定の互換性
  - Windows / POSIX の差分を吸収し、権限不足や未実装 API の場合は警告ログを出して安全にスキップするように修正。

### Known issues / Notes
- src/kabusys/research/factor_research.py の calc_momentum 関数の実装が途中で終端（ファイル末尾に未完のトークンが存在）しています。研究用ファクタ計算は設計・定数・インターフェースの骨格は整っていますが、一部実装とテストが残っています。
- 一部のモジュール（例: monitoring.system_monitor や execution.execution_engine など）はこの差分で参照されているものの、本差分に含まれる該当実装の詳細がここには示されていません。実際の動作はそれらコンポーネントの実装・設定に依存します。
- PAPER_FILL_MODE の検証は厳格で、不正値だと起動時に ValueError を投げます。環境変数設定時は注意してください。

---

初回リリースに含まれる主な機能は上記の通りです。各モジュールの詳細な使用方法や設定手順はリポジトリ内のドキュメント（README / PortfolioConstruction.md / StrategyModel.md 等）を参照してください。