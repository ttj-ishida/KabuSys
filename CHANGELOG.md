KEEP A CHANGELOG形式 — 変更履歴 (日本語)
======================================

すべての変更は Keep a Changelog の慣習に準拠して記載しています。
バージョン、追加(Added)、変更(Changed)、修正(Fixed)、既知の問題(Notes) などを含みます。

0.1.0 — 2026-04-19
------------------

Added
- 基本アプリケーションフレームワークを追加
  - パッケージバージョンを __version__ = "0.1.0" として定義。
- 実行エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV に応じて本番/ペーパートレードを切り替え。
    - ペーパートレード時は専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - エンジンの PID ファイル (data/execution.pid) と停止フラグ (data/stop_requested.flag) をサポート。停止フラグ検知で安全に停止。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - RiskManager の初期設定 (max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等) をコード内に定義。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - ポーリング間隔を MONITOR_POLL_INTERVAL 環境変数で上書き可能（デフォルト 60 秒）。不正な値はログ警告のうえデフォルトを使用。
    - 監視は環境に依らず本番 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ (data/stop_requested.flag) 検知でループを終了。
    - プロセス優先度を最初に "high" に設定。

- 設定・環境管理
  - config.py: Settings クラスを実装。環境変数から各種設定値を取得・検証。  
    - J-Quants / kabuAPI / LINE / DB パス / 監視閾値等をプロパティとして提供。  
    - PAPER_FILL_MODE の有効値検証 ("instant","partial","never","reject") を導入。  
    - env の値検証 (development|paper_trading|live)、LOG_LEVEL 検証を実装。  
    - .env の自動読み込み機構を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。OS 環境変数は上書き保護。
  - config_setup.py: 対話式 .env ウィザードを追加。  
    - .env の初期作成・更新を対話的に行い、機密項目はマスク表示。  
    - デフォルト・選択肢を提示し、確認後に .env を書き出し。
  - validate_config.py: 起動前の設定検証 CLI を追加。  
    - 必須環境変数チェック、KABUSYS_ENV や LOG_LEVEL の妥当性、DB パス親ディレクトリの存在有無、config/*.yaml の存在とパース（PyYAML がインストールされている場合）を検証。  
    - --strict オプションで警告を失敗扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一ログ初期化ユーティリティを追加。  
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30日分保持）をルートロガーに設定。  
    - LOG_DIR 環境変数や引数でログ格納先を変更可能。ディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
  - utils/process_priority.py: プロセス優先度 (high/normal/low) と CPU affinity 設定ユーティリティを追加。  
    - Windows/Linux/macOS に対する差分吸収実装（psutil ベース）。アクセス権限や未対応環境での失敗は警告でスキップ。

- ポートフォリオ構築（純粋関数モジュール）
  - portfolio/portfolio_builder.py: 候補選定・重み算出を実装。  
    - select_candidates: スコア降順で上位 N を選択（signal_rank でタイブレーク）。  
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア正規化配分（スコア合計が 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py: セクター上限とレジーム乗数を実装。  
    - apply_sector_cap: 既存ポジションを考慮してセクター集中を制限（"unknown" セクターは制限対象外）。当日売却予定銘柄をエクスポージャー計算から除外するオプションあり。  
    - calc_regime_multiplier: market regime ("bull","neutral","bear") に基づく投下資金乗数を返す（未知レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py: 発注株数算出ロジックを実装。  
    - risk_based / equal / score の配分方式をサポート。  
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash に基づくスケールダウン）、cost_buffer（手数料/スリッページ見積り）を考慮。  
    - スケーリング時には残差に基づき lot 単位で追加配分するアルゴリズムを実装。

- 監視・検証ツール
  - monitoring 初期化: monitoring_db.init_monitoring_db を通じて監視テーブルの冪等初期化を行う呼び出しを追加（監視と実行両方で利用）。
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート出力ツールを追加。  
    - system_status / trade_logs / risk_logs から稼働率、注文成功率・送信率、リスク却下数、レイテンシ（AVG/MAX/P95）を算出してレポート出力。  
    - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づき PASS/FAIL 判定を行う。  
    - --from / --to / --db オプションをサポート。DB の存在チェックあり。

- リサーチ（未完成の一部を含む）
  - research/factor_research.py: ファクター計算モジュールを追加（Momentum/Value/Volatility/Liquidity の方針と定数を定義）。  
    - DuckDB を使った prices_daily/raw_financials に基づく計算を想定（実装は一部未完）。

Changed
- 新規プロジェクト初期導入のため該当なし。

Fixed
- 新規プロジェクト初期導入のため該当なし。

Notes / Known issues / TODO
- position_sizing: price が欠損 (0.0) の場合にエクスポージャーが過少見積りされる旨の TODO コメントあり。前日終値や取得原価などを使ったフォールバックが想定されている。
- portfolio/position_sizing: 将来的に銘柄別 lot_size をサポートする余地あり（現状は全銘柄共通 lot_size を想定）。
- research/factor_research.py: ファイル末尾で実装途中で切れている（calc_momentum の途中）。追加の実装が必要。
- process_priority / set_cpu_affinity: アクセス権限不足や非対応 OS では設定をスキップし警告になる可能性あり。
- logging_setup: ログディレクトリ作成に失敗した場合はファイル出力が無効化され、警告が出力される。
- validate_config: PyYAML 未インストール時は YAML のパース検証をスキップして警告を出す。
- run_monitoring: 監視は「環境にかかわらず本番 sqlite_path を使用する」仕様のため、ペーパー/開発環境での監視 DB 分離を明示的に行っていない点に注意。

開発者向けメモ
- .env の自動ロードはプロジェクトルートが検出できない場合はスキップされる。テスト環境や特殊な配置環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化可能。
- PAPER_FILL_MODE の値検証により、誤った文字列設定時は ValueError が発生するため .env 作成時に正しい選択肢を使用すること。
- ExecutionEngine の初期化時にエラーが発生した場合はリソースクローズのため finally ブロックで DB コネクションを確実に閉じる設計。

以上がコードから推測できる主要な変更点・初期機能一覧です。追加の変更履歴や過去バージョンの差分があれば、それに基づきリリースノートを拡張できます。