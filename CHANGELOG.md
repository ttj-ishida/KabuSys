# CHANGELOG

この CHANGELOG はコードベースの内容から推測して作成した変更履歴です。実際のコミット履歴ではなく、ソースコードの機能追加・振る舞いに基づく要約です。

フォーマットは「Keep a Changelog」準拠です。

Unreleased
----------
- ドキュメント化されている既知の制約・TODO を追加
  - position_sizing の lot_size 将来的拡張、price のフォールバック処理など、いくつかの TODO コメントが存在するため将来的な改良が想定される。
  - research/factor_research モジュールは途中（calc_momentum の実装が途中で切れているため）であり、完成・テストが必要。

0.1.0 - 2026-04-22
-----------------
Added
- 基本アプリケーションエントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用 MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db）に記録して本番 DB と分離して動作する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用する設計。
- 設定・環境管理
  - config.py:
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml を基準）。
    - .env の行パースはクォート・エスケープ・インラインコメントを考慮する堅牢な実装。
    - Settings クラスを導入し、各種環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABUSYS_ENV、データベースパス、監視閾値 等）をプロパティとして提供。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH などペーパートレード向け設定を追加。
- 設定ユーティリティ
  - config_setup.py: 対話式 .env 作成ウィザードを追加。既存 .env 読込、シークレットマスク、デフォルト提示、確認後書き込みを行う。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数・パス存在・YAML ファイルの簡易パース等をチェック。--strict オプションで警告を FAIL 扱いにできる。
- 実行ロジック（Execution）
  - execution パッケージ（コード上の参照による）：BrokerClientFactory によるブローカークライアント選択、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てと起動制御（PID ファイル、停止フラグ対応）を実装。
  - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）をコード内で定義。
- 監視（Monitoring）
  - monitoring 方面の DB 初期化（init_monitoring_db）や SystemMonitor の一回チェック（check_once）呼び出し周りを統合。停止フラグファイルにより安全にループを終了可能。
- ポートフォリオ構築（Portfolio）
  - portfolio モジュールを追加（純粋関数群、DB 参照なし）。
    - portfolio_builder: select_candidates（スコア降順選抜）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等重にフォールバック）。
    - risk_adjustment: apply_sector_cap（セクター集中上限に基づく候補除外）、calc_regime_multiplier（market regime に応じた資金乗数）。
    - position_sizing: calc_position_sizes（risk_based / equal / score の配分法、単元株丸め、aggregate cap スケーリング、cost_buffer による保守見積り）。
  - portfolio パッケージの __all__ を用いた明示的エクスポート。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py:
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30 日保持）をルートロガーに設定する共通セットアップを提供。LOG_DIR / LOG_LEVEL 環境変数や引数で上書き可。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続する耐障害性を備える。
  - utils/process_priority.py:
    - set_process_priority: Windows と POSIX（Linux, Darwin, FreeBSD）を吸収するプロセス優先度設定。psutil を利用し権限不足等の例外は警告によりスキップする。
    - set_cpu_affinity: 指定コア数に CPU affinity を設定するユーティリティ（存在しない OS/権限エラーは警告でスキップ）。
- ツール
  - tools/paper_verification_report.py:
    - ペーパートレード用 SQLite を解析し、システム稼働率・注文成立率・送信率・レイテンシ（平均/最大/P95）・リスク却下数を集計してレポート出力する CLI を追加。閾値に基づく PASS/FAIL 判定を行う。--from / --to / --db オプションをサポート。
    - P95 計算・欠損データハンドリングを実装。
- リサーチ（Research）
  - research/factor_research.py: ファクター計算モジュールの骨格（Momentum, Value, Volatility, Liquidity 指標の設計、DuckDB 接続受け取りの方針、calc_momentum の開始）を追加。DuckDB の prices_daily / raw_financials を参照して定量ファクターを返す設計。
- パッケージ情報
  - kabusys/__init__.py にバージョン __version__ = "0.1.0" を追加。

Changed
- なし（初期リリース相当のため新規追加中心）

Fixed
- なし（初期リリース）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / 既知の制約・今後の改善点
- research/factor_research.calc_momentum の実装が途中で切れている（ソースから推測）。完全な実装とテストが必要。
- position_sizing のコメントにある通り、将来的には銘柄別の lot_size をサポートするための拡張を検討すべき。
- apply_sector_cap は price_map に価格が欠損（0.0）だとエクスポージャーが過少見積りされる可能性がある。前日終値等のフォールバックを追加することが望まれる。
- .env 自動読み込みはプロジェクトルート検出に依存するため、配布後にプロジェクトルートが見つからないケースでは自動ロードがスキップされる挙動に注意。
- process_priority / set_cpu_affinity は権限不足や OS 非対応時に動作制限されるが、安全にスキップされるよう実装されている。

以上。