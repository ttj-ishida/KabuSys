# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従っています。  
このリポジトリが最初に公開されたバージョンを記録します。

## [0.1.0] - 2026-04-21

初回リリース。日本株向けの自動売買（KabuSys）コア機能とユーティリティ群を追加しました。主な追加点は以下の通りです。

### Added
- 全体
  - パッケージの初期バージョンを追加（kabusys v0.1.0）。
  - モジュール構成を整備: execution, monitoring, portfolio, research, utils, tools, config 関連などを含む。

- 起動スクリプト
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV による paper_trading 処理分離をサポート。paper_trading 時は専用 SQLite（既定: data/paper_trading.db）を使用し、MockBrokerClient を利用可能（BrokerClientFactory 経由）。
    - プロセス優先度を起動時に "high" に設定（set_process_priority を利用）。
    - 実行中の PID をファイルに保存する仕組み（data/execution.pid）。
    - 停止フラグ（data/stop_requested.flag）をチェックして安全終了。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境に関わらず本番用 sqlite_path を参照（監視は本番 DB を用いる設計）。
    - 停止フラグ検出でループを終了。

- 設定管理
  - config.Settings クラスを追加し、環境変数経由で設定値を提供。
    - env（KABUSYS_ENV）、log_level、データベースパス、LINE 通知トークン、kabu API パスワード、J-Quants トークン等をプロパティで取得。
    - 各種値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
  - .env 自動読み込み機能を追加（プロジェクトルートの .env を自動的に取り込む。OS 環境変数は保護）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env/.env.local の読み込み順と override ルールを実装。
    - .env のパースは export 文、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。

- 設定ユーティリティ / CLI
  - config_setup: 対話式ウィザードで .env を初期作成・更新する CLI を追加（python -m kabusys.config_setup）。
    - J-Quants / kabu / DB パス / ログレベル 等の入力項目を用意。既存値の読み込みやシークレット表示（マスク）に対応。
  - validate_config: .env と config/*.yaml の設定を起動前に検証する CLI を追加（python -m kabusys.validate_config）。
    - 必須環境変数の有無、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML がある場合）パース検証を実施。
    - --strict モードで警告も FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア順で BUY 候補を選択（同点タイブレークに signal_rank を使用）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分を実装。全スコアが 0 の場合は等配分にフォールバック（警告ログ）。
  - portfolio.risk_adjustment
    - apply_sector_cap: 既存ポジションを考慮したセクター集中上限チェック。売却予定銘柄を除外するオプションや "unknown" セクターを除外しない挙動を実装。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジームは 1.0 にフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method (risk_based / equal / score) に基づく発注株数計算。単元株（lot_size）丸め、1銘柄上限、aggregate cap スケーリング、cost_buffer（手数料・スリッページ想定）等に対応。
    - risk_based 方式では stop_loss_pct と risk_pct に基づく株数を計算。

- 実行周辺ユーティリティ
  - utils.logging_setup
    - 統一的なログ設定ユーティリティを追加。
    - stdout への StreamHandler と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定。ログディレクトリ作成に失敗した場合はコンソールのみで継続。
    - ログレベルは関数引数 > 環境変数 LOG_LEVEL > デフォルト の優先順で解決。
  - utils.process_priority
    - プラットフォームを吸収したプロセス優先度設定（Windows の priority class / POSIX の nice 値を扱う）。
    - set_cpu_affinity による CPU ピン止め機能を提供（利用可能なコア数を考慮）。
    - 権限不足などで設定できない場合は警告ログでスキップ。

- モニタリング / データベース
  - monitoring 初期化（monitoring_db.init_monitoring_db の呼び出しにより監視テーブルを冪等的に準備）。
  - run_monitoring および run_execution から DuckDB（分析用）と SQLite（監視 / 履歴用）への接続を確立。

- 実行検証ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成スクリプトを追加（期間指定可能）。
    - system_status / trade_logs / risk_logs を元に、稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL を出力。
    - デフォルト閾値を設定（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）。

- 研究用モジュール（骨組み）
  - research.factor_research を追加（定量ファクター計算の設計と一部実装）。
    - モメンタム、MA200、ATR、出来高系などの計算方針を実装予定。DuckDB 接続を受ける設計で、prices_daily / raw_financials テーブルを利用する想定。

### Changed
- ログ設計
  - ルートロガーの既存ハンドラをクリアしてから再設定することで、二重出力を防止するようにした。
  - StreamHandler は stdout を使用（cron や Task Scheduler からのリダイレクトを想定）。

### Fixed
- 環境変数読み込み
  - .env のパースロジックでシングル/ダブルクォート、エスケープ、インラインコメント等の扱いを改善。export KEY=.. 形式にも対応。

### Known issues / Notes
- research.factor_research は設計の骨子と一部実装が含まれていますが、全関数の実装が完了していない可能性があります（ファイル先頭に設計方針と一部定数が定義されています）。
- position_sizing の価格フォールバック処理は TODO コメントで指摘があり、price が欠損するケースでの改善（前日終値や取得原価のフォールバック）が将来的な課題として残っています。
- 実際のブローカークライアント・ExecutionEngine 等の細部実装（broker_factory、execution_engine、order_manager 等）は本リリースで API が定義され使用されていますが、外部環境依存のため本番運用では事前の検証を推奨します。

---

今後のリリースでは以下のような改善を予定しています:
- research モジュールの完全実装と単体テストの追加
- strategy / execution のエンドツーエンドテストおよびロギング/監視の強化
- 銘柄ごとの lot_size 対応や価格フォールバックの改善

もし意図しない差分や誤記があれば指摘ください。