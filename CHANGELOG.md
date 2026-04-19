# Changelog

すべての変更は Keep a Changelog の仕様に準拠します。  
予定表記や日付はソースコード内の記述・現在の日付（2026-04-19）等から推測して作成しています。

## [Unreleased]
- 今後の変更に備えたプレースホルダ。

## [0.1.0] - 2026-04-19
初期リリース。日本株自動売買システム「KabuSys」のコアユーティリティ、CLI、実行・監視スクリプト、ポートフォリオ構成ロジック、検証ツール等を追加。

### Added
- 基本情報
  - パッケージバージョンを定義（kabusys/__init__.py: __version__ = "0.1.0"）。

- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV に応じた DB の切り分け（paper_trading 時は専用 DB を使用）。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine をスレッドで起動。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止、PID ファイル取り扱い、リソースクリーンアップ。
    - デフォルトでプロセス優先度を high に設定。

  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に依存せず本番用 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ検知、例外時のロギング、DuckDB 接続管理。

- 設定管理・ユーティリティ
  - config.py: Settings クラスを実装。
    - .env の自動読み込み（プロジェクトルート検出: .git または pyproject.toml 基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプション。
    - 必須/任意の環境変数取得ラッパー、各種パス（DUCKDB_PATH/SQLITE_PATH/PAPER_TRADING_SQLITE_PATH 等）、閾値・フラグ（CPU/MEM/DISK の閾値、KILL_FLAG_CLEAR_ON_START 等）を提供。
    - PAPER_FILL_MODE（paper trading の fill 動作）等の検証とデフォルト値。

  - config_setup.py: 対話式 .env ウィザードを追加。
    - 初期 .env 作成・更新を支援。秘密値はマスク表示、選択肢サポート、保存前の確認、.env ファイルへの書き出し機能。

  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数・KABUSYS_ENV 値・LOG_LEVEL・DB パスの親ディレクトリ・config/*.yaml の存在と YAML パース（PyYAML があれば検証）等をチェック。
    - --strict モードで警告を失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。
    - stdout 出力用 StreamHandler と日次ローテーションの TimedRotatingFileHandler（既定 logs/）をルートロガーに設定。
    - 既存ハンドラをクリアして二重登録を防止。LOG_DIR, LOG_LEVEL の解決ルールを実装。
    - ファイル出力ディレクトリ作成失敗時はコンソールのみで継続。

  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux, macOS, FreeBSD）を吸収。psutil を用いた nice / priority 設定を提供。
    - set_cpu_affinity によりプロセスを最初の N コアにピン留め可能（権限や OS に依存するため失敗時は警告でスキップ）。

- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコア降順選択（同点時は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（スコア全0 の場合は等配分にフォールバック）。

  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック（既存保有を考慮し、上限超過セクターの新規候補を除外）。unknown セクターは除外対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知のラベルはフォールバックで 1.0）。

  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数算出。
      - 損切り率・risk_pct に基づく risk_based、重みベースの equal/score を実装。
      - lot_size（単元）での丸め、portfolio_value に対する per-stock 上限、aggregate cap（available_cash）でのスケールダウン。
      - cost_buffer を加えてスリッページ/手数料を保守的に見積もるロジック、スケール中の端数調整アルゴリズムを実装。

- 監視・検証ツール
  - monitoring.monitoring_db (参照して初期化呼び出しがあることを想定): 監視テーブル初期化をサポート（init_monitoring_db を各起動スクリプトで呼び出し）。
  - tools/paper_verification_report.py:
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から統計を集計し、PASS/FAIL 判定の検証レポートを出力するスクリプトを追加。
    - システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を算出。P95 算出ロジック・閾値を定義。
    - DB がない場合やテーブル欠如時に安全に N/A を扱うフェイルセーフ。

- リサーチ（作業中）
  - research/factor_research.py:
    - ファクター計算モジュールの骨格を追加（モメンタム・MA200乖離・ATR 等の設計方針と定数を定義）。DuckDB 接続を受けて prices_daily / raw_financials を参照する想定。
    - calc_momentum の関数骨子が開始されている（実装途中）。

### Changed
- なし（初期リリース）

### Fixed
- なし（初期リリース）

### Notes / 実装上の挙動（重要）
- run_monitoring は MONITOR_POLL_INTERVAL の不正値を検出してデフォルト 60 秒へフォールバックする（0 以下や非整数は警告）。
- run_monitoring は監視用 DB 初期化を行うが、「監視は本番 sqlite_path を使用する」と明示的に記載されているため環境に関係なく本番監視 DB を用いる設計。
- run_execution は paper_trading 環境時に paper_sqlite_path を使用し、本番 DB と明確に分離する。
- logging_setup はログディレクトリ作成失敗時にファイルハンドラをスキップしてコンソールログのみで継続する堅牢設計。
- process_priority / set_cpu_affinity は権限不足や未対応 OS の場合に警告を出して処理をスキップする（安全側のフォールバック）。
- config.py の自動 .env 読み込みはプロジェクトルートが特定できない場合はスキップされるため、配布後にも安全に動作する設計。
- validate_config は PyYAML 未インストール時に YAML 検証をスキップして警告を出す（依存関係がオプション）。

---

この CHANGELOG はソースコードの内容から推測して作成しています。実際の変更履歴（コミット単位や日付）はリポジトリの Git ログ等を参照して更新してください。必要であれば、各ファイルのより細かい変更点（関数毎の説明や既知の TODO）を CHANGELOG に追加できます。