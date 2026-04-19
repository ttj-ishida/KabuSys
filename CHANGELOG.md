# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティック・バージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-04-19
初回公開リリース。

### Added
- 実行エントリ・監視エントリ
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の SQLite（data/paper_trading.db など）を使用し、本番 DB と分離して動作。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager/ RiskManager/ Reconciler の組み立て、ExecutionEngine のデーモンスレッド実行と停止フラグ処理を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は実行環境にかかわらず本番の sqlite_path を使用して監視データを記録。
    - 停止フラグファイルを検知して安全にループ終了。
- 設定・環境周り
  - config.py: Settings クラスを追加。
    - .env 自動ロード（.env, .env.local）機能（プロジェクトルート検出: .git または pyproject.toml）。
    - キー毎のプロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、各種閾値、PID/kill flag パスなど）を提供。
    - 環境変数の検証（有効値チェック）や paper_fill_mode の厳密な検証を実装。
    - settings インスタンスをモジュールレベルでエクスポート。
  - config_setup.py: .env 対話式ウィザードを追加。
    - 初期 .env 作成・既存 .env の更新、シークレット入力マスク、保存前確認などの対話フローを提供。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須/任意環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境向けの追加ガードを実装。
    - --strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: シグナルをスコア降順にソートして上位 N を返す。
    - calc_equal_weights: 等金額配分重み計算。
    - calc_score_weights: スコアに基づく重み計算。全スコアが 0 の場合は等金額にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック（既存ポジションをセクター別に集計し、新規候補を除外）。
      - "unknown" セクターは上限の適用対象外。
      - 当日売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を返す（未知のレジームはフォールバック 1.0 として警告）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく株数計算を実装。
      - lot_size（単元）で丸め、1銘柄上限や aggregate cap（available_cash）超過時のスケールダウン、cost_buffer を加味した保守的見積り、残差の公平配分ロジックを実装。
      - 価格欠損（price <= 0）時はスキップ。
- ユーティリティ
  - utils/logging_setup.py:
    - 統一的なログ設定ユーティリティを提供。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。
    - LOG_DIR の作成失敗等に対するフォールバック（コンソール出力のみ）を実装。
  - utils/process_priority.py:
    - プロセス優先度（Windows の priority class / POSIX の nice）を抽象化して設定するユーティリティを追加。
    - CPU affinity 設定関数 set_cpu_affinity を追加（最初の N コアに固定）。
    - アクセス権限や未対応 OS の場合は警告を出して安全にスキップ。
- 分析・検証ツール
  - tools/paper_verification_report.py:
    - ペーパートレード用 SQLite DB を読み、システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計してレポート出力。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を実装。
    - --from/--to/--db オプションをサポート。
- リサーチ（ファクター計算）
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールを追加（モメンタム / MA / ATR / 出来高等の計算方針と定数定義を含む）。関数群は DuckDB 接続を受け取り純粋関数として動作する設計。

### Changed
- ロギングの標準化
  - すべての起動スクリプトから utils.setup_logging を呼び出すことでログ出力フォーマット・ファイル配置を統一。

### Fixed
- 環境変数読み込みの堅牢化
  - .env パーサ（config._parse_env_line）でクォート・エスケープやインラインコメントを考慮するよう改善。export プレフィックス対応、空行/コメント行の無視、上書きオプションと保護キー採用。

### Notes / Behavior
- run_monitoring は MONITOR_POLL_INTERVAL に不正な値（0 以下や非数）が設定された場合、自動的にデフォルト 60 秒にフォールバックし警告を出力します。
- Monitoring（run_monitoring）は実行環境を問わず Settings.sqlite_path（本番監視 DB）を使用します。一方、Execution は KABUSYS_ENV=paper_trading の場合 paper_sqlite_path を使用して DB を分離します。
- calc_score_weights は全スコアが 0.0 の場合に等金額配分にフォールバックして logger.warning を出します。
- apply_sector_cap はセクターが不明な銘柄（"unknown"）にはセクター上限を適用しません（除外しない）。

### Security
- 秘匿情報（J-Quants トークン、kabu API パスワード等）は .env に保存する想定。config_setup の出力では .env を Git 管理下に置かない旨の注意を明記。

---

今後のリリースでは、テストの追加、DuckDB 上でのファクター計算の完全実装、ExecutionEngine / SystemMonitor の詳細実装の改善、各種設定値の更なる検証追加などを予定しています。