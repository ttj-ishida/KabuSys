CHANGELOG
=========

すべてのバージョン履歴は Keep a Changelog の形式に準拠して記載しています。  
参考: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
(今後の改善・未解決の既知事項)

- Known: research/factor_research.py の calc_momentum の実装が途中で終端している（ファイル末尾に未完の行が存在）。この関数は現状で計算を完了できないため、リリース前に実装を完了する必要があります。
- TODO: portfolio/risk_adjustment.apply_sector_cap 内で price が欠損(0.0) 的扱いになるとエクスポージャーが過小評価される旨の注記あり。価格フォールバック（前日終値など）の導入検討が推奨されます。
- TODO: portfolio/position_sizing の将来的拡張として、銘柄毎の lot_size を stocks マスタに持たせる設計がコメントに残っている（現状は全銘柄共通の lot_size を想定）。
- 予定: 追加ユニットテスト（特に position sizing / scaling ロジックや apply_sector_cap）を整備することを推奨。

v0.1.0 - 2026-04-22
-------------------

Added
- プロジェクト初期リリース。
- 基本設定・環境変数管理
  - kabusys.config:
    - .env 自動読み込み（プロジェクトルート検出: .git / pyproject.toml を基準）。
    - .env/.env.local の読み込み順と OS 環境変数保護（override/protected）の実装。
    - 環境変数パーサーは export プレフィックス、クォート、エスケープ、インラインコメントを扱う独自ロジックを搭載。
    - Settings クラスで主要な設定値をプロパティとして公開（J-Quants / kabu API / DB パス / paper_trading 用設定 / 監視閾値など）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
- 環境設定ツール
  - kabusys.config_setup:
    - 対話式ウィザードで .env を作成・更新する CLI。
    - J-Quants・kabu API パスワード等のシークレット入力に対応。
    - 保存前の確認表示、.env のテンプレート書き出し機能を提供。
- 設定検証
  - kabusys.validate_config:
    - .env および config/*.yaml の起動前検証 CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、PyYAML による YAML 構文検証（PyYAML 未インストール時はスキップ）を実行。
    - --strict オプションで警告をエラー扱いにできる。
- 起動スクリプト
  - run_monitoring.py:
    - SystemMonitor ポーリングループの起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず production 相当の sqlite_path を使用。
    - 停止フラグ (data/stop_requested.flag) の検出で安全にループを終了。
    - duckdb と sqlite3 の接続管理、監視 DB 初期化の呼び出し。
  - run_execution.py:
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - ExecutionEngine を別スレッドで起動し、停止フラグで安全に停止。実行時の PID ファイル管理（data/execution.pid）。
- ロギング・プロセスユーティリティ
  - kabusys.utils.logging_setup:
    - setup_logging 関数で StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション・30日分保持）をルートロガーに設定。
    - LOG_DIR / app_name / LOG_LEVEL の解決ルールを実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
  - kabusys.utils.process_priority:
    - プラットフォームを吸収したプロセス優先度設定ユーティリティ（Windows の HIGH_PRIORITY_CLASS / POSIX の nice 値など）。
    - CPU affinity 設定のユーティリティも提供。権限不足等で失敗した場合は警告を出してスキップ。
- Monitoring / Execution に関連する初期化ユーティリティ呼び出しの統合（監視 DB 初期化、duckdb 接続など）。
- Portfolio モジュール（銘柄選定〜株数決定までの純粋関数群）
  - kabusys.portfolio.portfolio_builder:
    - select_candidates: スコア降順・タイブレーク条件ありで候補選定。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分（スコア合計が 0 の場合は等分配にフォールバックして警告）。
  - kabusys.portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限のフィルタリング（売却予定銘柄はエクスポージャー計算から除外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear 等のマッピング、未知レジームはフォールバック）。
  - kabusys.portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算、単元株 (lot_size) 丸め、aggregate cap（available_cash に対するスケーリング）と残差の再配分アルゴリズムを実装。
    - cost_buffer を考慮した保守的なコスト見積りとスケーリング処理。
- Research / Factor 計算骨組み
  - kabusys.research.factor_research:
    - Momentum / MA200 / ATR / Volume 等のファクター計算方針、定数（期間定義）、DuckDB 接続を使った設計方針を追加。注: calc_momentum は未完（後述の Known に記載）。
- Tools
  - kabusys.tools.paper_verification_report:
    - Paper Trading の検証レポート生成 CLI。
    - 稼働率（system_status）、注文成功率・送信率（trade_logs）、リスク却下数（risk_logs）、API レイテンシ指標（平均・最大・P95）を集計・出力。
    - 合格基準（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 latency <= 200 ms）を定義し PASS/FAIL 判定を行う。
    - 日付フィルタ（--from / --to）および DB パス指定（--db / 環境変数）に対応。
- パッケージメタ
  - kabusys.__init__.__version__ を "0.1.0" に設定。

Changed
- N/A（初回リリース）

Fixed
- N/A（初回リリース）

Security
- N/A

Removed / Deprecated
- N/A

Notes / 実装上の注記
- run_monitoring と run_execution は起動時に set_process_priority("high") を実行している（権限不足で失敗した場合はログ警告）。
- run_execution は paper_trading 環境で本番 DB と完全分離される設計（settings.paper_sqlite_path を使用）。
- .env 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途など）。
- validate_config は PyYAML 未インストール時に YAML 検証をスキップし警告を出す実装（依存の柔軟性を確保）。
- ログは stdout に出力する設計（cron / scheduler での stdout/stderr リダイレクトを意識）。
- paper_verification_report の P95 計算は単純なパーセンタイルアルゴリズム（並び替え後 index を取る方式）。大規模データでの性能や確定的なパーセンタイル定義に関する確認が必要。

開発者向け推奨事項
- factor_research.calc_momentum の完成と単体テスト追加。
- position_sizing の lot_size 拡張（銘柄毎設定）や価格フォールバックロジックの導入。
- 主要関数群（portfolio / risk / sizing）に対するより多くのユニットテスト（特に aggregate scaling の境界ケース）。
- CI に validate_config のチェックを追加して環境設定ミスを早期検出。

以上。