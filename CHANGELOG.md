# Changelog

すべての注目すべき変更をここに記録します。フォーマットは "Keep a Changelog" に準拠します。

最新版: 0.1.0 (初期リリース)

## [Unreleased]
- なし

## [0.1.0] - 2026-04-21

### Added
- 初回リリースとして KabuSys の基本コンポーネントを追加しました。主な追加点は以下の通りです。

- 環境設定 / 設定読み込み（src/kabusys/config.py）
  - .env / .env.local からの自動環境変数読み込みを実装（プロジェクトルート検出: .git または pyproject.toml を利用）。
  - export KEY=val 形式・クォート文字列・インラインコメントなどに対応した堅牢なパーサを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
  - Settings クラスを導入し、J-Quants / kabu API / DB パス / paper trading 等の設定プロパティを提供。
  - paper_fill_mode のバリデーション（instant/partial/never/reject）や env 値検証（KABUSYS_ENV, LOG_LEVEL）を実装。

- 対話式設定ウィザード（src/kabusys/config_setup.py）
  - .env の初期作成・更新を支援する CLI ウィザードを追加。
  - シークレット入力のマスク、既存 .env の読み込み、確認表示、.env への書き出し機能を実装。

- 設定検証 CLI（src/kabusys/validate_config.py）
  - 必須環境変数やパス、config/*.yaml の存在・パース検証を行う CLI を追加。
  - --strict オプションで警告も失敗扱いにできる。
  - PyYAML 未インストール時は YAML 検証をスキップして警告を出す。

- 起動スクリプト：Execution / Monitoring（src/kabusys/run_execution.py, src/kabusys/run_monitoring.py）
  - run_execution:
    - プロセス優先度を最初に "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を利用し、本番 DB と分離。BrokerClientFactory により MockBrokerClient 利用を選択。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を別スレッドで実行。data/stop_requested.flag による安全停止、pid ファイル管理を実装。
    - RiskConfig のデフォルト値（max_position_pct=0.20 等）を設定し、初期 available_cash を broker.get_available_cash() から取得。
  - run_monitoring:
    - SystemMonitor のポーリングループ起動スクリプトを提供。
    - MONITOR_POLL_INTERVAL 環境変数で間隔上書き（デフォルト 60 秒）。不正値はデフォルトへフォールバックして警告。
    - 監視用 DB は環境に関わらず本番 sqlite_path を使用（初期化関数 init_monitoring_db を呼び出し）。
    - data/stop_requested.flag による停止検知、例外時のロギング/リカバリ（次のポーリングへ継続）。

- ロギングユーティリティ（src/kabusys/utils/logging_setup.py）
  - ルートロガーに対する共通初期化関数を実装。
  - stdout 出力の StreamHandler と 日次ローテートする TimedRotatingFileHandler（logs/<app_name>.log、30日保持）を設定。
  - LOG_LEVEL / LOG_DIR / app_name を解決し、既存ハンドラの二重登録を防止。
  - ログディレクトリ作成失敗時はファイル出力をスキップして標準出力のみで継続。

- プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
  - set_process_priority(level) による Windows / POSIX (Linux, Darwin, FreeBSD) 対応の優先度設定を提供。psutil を使用し、権限不足や未サポート環境では警告を出してスキップ。
  - set_cpu_affinity(cpu_count) によるコア固定機能を実装（安全なフォールバックとエラーハンドリング付き）。

- ポートフォリオ構築ライブラリ（src/kabusys/portfolio/*）
  - portfolio_builder:
    - select_candidates: スコア降順・signal_rank でのタイブレークによる候補選定。
    - calc_equal_weights, calc_score_weights: 等分配 / スコア加重（全スコア0時は等分配にフォールバック）を実装。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存ポジションを基に新規候補をフィルタ）。unknown セクターは上限適用除外。
    - calc_regime_multiplier: market regime による投下資金乗数（bull/neutral/bear）を実装。未知レジームは警告後フォールバック。
  - position_sizing:
    - calc_position_sizes: risk_based / equal / score の配分方式をサポート。lot_size（単元）で丸め、per-stock 上限・aggregate cap（available_cash）を考慮したスケーリングと残余分の配分ロジックを実装。cost_buffer による保守的コスト見積りを考慮。

- Paper Trading 検証レポート生成ツール（src/kabusys/tools/paper_verification_report.py）
  - 指定期間の paper_trading DB（デフォルト: data/paper_trading.db）から以下の指標を集計・出力:
    - 稼働率 (uptime)、ポーリング数、エラー数
    - 注文 Created/ Filled / Sent カウント → 注文成功率・送信率
    - risk_logs によるリスク却下数
    - 平均 / 最大 / P95 レイテンシ（ms）
  - PASS/FAIL 判定ロジック（閾値はソース内定義: uptime >= 99%、fill >= 90%、send >= 95%、P95 <= 200ms）。
  - CLI オプション --from/--to/--db を提供。

- 研究用ファクター計算（src/kabusys/research/factor_research.py）
  - DuckDB 接続を受けて Momentum / Value / Volatility / Liquidity 系ファクターを計算する設計（prices_daily / raw_financials テーブル参照）。
  - モメンタム計算用の定数・骨格を実装（1M/3M/6M リターン、MA200 乖離、ATR、出来高系）。（一部実装は進行中の箇所あり）

- パッケージメタ情報（src/kabusys/__init__.py）
  - バージョン情報 __version__ = "0.1.0" を設定し、主要サブパッケージを __all__ に追加。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

注記:
- 多くの機能は外部ライブラリ（psutil, duckdb, sqlite3, PyYAML 等）への依存があります。実行環境に応じて必要なパッケージをインストールしてください。
- run_execution/run_monitoring はファイルベースの停止フラグ（data/stop_requested.flag）や pid ファイルを用いる設計です。運用時はこれらの配置・権限を適切に管理してください。
- research/factor_research.py はファクター計算の主要ロジックを定義していますが、一部実装やテストが未完の箇所があります。研究用途として導入し、運用前に検証してください。