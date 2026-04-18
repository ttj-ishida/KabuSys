CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
このファイルは、コードベースから推測した初期リリース向けの変更履歴です。

フォーマット:
  - Added: 新機能
  - Changed: 既存機能の変更（後方互換性に注意）
  - Fixed: バグ修正
  - Deprecated / Removed / Security: 該当するものがあれば記載

Unreleased
----------
（なし）

[0.1.0] - 2026-04-18
--------------------

Added
- 基本アーキテクチャと初期機能を実装（初回リリース）。
- 環境設定・読み込み
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。  
    - 優先順位: OS 環境変数 > .env.local > .env
    - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定可能。
  - Settings クラスにより環境変数をプロパティとして一元管理。
    - 多数の設定プロパティを提供（J-Quants / kabuAPI / LINE / DB パス / 監視閾値 等）。
    - KABUSYS_ENV, LOG_LEVEL などの入力検証を実施。
    - PAPER_FILL_MODE の検証（"instant" | "partial" | "never" | "reject"）。
    - PAPER_TRADING_SQLITE_PATH、DUCKDB_PATH、SQLITE_PATH 等のデフォルトパスを提供。
- 設定用 CLI / ユーティリティ
  - 対話式ウィザード: kabusys.config_setup
    - .env の初期作成・更新を対話式で支援。
    - シークレット項目はマスク表示。生成された .env をファイルに保存可能。
  - 設定検証 CLI: kabusys.validate_config
    - 必須環境変数・パス・config/*.yaml の存在や YAML パースを検証。
    - --strict オプションで警告を失敗扱いにする機能。
    - 本番（KABUSYS_ENV=live）向けの追加ガード（LINE 通知設定や Kill Switch 設定の警告）。
- 実行系 / 監視
  - run_execution.py
    - ExecutionEngine の起動スクリプトを実装。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用し、本番 DB と分離。
    - BrokerClientFactory を通じて実ブローカー／モックを切り替え可能。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み合わせて ExecutionEngine を起動。
    - stop フラグ（data/stop_requested.flag）および PID ファイル管理（data/execution.pid）に対応。
    - RiskManager のデフォルト設定を提供（max_position_pct, max_utilization 等）。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを実装。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用 sqlite_path を参照（環境に依らず本番監視 DB を使用する設計）。
    - stop フラグ検知で優雅に終了。
- データベース接続
  - sqlite3（監視・注文履歴等）と DuckDB（分析向け）両方の接続をサポート。
  - init_monitoring_db による監視テーブルの冪等初期化を実装。
- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio モジュールを追加:
    - portfolio_builder: 候補選定(select_candidates)、等分配(calc_equal_weights)、スコア加重(calc_score_weights)。
    - risk_adjustment: セクター上限適用(apply_sector_cap)、レジーム乗数(calc_regime_multiplier)。
      - calc_regime_multiplier: "bull"/"neutral"/"bear" に応じた乗数を返す（未知のレジームは 1.0 でフォールバック）。
    - position_sizing: calc_position_sizes により株数決定ロジックを実装（risk_based / equal / score）。
      - 単元株（lot_size）考慮、max_position_pct / max_utilization / cost_buffer（手数料・スリッページ想定）などに対応。
      - 集約キャップ超過時のスケーリング・端数調整ロジックを実装。
- ロギング / プロセス制御ユーティリティ
  - utils.logging_setup.setup_logging
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL から設定を解決。既存ハンドラの二重登録を防止。
  - utils.process_priority
    - set_process_priority(level) でプラットフォームに依存せずプロセス優先度を設定（Windows / POSIX を吸収）。
    - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアにピン固定可能（未設定で全コア）。
    - 呼び出し元は run_* スクリプト内で起動直後に優先度を "high" に設定。
- ツール
  - tools.paper_verification_report
    - Paper Trading の SQLite を走査して検証レポートを生成する CLI を実装。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなどを算出し PASS/FAIL 判定を行う。
    - --from / --to / --db オプションをサポート。
- research/factor_research（解析用）
  - ファクター計算フレームワークの骨格を実装（Momentum / Value / Volatility / Liquidity の方針、定数定義、calc_momentum の開始など）。
  - DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。
- パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として設定。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / Implementation details
- 環境変数のパースは .env のクォート / エスケープ / インラインコメントを考慮する独自実装を行っている。
- .env の上書きポリシー:
  - OS 環境変数は保護され、.env.local の override=True でも上書きされない。
- Paper Trading と本番 DB の完全分離:
  - Execution は settings.is_paper を参照して paper_sqlite_path を使用する（paper_trading の DB は data/paper_trading.db がデフォルト）。
- ログディレクトリの作成に失敗した場合はファイル出力を無効化し、コンソール出力のみで継続する設計。
- process_priority や CPU affinity の設定は権限不足や未対応プラットフォームで失敗する可能性があり、その場合は警告を出してスキップする。

Known issues / TODOs / Limitations
- 一部関数に TODO コメントあり（例: risk_adjustment.apply_sector_cap 内の price 欠損時のフォールバック価格ロジック）。
- position_sizing では将来的な拡張として銘柄別 lot_size を想定しているが現状は単一の lot_size 引数。
- research/factor_research の calc_momentum 等は断片的な実装（本リリースでは骨格・方針を提供）。
- run_monitoring は monitoring 用 DB を常に本番 sqlite_path から参照する設計のため、テスト時の分離に注意が必要。
- Paper Trading レポート生成は DB スキーマに依存する（テーブルがない場合は N/A を返す挙動）。

開発者向け補足
- 実行例:
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証:   python -m kabusys.validate_config [--strict]
  - Execution 起動: python -m kabusys.run_execution
  - Monitoring 起動: python -m kabusys.run_monitoring
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 重要環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
  - KABUSYS_ENV（development | paper_trading | live）
  - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
  - LOG_LEVEL, LOG_DIR, MONITOR_POLL_INTERVAL, KILL_FLAG_CLEAR_ON_START

ライセンスやセキュリティ
- .env は絶対に Git にコミットしない旨を config_setup のヘッダで明示。

---

この CHANGELOG はコードの内容から推測して作成しています。実際のリリースノートや意図と差異がある場合は、差分や補足情報を提供いただければ更新します。