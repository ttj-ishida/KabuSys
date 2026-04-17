# Changelog

すべての重要な変更点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

全般:
- 初期リリース (0.1.0)。プロジェクトの基本的な CLI / 実行スクリプト、設定管理、ポートフォリオ構築ロジック、ユーティリティ、検証・レポートツール等を含みます。

## [Unreleased]

## [0.1.0] - 2026-04-17

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 設定管理
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env パーサ実装（export プレフィックス対応、シングル/ダブルクォート、エスケープ、インラインコメント処理）。
  - Settings クラスを実装し、各種環境変数の取得・検証を提供（J-Quants/Tokabu API、DB パス、監視閾値、実行環境など）。
  - 環境値の事前検証 CLI: `kabusys.validate_config`（.env と config/*.yaml の存在・妥当性チェック、--strict オプション対応）。
  - インタラクティブな .env 作成ウィザード: `kabusys.config_setup`（既存 .env 読み込み、マスク表示、確認・保存機能）。

- 実行スクリプト
  - 監視ループ起動: `run_monitoring.py`
    - SystemMonitor の初期化とポーリングループを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視 DB は KABUSYS_ENV に依らず本番用 sqlite_path を使用。
    - 停止制御: プロジェクトの data/stop_requested.flag を検知してループを終了。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority 経由）。
  - 実行エンジン起動: `run_execution.py`
    - ExecutionEngine の起動・スレッド実行、停止フラグ監視、PID ファイル管理。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を使用して本番 DB と分離。
    - BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler 等を組み立てて実行。

- 監視/モニタリング
  - 監視 DB 初期化ユーティリティ（init_monitoring_db）を呼び出して必要テーブルの冪等的作成を保証。

- 実行コンポーネントのデフォルト設定
  - RiskManager の既定パラメータ（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20 等）を定義。
  - ExecutionEngine における EngineConfig 初期化（target_date に date.today() を使用）。

- ツール
  - Paper Trading 検証レポート生成スクリプト: `kabusys.tools.paper_verification_report`
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から集計を行い、稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）等を出力。
    - 判定基準（デフォルト閾値）を定義:
      - 稼働率: >= 99.0%
      - 注文成功率 (fill_rate): >= 90.0%
      - 送信率 (send_rate): >= 95.0%
      - P95 レイテンシ: <= 200 ms
    - 日付フィルタ (--from/--to)、--db オプション対応。
    - P95 計算ユーティリティ実装。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - 候補選定・重み付け: select_candidates, calc_equal_weights, calc_score_weights を実装。
    - select_candidates: スコア降順、同点は signal_rank 昇順でタイブレーク。
    - calc_score_weights: 全スコアが 0 の場合は等分配にフォールバック（警告ログ）。
  - リスク調整: apply_sector_cap, calc_regime_multiplier を実装。
    - セクター集中上限（max_sector_pct）に基づき候補を除外。unknown セクターは除外対象外。
    - 市場レジーム乗数: bull/neutral/bear に対応（デフォルトフォールバックあり）。
  - ポジションサイズ計算: calc_position_sizes を実装。
    - allocation_method: "risk_based" / "equal" / "score" に対応。
    - 単元（lot_size）で丸め、max_position_pct・max_utilization・cost_buffer を考慮した aggregate scale-down を実装。
    - 端数処理で残余キャッシュを利用し、lot 単位で追加配分するアルゴリズムを導入。
    - 価格欠損時のスキップ、価格ゼロの安全弁等を考慮。

- 研究（リサーチ）モジュール
  - ファクター計算: `kabusys.research.factor_research`
    - DuckDB 接続を受け取り prices_daily 等のテーブルからモメンタム・ボラティリティ等のファクターを算出する関数を実装（例: calc_momentum, calc_volatility）。
    - momentum: 1M/3M/6M リターン、MA200 乖離率を計算（データ不足の場合は None）。
    - volatility: ATR、平均売買代金、出来高比率等を計算する準備。

- ユーティリティ
  - プロセス優先度・CPU affinity ユーティリティ: `kabusys.utils.process_priority`
    - Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収してプロセス優先度 (nice / HIGH_PRIORITY_CLASS 等) を設定。
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未対応 OS の場合は警告ログでスキップする安全設計。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Deprecated
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- .env の取り扱いに関する注意を README/ウィザードヘッダーに追加（.env をコミットしないことを明記）。

---

注意事項 / マイグレーションノート:
- .env は自動で読み込まれますが、OS 環境変数が優先されます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- paper_trading 実行時は monitoring DB と本番 DB を分離するため、`PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）を利用します。誤って本番 DB を上書きしないよう注意してください。
- 監視ループはデフォルト 60 秒でポーリングします。短くすると負荷が高まるため運用時は慎重に設定してください（ENV: MONITOR_POLL_INTERVAL）。
- プロセス優先度や CPU affinity の設定は権限に依存し、失敗した場合はログの警告でスキップされます。

README やドキュメントに記載されている「次のステップ」通り、まず .env を作成（python -m kabusys.config_setup）→ 設定検証（python -m kabusys.validate_config）→ 実行（python -m kabusys.run_execution / run_monitoring）を推奨します。