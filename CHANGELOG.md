CHANGELOG
=========

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

Added
- 起動スクリプトを追加 / 改良
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用。
    - 停止はプロジェクト直下の data/stop_requested.flag により検知。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db、環境変数で上書き可）と MockBrokerClient を使用し、本番 DB と分離。
    - 実行中は PID ファイル(data/execution.pid) を使用。停止フラグでセッション停止を行う。

- 設定・環境周りのユーティリティ
  - config.py: Settings クラスを追加。
    - 各種環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE 等）をプロパティで取得。
    - KABUSYS_ENV のバリデーション（development, paper_trading, live）を組込。
    - PAPER_FILL_MODE の有効値チェックと説明を実装。
    - 自動 .env ロード機能を実装（プロジェクトルートの判定 .git または pyproject.toml を探索）。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - config_setup.py: インタラクティブな .env 作成ウィザードを追加。
    - 標準項目の対話的入力、既存 .env の読み込み、保存機能を提供。
    - 秘匿項目はマスク表示。保存キャンセルや中断処理を実装。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と YAML パース検証（PyYAML が存在する場合）。
    - --strict モードを追加（警告を FAIL 扱いで exit(1)）。

- ログ・プロセスユーティリティ
  - utils/logging_setup.py:
    - StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、デフォルト 30 日保持）をルートロガーに設定するユーティリティを追加。
    - LOG_DIR / LOG_LEVEL からの解決や、ログディレクトリ作成失敗時のフォールバック（コンソールのみ）を実装。
  - utils/process_priority.py:
    - クロスプラットフォームでプロセス優先度（high/normal/low）を設定する set_process_priority を追加。
    - CPU affinity を第一 N コアに固定する set_cpu_affinity を追加（psutil を使用、権限不足や未サポート環境では警告してスキップ）。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順で候補選定、signal_rank によるタイブレークを実装。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア合計が 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合に当該セクターの新規候補を除外するロジックを実装（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数を返す（bull/neutral/bear）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に応じて発注株数を計算。
      - risk_based: risk_pct / stop_loss_pct を使ったポジションサイズ算出。
      - equal/score: weight と max_utilization を使って割当。
      - 単元株（lot_size）で丸め、max_position_pct による per-stock キャップ、aggregate cap による全体スケールダウン（cost_buffer を考慮）。
      - スケールダウン時は残差を考慮し lot 単位で追加配分するロジックを実装。

- 解析・ツール
  - tools/paper_verification_report.py:
    - Paper Trading 検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、P95 レイテンシ等を算出して PASS/FAIL 判定を行う。
    - デフォルト閾値を設定（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）。
    - --from / --to / --db オプションをサポート。P95 は簡易計算を実装。

Changed
- 環境変数のロード順序を明確化
  - OS 環境変数 > .env.local > .env（.env.local は .env を上書き可能）。
  - .env 読み込みはプロジェクトルートが検出できない場合はスキップ。
- ロギングのデフォルト出力先を stdout にし、cron/Task Scheduler 等との相性を考慮。
- run_execution/run_monitoring の起動時にプロセス優先度を "high" に設定する呼び出しを追加。

Fixed
- 環境変数パーサの堅牢化
  - config._parse_env_line にて export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いをサポート。
  - 無効行やキー無し行を適切にスキップするよう改善。
- MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）に対するフォールバック処理を追加し、警告ログを出すようにした（デフォルト 60 秒）。
- ログディレクトリ作成失敗時にファイルハンドラ作成をスキップしてコンソール出力のみで継続するよう修正。

Security
- .env ファイルの取り扱いに関する注意喚起を config_setup のヘッダに追加（.env を Git にコミットしない旨）。

0.1.0 - 2026-04-25
------------------

Initial public release
- 上記のコア機能をまとめて公開:
  - 起動スクリプト（run_execution, run_monitoring）
  - 設定管理・ウィザード・検証ツール（config, config_setup, validate_config）
  - ロギング・プロセス制御ユーティリティ（utils.logging_setup, utils.process_priority）
  - ポートフォリオ構築ライブラリ（portfolio.*）
  - Paper Trading レポートツール（tools.paper_verification_report）
  - 解析基盤の下地（research.factor_research の一部実装）
- パッケージバージョンを __version__ = "0.1.0" に設定。

Upgrade notes
- 自動 .env ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で利用）。
- paper_trading 用 DB を利用するには KABUSYS_ENV=paper_trading を設定してください。paper_trading 時は paper_trading 専用の SQLite を使用し、本番データと完全に分離されます（デフォルト: data/paper_trading.db）。
- 本番（live）運用時は validate_config を実行し、LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値などを必ず確認してください。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます。ファイル出力に失敗した場合、ログはコンソール (stdout) のみになります。

参考: 主な CLI / 実行方法
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL に
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例: --from 2026-04-01 --to 2026-04-11
- 実行スクリプト:
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring

---

今後の予定（予定項目）
- research.factor_research の完全実装（ファクター計算ロジックの完成）。
- 銘柄別 lot_size、手数料/スリッページのより詳細なモデル化。
- ブローカークライアントの具体実装とテストヘルパーの拡充。