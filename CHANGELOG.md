# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
言語: 日本語

全般
- バージョン: 0.1.0
- 説明: KabuSys の初期実装。監視・実行ランナー、設定管理、ポートフォリオ構築、リスク調整、ポジションサイジング、ユーティリティ群、検証用ツールなど、主要機能を含む最初のリリースです。

Unreleased
- （なし）

v0.1.0 - 2026-04-19
- Added
  - 実行・監視ランナー
    - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV が `paper_trading` のときは MockBrokerClient を使用し、ペーパートレード用の専用 SQLite DB（data/paper_trading.db、環境変数で上書き可）を利用する挙動を実装。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番用の sqlite_path を使用する設計。
    - 両スクリプトに「停止フラグ」ファイル検知処理を実装（data/stop_requested.flag）。Execution は停止時にエンジン stop() を呼び、Monitoring はループを抜けて終了する。
    - run_execution は実行プロセス用 PID ファイルの取り扱いを行う（data/execution.pid を想定）。

  - 設定・環境変数管理
    - config.py: Settings クラスを導入。.env 自動読み込み（プロジェクトルート検出機能に基づく）を実装。多くの設定プロパティを提供（J-Quants、kabu API、LINE、DB パス、監視閾値、環境種別判定等）。
    - .env パーサーは export 句、クォート文字列、エスケープ、インラインコメント（一定条件下）に対応。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、KILL_FLAG_CLEAR_ON_START 等の環境変数をサポートし、一定の検証（有効値チェック）を実施。

  - 設定操作用 CLI / 検証ツール
    - config_setup.py: インタラクティブな環境設定ウィザードを追加。.env の初期生成 / 更新を支援する。シークレット項目はマスク表示。
    - validate_config.py: 起動前に .env および config/*.yaml の設定不備を検出する CLI を追加。必須環境変数チェック、KABUSYS_ENV と LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、YAML ファイルの存在と（PyYAML があれば）構文検証、live 環境向けの追加ガードを実装。--strict オプションをサポート（警告を FAIL 扱いにする）。

  - ロギング・プロセス制御ユーティリティ
    - utils/logging_setup.py: 統一的なロギング設定を提供する setup_logging() を追加。Console (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。LOG_DIR/LOG_LEVEL の解決とエラー耐性を実装。
    - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加。`set_process_priority("high"|"normal"|"low")` と `set_cpu_affinity()` を提供。Windows と POSIX(nice) を考慮、権限不足等の失敗は警告でスキップする。

  - ポートフォリオ構築ライブラリ（純粋関数群）
    - portfolio/portfolio_builder.py: 候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重 calc_score_weights を追加。スコアが全て 0 の場合のフォールバック動作をログ出力。
    - portfolio/risk_adjustment.py: セクター集中上限を適用する apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を追加。未知レジームはフォールバックして 1.0 とし警告を出す。
    - portfolio/position_sizing.py: allocation_method（"risk_based" / "equal" / "score"）に基づき発注株数を計算する calc_position_sizes を実装。単元株（lot_size）、コストバッファ、per-stock と aggregate cap、スケールダウン・端数配分ロジックなどを含む。価格欠損時のスキップや上限チェックを行う。

  - ペーパートレード検証ツール
    - tools/paper_verification_report.py: ペーパートレード用 SQLite DB から検証レポートを生成する CLI を追加。日付フィルタ（--from/--to）、DB パスの指定（--db または環境変数 PAPER_TRADING_SQLITE_PATH）をサポート。稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ等を集計し、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を行う。P95 計算、欠損テーブルへの耐性も実装。

  - 研究用ファクター計算（初期）
    - research/factor_research.py: DuckDB を用いたファクター計算モジュールの追加（モメンタム・MA・ATR・流動性等を設計）。calc_momentum 等の実装方針と定数群を導入（ファイルは継続実装予定、設計に沿った関数シグネチャを提供）。

  - パッケージメタ
    - __init__.py にバージョン情報 __version__ = "0.1.0" を追加。

- Changed
  - なし（初期リリース）

- Fixed
  - なし（初期リリース）

- Security
  - 設定ファイル (.env) に関する注意喚起を config_setup のヘッダに明記（.env を Git にコミットしないこと）。

補足（実装上の挙動／設計上のポイント）
- ロギングは標準エラーではなく stdout に出力する設計（cron / Task Scheduler 等で stdout/stderr を一本化して扱う運用を想定）。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行い、OS 環境変数が既に設定されているキーは上書きされない（.env.local は上書き可能）。テスト等で無効化できる KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。
- run_monitoring は監視 DB 初期化（init_monitoring_db）を行い、DuckDB も利用して分析用の接続を確立する。monitor.check_once() 呼び出しで例外を捕捉・ログ出力し、継続稼働を保証する。
- run_execution は BrokerClientFactory を用いてブローカークライアントを生成し、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立ててバックグラウンドスレッドでセッションを実行する。停止フラグで安全に停止する仕組みを持つ。
- position_sizing の aggregate キャップ処理は可用現金に応じたスケーリングと、lot_size 単位での端数再配分を提供する。cost_buffer により手数料やスリッページを保守的に見積もることが可能。

今後の予定（短期）
- research/factor_research の関数群の完成（ファクター算出ロジックの SQL/Python 実装完了）。
- ExecutionEngine / Monitoring の統合テスト強化、及びドキュメント追加（運用手順・デプロイ手順）。
- 追加の運用モニタリング・アラート（LINE 通知周りの拡充）、および BrokerClient の実装・テスト。

---  
この CHANGELOG はソースコードから推測して作成されています。実際のリリース日・変更者情報等が必要な場合は追記してください。