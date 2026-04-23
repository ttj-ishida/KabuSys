# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはリポジトリ内のコードから推測して作成した暫定的な変更履歴です。実際のリリースノート作成時は必要に応じて加筆・修正してください。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-23

### Added
- 初期リリース: KabuSys のコア機能群を追加。
- 実行エントリポイント
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の MockBrokerClient を使用し、paper_trading 用の SQLite DB（デフォルト: `data/paper_trading.db`）に記録することで本番 DB と完全に分離。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を利用）。
    - 停止制御: プロジェクトの `data/stop_requested.flag` を監視し、検知時にエンジン停止処理を実行。
    - 実行中の PID を `data/execution.pid` に書き込む仕組み（Engine 側の pid_file パラメータ）。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔の上書き（デフォルト 60 秒）。不正値はデフォルトへフォールバックして警告を出力。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視 DB を初期化（monitoring DB の初期化処理を呼び出す）。
    - 停止フラグ `data/stop_requested.flag` を検出して安全にループを終了。
- 設定・環境管理
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env/.env.local の読み込み順、OS 環境変数の保護（上書き禁止）に対応。
    - 複数の設定プロパティを備えた Settings クラスを実装（J-Quants トークン、kabu API、DB パス、PID ファイルパス、閾値、環境判定など）。
    - PAPER_FILL_MODE のバリデーション（許容値: "instant" / "partial" / "never" / "reject"）。
- 設定補助ツール
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。
    - デフォルト値の提示、シークレット項目のマスク、保存確認、.env ファイルテンプレート出力をサポート。
  - validate_config.py
    - 起動前に .env と config/*.yaml の妥当性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL チェック、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML が利用可能な場合）の検証、KABUSYS_ENV=live 時の追加ガードなど。
    - --strict オプションで警告を FAIL（exit(1)）として扱う機能を追加。
- ログ・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - すべての起動スクリプトから共通で使えるログ設定ユーティリティを実装。
    - StreamHandler を stdout に出力（cron 等で stdout/stderr をまとめてリダイレクトする運用を想定）。
    - 日次ローテーション（TimedRotatingFileHandler）でログを `logs/<app_name>.log` に保存、30 日分保持。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみ出力するフォールバックを実装。
  - utils/process_priority.py
    - Windows/Linux/macOS をまたいでプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）を設定するユーティリティを実装。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。権限不足や未サポート環境では警告を出してスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（sell_codes を除外して既存ポジションからセクター露出を算出）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier 実装（"bull"=1.0, "neutral"=0.7, "bear"=0.3、未知は 1.0 で警告フォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数決定ロジック calc_position_sizes を実装。
    - risk_based / equal / score 方式をサポート。単元株（lot_size）で丸め、ポートフォリオ全体の aggregate cap による縮小アルゴリズム（余りの分配ロジック含む）を実装。
  - portfolio/__init__.py で上記機能をエクスポート。
- リサーチ・ファクター計算
  - research/factor_research.py
    - Momentum（1M/3M/6M）や MA200 乖離などの計算方針と定数を実装。DuckDB 接続を受けて prices_daily / raw_financials テーブルから計算する設計。
    - （コード内に計算関数を実装中の痕跡あり）
- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。
    - デフォルト DB: 環境変数 `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`。
    - 指標: システム稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、レイテンシ（avg/max/P95）。P95 は独自計算実装。
    - デフォルトの合格基準（しきい値）を設定:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - CLI オプションで期間指定（--from / --to）と DB パス指定（--db）をサポート。

### Changed
- なし（初回リリースのため）

### Fixed
- ロギング初期化処理でログディレクトリ作成に失敗した場合、エラーではなく警告を出してファイルハンドラをスキップする堅牢化を実装（setup_logging）。
- 環境変数読み込みのパーサで引用符・エスケープ・インラインコメント・`export KEY=...` 形式に対応し、不正な行を無視する堅牢化を実装（config._parse_env_line, _load_env_file）。

### Security
- .env ファイルは Git にコミットしない旨を config_setup のテンプレートに明記（運用上の注意）。

### Notes / Usage
- 自動環境ロード:
  - デフォルトでプロジェクトルートの .env と .env.local を自動読み込みします。テストや特殊環境で無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Paper Trading:
  - paper_trading 実行時は本番 DB と分離された `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）を使用します。
  - PAPER_FILL_MODE により MockBrokerClient の約定挙動（instant/partial/never/reject）を切り替え可能。
- 停止制御:
  - プロセスはプロジェクト内 `data/stop_requested.flag` の存在を監視し、検知時に安全に停止します（run_execution/run_monitoring 共通）。
- ログ:
  - デフォルトでは logs/<app_name>.log に日次ローテーションで出力されます。ログ出力先を変更するには LOG_DIR または setup_logging の引数を利用してください。
- 実装状況:
  - research/factor_research.py はモメンタム算出等の実装が始まっていますが、ファイル末尾で途中になっている箇所が見られます（さらなる実装やテストが必要）。

---

今後のリリースで予定する改善（想定）
- factor_research の完全実装および単体テスト追加
- ExecutionEngine / SystemMonitor のエンドツーエンドテストとドキュメント充実
- ブローカークライアント（Mock 本番双方）の振る舞いとエラー処理強化
- ログやメトリクスの可観測性向上（Prometheus / Grafana などの統合検討）