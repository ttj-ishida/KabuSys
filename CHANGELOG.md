# CHANGELOG

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。セマンティックバージョニングを使用します。

- リリース日や変更は、コードベースから推測して記載しています。
- 小さな実装メモや既知の制約も補足として含めています。

## [Unreleased]

## [0.1.0] - 2026-04-19
初回公開リリース。自動売買システム「KabuSys」のコアユーティリティ、起動スクリプト、ポートフォリオ構築、監視、設定管理、検証ツール、及びペーパートレーディング検証レポート等を実装。

### Added
- 全体
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として追加。
  - DuckDB / SQLite を利用したデータ格納・分析の土台を整備。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV に応じて paper_trading 用 DB（data/paper_trading.db）を使用する仕組みを実装（本番 DB と分離）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler 組立て、エンジンのスレッド実行と停止フラグ（data/stop_requested.flag）による制御を実装。
    - 起動時にプロセス優先度を "high" に設定する処理を導入（utils.process_priority）。
    - PID ファイル (_EXECUTION_PID) 管理（ExecutionEngine に渡す）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用する（監視データは単一 DB に集約）。
    - 停止フラグファイルの検知で安全にループを終了する。

- 設定管理
  - config.py
    - Settings クラスを導入し、環境変数から設定を取り出すユーティリティを提供。
    - .env の自動ロード機能を実装（プロジェクトルート検出：.git または pyproject.toml を基準）。.env と .env.local の取り込みルール（.env.local が上書き）を導入。
    - 自動ロード無効化のための KABUSYS_DISABLE_AUTO_ENV_LOAD 対応。
    - 必須環境変数チェック用の _require()、各種パス、PAPER_FILL_MODE の厳密チェック、環境 (KABUSYS_ENV) とログレベルのバリデーション、is_live/is_paper/is_dev ヘルパーなどを実装。
  - config_setup.py
    - 対話式ウィザードで .env の初期作成／更新を支援する CLI を追加。
    - J-Quants、kabu API、DBパス、LINE 通知設定、ログレベル、Kill Switch の設定項目を実装。
    - 既存 .env 読み込みとマスク表示（シークレット項目）に対応。
  - validate_config.py
    - 起動前に環境変数や config/*.yaml の不備を検出する検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ確認、YAML ファイルの存在およびパース検証（PyYAML がインストールされている場合）、本番環境用の追加ガード（LINE 設定や KILL_FLAG_CLEAR_ON_START）などを実装。
    - --strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順、タイブレーク: signal_rank 昇順）。
    - 重み計算 calc_equal_weights（等金額）および calc_score_weights（スコア加重、全スコアが 0 の場合は等金額へフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中を検出して、既存保有比率が上限を超えているセクターの新規候補を除外するロジック。
      - セクター未登録（"unknown"）は上限適用対象外とする挙動。
      - 当日売却予定銘柄をエクスポージャー計算から除外する機能をサポート。
      - 既知のログ出力・デバッグメッセージを実装。
      - 価格欠損時の注記 TODO を残す（フォールバック価格の検討）。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジームは 1.0 にフォールバックし警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数算出ロジックを実装。
      - リスクベース（risk_pct, stop_loss_pct）、per-position と aggregate cap、lot_size（単元）の丸め、cost_buffer（手数料・スリッページ見積り）を考慮したスケーリングと残余配分。
      - 価格欠損時スキップ、最大保有株数判定、aggregate 超過時の比例スケーリング＋端数補正（lot 単位で残差配分）を実装。
      - 将来的な拡張（銘柄別 lot_size を持たせる TODO）を注記。

- 監視 / モニタリング
  - monitoring モジュール用の DB 初期化呼び出しを起動スクリプトに追加（init_monitoring_db を使用して冪等にテーブル保証）。
  - SystemMonitor 初期化・単回チェック check_once() をポーリングループで定期実行し、例外時はログ記録して再試行（ポーリングまで待機）する堅牢化を実装。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレーディング結果を SQLite から集計し、稼働率、注文成功率、送信率、P95 レイテンシ等を出力するレポート生成ツールを追加。
    - CLI 引数 --from/--to/--db に対応。PAPER_TRADING_SQLITE_PATH 環境変数対応。
    - 指標の閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）による PASS/FAIL 判定を実装。
    - P95 算出、NULL 考慮、テーブル未存在時の耐障害性（OperationalError をキャッチして N/A を扱う）を実装。

- ユーティリティ
  - utils/logging_setup.py
    - 共通ログセットアップ関数 setup_logging を追加。
    - root ロガーを一度クリアしてから StreamHandler（stdout）と TimedRotatingFileHandler（毎日ローテーション、30 日分保持）を設定。
    - ログレベルおよびログディレクトリ解決順を仕様化（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時にファイルハンドラをスキップし、コンソール出力のみで継続。
  - utils/process_priority.py
    - プロセス優先度（Windows の priority class / POSIX の nice）と CPU affinity 設定ユーティリティを実装。
    - クロスプラットフォーム差分を吸収（未対応 OS は警告スキップ）。
    - 権限不足や未実装 API に対して安全にフォールバックし警告出力。

- 研究用モジュール（ドラフト）
  - research/factor_research.py
    - モメンタムや MA200 乖離、ATR、流動性などのファクター計算設計を導入（DuckDB 接続を受けて prices_daily を参照する仕様）。
    - 設計方針コメントと定数（期間等）を実装。関数 calc_momentum の実装開始（ファイル末尾で途中までの状態）。

### Changed
- 該当なし（初回リリースのため新規追加中心）。

### Fixed
- 該当なし（初回リリースのため修正履歴なし）。

### Deprecated
- 該当なし。

### Removed
- 該当なし。

### Notes / Known issues
- apply_sector_cap 内で price_map に欠損（0.0）があるとエクスポージャーが過少見積りになり得る点を TODO として残している（将来的には前日終値などでフォールバック予定）。
- position_sizing は現状すべての銘柄で共通の lot_size を想定している。将来の拡張で銘柄別 lot_size をサポートする予定（TODO 記載あり）。
- research/factor_research.py の calc_momentum 実装はファイル末尾で途中（切れ）になっているため完全実装が必要。
- .env の自動読み込みはプロジェクトルート検出に依存するため、配布後や特殊配置では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って明示的に制御することを推奨。
- ログファイル出力はデフォルトで logs/ に作成するが、ディレクトリ作成に失敗した場合は stdout のみで運用される点に注意。

---

今後は Unreleased セクションに機能追加・バグ修正を継続して記録してください。