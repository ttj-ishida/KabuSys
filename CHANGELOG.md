CHANGELOG.md
=============

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

Unreleased
----------

- （なし）

0.1.0 - 2026-04-19
------------------

Added
- パッケージ初版リリース。
- コア実行スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV に応じて本番 / ペーパートレード DB を分離（paper_trading 時は PAPER_TRADING_SQLITE_PATH / data/paper_trading.db を使用）。
    - BrokerClientFactory を介して本番ブローカーまたは MockBrokerClient を自動選択。
    - ExecutionEngine を別スレッドで起動し、data/stop_requested.flag による優雅な停止をサポート。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - monitoring は環境にかかわらず本番用 sqlite_path を使用して監視データを記録。
    - data/stop_requested.flag による停止検知、KeyboardInterrupt のハンドリング、例外時のログ出力を実装。
- 設定・環境管理
  - config.py: Settings クラスを導入し、環境変数を型・値チェック付きで提供。
    - 自動 .env ロード機構（.env / .env.local）、プロジェクトルート検出（.git または pyproject.toml 基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - 必須環境変数取得ヘルパー（_require）や各種設定プロパティ（DB パス、PID ファイル、閾値、env/log_level 等）。
    - PAPER_FILL_MODE の検証、paper_sqlite_path などペーパートレード分離設定。
  - config_setup.py: 対話式 .env 作成ウィザード。
    - 初期値・説明付きの質問、既存 .env 読込、保存機能を提供。
  - validate_config.py: 起動前チェック CLI。
    - 必須環境変数、KABUSYS_ENV・LOG_LEVEL の妥当性、DB パス／config/*.yaml の存在と YAML パースチェック（PyYAML が存在する場合）。
    - --strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築ライブラリ（純粋関数群、DB 参照なし）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で選出（タイブレーク: signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全スコア 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（max_sector_pct）、当日売却予定銘柄を除外可能。
    - calc_regime_multiplier: 市場レジームに基づく資金乗数（bull/neutral/bear）と未知レジームのフォールバック挙動。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づいた発注株数計算。
    - 単元株（lot_size）丸め、1銘柄上限・総投資上限（available_cash）に対するスケーリング、cost_buffer（手数料・スリッページ見積）考慮。
    - 安全弁として max_per_stock、aggregate cap と残差処理（fractional remainder による追加配分）を実装。
- ユーティリティ
  - utils.logging_setup: 統一的なログ設定ユーティリティ。
    - stdout 用 StreamHandler と日次ローテーション（TimedRotatingFileHandler）を root ロガーに設定。
    - LOG_LEVEL / LOG_DIR 環境変数、引数による上書き、ログディレクトリ作成失敗時のフォールバック。
  - utils.process_priority: クロスプラットフォームのプロセス優先度 / CPU affinity 設定ユーティリティ。
    - Windows/Linux/macOS を吸収し、権限不足などは警告でスキップ。
    - set_process_priority(level)、set_cpu_affinity(cpu_count) を提供。
- ツール
  - tools.paper_verification_report: ペーパートレード検証レポート生成 CLI。
    - system_status / trade_logs / risk_logs テーブルから稼働率・注文成功率・送信率・レイテンシ等を集計。
    - P95 計算、閾値に基づく PASS/FAIL 判定（閾値はソース内で定義: 稼働率 99%、成立率 90% など）。
    - --from/--to/--db オプションで期間・DB を指定可能。PAPER_TRADING_SQLITE_PATH 環境変数対応。
- 監視 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を起動パスから呼び出し、監視用テーブルの存在を保証（冪等）。
- その他
  - パッケージメタ情報: __version__ = "0.1.0"
  - research.factor_research モジュールを追加（ファクター計算用、DuckDB を想定）。一部計算定数・calc_momentum の雛形を含む（今後拡張予定）。

Known issues / Notes
- research/factor_research.py はファクター計算の骨格を実装済みですが、いくつかの関数実装は今後の拡張対象です（データスキャン範囲や欠損処理など）。
- process_priority/set_cpu_affinity は権限や OS 実装差分により効果が制限される場合があり、その際は警告ログによりスキップします。
- .env の自動読み込みはプロジェクトルートの検出に依存します。配布後や特異なディレクトリ構成の場合、KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効化してください。
- Logging のファイルハンドラはログディレクトリ作成に失敗した場合はコンソールのみで動作します。

セキュリティ
- .env ファイルには機密情報を含めるため、README 等で .env を Git 管理に含めないことを強く推奨しています（config_setup.py にも同旨のコメントを記載）。

参考: 実行・運用メモ
- ペーパートレード:
  - KABUSYS_ENV=paper_trading を設定すると、run_execution は paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。
  - PAPER_FILL_MODE（instant/partial/never/reject）で MockBrokerClient の約定振る舞いを制御できます。
- 停止制御:
  - data/stop_requested.flag（プロジェクトルート配下の data/ ディレクトリ）を作成すると run_* スクリプトが検知して優雅に停止します。
- 設定検証:
  - python -m kabusys.validate_config で起動前チェックが可能。--strict を付けると警告も失敗扱いになります。

--- 

（今後のリリースでは、Strategy・Execution 各コンポーネントの詳細実装、ファクター計算の充実、テストカバレッジの拡充、ドキュメント追加を予定しています。）