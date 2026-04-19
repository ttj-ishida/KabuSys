# CHANGELOG

すべての変更は Keep a Changelog の方針に従って記載しています。  
このファイルはコードベースから推測して作成した変更履歴です。

フォーマット:
- 重要度順: Added / Changed / Fixed / Deprecated / Removed / Security
- 日付はリリース日を示します（推定値）。

## [0.1.0] - 2026-04-11
初回リリース。KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、監視・検証ツール群を含みます。

### Added
- CLI / 起動スクリプト
  - run_execution.py: 実行エンジン起動スクリプトを追加。環境に応じてブローカークライアントを生成し、ExecutionEngine をスレッドで実行。停止フラグ・PID ファイルの取り扱いを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ検知・例外耐性を備える。
  - kabusys.validate_config: .env や config/*.yaml の設定検証 CLI を追加。--strict オプションをサポート。
  - kabusys.config_setup: 対話式の .env 作成/更新ウィザードを追加（各種設定項目の説明・デフォルト値を含む）。
  - kabusys.tools.paper_verification_report: Paper Trading 用検証レポート生成ツールを追加。稼働率、注文成功率、送信率、レイテンシ（P95）等の判定を行う。
- 設定管理
  - kabusys.config: 環境変数読み込み・管理クラスを追加。プロジェクトルート検出による .env / .env.local 自動読み込み（OS 環境変数を保護して上書き制御）。多くの設定プロパティ（DB パス、Paper Trading の DB 切り分け、監視閾値、ログレベル等）を提供。
  - .env ファイルのパースロジック強化: export 形式対応、クォート付き値のエスケープ処理、インラインコメントの扱い等を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを追加。
- ロギング・プロセス制御ユーティリティ
  - kabusys.utils.logging_setup: stdout への StreamHandler と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を整備。LOG_DIR/LOG_LEVEL 解決ルールを実装。
  - kabusys.utils.process_priority: Windows / POSIX の差分を吸収したプロセス優先度設定（high/normal/low）と CPU affinity 設定を追加。アクセス権限がない場合は警告でスキップ。
- ポートフォリオ構築関連（純粋関数群）
  - kabusys.portfolio.portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順選定。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア全0 の場合はフォールバック）。
  - kabusys.portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限の実装（既存保有からセクター別エクスポージャ算出し、新規候補を除外）。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数 (bull/neutral/bear をサポート、未知レジームはフォールバック)。
  - kabusys.portfolio.position_sizing:
    - calc_position_sizes: リスクベース / equal / score ベースの株数算出ロジック。単元（lot）で丸め、max_position_pct や aggregate cap（available_cash）によるスケーリング、残差に基づく再配分アルゴリズムを実装。
- データベース / 分析連携
  - DuckDB 接続サポート（duckdb パスを Settings で管理し、起動時に接続）。
  - 監視 DB（SQLite）初期化ユーティリティを呼び出す仕組みを導入（monitoring テーブルの冪等初期化）。
- 監視・運用性向上
  - 停止フラグ (data/stop_requested.flag / kill.flag) と PID ファイルの取り扱いを標準化（起動スクリプトで利用）。
  - run_execution は paper_trading 環境のときに専用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と完全分離。
- 研究モジュール（骨格）
  - kabusys.research.factor_research: モメンタム・ボラティリティ等ファクター計算のための骨組みを追加（DuckDB 経由で prices_daily / raw_financials を参照する設計）。複数の定数・関数を定義（未完成箇所あり）。

### Changed
- ログ出力の標準化: すべての起動スクリプトが setup_logging を呼び出すことで、コンソールと日次ログファイルへ一貫した出力を行うようにした。
- 環境変数のロード順序: OS 環境 > .env.local > .env（.env.local は .env を上書きする）を明文化し実装。
- モニタリング挙動: Monitoring は環境に関係なく本番 sqlite_path を使用する仕様に明示（run_monitoring）。
- プロセス優先度: 起動時に set_process_priority("high") を呼び出して優先度を上げる（起動直後に実行）。
- run_monitoring の MONITOR_POLL_INTERVAL の不正値取り扱い: 0 以下や非数はデフォルト（60秒）にフォールバックして警告を出すようにした。
- logging_setup: ログディレクトリ作成失敗時はファイルハンドラをスキップして stdout のみで継続する堅牢化を実施。stdout を使用する設計変更（stderr ではなく stdout）。

### Fixed
- run_monitoring: monitor.check_once() 内で例外が発生しても監視ループを継続するように例外捕捉とログ出力を追加。
- config._load_env_file: ファイル読み込み失敗時に警告を出し、プロセスを中断しないよう安全に扱うよう改善。
- process_priority: 未対応 OS や権限エラー時に例外ではなく警告でスキップすることで起動失敗を防止。
- position_sizing: aggregate cap によるスケールダウン後の切り捨て・残差処理で、残余キャッシュに応じて lot 単位で再配分するロジックを追加し、より効率的な配分を実現。

### Deprecated
- なし（初回リリースのため該当なし）。

### Removed
- なし（初回リリースのため該当なし）。

### Security
- なし（明示的なセキュリティ修正は検出できず）。

---

注記（推測）
- 一部のモジュール（例: research.factor_research）は実装途中の箇所があり、今後のリリースで完成・追加テストが想定されます。
- 実行時の具体的な BrokerClient の切り替え（MockBrokerClient の利用など）は BrokerClientFactory に依存しており、この CHANGELOG では high-level な挙動のみを記載しています。
- 日付はコード内のコメント／ヘルプ文を参考に推定しています。