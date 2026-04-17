CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。

v0.1.0 — 2026-04-17
-------------------

Added
- 初回リリース。KabuSys の基本的な自動売買／検証基盤を実装。
- 設定管理
  - Settings クラスを導入し、環境変数経由で設定を一元管理（J-Quants / kabuステーション / DB パス /監視閾値 等）。
  - .env の自動ロード機能を実装（プロジェクトルートの .env / .env.local を読み込み、OS 環境変数を保護）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
  - PAPER_FILL_MODE といった Paper Trading 固有設定のバリデーション実装（有効値チェック）。
- 設定支援ツール
  - 対話式ウィザード (kabusys.config_setup) を追加。.env の初期作成／更新を支援。
  - 設定検証 CLI (kabusys.validate_config) を追加。必須環境変数、パス、config/*.yaml の存在・パースチェック、live 環境向けのガードチェック等を行う。--strict オプションで警告を失敗扱いにできる。
- 実行スクリプト
  - ExecutionEngine 起動スクリプト (run_execution.py) を追加。
    - KABUSYS_ENV=paper_trading 時は paper 専用 SQLite（data/paper_trading.db を既定）を使用し、本番 DB と完全分離。
    - BrokerClientFactory 経由でブローカクライアントを作成（モック含む）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。Engine はデーモンスレッドで run_session を実行し、data/stop_requested.flag による停止を監視。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を利用）。
  - SystemMonitor 起動スクリプト (run_monitoring.py) を追加。
    - 監視ループは MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下の値はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視 DB を初期化（init_monitoring_db 呼び出し）。
    - stop フラグ (data/stop_requested.flag) によりループ終了。
- DB / 分析
  - DuckDB 連携を組み込み（Settings.duckdb_path）。各処理で duckdb 接続を受け取る設計。
  - 監視用 SQLite (monitoring.db) と paper_trading 用 SQLite の分離をサポート。
- モジュールとアルゴリズム（ポートフォリオ構築）
  - portfolio.portfolio_builder
    - 銘柄候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全て 0 の場合は等金額にフォールバックして警告を出す。
  - portfolio.risk_adjustment
    - セクター集中制限（apply_sector_cap）：既存保有のセクター比率が閾値を超える場合、そのセクターの新規候補を除外。unknown セクターは除外しない動作。
    - レジーム乗数（calc_regime_multiplier）：regime ラベル（"bull"/"neutral"/"bear"）に基づき投下資金乗数を返す。未知レジームは 1.0 でフォールバックし警告を出す。
  - portfolio.position_sizing
    - allocation_method ("risk_based", "equal", "score") に対応した株数算出を実装。lot_size（単元）で丸め、1銘柄上限・aggregate cap（available_cash）に基づくスケーリングと端数配分ロジックを実装。
    - cost_buffer（手数料・スリッページ見積り）を考慮した保守的なコスト見積りを導入。
- Utilities
  - process_priority ユーティリティを実装（Windows / POSIX の差分吸収）。set_process_priority(level) で現在プロセスの優先度を設定。set_cpu_affinity(cpu_count) で CPU affinity を最初の N コアにピン留めする機能を提供。権限不足や未対応 OS の場合は警告を出してスキップ。
- リサーチ
  - research.factor_research モジュールを追加。DuckDB の prices_daily / raw_financials を使って各種ファクター（Momentum / Volatility / Liquidity / Value 等）を計算する設計。calc_momentum / calc_volatility 等の実装を含む（MA200、ATR、複数期間リターン 等）。
- ツール
  - tools.paper_verification_report を追加。Paper Trading 用 SQLite から以下の指標を集計してレポート出力:
    - 稼働率（system_status テーブル）、総ポーリング数、エラー数
    - 注文成功率（Filled / Created）、送信率（Sent / Created）
    - リスク却下数（risk_logs）
    - レイテンシ（avg / max / P95）
    - 基準値（稼働率 >=99%、fill>=90%、send>=95%、P95<=200ms）に基づく PASS/FAIL 判定
  - レポートは期間指定 (--from / --to) と DB パス指定 (--db) に対応。
- パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として定義。

Changed
- なし（初回リリースのため）。

Fixed
- なし（初回リリースのため）。

Removed
- なし（初回リリースのため）。

Notes / 注意点
- .env はセキュリティ上 Git にコミットしないことをドキュメントで強調（config_setup の出力にも記載）。
- run_monitoring と run_execution はプロセス優先度設定や stop フラグ、PID ファイル等の外部ファイルに依存。運用環境でのファイルパーミッションやディレクトリ構成に注意。
- position_sizing・risk_adjustment 等は現在メモリ内純粋関数として実装されており、外部 DB 参照は行わない。将来的な拡張（銘柄ごとの lot_size マスタ、価格フォールバック等）を想定したコメントを含む。
- research モジュールは DuckDB と prices_daily/raw_financials の整備を前提とする。PyYAML 等外部依存は設定検証ツールで graceful に扱う。

貢献方法
- バグ報告・機能提案は Issue を立ててください。プルリクエストはテスト・型チェック・ドキュメントを含めて提出してください。