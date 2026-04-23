CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

[Unreleased]
------------

（ありません）

[0.1.0] - 2026-04-23
-------------------

初回公開リリース。

追加
- 基本アプリケーションと CLI
  - パッケージ初期版を追加（バージョン: 0.1.0）。
  - メイン起動スクリプト:
    - run_execution.py: 実行エンジン（ExecutionEngine）起動スクリプトを追加。KABUSYS_ENV=paper_trading の際は MockBrokerClient を使用し、paper_trading 用に分離された SQLite（data/paper_trading.db を既定）を利用する。
    - run_monitoring.py: SystemMonitor 起動スクリプトを追加。監視は常に本番用 sqlite_path を使用。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）によりループ停止。
  - ユーティリティ / ツール:
    - config_setup.py: 対話式 .env 作成・更新ウィザードを追加（.env のテンプレートと書き込み機能を含む）。
    - validate_config.py: 起動前設定検証 CLI を追加（必須環境変数・KABUSYS_ENV 検証・YAML ファイル存在/パースチェック・本番ガード等）。
    - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95）などを集計して PASS/FAIL 判定を出力。
- 設定管理
  - config.py: Settings クラスを導入し、環境変数と .env ファイルの自動読み込み機能を実装（プロジェクトルート探索: .git または pyproject.toml を基準）。.env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。多くの設定プロパティ（DB パス、PID/kill フラグ、閾値、paper_trading の設定等）を提供。
  - .env パーサ: export 形式やクォート/エスケープ、インラインコメントを考慮した堅牢な行パース実装を追加。
  - PAPER_FILL_MODE（"instant" / "partial" / "never" / "reject"）などペーパートレード設定をサポート。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順で上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分の実装（スコア合計が 0 の際は等配分にフォールバックし警告）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中リスク制約に基づく候補除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数。
  - portfolio/position_sizing.py:
    - calc_position_sizes: リスクベース/等配分/スコア配分に基づく発注株数計算、単元株丸め、aggregate cap によるスケールダウン処理、コストバッファの考慮などを実装。
- ロギング・プロセス管理
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）をルートロガーへ設定。LOG_DIR/LOG_LEVEL の解決順／フォールバックを実装。ログディレクトリ作成失敗時はファイル出力をスキップ。
  - utils/process_priority.py: プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを追加。Windows と POSIX（Linux/Mac/FreeBSD）差分を吸収し、権限不足や未対応環境では警告を出して安全にスキップ。
- 監視 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を run スクリプトから利用し、監視テーブルの存在を保証（冪等）。
- 研究用モジュール（リサーチ）
  - research/factor_research.py: モメンタム・ボラティリティ等のファクター計算機能群の骨子を追加。DuckDB 接続を受け、prices_daily / raw_financials テーブルを参照してファクターを算出する設計。モメンタム計算（calc_momentum）の実装開始（関数の冒頭が存在）。

変更
- プロセス起動時の挙動
  - run_execution / run_monitoring のいずれも起動直後にプロセス優先度を "high" に設定する呼び出しを追加。
  - run_execution は paper_trading の場合、専用 sqlite_path（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）を使うように明示。
- .env 読み込み順序・保護
  - 自動ロード時の読み込み優先順位は OS 環境変数 > .env.local > .env。既存 OS 環境変数の上書きを防ぐため protected set を利用。
- ログ関連
  - StreamHandler は stdout を使用（stderr ではなく）。ファイルハンドラは日次ローテーション・30 日保持に設定。

修正
- 入力検証とフォールバック
  - MONITOR_POLL_INTERVAL が不正（整数変換不可や 0 以下）の場合は警告を出してデフォルト 60 秒にフォールバック。
  - PAPER_FILL_MODE が不正な文字列の場合は ValueError を送出して早期検知。
  - Settings.env / log_level の不正値検出を明確化（ValueError）。
- レポート生成の堅牢化
  - paper_verification_report.py: DB のテーブルが存在しない場合に sqlite3.OperationalError を捕捉してデフォルト値にフォールバックするように変更。P95 計算や各指標の N/A 表示を明確化。

既知の制限 / 注意事項
- research/factor_research.calc_momentum はファイル末尾が途中で切れている（スナップショットの都合）。完全な実装が必要。
- 一部の機能は外部依存（psutil、duckdb、PyYAML など）を必要とする。validate_config は PyYAML 未インストール時に YAML 検証をスキップして警告する。
- run_monitoring は「監視は常に本番 sqlite_path を使用する」という設計上、開発環境での分離を行っていない点に注意。
- ログディレクトリ作成に失敗した場合はファイル出力が無効化され、コンソール出力のみで継続する実装です。

セキュリティ
- .env ファイルを生成する際に、生成されたファイルは絶対に Git へコミットしない旨を README/生成メッセージで明示。

問い合わせ・貢献
- バグ・改善提案は Issue を立ててください。プルリク歓迎です。