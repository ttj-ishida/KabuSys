# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

## [0.1.0] - 2026-04-19

### Added
- 起動スクリプト
  - run_monitoring.py を追加。SystemMonitor のポーリングループを起動するエントリポイント。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止はプロジェクト `data/stop_requested.flag` ファイルの存在で検出。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して DB を初期化。
  - run_execution.py を追加。ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用し、MockBrokerClient を利用（本番 DB と分離）。
    - 起動時にプロセス優先度を "high" に設定。停止フラグで Engine を安全に停止。
    - 実行時の PID ファイルを data/execution.pid に記録（設定経由で変更可）。

- 設定管理とウィザード / 検証
  - config.py を追加。
    - .env 自動ロード（プロジェクトルートを .git または pyproject.toml で探索）。
    - エスケープやクォート、コメントを考慮した .env パース実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - Settings クラスに各種設定プロパティを実装（J-Quants・kabu API・DB パス・監視閾値など）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
  - config_setup.py を追加。
    - 対話式ウィザードで .env の初期作成・更新を支援。デフォルト値、シークレット表示、保存機能を提供。
  - validate_config.py を追加。
    - .env と config/*.yaml の基本検証を行う CLI。--strict で警告もエラー扱いにできる。
    - PyYAML の有無に応じた挙動、KABUSYS_ENV=live に関する追加警告を実装。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py を追加。
    - ルートロガーを統一的に設定するユーティリティ（console stdout + 日次ローテーションファイル出力）。
    - ログディレクトリ自動作成、既存ハンドラの二重登録防止、LOG_LEVEL/LOG_DIR による設定。
  - utils/process_priority.py を追加。
    - Windows / POSIX の差を吸収したプロセス優先度設定（high/normal/low）と CPU affinity 設定関数を提供。
    - 権限不足や未対応 OS の場合は警告を出して安全にフォールバック。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py を追加。
    - 候補選定 (select_candidates)、等重配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
  - portfolio/risk_adjustment.py を追加。
    - セクター集中制限 (apply_sector_cap)、市場レジーム乗数 (calc_regime_multiplier) を実装。
  - portfolio/position_sizing.py を追加。
    - 各種配分方式（risk_based / equal / score）に基づく発注株数計算。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cashを超えた場合のスケーリング）、
      cost_buffer を考慮した保守的見積り、残余配分ロジック等を実装。
  - portfolio/__init__.py でエクスポートを提供。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py を追加。
    - ペーパートレード用 SQLite DB から稼働率、注文成功率、送信率、レイテンシ等を集計して検証レポートを生成。
    - P95 レイテンシ計算、期間フィルタ（--from/--to）、閾値による PASS/FAIL 判定を実装。
    - PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションで DB パス指定可能。

- 研究用（ファクター計算）
  - research/factor_research.py を追加（モメンタム等のファクター計算の骨組み、DuckDB を使用）。

### Changed
- ログ出力の標準化
  - logging_setup でコンソールログは stdout を使用するように統一（cron/Task Scheduler でのリダイレクト運用を想定）。

- DB 初期化の扱い
  - run_monitoring は環境にかかわらず監視用テーブルの初期化に production sqlite_path（Settings.sqlite_path）を使用する旨を明確化（監視データは本番 DB 側で管理する設計）。

### Fixed
- .env パーサの強化
  - export プレフィックス対応、シングル・ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱いなどを正しく処理するよう改善。

### Notes / Behavior & Safety
- Paper Trading と本番 DB の分離
  - run_execution では settings.is_paper に応じて paper_sqlite_path を使用することで、paper_trading のデータを本番 DB と完全に分離する設計になっています。一方で run_monitoring はあえて本番 sqlite_path を使用します（監視は本番 DB を対象にするため）。

- 停止制御
  - run_monitoring/run_execution はプロジェクト配下の data/stop_requested.flag によって外部から安全に停止可能です。設定によっては起動時に kill flag の自動クリア等の動作があるため、本番環境では KILL_FLAG_CLEAR_ON_START の取り扱いに注意が必要です。

- 設定の自動読み込み
  - デフォルトでプロジェクトルートの .env, .env.local を自動で読み込みます（OS 環境変数は上書きされません）。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください（テスト環境等で便利）。

### Removed
- 特になし（初期リリース）

---

今後の予定（アイデア）
- strategy / execution 内の個別コンポーネント（Engine の詳細、Broker 実装等）の追加・ドキュメント化
- metrics の可視化・CSV/HTML 出力、より詳細なファクター計算の完成
- 単体テストの追加と CI の導入

（以上）