# Changelog

すべての注目すべき変更履歴はここに記載します。本ファイルは Keep a Changelog の形式に準拠します。  

各バージョンの記載は、公開時点での主要な追加・変更・修正を簡潔にまとめたものです。

## [Unreleased]

### Added
- （今後のリリースに向けた未反映の変更はここに記載します）

---

## [0.1.0] - 2026-04-17

初回リリース。以下の主要コンポーネントと CLI、ユーティリティを実装しています。

### Added
- 設定管理
  - Settings クラスを実装し、環境変数からアプリケーション設定を一元管理。
  - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可。
  - .env パースの強化（export 形式・クォート文字列・エスケープ・インラインコメント処理に対応）。
  - 設定項目（DB パス、KABUSYS_ENV、PAPER_FILL_MODE、PID/kill フラグパス等）の取得メソッドを提供。PAPER_FILL_MODE のバリデーションを実装。

- CLI ツール
  - config_setup: 対話式ウィザードで .env ファイルを生成・更新する CLI を実装。各項目の説明、デフォルト、シークレット扱い表示に対応。
  - validate_config: .env と config/*.yaml の設定妥当性チェックを行う CLI を実装。--strict オプションで警告を失敗扱いにできる。PyYAML 未導入時のフォールバック挙動を明記。
  - tools/paper_verification_report: ペーパートレード用の検証レポート生成ツールを実装。期間指定 (--from/--to) と DB パス指定 (--db) に対応。デフォルト DB パスは `data/paper_trading.db` または環境変数 `PAPER_TRADING_SQLITE_PATH`。

- 実行・監視エントリポイント
  - run_execution: ExecutionEngine 起動スクリプトを提供。プロセス優先度を高く設定、紙トレード（KABUSYS_ENV=paper_trading）の場合は paper_trading 用 DB に完全分離して接続（`data/paper_trading.db`）。BrokerClientFactory を用いてブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててエンジンを非同期スレッドで実行。停止フラグ（data/stop_requested.flag）および実行 PID ファイル管理をサポート。
  - run_monitoring: SystemMonitor 用のポーリングループ起動スクリプトを提供。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き（デフォルト 60 秒）。監視は常に本番用 sqlite_path を使用して監視 DB を初期化。停止フラグの検知と安全終了に対応。

- ポートフォリオ構築（pure functions）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順でソートし上位候補を返す。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。スコア総和が 0 の場合は等金額配分にフォールバックし警告を出す。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクターごとの既存エクスポージャが閾値を超える候補を除外するロジック。sell_codes（当日売却予定）を除外して計算。unknown セクターは上限適用対象外。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を返す（未知レジームは警告を出し 1.0 を返す）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based"、"equal"、"score"）に基づいて発注株数を算出。損切り率・リスク率・単元株丸め（lot_size）・max_position_pct・max_utilization・cost_buffer を考慮した aggregate cap（スケーリング）処理を実装。スケールダウン時の残差配分ロジックも実装。

- リサーチ / ファクター計算
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターンおよび 200 日移動平均乖離率（ma200_dev）を DuckDB 上の prices_daily テーブルから計算。
    - calc_volatility: ATR（20 日）、相対 ATR、20 日平均売買代金、出来高比などを計算するクエリ基盤を実装。
    - DuckDB を使った SQL ベースの集計で、データ不足時には None を返す設計。

- モニタリング DB 初期化
  - monitoring.monitoring_db の初期化を起動スクリプト側で呼び出し、監視テーブルの存在を保証（冪等）。

- プロセス制御ユーティリティ
  - utils.process_priority
    - set_process_priority: Windows / POSIX（Linux, Darwin, FreeBSD）に対応してプロセス優先度を設定。権限不足や未サポート機能はロギングしてスキップ。
    - set_cpu_affinity: 指定コア数で CPU affinity を設定（存在しない・権限不足時は警告）。

- ペーパートレード検証（ツール）
  - tools.paper_verification_report による指標算出と判定ロジックを提供（稼働率、注文成功率・送信率、P95 レイテンシなど）。既定の合格閾値を設定（例: 稼働率 >= 99%、注文成功率 >= 90%、P95 <= 200ms）。

- パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として設定。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

---

補足 / 使用例
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは paper_trading DB を使用して本番 DB と分離
- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定可能
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを明示可能、未指定時は PAPER_TRADING_SQLITE_PATH または data/paper_trading.db を使用

（この CHANGELOG はコード内容から推測して作成しています。実際のリリースノートとして公開する際は、差分やコミット履歴に基づいた精査を推奨します。）