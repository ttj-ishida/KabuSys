# CHANGELOG

すべての注目すべき変更をこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠しています。

今後のリリースでは、重要な変更・後方互換性の破壊・バグ修正などをここに追記してください。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-22

### Added
- 基本機能の初期実装を追加（パッケージ version=0.1.0）。
  - パッケージエントリポイント: kabusys パッケージを導入。
- 実行用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV により paper_trading モードで専用の MockBroker / DB を使用（data/paper_trading.db、環境変数で上書き可能）。
    - プロセス優先度を起動時に High に設定。
    - 停止フラグ（data/stop_requested.flag）および実行 PID ファイル（data/execution.pid）に対応。停止フラグ検知時に実行エンジンを安全に停止。
    - ExecutionEngine 起動前に監視用テーブルが存在することを保証（init_monitoring_db を呼び出し冪等に初期化）。
    - デフォルトの RiskManager 初期設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker など）を追加。初期ポートフォリオ値を broker.get_available_cash() から取得。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト: 60秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視プロセスは KABUSYS_ENV に関わらず本番の sqlite_path を使用して監視データを記録。
    - 停止フラグ検知でループを終了。KeyboardInterrupt にも対応し適切に DB 接続をクローズ。
- 設定管理
  - config.py: Settings クラスを追加。
    - .env の自動読み込み機能（プロジェクトルートの .env / .env.local、OS 環境変数優先）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - 多数の設定プロパティを提供（J-Quants / kabu API / DB パス / Paper trading 関連 / 監視閾値 / システム設定 等）。
    - 値検証を組み込み（KABUSYS_ENV の検証、LOG_LEVEL の検証、PAPER_FILL_MODE の有効値チェックなど）。
- 設定ユーティリティ・CLI
  - config_setup.py: 対話式ウィザードで .env を生成・更新するツールを追加。
    - 秘匿項目はマスク表示、選択肢・デフォルトのサポート、生成されるテンプレートの文言（.env を絶対にコミットしない旨）を含む。
  - validate_config.py: 起動前設定検証ツールを追加。
    - 必須/任意環境変数のチェック、KABUSYS_ENV の妥当性チェック、LOG_LEVEL のチェック、DB パスの存在チェック（親ディレクトリ）を実行。
    - config/*.yaml の存在確認と PyYAML が利用可能ならパース検証を行う。
    - --strict オプションを用意（警告も FAIL 扱い）。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順、同点時に signal_rank を用いたタイブレークで候補選定。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア加重配分を計算。全スコアが 0 の場合は等金額配分へフォールバック（警告出力）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター別エクスポージャーを算出し、指定上限を超えるセクターの新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を返す。未知のレジームは 1.0 にフォールバック（警告）。
  - portfolio.position_sizing
    - calc_position_sizes: 各銘柄の発注株数算出ロジック実装（allocation_method: risk_based / equal / score）。
      - risk_based: 損切り率・リスク許容率に基づく株数計算。
      - equal/score: ウェイトに基づき per-position / aggregate の上限を考慮して単元（lot_size）に丸め。
      - aggregate cap 超過時はスケールダウンし、残余キャッシュを fractional 残差順に lot 単位で再配分するロジックを導入。
      - price が欠損または 0 の場合にスキップする安全策を実装。
      - cost_buffer によりスリッページ/手数料を保守的に見積もる。
- 監視・検証ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs から各種指標を集計（稼働率、注文成功率、送信率、リスク却下数、平均/最大/P95 レイテンシ等）。
    - P95 計算ロジックを実装。
    - デフォルト閾値を定義して PASS/FAIL 判定を行う（稼働率 >= 99%、成功率/送信率/レイテンシ基準など）。
    - CLI オプションで日付範囲・DB パスを指定可能。PAPER_TRADING_SQLITE_PATH 環境変数を尊重。
- ログ / プロセスユーティリティ
  - utils.logging_setup
    - 統一ログ設定ユーティリティを追加。
    - StreamHandler は stdout を使用（cron/Task Scheduler での出力一本化に配慮）。
    - TimedRotatingFileHandler による日次ローテーション（30日保持）のファイル出力をサポート。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラを安全に flush/close の上でクリアし重複設定を防止。
  - utils.process_priority
    - set_process_priority: Windows / POSIX を吸収したプロセス優先度設定を追加（psutil 利用、例外を捕捉して安全にフォールバック）。
    - set_cpu_affinity: 最初の N コアにプロセスをピン留めするユーティリティを追加（環境による制限・例外処理あり）。
- utils パッケージ初期化ファイル等の追加。
- research.factor_research（部分実装）
  - ファクター計算モジュールの骨格を追加。モメンタム（1/3/6ヶ月、MA200乖離）、ATR、流動性系の計算方針を定義。DuckDB 接続を受け価格・財務データテーブルから計算する設計。モジュールは途中で実装中（calc_momentum の実装がファイル末尾で途切れています）。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / Implementation details
- .env パーサーは export プレフィックス対応、クォートされた値のバックスラッシュエスケープ処理、インラインコメント処理（クォート無しで '#' の前が空白の場合のみコメントとみなす）などをサポートし、実運用での柔軟な .env 設定を想定。
- 設定自動ロードはプロジェクトルートを .git または pyproject.toml を起点に探索するため、CWD に依存しない。
- 監視/実行スクリプトは DB 接続（sqlite3, duckdb）を確実にクローズするよう finally ブロックを設けている。
- 一部機能（例: research.calc_momentum の続き、ExecutionEngine 等の内部実装）は別モジュールで定義されており、本 CHANGELOG はリポジトリに含まれるファイルの現状から推測して記載しています。

---

今後のリリースでは、各コンポーネント（ExecutionEngine、BrokerClient、SystemMonitor、Reconciler、OrderManager 等）の詳細実装・テスト・ドキュメントを充実させ、API 仕様や設定の互換性に関する変更を明確に記載します。