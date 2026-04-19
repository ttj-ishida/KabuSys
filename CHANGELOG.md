# Changelog

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
フォーマット: 比較的最近のリリースを上から記載します。

## [0.1.0] - 2026-04-19

初回公開リリース。システム全体の起動スクリプト、設定管理、モジュール群（ポートフォリオ構築、ポジションサイジング、リスク調整、リサーチユーティリティ）、ユーティリティ類、および運用・検証ツールを実装しました。

### Added
- 汎用設定管理
  - kabusys.config.Settings クラスを追加。環境変数 / .env ファイルから各種設定を読み取り、型変換・妥当性チェックを行う。
  - プロジェクトルートを .git / pyproject.toml から自動検出し、自動的に .env / .env.local をロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パース機能はシングル/ダブルクォート、export 形式、インラインコメントなどに対応。
  - settings（モジュールレベルの Settings インスタンス）を提供。

- 環境設定ウィザード
  - kabusys.config_setup: 対話式ウィザードで .env を新規作成／更新する CLI を追加。
  - デフォルト項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL など）を用意。
  - シークレット入力のマスクや既存 .env 読み込みをサポート。

- 起動スクリプト
  - run_execution: ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV=paper_trading の際は paper_trading 用の SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory により本番/モックブローカーを選択。
    - プロセス優先度を起動時に設定（high）。
    - 実行はバックグラウンドスレッドで行い、 data/stop_requested.flag による外部停止制御をサポート。
    - order_repository, order_manager, risk_manager, reconciler 等の組み立てを行う。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境にかかわらず settings.sqlite_path（本番 sqlite_path）を使用して監視 DB を初期化。
    - 停止フラグ検知（data/stop_requested.flag）でループ終了、KeyboardInterrupt にも対応。

- 監視 DB 初期化フック
  - monitoring.monitoring_db:init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等に初期化）。

- ロギングユーティリティ
  - utils.logging_setup.setup_logging を追加（全起動スクリプトで共通利用）。
    - stdout 出力用 StreamHandler と、日次ローテート（TimedRotatingFileHandler）を用いたファイル出力を設定。
    - ログディレクトリは引数、環境変数 LOG_DIR、デフォルト logs/ の順で解決。ディレクトリ作成に失敗した場合はファイル出力を無効化して stdout のみで継続。
    - 既存ハンドラの重複登録防止（既存ハンドラは一旦 close/remove する）。
    - ログレベル解決: 引数 > LOG_LEVEL 環境変数 > デフォルト INFO。

- プロセス優先度 / CPU アフィニティ
  - utils.process_priority.set_process_priority: Windows / POSIX を吸収して現在プロセスの優先度を設定（high/normal/low）。
  - utils.process_priority.set_cpu_affinity: プロセスを最初の N コアにピンニングするユーティリティを追加。
  - 権限不足や未サポート環境ではワーニングを出して安全にスキップする実装。

- ポートフォリオ構築ライブラリ
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのスコア降順選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率配分（全スコアが 0 の場合は等金額にフォールバックして警告）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限に基づき候補を除外するフィルタリング。
      - sell_codes を除外してエクスポージャー計算が可能。
      - "unknown" セクターは上限を適用しない。
      - 実運用上の注意点として price の欠損時にエクスポージャーを過小評価する可能性がある点を TODO コメントで明記。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供。未知レジームは 1.0 でフォールバック（警告）。
  - portfolio.position_sizing
    - calc_position_sizes: 複数の配分方式（risk_based / equal / score）に対応した株数計算ロジックを実装。
      - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）によるスケーリング、および残余キャッシュを用いた端数配分のロジックを実装。
      - コストバッファ（手数料/スリッページ見積）を考慮した保守的見積りをサポート。
      - TODO: 将来的に銘柄別の lot_size を利用できるよう拡張予定（stocks マスタ参照）。

- リサーチ / ファクター計算（下地）
  - research.factor_research にモメンタム等のファクター計算モジュールを追加（設計コメント、定数、calc_momentum の雛形を含む）。DuckDB の prices_daily / raw_financials テーブルを参照する設計。注: calc_momentum はソース上で途中まで実装（初期実装/ワーキングドラフト）。

- 運用ツール
  - tools.paper_verification_report: Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から検証レポートを生成するスクリプトを追加。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）などの指標を計算してレポート出力。
    - 判定用閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。
    - 日付フィルタ（--from / --to）、--db オプションで DB パスを指定可能。
    - DB のテーブルが存在しない場合でも安全に N/A を返す実装を行い、sqlite3.OperationalError をハンドリング。

- 設定検証 CLI
  - validate_config: .env と config/*.yaml の存在・基本妥当性をチェックする CLI を追加。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。
    - KABUSYS_ENV / LOG_LEVEL の値検証、DB パスの親ディレクトリ存在チェック、YAML パースチェック（PyYAML があれば安全にパース）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict で警告も失敗扱いにできる。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Deprecated
- なし（初回リリース）

### Removed
- なし（初回リリース）

### Security
- なし（初回リリース）

### Notes / Known issues / TODO
- research.factor_research.calc_momentum はソース上で途中まで（start_da で切れているなど）であり、完全実装は今後の作業。現在は設計骨子と定数群、関数仕様を提供。
- portfolio.risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性があるため、将来的に前日終値や取得原価でのフォールバックを検討する必要あり（TODO）。
- portfolio.position_sizing:
  - 単元株数は現状グローバルな lot_size パラメータで処理。将来的に銘柄別の lot_map を受け取る拡張を予定（TODO）。
- run_monitoring は監視用途の SQLite パスに settings.sqlite_path（本番の設定）を常に使用する設計。必要に応じて環境的な分離が求められる場合は実装見直しの検討を推奨。

---

今後の予定:
- research モジュールの完全実装（ファクター計算の完成、標準化ユーティリティ連携）
- ExecutionEngine / SystemMonitor 周りの統合テストと稼働テスト
- 単体テスト・CI の整備およびドキュメント追加（運用手順、データベースマイグレーション等）

もし特定の変更点をより詳細に記載してほしい箇所があれば教えてください。