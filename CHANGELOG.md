CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています（日本語）。

Unreleased
----------

- なし

0.1.0 - 2026-04-18
------------------

Added
- パッケージ初回リリース: バージョンを __version__ = "0.1.0" として公開。
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine 起動用のエントリポイントを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離して MockBrokerClient を利用する設計を導入。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、デーモンスレッドでの engine.run_session 起動、停止フラグ（data/stop_requested.flag）検知による安全停止を実装。
    - エンジン PID 管理用ファイルの指定に対応（data/execution.pid デフォルト）。
    - DuckDB を分析用に接続。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 以下や非数）はデフォルトにフォールバックして警告を出力。
    - 監視処理は KABUSYS_ENV にかかわらず production の sqlite_path を使用（監視テーブルは常に本番 DB を想定）。
    - 停止フラグ（data/stop_requested.flag）検知、例外発生時のログ出力、KeyboardInterrupt でのグレースフルな終了を実装。
- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して決定）。
    - .env/.env.local の読み込み順序と既存 OS 環境変数保護機能を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - 安全な .env パース機能（export 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理など）を実装。
    - Settings クラスでアプリケーション設定をプロパティとして提供（DB パス、API トークン、LINE 設定、監視閾値、環境種別チェックなど）。不正値時に ValueError を投げるバリデーションを実装。
  - config_setup.py
    - .env を対話式に生成・更新するウィザードを実装。シークレット項目はマスク表示、既存値の読み込み、保存前の確認をサポート。生成時に .env を書き出す際のテンプレートを提供（.env を Git にコミットしない注意書き含む）。
  - validate_config.py
    - 起動前の設定検証 CLI を実装（必須環境変数、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パス、config/*.yaml の存在とパースチェック、live 環境向けガードなど）。
    - --strict オプションで警告を FAIL 扱いにできる。
- Utilities
  - utils/logging_setup.py
    - 統一ログ初期化ユーティリティを実装。stdout 出力（StreamHandler）と日次ローテートのファイル出力（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイルハンドラをスキップして stdout のみで継続。
    - ログレベル・ログディレクトリの解決順（引数 > 環境変数 > デフォルト）に対応。
  - utils/process_priority.py
    - psutil を用いたプロセス優先度設定・CPU affinity 設定ユーティリティを実装。Windows / POSIX (Linux/Mac/FreeBSD) の差分を吸収し、アクセス権限不足や未実装環境では警告ログを出して安全にフォールバック。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等重み（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコアが全て 0 の場合は等重みへフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限適用（apply_sector_cap）を実装。既存保有と当日売却予定を考慮して新規候補をフィルタするロジックを用意。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear をマップ、未知のレジームはフォールバックして警告）。
  - portfolio/position_sizing.py
    - 株数決定ロジック（calc_position_sizes）を実装。risk_based / equal / score の割当方式をサポート。単元（lot_size）丸め、max_position_pct、max_utilization、cost_buffer（手数料/スリッページ見積り）を考慮した aggregate cap スケーリング、残差処理によるロット単位での再配分ロジックを実装。
  - portfolio/__init__.py で上記関数群を公開。
- Research
  - research/factor_research.py（ファクター計算モジュールの骨組み）
    - DuckDB 接続を受け、prices_daily / raw_financials を参照して Momentum / Value / Volatility / Liquidity 等のファクターを計算する方針と定数を定義。モメンタム計算用の関数 calc_momentum の冒頭実装および定数を追加（計算ロジックの続きはファイル末尾で未完）。
- Tools
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを実装。
    - PAPER_TRADING_SQLITE_PATH（または --db オプション）で指定した SQLite から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）などを集計して PASS/FAIL 判定を出力する。
    - P95 計算、期間フィルタ、N/A 表示などを実装。デフォルトしきい値（稼働率 99%、成功率 90% 等）を設定。
- 監視 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を各スクリプトから呼び出して、監視用テーブルが存在することを保証（冪等）。

Changed
- 初回リリースのため該当なし。

Fixed
- .env パースの堅牢化: export 形式対応、引用符内のエスケープ処理、インラインコメント処理などにより .env の読み込みが信頼性向上。
- logging_setup: ログディレクトリ作成に失敗した場合でも stdout のみで継続するフォールバックを追加（起動失敗を避ける改善）。
- process_priority: 未対応 OS や権限不足時に警告を出してスキップするようにして起動の安全性を向上。

Deprecated
- なし

Removed
- なし

Security
- config_setup に .env を絶対に Git にコミットしない旨の注意コメントを追加（.env に API トークン等の機密情報が含まれるため）。
- Settings._require による必須環境変数未設定時の早期検出（ValueError 投出）により、秘密情報未設定での誤動作を防止。

Notes / Migration
- 監視 (run_monitoring) は KABUSYS_ENV に関係なく settings.sqlite_path（デフォルト data/monitoring.db）を使用します。監視 DB を分離したい場合は settings.sqlite_path を環境変数で明示的に上書きしてください。
- 実行 (run_execution) のペーパートレードは専用 DB（PAPER_TRADING_SQLITE_PATH）を使用するため、本番データと混ざることはありません。paper_trading を使用する場合は PAPER_TRADING_SQLITE_PATH を確認してください。
- MONITOR_POLL_INTERVAL に不正な値（文字列、0、負数）を設定した場合、デフォルト 60 秒にフォールバックして警告を出します。

Acknowledgements
- 初回リリースに含まれる多数のユーティリティ、ポートフォリオ構築ロジック、CLI ツールは将来的に拡張・テスト追加を予定しています。