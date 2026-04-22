CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]
-------------

- （なし）

[0.1.0] - 2026-04-22
-------------------

Added
- パッケージ初版リリース (バージョン 0.1.0)
  - 高水準の機能セットを追加:
    - 実行系（ExecutionEngine）起動スクリプト: run_execution.py
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB (デフォルト: data/paper_trading.db) を使用し、本番 DB と分離。
      - BrokerClientFactory によるブローカークライアント生成。
      - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
      - デーモンスレッドでエンジンを実行し、 data/stop_requested.flag に応じて安全に停止。
      - 実行時 PID を data/execution.pid に保存（設定により変更可能）。
    - 監視ループ起動スクリプト: run_monitoring.py
      - SystemMonitor のポーリングループを実行。デフォルトポーリング間隔 60 秒。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（不正な値はデフォルトにフォールバック）。
      - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path (SQLITE_PATH) を使用する設計。
      - 停止フラグ file: data/stop_requested.flag を検知してループ終了。
    - 環境設定管理: config.py
      - .env 自動ロード機能（プロジェクトルートを .git または pyproject.toml から検出）。
      - export プレフィックス、クォート文字、エスケープ、行内コメント等に対応した堅牢な .env パーサを実装。
      - 多数の設定プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID_FILE_PATH、kill/thresholds、KABUSYS_ENV/LOG_LEVEL 判定等）。
      - KABUSYS_ENV の有効値: development / paper_trading / live。LOG_LEVEL の検証。
    - 対話式設定ウィザード: config_setup.py
      - .env の初期作成・更新を対話式で支援。セクション分けされたテンプレートで保存。
      - 秘密値はマスク表示。生成された .env は Git へコミットしない注意書きあり。
    - 設定検証 CLI: validate_config.py
      - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス・config/*.yaml の存在／パースチェック（PyYAML があれば内容検証）。
      - 本番 (live) 向けの追加ガード（LINE 設定未指定や KILL_FLAG_CLEAR_ON_START の危険設定など）を警告表示。
      - --strict オプションで警告を FAIL 扱いにできる。
    - ロギングユーティリティ: utils/logging_setup.py
      - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定する共通セットアップ関数 setup_logging を提供。
      - LOG_DIR / LOG_LEVEL を環境変数または引数で上書き可能。ファイル出力に失敗した場合はコンソール出力のみで継続。
    - プロセス優先度 / CPU 固定ユーティリティ: utils/process_priority.py
      - クロスプラットフォーム対応の set_process_priority(level) / set_cpu_affinity(cpu_count) を提供。
      - Windows と POSIX の差異を吸収し、アクセス権限不足や未対応 OS の場合は警告を出して安全にスキップ。
    - ポートフォリオ構築モジュール (kabusys.portfolio)
      - portfolio_builder.py
        - select_candidates: BUY シグナルをスコア降順かつ signal_rank でタイブレークして上位 N を選択。
        - calc_equal_weights, calc_score_weights: 等金額・スコア加重の配分計算。全スコア 0 の場合は等金額にフォールバックし警告を出力。
      - risk_adjustment.py
        - apply_sector_cap: セクター別エクスポージャーが閾値を超える場合、新規候補を除外（"unknown" セクターは制限対象外）。
        - calc_regime_multiplier: レジーム ("bull","neutral","bear") に応じた投下資金乗数。未知レジームは 1.0 にフォールバック（警告）。
      - position_sizing.py
        - calc_position_sizes: リスクベース / equal / score に対応した株数算出。単元株（lot_size）、最大ポジション比率、利用可能現金（aggregate cap）、cost_buffer による保守的見積り、スケーリングと端数配分アルゴリズムを実装。
    - 研究用ファクター計算スケルトン: research/factor_research.py
      - DuckDB 接続を受け取り、prices_daily / raw_financials に基づくモメンタム・バリュー・ボラティリティ等の計算関数実装を想定した設計（実装の一部がスケルトン）。
    - Paper Trading 検証レポート: tools/paper_verification_report.py
      - ペーパートレード用 SQLite DB (PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db) から指標を集計してレポート出力（稼働率・注文成功率・送信率・P95 レイテンシ等）。
      - デフォルト合格基準 (例: uptime >= 99.0%, fill_rate >= 90%, send_rate >= 95%, P95 latency <= 200 ms) を用いた PASS/FAIL 判定。
      - --from / --to / --db CLI オプションを提供。

Changed
- なし（初版）

Fixed
- なし（初版）

Notes / 重要な挙動
- 監視（run_monitoring）は KABUSYS_ENV にかかわらず sqlite_path（SQLITE_PATH）を使用します。実運用でモニタリング DB を分離したい場合は SQLITE_PATH を別ファイルに設定してください。
- 実行エンジン（run_execution）は paper_trading 環境であれば paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を使用して本番データと分離します。
- .env の自動読み込みはデフォルトで有効（プロジェクトルートが検出できる場合）。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- process priority / cpu affinity の設定は権限によって失敗する可能性があり、その場合はログに警告を出して処理を継続します。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されますが、ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。
- config_setup で生成した .env はセキュリティ上 Git にコミットしないでください（ファイルヘッダに注記あり）。

コマンド／エントリポイント（主なもの）
- python -m kabusys.run_monitoring
- python -m kabusys.run_execution
- python -m kabusys.validate_config [--strict]
- python -m kabusys.config_setup [--env-file PATH]
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

開発メモ
- Portfolio / position sizing の一部は将来的に銘柄ごとの lot_size をサポートするなど拡張を想定（TODO コメントあり）。
- research モジュールは DuckDB ベースでの計算を前提とした実装を想定しており、必要に応じて完全実装を追加してください。