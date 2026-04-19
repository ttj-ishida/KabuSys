CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
日付はコードベース中の記述やファイルから推測して付与しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-19
--------------------

Added
- 初回リリース。KabuSys 自動売買システムのコアユーティリティと CLI / ランナー群を追加。
  - 起動スクリプト
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 停止フラグ（data/stop_requested.flag）検知による安全停止、SQLite / DuckDB の接続管理を実装。
      - 監視は環境設定にかかわらず本番用 sqlite_path を使用する旨を明確化。
    - run_execution.py
      - ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し paper_trading 専用 DB（data/paper_trading.db をデフォルト）に記録して本番 DB と完全分離。
      - 停止フラグ（data/stop_requested.flag）検知によるセッション停止、実行用 PID ファイル管理を実装。
  - 設定管理
    - config.py
      - .env 自動読み込み（プロジェクトルートの検出: .git または pyproject.toml ベース）、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート。
      - .env のパースロジックを充実（export 形式、クォート内のバックスラッシュエスケープ、インラインコメント処理などをサポート）。
      - 各種設定プロパティを提供（J-Quants / kabuAPI / DB パス / Paper Trading 設定 / 監視閾値 / 環境種別 等）。
      - PAPER_FILL_MODE の検証と有効値チェックを実装。
    - config_setup.py
      - 対話式 .env 作成ウィザードを追加（既存 .env の読み込み・更新、秘密値マスキング表示、保存）。
    - validate_config.py
      - 起動前の設定検証 CLI を追加。
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検査（PyYAML がある場合）を実装。
      - --strict オプションで警告も FAIL 扱いにできる。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder
      - select_candidates: BUY シグナルのスコアソートと上位 N 選出。
      - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分（全スコアが 0 の場合は等分配へフォールバック）。
    - portfolio.risk_adjustment
      - apply_sector_cap: セクター集中上限チェック。既存保有のセクター別エクスポージャ計算と候補除外。
      - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear、未知レジームはフォールバック）。
    - portfolio.position_sizing
      - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算。
      - 単元（lot_size）丸め、per-position 上限、aggregate cap（available_cash）に基づくスケーリング、cost_buffer を用いたコスト保守見積り、端数分配ロジックを実装。
  - ユーティリティ
    - utils.logging_setup
      - 統一ログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。
      - LOG_DIR/LOG_LEVEL の解決順を定義。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - utils.process_priority
      - プロセス優先度設定ユーティリティを追加（Windows / POSIX の差分を吸収）。
      - CPU affinity 設定関数 set_cpu_affinity を提供。権限不足や未対応 OS 時に安全にスキップする設計。
  - ツール類
    - tools.paper_verification_report
      - Paper Trading 用検証レポート生成スクリプトを追加。システム稼働率、注文成功率・送信率、リスク却下数、平均/最大/P95 レイテンシなどを算出して PASS/FAIL を判定。
      - コマンドライン引数 --from / --to / --db をサポート。PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定可能。
  - 研究用モジュール（骨組み）
    - research.factor_research
      - モメンタム等のファクター計算のための基本設計と一部実装（定数、関数プロトタイプ）を追加。DuckDB 接続を受け取る設計。

Changed
- なし（初回リリースのため該当なし）。

Fixed
- なし（初回リリースのため該当なし）。

Notes / 実装上の注意
- 監視（run_monitoring）は意図的に環境に依存せず本番 sqlite_path を参照する設計になっています（監視データは本番 DB に集約する想定）。
- 実行エンジン（run_execution）は paper_trading 環境時に DB を分離することでペーパートレードと本番のログを混在させないように設計されています。
- .env のパースは実運用の .env ファイルに多く見られるパターン（export プレフィックス、クォート、エスケープ、インラインコメント）に耐性があるよう強化されていますが、極端なケースは想定外の振る舞いをする可能性があります。
- ログ設定はログディレクトリ作成に失敗した場合でも起動を止めずに stdout 出力のみで継続するため、システム監視環境においても柔軟に動作します。
- プロセス優先度・CPU affinity の設定は権限不足や未サポート OS の場合は警告ログを出してスキップする安全設計です。

開発 / 今後の TODO（コード内コメントより推測）
- position_sizing: 銘柄別の lot_size 対応（将来的に stocks マスタに lot_size を追加）。
- risk_adjustment.apply_sector_cap: 価格欠損時のフォールバック（前日終値や取得原価など）を検討。
- research.factor_research: ファクター計算の具体実装（SQL クエリや欠損処理）の続き実装。
- ロギング・監視周りの詳細メトリクス出力やアラート連携（LINE 送信など）の実装強化。

メンテナンス
- バージョンは src/kabusys/__init__.py にて __version__ = "0.1.0" として管理。

-----