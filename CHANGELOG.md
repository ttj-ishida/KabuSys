# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングを採用します。

## [Unreleased]

## [0.1.0] - 2026-04-17
初回リリース — 基本機能の実装一式を追加。

### Added
- 基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 設定管理
  - 環境変数/.env 管理モジュールを追加（kabusys.config）。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）。
    - 自動で .env / .env.local を読み込み（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
    - export 形式やクォート、インラインコメントに対応した行パーサを実装。
    - 環境変数上書き時に OS 環境変数を保護する仕組みを実装。
    - `Settings` クラスを導入し、J-Quants / kabuステーション / DB / 監視閾値等のプロパティを提供。
    - `PAPER_FILL_MODE` のバリデーション（有効値: instant|partial|never|reject）。
    - `KABUSYS_ENV` / `LOG_LEVEL` の検証と `is_live` / `is_paper` / `is_dev` のユーティリティ。

- 設定ユーティリティ CLI
  - 対話式 .env ウィザード（kabusys.config_setup）を追加。
    - .env の読み込み・既存値の利用、秘密値のマスク表示、保存機能を提供。
  - 設定検証 CLI（kabusys.validate_config）を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML があれば）パース検証。
    - `--strict` オプションで警告も失敗扱いにする。

- 実行・監視ランナー
  - Execution エントリスクリプト（kabusys.run_execution）を追加。
    - 起動時にプロセス優先度を "high" に設定。
    - `KABUSYS_ENV=paper_trading` の場合は paper 専用 SQLite（`PAPER_TRADING_SQLITE_PATH` / default: data/paper_trading.db）を用いることで本番 DB と分離。
    - BrokerClientFactory によるブローカクライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立て。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を組み込み、`initial_portfolio_value` を broker.get_available_cash() から初期化。
    - ExecutionEngine をバックグラウンドスレッドで実行し、プロジェクト内の stop フラグファイル（data/stop_requested.flag）や PID ファイル（data/execution.pid）により停止制御。
    - 監視テーブルの存在を保証するため init_monitoring_db() を呼び出す（冪等）。

  - Monitoring エントリスクリプト（kabusys.run_monitoring）を追加。
    - 起動時にプロセス優先度を "high" に設定。
    - 監視ループのポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値や 0 以下はデフォルトにフォールバック。
    - Monitoring は実行環境にかかわらず本番用 `sqlite_path` を使用する（監視 DB は一元管理）。
    - stop フラグファイル検知でループを終了し、SystemMonitor.check_once() を安全に呼び出す（例外はログに残して次ポーリングへ）。

- 監視 DB 初期化ユーティリティ
  - init_monitoring_db()（monitoring.monitoring_db）を利用して監視用テーブルの存在を保証する処理を導入。

- ポートフォリオ構築ライブラリ
  - portfolio.portfolio_builder
    - select_candidates: スコア降順・タイブレークルールで候補選定。
    - calc_equal_weights: 等金額配分を返す。
    - calc_score_weights: スコア加重配分を返す。全スコアが 0 の場合は等金額にフォールバックし警告ログを出力。

  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中を抑制するため、既存保有のセクターエクスポージャーが閾値を超える場合に当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: レジームラベルに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバックして警告ログ。

  - portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に応じた発注株数計算を実装。
      - リスクベース（risk_based）ではリスク許容率・ストップロスから株数を算出し単元株（lot_size）で丸め。
      - equal/score 方式では重み・max_utilization・max_position_pct を考慮して目標株数を算出。
      - aggregate cap のスケールダウン処理を実装（コストバッファを考慮、端数は lot_size 単位で残差配分）。
      - 価格欠損時のスキップやログ出力、lot_size 固定制約あり。将来的に銘柄別 lot_size 拡張を想定した TODO コメントあり。

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level): Windows と POSIX (Linux, macOS, FreeBSD) に対応、psutil を利用して優先度を設定。権限不足など失敗時は警告ログを出してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数に固定するユーティリティ（無指定は何もしない）。権限不足や未対応環境では警告を出してスキップ。

- 研究用ファクター計算
  - research.factor_research
    - DuckDB 接続を受け、prices_daily / raw_financials を用いてファクターを計算する設計。
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev の算出（データ不足時は None）。
    - calc_volatility: ATR(20), 相対 ATR, 20日平均売買代金, 出来高比率等の算出（データ不足時は None）。
    - DuckDB SQL を活用した窓関数中心の実装と、スキャン範囲バッファ設定。

- Paper Trading 検証レポート
  - tools.paper_verification_report
    - paper_trading SQLite（デフォルト: data/paper_trading.db）から各種指標を集計して人間向けレポートを出力。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率、リスク却下数、レイテンシ（avg/max/P95）を算出。
    - P95 計算ヘルパ、期間フィルタ（--from / --to）、--db オプションをサポート。
    - 判定基準（閾値）を定義し PASS/FAIL 判定を行う。

### Changed
- 設定の自動読み込みの優先順位を明確化: OS 環境変数 > .env.local > .env。既存 OS 環境変数は保護されるため失敗による上書きは発生しない。
- 監視（run_monitoring）は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する旨を明記（監視データは環境に依存しない一元管理を想定）。

### Notes / Implementation details
- 多くの関数は外部副作用を最小化するよう設計され、DB 参照箇所は明示（DuckDB / SQLite）、ポートフォリオ関連関数は純粋関数（メモリ内計算）として実装。
- 例外処理やログ出力を積極的に行い、実運用での安全性（stop フラグ対応・権限不足時のフォールバックなど）を重視しています。
- 一部ファイル（例えば factor_research の末尾やドキュメント参照）は将来的に拡張・補完される余地があります（TODO コメントあり）。

---

今後のリリースでは、テストカバレッジの追加・ブローカラッパーの拡充・銘柄別 lot_size 対応・更なる監視アラート（LINE通知等）を予定しています。