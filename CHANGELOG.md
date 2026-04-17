# Changelog

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) の形式に従って記載しています。

## [Unreleased]

（現在のリポジトリ状態を基に推測して CHANGELOG を作成しています。実際のリリース履歴は開発プロセスに応じて調整してください。）

### 追加
- 全体
  - パッケージの初期実装を追加。バージョンは `__version__ = "0.1.0"`。
  - DuckDB と SQLite を併用したデータ処理/監視インフラを導入。
- 設定関連
  - Settings クラスを実装し、環境変数から各種設定（DBパス、APIトークン、監視閾値、実行環境など）を取得できるようにした。
  - .env 自動ロード機構を実装（プロジェクトルート探索: .git または pyproject.toml を基準）。
  - .env のパースを堅牢化:
    - export KEY=val 形式対応、シングル/ダブルクォート内のエスケープ対応、インラインコメントの扱いなど。
    - OS 環境変数を保護して .env.local で上書き可能にする仕組みを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、KILL_FLAG_CLEAR_ON_START 等の環境変数をサポート・検証。
- CLI ツール
  - config_setup: 対話式ウィザードで .env を初期作成/更新する CLI を追加。
  - validate_config: .env や config/*.yaml の簡易検証ツールを追加。--strict オプションで警告を FAIL 扱いにできる。
- 実行/監視プロセス
  - run_execution: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使い、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント抽象化を利用。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立て、ExecutionEngine に渡す。
    - 停止フラグ（data/stop_requested.flag）および実行用 PID ファイル(data/execution.pid) に対応。
    - RiskManager のデフォルト設定を定義（max_position_pct, max_utilization, rate_limit_per_sec 等）。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - モニタリングは環境に関わらず本番用 sqlite_path を使用。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 起動時にプロセス優先度を High に設定し、停止フラグでループを終了。
    - check_once() の例外を捕捉してログに出力しつつ次のポーリングへフォールバック。
- utils
  - process_priority: プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加。
    - set_process_priority(level) を実装（Windows, Linux/macOS 等対応）。
    - set_cpu_affinity(cpu_count) を実装（指定コア数でプロセスをピン固定）。
    - アクセス権や未対応環境での失敗は警告ログにとどめる安全設計。
- ポートフォリオ構築
  - portfolio モジュールを追加（完全に純粋関数で DB に依存しない実装）。
  - portfolio_builder:
    - select_candidates: スコア降順かつ tie-break に signal_rank を使った候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア全体が 0 の場合は等配分にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限の適用（sell_codes を除外して既存ポジションのエクスポージャー計算）。
    - calc_regime_multiplier: market regime (“bull”, “neutral”, “bear”) による投下資金乗数。
  - position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく株数算出。
    - 単元株（lot_size）、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap スケーリングと lot_size 切り捨て/再配分ロジックを実装。
- リサーチ/ファクター
  - research.factor_research:
    - calc_momentum: Mom(1M/3M/6M) と 200 日移動平均乖離率を DuckDB を使って計算。
    - calc_volatility: ATR(20)、ATR 比率、20日平均売買代金、出来高比率等を計算する処理を実装（DuckDB SQL によるウィンドウ集計）。
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を行う。
    - デフォルト閾値を定義（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）。
    - 日付フィルタ (--from/--to) と DB パス指定 (--db / PAPER_TRADING_SQLITE_PATH) をサポート。
- モジュールエクスポート
  - kabusys.portfolio パッケージで主要関数を外部に公開する __all__ を整備。

### 変更
- デフォルト挙動・安全性
  - 設定読み込み順序を OS 環境 > .env.local > .env に定義し、OS 環境を保護する動作を導入。
  - run_execution/run_monitoring 起動時にプロセス優先度を設定して実行の安定化を狙う。
  - run_execution では paper_trading 用 DB を分離して本番データと混ざらないようにした。

### 修正
- 入力/出力の堅牢化
  - .env 読み書きのエラーを warnings.warn で通知するなど安全に失敗する実装。
  - run_monitoring のポーリングループで check_once() の例外を捕捉してログを残すようにして、監視が一度の例外で停止しないようにした。
  - process_priority の実行で権限エラーや未対応 API の場合は警告ログを出す実装にしてクラッシュを回避。

### 既知の制約 / TODO（コードから推測）
- position_sizing の lot_size は現状全銘柄共通の想定。将来的に銘柄別 lot_map を導入する余地あり。
- apply_sector_cap の価格欠損（price が 0.0 の場合）によりエクスポージャーが過少見積りされる可能性がある旨の TODO コメントあり（前日終値等のフォールバックを検討）。
- research.factor_research のクエリ実行範囲や NULL 扱いの設計は大量データ運用時にチューニングが必要。
- Paper Trading 検証ツールは DB スキーマ（system_status / trade_logs / risk_logs / latency 列等）に依存するため、schema の変更はツール側の修正を伴う。

---

## [0.1.0] - 2026-04-17

初期公開リリース。
- 上記「追加」項目の全機能を含む初回リリース。
- CLI（config_setup, validate_config）、実行スクリプト（run_execution, run_monitoring）、ユーティリティ群、ポートフォリオ構築・サイズ算出・リスク調整ロジック、ファクター計算、Paper Trading 検証レポートを含む。

（注）リリース日・バージョンはソース内の __version__ と推測日を基に設定しています。実際のリリース運用に合わせて日付・バージョンを調整してください。