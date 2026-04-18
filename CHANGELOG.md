# Changelog

すべての変更は Keep a Changelog の形式に従います。  
通常の慣例に従い、セマンティック バージョニングを採用します。

## [Unreleased]

## [0.1.0] - 2026-04-18

初期リリース。KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築・ポジション計算ロジック、設定管理、各種 CLI ツールを導入します。

### Added
- パッケージ基礎
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - モジュールエクスポートを整理（portfolio, execution, monitoring 等を想定）。
- 設定管理
  - Settings クラス（kabusys.config）を実装：
    - 環境変数経由で各種設定を取得（例: KABUSYS_ENV, LOG_LEVEL, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - 各プロパティにデフォルト値やバリデーション（KABUSYS_ENV の有効値チェック、LOG_LEVEL の有効値チェック、PAPER_FILL_MODE の許容値チェックなど）を実装。
    - パス類は Path 型で返却（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH 等）。
  - .env 自動読み込み機構（config モジュール）:
    - プロジェクトルートを .git または pyproject.toml から自動検出。
    - 読み込み順序: OS 環境変数 > .env.local > .env（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env の高度なパースを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、行内コメントルールなど）。
- 設定ウィザード CLI
  - kabusys.config_setup による対話式 .env 作成・更新ウィザードを追加：
    - 必須/任意項目、シークレット入力、選択肢、デフォルト値をサポート。
    - .env をテンプレート形式で書き出す _write_env を提供。
- 設定検証 CLI
  - kabusys.validate_config を追加：
    - 必須環境変数の有無、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML がインストールされている場合の）パース検証を実施。
    - --strict オプションで警告を失敗扱いにできる。
- ログ設定ユーティリティ
  - kabusys.utils.logging_setup.setup_logging を追加：
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。
    - ログディレクトリ自動作成、失敗時のフォールバック（コンソールのみ）対応。
    - LOG_LEVEL / LOG_DIR / 引数を組み合わせた柔軟な解決。
- プロセス優先度 / CPU affinity
  - kabusys.utils.process_priority を追加：
    - set_process_priority(level: "high"|"normal"|"low")：Windows/Linux/macOS を吸収してプロセス優先度を設定（psutil ベース、権限不足等は警告でスキップ）。
    - set_cpu_affinity(cpu_count: Optional[int])：最初の N コアにピン留め。エラー時は警告でスキップ。
- 実行 / 監視 起動スクリプト
  - run_execution.py:
    - ExecutionEngine の起動スクリプト。KABUSYS_ENV が paper_trading の場合は paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine を組み立てて起動。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理をサポート。スレッドで engine.run_session を実行し、フラグ検知で安全停止。
  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトフォールバック。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する（設計上の意図）。
    - stop フラグ検知でループ終了。例外はログに例外情報を出力して次ポーリングへ継続。
- データベース初期化サポート
  - monitoring 用テーブルの初期化ヘルパ（init_monitoring_db を各起動スクリプトで呼び出し、冪等に監視テーブルを保証）。
- ポートフォリオ構築ライブラリ
  - kabusys.portfolio モジュールを追加。純粋関数群で DB 非依存（メモリ内計算のみ）。
  - portfolio_builder:
    - select_candidates(buy_signals, max_positions=10)：スコア降順・タイブレークに signal_rank を利用して候補を選択。
    - calc_equal_weights / calc_score_weights：等金額配分、スコア正規化配分。スコア合計が 0 の場合は等金額にフォールバック（警告）。
  - risk_adjustment:
    - apply_sector_cap：同一セクターの既存保有比率が上限（max_sector_pct、デフォルト 30%）を超える場合、新規候補を除外（"unknown" セクターは無視）。当日売却予定銘柄はエクスポージャー計算から除外可能。
    - calc_regime_multiplier：市場レジーム (bull/neutral/bear) に応じた投下資金乗数を返す（デフォルト/フォールバック: bull=1.0, neutral=0.7, bear=0.3、未知は 1.0 にフォールバックと警告）。
  - position_sizing:
    - calc_position_sizes：allocation_method ("risk_based" | "equal" | "score") に応じて発注株数を算出。
      - リスクベース: risk_pct, stop_loss_pct を使用して目標株数を算出。
      - 等配/スコア: weight を用いて個別配分を算出。
      - lot_size（単元株）で丸め、per-position 上限（max_position_pct）、aggregate cap（available_cash）を適用。
      - cost_buffer を使用して手数料・スリッページを保守的に見積もり、投資合計が available_cash を超える場合はスケールダウンして残差は lot_size 単位で配分。
- リサーチ / ファクター計算（基盤）
  - kabusys.research.factor_research: DuckDB 接続を受け取り、prices_daily / raw_financials を参照してモメンタム/Value/Volatility/Liquidity 等のファクターを計算する設計（モジュール構成と定数、calc_momentum の仕様を定義。実装の続きを含む）。
- ツール
  - kabusys.tools.paper_verification_report:
    - ペーパートレード用 SQLite DB（PAPER_TRADING_SQLITE_PATH）から指標を抽出して検証レポートを印字。
    - 指標: 稼働率 (uptime)、注文成功率 (fill_rate)、送信率 (send_rate)、P95 レイテンシ等。
    - デフォルト合格基準（例: uptime >= 99.0%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200 ms）。日付フィルタ (--from / --to) をサポート。
    - DB にテーブルが存在しない場合はフォールバックして N/A を扱う耐障害性を実装。
- その他ユーティリティ
  - tools/__init__.py の追加（パッケージ化）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- （現状特記事項なし）

### Notes / Implementation details
- 起動スクリプトは stop フラグ（data/stop_requested.flag）を用いた外部からの停止制御を採用。これは運用上の Kill Switch として利用可能。
- ログは標準出力とファイルに同時に出力する設計だが、ログディレクトリ作成失敗時はファイル出力を自動で無効化してコンソールのみで継続するため、Cron / Scheduler 環境でも起動失敗しにくい設計。
- プロセス優先度や CPU affinity 設定は権限に依存するため、失敗時は警告ログを出して処理継続する（安全設計）。
- .env のパースロジックは多くのケース（export プレフィックス、クォート内のエスケープ、インラインコメント）に対応しており、手動編集の柔軟性を高めている。
- Paper Trading と Live の DB 分離を明示（実行スクリプトが環境に応じて paper_sqlite を使用）。Monitoring は環境を問わず本番 sqlite_path を使用する意図がコードに明示されているため、運用時に注意が必要。

---

開発中の機能や TODO（コード内コメント参照）は今後のリリースで順次追加します。問題や要望があれば issue を作成してください。