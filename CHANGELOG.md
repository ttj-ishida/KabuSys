# Changelog

すべての重要な変更はこのファイルに記載します。フォーマットは "Keep a Changelog" に準拠しています。  
各リリースは日付順（最新→過去）で記載します。

注意: コードベースから推測して作成しています。実際の変更履歴やリリース日とは異なる場合があります。

## [Unreleased]

- ドキュメント化・コード整備のみ（特記事項なし）

## [0.1.0] - 2026-04-17

最初の公開リリース。日本株自動売買システム KabuSys の基本コンポーネントを実装しました。以下の機能・ユーティリティを含みます。

### Added
- コア設定・初期化
  - Settings クラスを追加し、環境変数からアプリ設定を取得可能に（J-Quants / kabuステーション / DB / 監視閾値等）。
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。

- 対話式設定ウィザード
  - config_setup CLI を追加（python -m kabusys.config_setup）。
  - .env の初期作成・更新を対話形式で支援。秘密項目のマスク表示、デフォルト値のサポート、.env 出力フォーマットを実装。

- 設定検証ツール
  - validate_config CLI を追加（python -m kabusys.validate_config）。
  - 必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスや config/*.yaml の存在とパース検証、live 環境向けの追加警告等を実装。
  - --strict オプションで警告を FAIL として扱う機能を追加。

- 実行・監視用の起動スクリプト
  - run_execution.py を追加。ExecutionEngine の起動フローを実装。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組立て、ExecutionEngine のスレッド実行、stop flag による安全停止、execution.pid の利用などを実装。
  - run_monitoring.py を追加。SystemMonitor のポーリングループ起動。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔の上書き（デフォルト 60 秒）。無効値はデフォルトにフォールバックして警告ログを出力。
    - 監視は KABUSYS_ENV に関係なく本番 sqlite_path を使用して監視テーブルを初期化。
    - data/stop_requested.flag による外部停止検知を実装。

- データベース / 分析
  - DuckDB と SQLite の両接続に対応（Settings.duckdb_path, Settings.sqlite_path）。
  - init_monitoring_db による監視テーブル初期化呼び出し（冪等）。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのスコア降順選定（同点時は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分。スコア合計が 0 の場合は等配分へフォールバックし警告を出力。
  - portfolio.risk_adjustment
    - apply_sector_cap: 既存保有に基づくセクター集中制限。unknown セクターは上限判定から除外。
    - calc_regime_multiplier: market レジーム ("bull","neutral","bear") に応じた投下資金乗数（未知レジームは 1.0 にフォールバックし警告）。
  - portfolio.position_sizing
    - calc_position_sizes: risk_based / equal / score の割当方式をサポート。lot_size（単元株）丸め、1 銘柄上限・投下合計（aggregate cap）のスケーリング、cost_buffer（手数料・スリッページ考慮）を実装。端数処理は残差に基づいて追加配分するアルゴリズムを提供。

- リサーチ / ファクター計算
  - research.factor_research を追加。
    - Momentum, Volatility（ATR）, Liquidity 等の因子計算を DuckDB 上の prices_daily テーブルを用いて実装。
    - データ不足時は None を返す安全設計。計算ウィンドウとスキャン範囲は定数化。

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収し、アクセス権限不足や未サポート環境では警告ログを出して処理をスキップ。

- ツール
  - tools.paper_verification_report を追加（python -m kabusys.tools.paper_verification_report）。
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を解析して検証レポートを生成。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率、リスク却下数、API レイテンシ（平均/最大/P95）など。
    - 閾値判定と PASS/FAIL 判定を組み込み。P95 はカスタム計算を実装。
    - 日付フィルタ（--from / --to）と --db オプションをサポート。

### Changed
- （初回リリースのため無し）

### Fixed
- （初回リリースのため無し）

### Security
- .env ファイル（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を生成する際に Git にコミットしないよう README へ注意を出力する構成に準拠（config_setup が .env ヘッダに注記）。

### Notes / 実装上の注意点
- .env パーサは以下をサポート:
  - 空白・コメント行、行頭の "export " プレフィックス、クォートされた値（シングル/ダブル）、およびインラインコメントの扱い（クォートありはエスケープを考慮して閉じクォートまでを値として扱う）。
- Settings.paper_fill_mode は有効値チェックを行い、不正な値では ValueError を送出。
- run_monitoring/run_execution は stop flag（data/stop_requested.flag）を監視して安全に終了する仕組みを持ちます。
- process_priority や CPU affinity の設定は権限不足や未サポート環境で例外にならないよう保護されています（警告ログのみ）。
- ファイルパスやディレクトリ存在チェックは validate_config で事前に警告を出すようにしています（起動時に自動作成される場合があるため注意喚起）。

---

Maintainers:
- 今後のリリースでは変更内容をセクション (Added, Changed, Fixed, Deprecated, Removed, Security) に分けて記載してください。