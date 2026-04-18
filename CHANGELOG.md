CHANGELOG
=========

すべての変更は Keep a Changelog の慣例に従って記載しています。  
日付はコードベースから推測したリリース日です。

Unreleased
----------

- なし

[0.1.0] - 2026-04-18
--------------------

Added
- 初回公開リリース。
- 実行・監視エントリポイントを追加
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading DB（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を利用する仕様を実装。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、および ExecutionEngine のデーモンスレッド起動を行う。
    - 停止制御はプロジェクト直下の data/stop_requested.flag と data/execution.pid を使用。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 監視モジュールは環境にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化。
    - 停止制御は data/stop_requested.flag を使用。
- 設定管理・読み込み機能を追加
  - config.py
    - .env/.env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env の行パーサーを実装（export プレフィックス対応、シングル/ダブルクォート対応、インラインコメント処理、保護された OS 環境変数の上書き制御）。
    - Settings クラスを提供し、環境変数の取得とバリデーションを簡易化（KABUSYS_ENV・LOG_LEVEL・PAPER_FILL_MODE 等の検証、各種パスの Path 変換）。
- CLI ユーティリティを追加
  - validate_config.py
    - .env と config/*.yaml の起動前検証ツールを追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パス親ディレクトリチェック、YAML パース確認（PyYAML がない場合はスキップして警告）、本番向けの追加ガードを実装。
    - --strict モードで警告も失敗として扱える。
  - config_setup.py
    - 対話式ウィザードで .env を作成/更新するツールを追加。既存値の再利用、シークレットマスク表示、デフォルト値・選択肢のサポート、.env のテンプレート書き出しを実装。
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite DB を読み、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数などを集計して検証レポートを出力するツールを追加。
    - 閾値を用いた PASS/FAIL 判定を実装（稼働率99%・成立率90% 等のデフォルト閾値）。
- ポートフォリオ構築関連の純粋関数群を追加（DB 非依存、メモリ内計算）
  - portfolio/portfolio_builder.py
    - BUY シグナルの候補選定 (select_candidates)、等重み (calc_equal_weights)、スコア重み (calc_score_weights) を実装。スコアが全て 0 の場合は等重みへフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用 (apply_sector_cap)、市場レジームに基づく乗数計算 (calc_regime_multiplier) を実装。
    - 未知のレジームは警告を出してフォールバック（1.0）。
  - portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に基づく株数計算を実装。単元株（lot_size）丸め、1 銘柄上限・総投資上限（aggregate cap）のスケーリング、手数料・スリッページを考慮する cost_buffer、空価格ハンドリング等を実装。
- ユーティリティを追加/強化
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを実装。stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log）を設定。既存ハンドラの二重登録防止とログディレクトリ作成失敗時のファイル出力無効化処理を実装。
  - utils/process_priority.py
    - クロスプラットフォームのプロセス優先度設定と CPU affinity 設定を実装（psutil を利用）。Windows と POSIX（Linux/Mac/FreeBSD）向けに差分吸収、サポート外 OS や権限不足時は警告を出してスキップ。
- research/factor_research.py
  - ファクター計算モジュールの骨子を追加（Momentum / Value / Volatility / Liquidity の方針、DuckDB 接続利用の設計）。モメンタム計算関数の実装開始（calc_momentum）。

Changed
- ルートパッケージのバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
- ロガーの標準出力先を stderr から stdout に変更（cron/Task Scheduler でリダイレクトしやすくするため）: utils/logging_setup.py。

Fixed
- MONITOR_POLL_INTERVAL の不正値に対する保護
  - run_monitoring.py の _get_poll_interval() で 0 以下や非整数が指定された場合に警告を出しデフォルト値（60 秒）にフォールバックするように改善。
- .env パーサーの堅牢化
  - config._parse_env_line() が export プレフィックス、クォート、エスケープ、インラインコメントに対処するよう改善。

Security
- シークレット値の取り扱いを配慮
  - config_setup の対話表示でシークレットはマスク表示（****）し、.env のテンプレートにもプレーンテキストで書き出すが README 等で .env を Git に含めない注意書きを出力。

Notes / 注意事項
- 監視 (monitoring) は「環境にかかわらず」settings.sqlite_path（デフォルト: data/monitoring.db）を使用する設計になっています。本番運用でモニタリング DB を切替えたい場合は運用フローを要確認。
- Paper Trading と Live は DB を分離する設計です（Paper Trading: settings.paper_sqlite_path、Live/Dev: settings.sqlite_path）。
- 一部モジュール（research/factor_research.py）は実装途中の箇所があり、追加の実装・テストが必要です。
- 本リリースではユニットテスト・CI 設定に関する記載はコードからは確認できません。継続的な品質確保のためテストの整備を推奨します。

参考 (環境変数 / デフォルト)
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒, デフォルト 60）
- KABUSYS_ENV: execution/monitoring の実行環境（development / paper_trading / live, default=development）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（監視用デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用デフォルト）
- LOG_LEVEL / LOG_DIR / PID_FILE_PATH / KILL_FLAG_* など多数の環境変数を Settings でラップして提供

If you want, 次のリリース向けに以下を CHANGELOG に追記できます:
- research モジュールの完了（全ファクター計算の実装）
- ExecutionEngine / BrokerClient の詳細実装に関する改善・エラーハンドリング強化
- 単体テスト・統合テストの追加および CI 設定記載