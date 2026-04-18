CHANGELOG
=========

すべての注目すべき変更を記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

現在のバージョン: 0.1.0

[Unreleased]
------------

（なし）

[0.1.0] - 2026-04-18
-------------------

Added
- 初回リリース: KabuSys コードベースの基本機能を追加。
  - 実行/監視エントリポイント
    - run_execution.py
      - ExecutionEngine 起動スクリプトを追加。プロセス優先度を "high" に設定し、PID ファイル管理、停止フラグ（data/stop_requested.flag）による安全停止をサポート。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用し、本番 DB と完全分離。BrokerClientFactory により MockBrokerClient を選択可能。
      - ExecutionEngine の依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler）を組み立ててスレッドで実行。RiskManager にデフォルト構成を設定（max_position_pct 等）。
    - run_monitoring.py
      - SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は常に本番 sqlite_path を使用する設計（環境に依存しない監視 DB）。
      - stop フラグファイル検出で安全にループを終了、例外はログに出力して次回ポーリングに継続。
  - 設定管理
    - config.py
      - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。.env と .env.local の優先順位を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
      - .env パーサは export プレフィックス、クォート文字列（エスケープ対応）、インラインコメントの挙動などに対応。
      - Settings クラスにより環境変数アクセスをラップ（duckdb/sqlite/paper_trading path、paper fill mode のバリデーション、閾値設定、env/log level 判定等）。
    - config_setup.py
      - 対話式ウィザードで .env を生成/更新する CLI を追加。秘密項目はマスク表示、選択肢/デフォルト/確認プロンプトを提供。
    - validate_config.py
      - 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV の妥当性、DB パス親ディレクトリ存在確認、config/*.yaml の存在と（可能なら）パース検証を実行。--strict モードで警告を FAIL 扱いにできる。
  - ログ・プロセス管理ユーティリティ
    - utils/logging_setup.py
      - 全起動スクリプトで共通使用できるログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。LOG_LEVEL/LOG_DIR の解決順を実装し、ディレクトリ作成失敗時にファイル出力をフォールバックする。
    - utils/process_priority.py
      - Windows と POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。psutil ベースで実装し、権限不足や未対応 OS は警告を出してスキップ。CPU affinity 設定用の set_cpu_affinity も提供。
  - ポートフォリオ構築ライブラリ（純粋関数群）
    - portfolio/portfolio_builder.py
      - 候補選定(select_candidates)、等金額配分(calc_equal_weights)、スコア加重配分(calc_score_weights) を実装。スコア全0 の場合は等配分にフォールバックして警告を出す。
    - portfolio/risk_adjustment.py
      - セクター集中上限適用(apply_sector_cap) を実装。既存保有のセクター別エクスポージャーに基づいて新規候補を除外（"unknown" セクターは除外対象外）。当日売却予定銘柄をエクスポージャー計算から除外可能。
      - レジーム乗数(calc_regime_multiplier) を実装（"bull":1.0, "neutral":0.7, "bear":0.3、未知レジームは警告して 1.0 フォールバック）。
    - portfolio/position_sizing.py
      - ポジションサイズ計算(calc_position_sizes) を実装。allocation_method として "risk_based" / "equal" / "score" をサポート。単元株（lot_size）丸め、per-stock 上限・aggregate cap（available_cash）スケーリング、cost_buffer を考慮した保守的見積を実装。スケールダウン時の端数配分ロジックも実装。
    - portfolio/__init__.py
      - 上記関数群を公開。
  - 研究/ファクター計算（基礎実装）
    - research/factor_research.py
      - モメンタム、ボラティリティ等を計算するための設計と基礎実装を追加（DuckDB 接続を受け prices_daily / raw_financials を参照する想定）。（注: ファイル冒頭に計算方針・定数を定義、モメンタム計算関数の骨格が存在）
  - ツール
    - tools/paper_verification_report.py
      - Paper Trading の検証レポート出力スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL 判定を行う。閾値はソース内定数で定義（稼働率 99%、成立率 90% 等）。--from/--to/--db オプション対応。DB 存在チェック/例外耐性あり。
  - パッケージメタ情報
    - __init__.py にて __version__ = "0.1.0" を設定。

Changed
- 初回リリースにつき変更履歴はなし。

Fixed
- 初回リリースにつき修正履歴はなし。

Removed
- 初回リリースにつき削除履歴はなし。

Notes / 開発者向けメモ
- .env 自動読み込みはプロジェクトルート検出に依存するため、パッケージ配布後も CWD に依存せず動作するよう設計されています。自動読み込みを抑止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_execution/run_monitoring は stop flag（data/stop_requested.flag）を用いて外部から安全に停止可能です。実運用では PID ファイルや kill flag 設定 (Settings.kill_flag_path, KILL_FLAG_CLEAR_ON_START) の運用を検討してください。
- Paper Trading 周りは本番 DB と明確に分離する設計です（PAPER_TRADING_SQLITE_PATH / paper_sqlite_path）。検証用ツール群は paper_trading DB に依存します。
- logging_setup は起動環境によりファイル出力が失敗する場合でもコンソール出力を確保するフェイルセーフを持ちます。

今後の予定（例）
- research/factor_research の各ファクター計算の完全実装・テスト追加。
- ExecutionEngine / RiskManager の単体テスト・統合テスト整備。
- 銘柄別 lot_size のサポート（stocks マスタ参照）や手数料モデルの拡張。
- config/*.yaml の雛形自動生成・ドキュメント強化。