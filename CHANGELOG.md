CHANGELOG
=========

すべての重要な変更点を記録します。  
このファイルは「Keep a Changelog」フォーマットに準拠しています。

未リリース
---------

（空）

0.1.0 - 2026-04-21
-----------------

Added
- プロジェクト初版リリース。
- 実行スクリプト・ランチャーを追加
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading 時は専用の Paper Trading SQLite DB（data/paper_trading.db、PAPER_TRADING_SQLITE_PATH で上書き可能）を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアントの生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み合わせて Engine を起動。エンジンはスレッドで実行され、data/stop_requested.flag の存在で停止。
    - 実行 PID を data/execution.pid に書き出し（pid_file パス可変）。
    - デフォルトでプロセス優先度を "high" に設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はフォールバックして警告）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（data/monitoring.db）を使用して永続化。
    - 停止フラグ（data/stop_requested.flag）を検知して安全にループを終了。
- 設定管理・CLI を追加
  - config.py
    - .env / .env.local の自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。読み込み順: OS 環境 > .env.local > .env（既存の OS 環境は保護）。
    - .env パースの堅牢化（export プレフィックス・シングル/ダブルクォート、エスケープ、インラインコメントの取り扱い）。
    - Settings クラスを提供し、各種環境変数をプロパティとして取得（バリデーション含む）。
    - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の検証ロジックを実装。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成/更新可能。シークレットはマスク表示。出力テンプレートは .env 書式のコメント付き。
  - validate_config.py
    - .env と config/*.yaml の起動前検証 CLI。
    - 必須環境変数や KABUSYS_ENV、DB パス、YAML のパースチェック（PyYAML 未インストール時は YAML 検証をスキップして警告）を実行。
    - --strict モードで警告を失敗扱いにできる。
- ロギング・プロセスユーティリティを追加
  - utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定するユーティリティ。
    - LOG_LEVEL / LOG_DIR / 引数による上書き、ログディレクトリ作成失敗時のフォールバック動作を実装。
  - utils/process_priority.py
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。Windows / POSIX の差分を吸収し、権限不足などは警告でスキップ。
- ポートフォリオ構築ロジックを追加（純関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選択。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等配分へフォールバックし警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクターごとの既存エクスポージャが上限を超えている場合、新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull/neutral/bear のマッピング、および未知レジームでのフォールバックと警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づき注文株数を算出。単元株（lot_size）丸め、ポジション上限、aggregate cap（available_cash）によるスケーリング、スケール後の余り処理を実装。コストバッファ（手数料/スリッページ）を考慮。
- Paper Trading 検証ツールを追加
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / --db）からレポートを生成する CLI。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、API レイテンシ（avg/max/P95）など。
    - デフォルト基準（閾値）を設定し、PASS/FAIL 判定を出力（閾値および P95 計算実装含む）。
- 研究モジュール（開始）
  - research/factor_research.py
    - DuckDB を用いたファクター計算フレームワーク（モメンタム等）の骨組みを追加。calc_momentum の実装途中（prices_daily / raw_financials を用いる設計）。

Changed
- デフォルト DB/ログ/設定パスの明示
  - DuckDB、SQLite、ログディレクトリなどのデフォルトパスを明確化（data/kabusys.duckdb, data/monitoring.db, logs/）。
- ログ出力先を stdout に明示（cron/task scheduler からの一元化を想定）。

Fixed
- N/A（初版のため既知のバグ修正履歴はなし）。

Deprecated
- N/A

Removed
- N/A

Security
- 環境変数ウィザードでシークレットをマスク表示するなど、機密情報取り扱いへの注意喚起を追加。

注記
- このリリースはプロジェクトの初期実装をまとめたもので、各モジュールはユニットテストや統合テストにより追加の検証が推奨されます。
- research/factor_research.py の一部（calc_momentum の末端）が途中で切れているため、完全実装や追加テストが必要です。