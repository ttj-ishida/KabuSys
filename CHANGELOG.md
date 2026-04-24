CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

Unreleased
----------

- 進行中 / 注意事項
  - research/factor_research.py の末尾が未完（実装途中の断片あり）。ファクター計算モジュールは概ね設計済みだが一部実装が完了していないため、当該機能は次リリースまで「実験的」扱いとしてください。
  - 一部の TODO コメント（価格フォールバック、銘柄別単元対応など）が残っています。運用前に該当箇所の評価を推奨します。

[0.1.0] - 2026-04-24
--------------------

Added
- 初回リリース (v0.1.0)
  - 全体概要
    - 日本株自動売買システム "KabuSys" の基本モジュール群を追加。
    - バージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として明示。
  - 環境/設定管理
    - .env 自動ロード機能を追加（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env の解析器を実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープに対応）。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD フラグをサポート。
    - Settings クラスを実装し、環境変数から各種設定を取得・検証（J-Quants / kabuAPI / データベースパス / PAPER_FILL_MODE の妥当性チェック等）。
    - 環境値検証用の CLI を追加: python -m kabusys.validate_config
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、config/*.yaml の存在・パース検証（PyYAML が存在しない場合はスキップ）、本番環境向けの追加警告を提供。
      - --strict オプションで警告を FAIL 扱いにできる。
    - 対話式 .env 作成ウィザードを追加: python -m kabusys.config_setup
      - 対話的に .env を生成・更新するユーティリティ。既存値の再利用、シークレット項目のマスク表示、保存確認をサポート。
  - 実行/監視スクリプト
    - 実行エンジン起動スクリプト: src/kabusys/run_execution.py
      - ExecutionEngine の起動フローを整備。プロセス優先度設定、SQLite/DuckDB 接続、Broker クライアント生成、OrderManager / RiskManager / Reconciler の組み立て、スレッド起動・停止フラグ監視を実装。
      - KABUSYS_ENV=paper_trading 時は専用の PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離。
      - 起動時に停止フラグ（data/stop_requested.flag）を検出すると起動をスキップする。
    - 監視ループ起動スクリプト: src/kabusys/run_monitoring.py
      - SystemMonitor の初期化とポーリングループを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関係なく本番 sqlite_path を使用する挙動を明示。
      - 停止フラグの検出で安全にループ終了、例外時にもログ出力して次ポーリングまで継続する設計。
  - Execution / Broker / Risk / Order 周り（基盤）
    - Execution コンポーネントの依存性注入に対応（BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager）。
    - RiskConfig / EngineConfig により実行パラメータをコード上で明示（例: max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - Paper Trading 用検証ツール
    - tools/paper_verification_report.py を追加。paper_trading 用 SQLite（環境変数 PAPER_TRADING_SQLITE_PATH または --db）から統計を抽出し、稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを計算して PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ、N/A 表示の整備。
  - ポートフォリオ構築ライブラリ
    - portfolio モジュールを追加:
      - portfolio_builder.py: 候補選定 (select_candidates), 等重み / スコア重み計算 (calc_equal_weights, calc_score_weights)。
      - risk_adjustment.py: セクター上限適用 (apply_sector_cap)、レジーム乗数計算 (calc_regime_multiplier)。
      - position_sizing.py: 発注株数計算 (calc_position_sizes) — risk_based / equal / score の各方式をサポート。単元株（lot_size）、コストバッファ、aggregate cap のスケーリングと端数処理を実装。
    - portfolio/__init__.py で上記関数をエクスポート。
  - ユーティリティ
    - logging_setup.py: 統一ログ設定ユーティリティを追加
      - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。既存ハンドラをクリアして再設定する。
      - ログレベル / ログディレクトリの解決順を実装（引数 > 環境変数 > デフォルト）。
      - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加
      - Windows/Linux(macOS/FreeBSD) を吸収する実装。set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を提供。アクセス権限不足や未サポート環境では警告を出してスキップ。
  - DB / ストレージ
    - SQLite（監視・paper_trading 用）と DuckDB（分析用）を併用する設計を採用。デフォルトパスは Settings で定義（data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb）。
  - ログ・オペレーション
    - デフォルトでアプリ名単位のログファイル（logs/<app_name>.log）を出力。stdout にも同時出力し、cron 等によるログリダイレクトに対応。

Changed
- N/A（初回リリースのため履歴比較対象なし）

Fixed
- N/A（初回リリース）

Deprecated
- N/A

Removed
- N/A

Security
- N/A

Notes / マイグレーション
- 環境変数の重要点
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須。未設定時は validate_config でエラー。
  - KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかであること（Settings で検証）。
  - PAPER_FILL_MODE は "instant" | "partial" | "never" | "reject" のいずれかである必要あり（デフォルト "instant"）。
  - SQL/DB パスはデフォルトで data/ 配下を使用。paper_trading は is_paper 判定で専用 DB に切り替わるため、本番 DB と分離される点に注意。
  - MONITOR_POLL_INTERVAL で監視ポーリング間隔を上書き可能（整数秒、1 秒未満や不正値は既定値 60 秒にフォールバックする）。
  - KILL_FLAG_CLEAR_ON_START が本番で "1" の場合は危険（validate_config が警告を出す）。
- 運用上の注意
  - run_monitoring は「監視」は本番 sqlite_path を参照する用途で設計されているため、paper_trading 環境でも監視 DB が本番のパスに向く点に注意してください（意図的な挙動としてドキュメント化済み）。
  - ログディレクトリ作成やプロセス優先度設定は権限に依存するため、権限不足時は警告を出してスキップします。運用環境では適切な権限設定を推奨します。
- 既知の制限
  - factor_research.py が未完。ファクター計算は設計済みだが、一部実装（関数末尾の続き）が不足。
  - position_sizing の lot_size は現状グローバル固定（将来的に銘柄別単位対応を予定）。

貢献・報告
- バグ報告・改善提案は Issue を作成してください。重要な TODO はコード内コメントとして残しています。