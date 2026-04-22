CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

現在のバージョン: 0.1.0 (初回リリース)
リリース日: 2026-04-22

Unreleased
----------

(なし)

0.1.0 - 2026-04-22
------------------

Added
- 基本パッケージ初回リリース。
  - パッケージメタ:
    - バージョン: 0.1.0
    - パッケージ名: kabusys
- 実行用スクリプト:
  - run_execution.py
    - ExecutionEngine 起動スクリプトを提供。プロセス開始時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite (PAPER_TRADING_SQLITE_PATH / data/paper_trading.db) を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成。OrderRepository, OrderManager, RiskManager, Reconciler を組み立て ExecutionEngine をスレッドで実行。
    - 停止制御: data/stop_requested.flag による停止検知、data/execution.pid を PID ファイルとして使用。
    - RiskManager のデフォルト設定例を含む（max_position_pct, max_utilization, rate_limit_per_sec など）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。起動時にプロセス優先度を "high" に設定。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバックする。
    - 監視は環境設定にかかわらず本番 sqlite_path を使用することを明確化。
    - 停止制御: data/stop_requested.flag を検知してループ終了。check_once() 実行時の例外は捕捉してログ出力後に次回ポーリングへ耐久的に復帰。
- 設定管理:
  - config.py
    - .env 自動ロード機能 (.env / .env.local) を実装。OS 環境変数を保護するための上書き/保護ロジックあり。
    - .env のパースは export キーワード対応、シングル/ダブルクォート・バックスラッシュエスケープ・インラインコメント処理等に対応する堅牢な実装。
    - Settings クラスを提供し、各種環境変数の取得とバリデーションを一元化（J-Quants, kabu API, LINE, DB パス, 監視閾値, env/log_level 判定など）。
    - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等の値チェック（有効な選択肢に限定）。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を提供。既存 .env の読み込み・マスク表示・確認・保存機能あり。
    - 出力される .env ファイルはテンプレートヘッダ付きで、機密値はマスクして表示。
  - validate_config.py
    - 起動前の設定検証 CLI を提供。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML がない場合はスキップ＆警告）。
    - --strict オプションで警告も失敗とみなす挙動を提供。終了コードで結果を表現（エラー:1、警告×strict:1、正常:0）。
- ポートフォリオ構築ライブラリ (純粋関数群、DB 非依存):
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順でソートし上位 N 件を抽出。タイブレークに signal_rank を利用。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を提供。全スコア 0 の場合は等金額にフォールバックして警告ログ出力。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限ロジックにより、既存保有比率が閾値を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム ("bull","neutral","bear") に応じた投下資金乗数を返す。未知レジームは警告を出し 1.0 でフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based","equal","score") に基づく発注株数計算。単元株（lot_size）丸め、per-position 上限・aggregate cap（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的見積り、残差の lot_unit 割当アルゴリズムを実装。
- utilities:
  - utils.logging_setup
    - setup_logging: ルートロガーに StreamHandler(stdout) と TimedRotatingFileHandler（デフォルト logs/<app>.log、日次ローテーション、30 日保持）を設定。ログディレクトリ作成失敗時はファイル出力を無効化しコンソール出力にフォールバック。
    - ログレベル、ログディレクトリ解決順を明示（引数 > 環境変数 > デフォルト）。
  - utils.process_priority
    - set_process_priority: Windows と POSIX (Linux/Mac/FreeBSD) を吸収してプロセス優先度を設定。権限不足等は警告ログでスキップ。
    - set_cpu_affinity: 指定コア数で CPU affinity を設定する補助関数。使用不可時は警告でスキップ。
- monitoring / DB:
  - monitoring.monitoring_db の初期化が run スクリプトから呼び出されることで監視用テーブルの存在を保証（冪等）。
  - DuckDB と SQLite の両方を利用する設計（duckdb は分析用、sqlite は監視/履歴用）。
- tools:
  - tools.paper_verification_report
    - ペーパートレード用検証レポート生成CLI。期間フィルタ (--from/--to) と DB パス指定 (--db) をサポート。
    - 指標: 稼働率(uptime_pct)、注文成功率(fill_rate)、送信率(send_rate)、API レイテンシ（avg/max/P95）等。P95 計算、閾値による PASS/FAIL 判定を実装。
    - デフォルト閾値をファイル冒頭に定義 (稼働率 99%、Fill Rate 90%、Send Rate 95%、P95 200 ms)。
- research:
  - research.factor_research
    - DuckDB を用いたファクター計算モジュールの骨組みを追加。モメンタム/バリュー/ボラティリティ/流動性等の算出方針を注記。calc_momentum 等の関数が実装途上（ファイル末尾で途中）で、DuckDB prices_daily/raw_financials を参照して計算する設計。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / 観察事項（実装から推測）
- 設計上の分離:
  - paper_trading と live は DB を分離することによりデータ汚染を防止。
  - 監視は常に本番用 sqlite_path を参照する設計になっている点に注意（監視は環境に依存しない想定）。
- ログ・優先度関連:
  - 起動スクリプトは起動直後にプロセス優先度を上げ、ログを統一的に初期化するため運用時の安定性を重視する作り。
- エラーハンドリング:
  - 長時間動作するプロセス（監視ループ・エンジン）で例外を吞んで継続する実装があり、可用性重視の設計思想が伺える。
- まだ未実装 / TODO:
  - research.factor_research の calc_momentum 関数が途中で終わっている（今後完成が必要）。
  - position_sizing の price 欠損時のフォールバック価格処理は TODO コメントとして残されている。

お問い合わせ・貢献
- 変更内容やリリースノートの補足が必要な場合はソースコード内のコメントや関数 docstring を参照してください。必要であれば、ソースの追加差分に基づいて更に詳細な変更ログを作成します。