# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-20

初回リリース。以下の主要機能、CLI、ユーティリティ、ライブラリを追加しました。

### Added
- 実行エントリ／デーモン
  - run_execution.py — ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）に記録して本番 DB と完全分離。
    - 起動時にプロセス優先度を "high" に設定。
    - BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler を組み合わせて ExecutionEngine を生成・実行。デーモン化されたスレッドでセッションを実行し、プロセス停止フラグ (data/stop_requested.flag) により安全停止可能。
    - ExecutionEngine に渡されるデフォルト RiskConfig 値を設定（例: max_position_pct=0.20、max_utilization=0.80、rate_limit_per_sec=5、circuit_breaker_errors=10、circuit_breaker_window_sec=60、max_drawdown=0.20）。initial_portfolio_value はブローカの利用可能現金を初期値として取得。

  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60秒）。不正な値（0以下や非数）はデフォルトにフォールバックして警告を出力。
    - 監視は KABUSYS_ENV にかかわらず本番の sqlite_path を使用して監視テーブルを初期化（init_monitoring_db）。
    - duckdb を併用した接続管理。
    - 停止フラグ (data/stop_requested.flag) 検知でループ終了。

- 設定管理
  - config.py — Settings クラスを導入。
    - .env/.env.local の自動ロード機能（ルート検出は .git または pyproject.toml を基準）。OS 環境変数を保護して上書きを制御可能（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込み無効化）。
    - .env パーサは `export KEY=val` 形式、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント処理に対応。
    - 各種プロパティを用意（J-Quants トークン、kabu API 設定、DuckDB/SQLite パス、Paper Trading 関連、ログ・キルフラグ・監視閾値など）。
    - PAPER_FILL_MODE の検証（有効値: "instant" | "partial" | "never" | "reject"）を実装。

  - config_setup.py — 対話式 .env 作成ウィザードを追加。
    - 標準項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LINE トークン等）を対話形式で生成・更新。
    - シークレットのマスク表示、選択肢・デフォルト値サポート、.env ファイル書き出し機能を提供。

  - validate_config.py — 設定検証 CLI を追加。
    - 必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証を実施。
    - 本番（live）用の追加ガード（LINE 通知設定の未設定警告、KILL_FLAG_CLEAR_ON_START 設定警告）。
    - --strict オプションで警告も失敗扱いにできる。

- ツール
  - tools/paper_verification_report.py — Paper Trading の検証レポート生成ツールを追加。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（平均・最大・P95）などを SQLite (data/paper_trading.db デフォルト) から集計してレポート出力。
    - CLI オプション --from / --to / --db により期間・DB 指定可能。
    - P95 計算実装と閾値（稼働率 99.0%、fill_rate 90%、send_rate 95%、P95 レイテンシ 200ms）による PASS/FAIL 判定。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - kabusys.portfolio.portfolio_builder:
    - select_candidates: スコア降順＋signal_rank タイブレークで候補抽出。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重。スコアが全て 0 の場合は等金額にフォールバックして警告。

  - kabusys.portfolio.risk_adjustment:
    - apply_sector_cap: 既存保有のセクター比率に基づいて新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた資金乗数を提供（未知のレジームは警告して 1.0 をフォールバック）。

  - kabusys.portfolio.position_sizing:
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に応じて発注株数を計算。単元株（lot_size）丸め、per-stock 上限・aggregate cap、cost_buffer を利用した保守的見積り、スケールダウンと残差分配ロジックを実装。

  - 包装モジュール kabusys.portfolio を公開。

- ユーティリティ
  - utils/logging_setup.py:
    - 共通のログ設定ユーティリティを導入。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler、30日分保持）をルートロガーに設定。
    - 既存ハンドラのクリーンアップ、LOG_LEVEL / LOG_DIR による解決、ログディレクトリ作成失敗時のフォールバックを実装。

  - utils/process_priority.py:
    - プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを追加。Windows/Linux/macOS の差分吸収（psutil ベース）、権限不足や未対応 OS では警告を出して安全にスキップ。

- 研究モジュール（骨子）
  - research/factor_research.py を追加（モメンタム等のファクター計算を提供する設計、DuckDB 接続を利用）。モメンタム関連定数と calc_momentum の実装開始（ファイル終端で未完の箇所あり）。

- パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" に設定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （現時点で特記事項なし）

### Notes / Known issues
- research/factor_research.py は実装途中の箇所（ファイル末尾に未完の記述）が存在します。必要に応じて補完・テストを行ってください。
- 一部の機能は psutil や PyYAML といった外部ライブラリに依存します。これらが未インストールの場合は警告を出して機能の一部検証や処理（YAML パース、プロセス優先度設定等）をスキップします。
- .env は機密情報を含むため、README 等で .gitignore に追加してコミットしない旨を周知してください（config_setup.py の出力ヘッダでも警告）。

---

今後の予定（提案）
- research モジュールの完実装とユニットテスト追加
- Execution/Monitoring 周りの統合テスト（Paper/Live 切替を含む）
- 各純粋関数群のユニットテスト拡充（edge case と境界値）