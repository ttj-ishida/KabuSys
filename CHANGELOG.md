# Changelog

すべての重要な変更点を記載します。フォーマットは「Keep a Changelog」に準拠しています。  
バージョン番号はパッケージの `__version__`（src/kabusys/__init__.py）に基づきます。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-18

Added
- パッケージ初期リリース。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト: 60秒）。不正値（0以下や非数）はデフォルトにフォールバックして警告を出力。
    - 監視側は KABUSYS_ENV にかかわらず本番用の `sqlite_path` を使用して DB に接続する実装（監視テーブル初期化を含む）。
    - 停止用フラグファイル（data/stop_requested.flag）を検知して安全にループを終了。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を用い、`data/paper_trading.db` に記録して本番 DB と分離。
    - 起動時にプロセス優先度を "high" にセット。停止フラグ（data/stop_requested.flag）検出時に Engine を安全に停止。
    - 実行 PID を data/execution.pid に書き出す仕組み（Engine の pid_file 指定）。
- 設定・環境管理
  - config.py
    - .env 自動読み込み（プロジェクトルートの検出: .git または pyproject.toml を基準）。OS 環境変数優先、`.env.local` は `.env` 上書きで適用。
    - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - `.env` の行パースロジック強化（`export KEY=val`、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント取り扱い等）。
    - Settings クラスを提供し、各種設定値（API トークン、DB パス、Paper Trading 設定、監視閾値、環境判定・ログレベル判定等）をプロパティで取得可能。バリデーションとデフォルト値を実装。
    - Paper Trading 関係: `paper_fill_mode`（instant/partial/never/reject）、`paper_sqlite_path` のサポート。
- 設定支援ツール
  - config_setup.py
    - 対話式ウィザードで `.env` を生成・更新する CLI を追加。
    - 各設定項目の説明、デフォルト、シークレット表示（マスク）、選択肢サポートを提供。
    - 生成後の確認プロンプトと `.env` 書き出し機能。
  - validate_config.py
    - 起動前に `.env` と `config/*.yaml` の存在・妥当性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、YAML パースチェック（PyYAML がある場合）を実装。
    - `--strict` オプションで警告も失敗扱いにできる。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START の危険な設定に対する警告）。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一されたロギング設定関数 `setup_logging(app_name, log_dir, level)` を追加。
    - stdout に出力する StreamHandler と日次ローテーション（TimedRotatingFileHandler）でログファイル（logs/<app_name>.log）を出力。ファイル出力の失敗時はコンソールのみで継続。
    - ログディレクトリ自動作成、既存ハンドラの安全なクリア処理、ログレベルの解決順序（引数 > 環境変数 LOG_LEVEL > デフォルト）を実装。
  - utils/process_priority.py
    - プロセス優先度（high/normal/low）と CPU affinity 固定のユーティリティを提供（Windows/Linux/macOS 対応を抽象化）。
    - psutil を使って nice 値・Windows 優先度クラスを設定。権限不足や未対応 OS の場合は警告を出してスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）：スコア降順、同点は signal_rank 昇順でタイブレーク。
    - 重み計算: 等分配（calc_equal_weights）、スコア加重（calc_score_weights）。スコア合計が 0 の場合は等分配にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）：既存ポジションのセクター別時価を計算し、1セクター上限（max_sector_pct）を超える場合は同セクターの新規候補を除外。セクター不明 ("unknown") は上限の適用対象外とする。
    - 市場レジーム乗数（calc_regime_multiplier）： "bull"=1.0, "neutral"=0.7, "bear"=0.3、未知レジームは警告の上 1.0 フォールバック。
  - portfolio/position_sizing.py
    - 発注株数算出（calc_position_sizes）：
      - allocation_method: "risk_based" / "equal" / "score" をサポート。
      - risk_based: ポジションあたりのリスク（risk_pct）、損切り率（stop_loss_pct）に基づく基本株数算出。
      - equal/score: 重み（weights）に基づく配分。
      - 単元株（lot_size）で丸め、1 銘柄上限（max_position_pct）・合計投下上限（max_utilization, available_cash）を考慮。
      - cost_buffer による手数料/スリッページを保守的に見積もり、合計コストが利用可能現金を超える場合はスケーリング、端数は lot_size 単位で残差に基づき追加配分するロジックを実装。
      - 価格未取得や 0 の場合は該当銘柄をスキップしログ出力。
- モニタリング DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を呼ぶ各スクリプトによって、監視用テーブルが存在することを保証する（冪等）。
- 実行エンジン周辺コンポーネント（読み込み）
  - execution.*（broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager）を組み立てる起動フローを実装（起動スクリプト run_execution での組立てを参照）。
  - RiskManager にデフォルト設定を注入（max_position_pct, max_utilization, rate_limit 等）。初期ポートフォリオ値は broker.get_available_cash() を用いる。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から集計し、検証レポートを標準出力に生成する CLI を追加。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）、リスク却下数 等。
    - 閾値による PASS/FAIL 判定（稼働率 >= 99.0%、fill_rate >= 90%、send_rate >= 95%、P95 レイテンシ <= 200ms）。
    - コマンドライン引数: --from, --to（YYYY-MM-DD）、--db（DB パス）。環境変数 `PAPER_TRADING_SQLITE_PATH` での指定も可能。
- 研究用モジュール（部分実装）
  - research/factor_research.py
    - DuckDB の `prices_daily` 等を用いてモメンタム・ボラティリティ・バリュー等のファクターを計算する設計を追加。モメンタム計算関数（calc_momentum）の実装開始（ターゲット日・horizon 定義等）。（ファイル末尾で実装途中の箇所あり）

Security, Documentation, Tests
- ドキュメントや README については未付属。各モジュール内に操作説明や使用例を docstring として追加。

Notes / 注意事項
- Config 自動読み込みはプロジェクトルートの検出に依存するため、パッケージ配布後も __file__ を起点とした探索で動作するよう設計されているが、プロジェクトルートが特定できない場合は自動ロードをスキップする。
- run_monitoring が監視 DB として常に production 用 sqlite_path を使用する点、run_execution が paper_trading 時に DB を分離する点は運用上の重要な挙動であるためデプロイ時に確認すること。
- process priority / cpu affinity の設定は権限に依存するため、権限不足時は警告を出して処理を継続する（例: 非権限ユーザでの起動）。
- logging_setup はログディレクトリ作成に失敗した場合にファイル出力をスキップして stdout のみでログを提供する。

----------------------------------------------------------------------
このリリースはコードベースの現状から推測して作成しています。実際のリリースノートや運用上の注意はプロジェクトの公式ドキュメントを参照してください。