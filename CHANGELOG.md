Keep a Changelog
===============

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

※ 以下の変更点はソースコードの内容から推測してまとめたものです。

Unreleased
----------

(現在の開発中の変更点はここに記載します)

0.1.0 - 2026-04-19
------------------

Added
- 基本アプリケーション初期実装
  - パッケージバージョンを `__version__ = "0.1.0"` として導入。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite（data/paper_trading.db）を使用。
    - BrokerClientFactory によるブローカークライアント生成（paper_trading 時は MockBrokerClient を想定）。
    - スレッドで ExecutionEngine を実行し、data/stop_requested.flag の検知で安全に停止。
    - 実行 pid を data/execution.pid に出力する仕組み（pid_file の受け渡し）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。
    - data/stop_requested.flag の検知でループ終了。KeyboardInterrupt に対応。
- 設定管理
  - config.py: 環境変数/.env の自動ロードと Settings クラスを実装。
    - プロジェクトルート検出（.git または pyproject.toml 基準）、自動で .env/.env.local を読み込む（無効化フラグあり）。
    - .env の行パーサは export 形式・クォート・エスケープ・インラインコメントに対応する堅牢な実装。
    - 各種設定プロパティを提供（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視閾値 / ログレベル 等）。
    - 環境変数の妥当性チェック（KABUSYS_ENV, LOG_LEVEL 等）を実装。
- 設定ユーティリティ
  - config_setup.py: 対話式 .env 作成ウィザードを実装。
    - 既存 .env の読み込み、項目ごとの説明・デフォルト値提示、シークレットマスク表示、保存機能を備える。
  - validate_config.py: 起動前の設定検証 CLI を実装。
    - 必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在確認、live 環境に対する追加ガード。
    - --strict オプションで警告を失敗として扱う機能を追加。
    - PyYAML が未インストールの場合は YAML 検証をスキップする挙動。
- 監視・実行周りの初期化
  - monitoring.monitoring_db.init_monitoring_db 呼び出しにより監視用テーブルを冪等に初期化。
  - duckdb の接続を導入（分析用 DB として利用）。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。
    - stdout への StreamHandler と 日次ローテートする TimedRotatingFileHandler（デフォルト logs/<app>.log、30日保持）をルートロガーに設定。
    - 既存ハンドラをクリアして二重設定を防止。ログディレクトリ作成失敗時はファイル出力をスキップする安全設計。
  - utils/process_priority.py: プラットフォーム非依存のプロセス優先度 / CPU affinity 設定を追加。
    - Windows / POSIX（Linux, macOS 等）に対応し、psutil を利用。権限不足時は警告を出してスキップ。
    - set_cpu_affinity により指定コア数への固定が可能。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - 信号から候補選定 (select_candidates)、等分配 (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。
    - スコアが全て 0 の場合は等分配にフォールバックして警告を出す仕様。
  - portfolio/risk_adjustment.py
    - セクター集中制限 (apply_sector_cap)、市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装。
    - 未知のレジームはフォールバック（1.0）し、warning を出力。
  - portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に応じた発注株数計算を実装。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap・cost_buffer を考慮したスケーリング、残差処理の実装あり。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード履歴から検証レポートを生成する CLI を追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定する。
    - デフォルト DB パスは data/paper_trading.db。--from/--to/--db オプションに対応。
    - P95 計算、各種安全な NULL ハンドリング、閾値の定義を含む。
- research
  - research/factor_research.py: ファクター計算用モジュールの骨組みを追加（モメンタム・ボラティリティ等を想定。DuckDB を使用）。一部実装が継続中（ファイル末尾で切れている）。

Changed
- 監視・実行スクリプト共通の振る舞い
  - 起動時にまずプロセス優先度を "high" に設定してからその他初期化を行うように統一。
  - DB 接続後は最後に必ず close() するように設計（finally ブロックで確実にクローズ）。
- ログ出力の統一
  - 全スクリプトで setup_logging() を呼ぶようにしてログのフォーマット・出力先を統一。

Fixed
- 環境変数の不正値に対する堅牢化
  - MONITOR_POLL_INTERVAL が不正（非数値や 0 以下）の場合、警告を出してデフォルト値にフォールバックするように実装。
  - PAPER_FILL_MODE の不正値チェックを追加し、不正な場合は ValueError を発生させ明示する。
- 設定検証の改善
  - validate_config により設定漏れ・推奨値違反（live 環境での注意点）を起動前に検出可能に。

Security
- .env ファイル生成ウィザードで注意喚起を出力（.env を Git にコミットしないよう表示）。

Notes / Implementation details
- stop/kill flag の取り扱い
  - data/stop_requested.flag / data/kill.flag 等のフラグファイルにより外部から停止命令を与えられる運用を想定。config の KILL_FLAG_CLEAR_ON_START オプションにより起動時の自動クリア制御が可能。
- DB 分離
  - 実行（Execution）は paper_trading 時に専用 SQLite を使用して本番データと完全に分離する設計。
  - 監視（Monitoring）は環境にかかわらず監視用 sqlite_path を使用する（監視データの一元化を想定）。
- 外部ライブラリ
  - psutil, duckdb, PyYAML（任意）などを利用。PyYAML がない場合は YAML 内容検証をスキップする。

今後の予定（推測）
- research/factor_research の完全実装（モメンタム / ATR / 流動性等の算出ロジックの完成）。
- ExecutionEngine / BrokerClient の細部実装（実取引インターフェース、Mock の詳細）。
- 単体テスト・統合テストの整備、CI ワークフローへの組み込み。
- 監視アラートの通知機能（LINE など）や configurability の拡充。

----------