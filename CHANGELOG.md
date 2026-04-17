# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。以下はリポジトリ内のコードから推測して作成した初期リリースの変更履歴です（推測に基づく記述を含みます）。

## [0.1.0] - 2026-04-17

### Added
- 初期リリース。KabuSys の基盤機能を追加。
- 実行エントリ / デーモン制御
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）を監視して安全に停止。
    - 監視は環境設定にかかわらず本番用の SQLite パスを使用するよう実装。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority を使用）。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は Paper Trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離（MockBrokerClient 想定）。
    - 実行中の PID をファイルに記録する（data/execution.pid の使用を想定）。
    - 停止フラグ検知でエンジンを安全に停止。
    - 起動時にプロセス優先度を "high" に設定。

- 設定・環境管理
  - config.py
    - .env の自動読み込み機能を実装（プロジェクトルートの .env / .env.local を読み込み、OS 環境変数は保護）。
    - .env パーサを実装（クォート、エスケープ、コメント処理に対応）。
    - Settings クラスを追加し、アプリケーション設定をプロパティ経由で取得（J-Quants / kabu API / DB パス / モニタ閾値等）。
    - 設定値検証（`KABUSYS_ENV`, `LOG_LEVEL`, `PAPER_FILL_MODE` などの妥当性チェック）を実装。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加（項目のマスク表示、デフォルトの提示、保存確認）。
  - validate_config.py
    - 起動前に .env と config/*.yaml をチェックする CLI を追加。
    - 必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL の妥当性検証、DB パス親ディレクトリ存在警告、PyYAML が無い場合の YAML 検証スキップ、`--strict` オプションによる警告を FAIL 扱いにするモード等。

- モニタリング / DB 初期化
  - 各起動スクリプトで監視用テーブルの初期化を行う（init_monitoring_db を呼び出し、冪等に監視テーブルを保証）。

- Execution 周辺コンポーネント（推測）
  - BrokerClientFactory により実行環境に応じた BrokerClient（実ブローカー or Mock など）を生成。
  - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine といった実行パイプラインコンポーネントの組み立てロジックを反映（RiskManager のデフォルト設定値をコードに含む）。

- ポートフォリオ構築（純関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順、同点は signal_rank でタイブレーク。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分、全スコアが 0 の場合は等金額にフォールバックして警告を出力。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限に基づき候補を除外（"unknown" セクターは上限適用外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（"bull"/"neutral"/"bear" マップ、未知レジームは 1.0 でフォールバック・警告）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based"/"equal"/"score"）に基づく株数決定ロジック。
    - 単元株（lot_size）丸め、per-stock 上限（max_position_pct）、aggregate cap によるスケーリング、cost_buffer（手数料/スリッページ考慮）等を実装。
    - 価格欠損時のスキップやログ出力、スケールダウン時の残差処理（lot_size 単位での追加配分）を実装。

- リサーチ / ファクター計算
  - research.factor_research
    - DuckDB を用いたファクター計算（momentum: 1M/3M/6M リターン、MA200 乖離、volatility: ATR20、流動性指標 等）。
    - prices_daily テーブル参照、計算用のウィンドウ定数を定義。

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level) を実装（Windows と POSIX（Linux/Mac/FreeBSD）を吸収）。
    - set_cpu_affinity(cpu_count) によりプロセス CPU affinity を設定（権限不足や未実装環境では警告を出してスキップ）。
    - 例外時に安全にフォールバックする実装。

- ツール
  - tools.paper_verification_report
    - ペーパートレード履歴 DB から検証レポートを生成する CLI を追加。
    - 稼働率、注文成功率（Fill）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）を集計し PASS/FAIL 判定する仕様。
    - デフォルトしきい値（稼働率 99%、Fill 90% など）を定義。
    - 日付フィルタ、DB パス指定オプションを提供。

### Changed
- 初回リリースのため該当なし（このバージョンで導入された機能を列挙）。

### Fixed
- 初回リリースのため該当なし（既存バグ修正はなし）。

### Notes / Migration
- .env は自動読み込みされる（プロジェクトルートに .env/.env.local が存在する場合）。OS 環境変数は優先され上書きされない（.env.local は上書き可能だが OS 環境変数は保護される）。
- 本番運用時は KABUSYS_ENV を適切に設定し、特に `KABUSYS_ENV=live` の場合は LINE 通知設定等を確認すること（validate_config のワーニング参照）。
- .env ファイルは機密情報を含むため絶対にリポジトリにコミットしないこと（config_setup のヘッダにも注意書きあり）。
- Settings のプロパティは必須環境変数が未設定だと ValueError を発生させるため、運用環境では必ず validate_config を実行して検証することを推奨。

（注）本 CHANGELOG は提供されたソースコードの内容から機能・挙動を推測して作成したものです。実際のリリースノートや運用手順はリポジトリのドキュメントや正式なリリース管理に従ってください。