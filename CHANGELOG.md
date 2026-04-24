CHANGELOG
=========

このファイルは Keep a Changelog 準拠で記述しています。
セマンティックバージョニングに従います: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（現在のスナップショットに基づく未リリースの変更はありません）

0.1.0 - YYYY-MM-DD
------------------
初期リリース（コードベースのスナップショットに基づく機能一覧と変更点）

Added
- 環境・設定管理
  - .env の自動読み込み（プロジェクトルートの検出: .git または pyproject.toml を基準）を実装。
  - .env のパース機能を提供（export 形式、クォート、インラインコメントの扱いに対応）。
  - Settings クラスを実装し、環境変数からアプリ設定を一元取得。必須値の検査、列挙値チェック、デフォルト値の解決を含む。
  - KILL_FLAG_CLEAR_ON_START, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等の設定キーをサポート。

- CLI ツール
  - config_setup: 対話式ウィザードで .env の初期作成・更新を支援（シークレット入力、選択肢、デフォルト、保存確認）。
  - validate_config: .env と config/*.yaml の事前検証ツール（--strict で警告を FAIL 扱いに可能）。必須環境変数チェック、パス存在チェック、PyYAML が無い場合のフォールバック等を実装。

- 実行スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - プロセス優先度を "high" に設定（起動直後）。
    - 環境に応じて paper_trading 用の専用 SQLite を使用し本番 DB と分離（KABUSYS_ENV=paper_trading 時）。
    - BrokerClientFactory を介したブローカークライアント生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立てとセッション実行ループ、stop フラグ/ pid ファイルの扱いを実装。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値時のフォールバック）。
    - Monitoring は環境に依らず本番 sqlite_path を使用（監視データの一元化）。
    - 停止フラグによる優雅な終了、チェック中の例外をログ出力して次のポーリングに継続。

- ロギング・プロセスユーティリティ
  - logging_setup: StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定するユーティリティを追加。ログディレクトリ作成失敗時はコンソールのみで継続。
  - process_priority: Windows / POSIX の差を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。CPU affinity 設定機能も提供。権限不足時は警告を出してスキップ。

- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio_builder:
    - select_candidates: BUY シグナルのスコアで上位 N 件選定。
    - calc_equal_weights / calc_score_weights: 等金額およびスコア加重配分（全スコア0 の場合は等分にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中を抑制する候補フィルタ（既存保有を考慮、"unknown" セクターは除外しない）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を計算（未知レジームはフォールバック1.0）。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数算出。損切り率・リスク率・単元株（lot_size）・max_position_pct・max_utilization・cost_buffer を考慮した aggregate cap のスケーリング処理を実装。

- データ分析・検証ツール
  - tools/paper_verification_report:
    - Paper Trading 検証レポート生成 CLI を追加。system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）を算出し、閾値による PASS/FAIL 判定を行う。
    - P95 計算ロジック、期間フィルタ、DB パス引数（または環境変数）をサポート。デフォルト閾値を定義（稼働率 99%, 成立率 90% 等）。

- データ処理（研究モジュール）
  - research/factor_research: DuckDB 接続を用いたモメンタム等ファクター計算モジュールの実装を開始。モジュール設計（1M/3M/6M リターン、MA200 乖離、ATR、出来高系指標）と calc_momentum の骨組みを含む（計算ロジック途中まで実装）。

- パッケージおよびエクスポート
  - kabusys.__version__ = "0.1.0"
  - kabusys.portfolio から主要関数をエクスポートする __all__ を定義。

Fixed
- run_monitoring の MONITOR_POLL_INTERVAL が 0 以下や非整数のときに time.sleep で ValueError にならないよう、バリデーションとフォールバックを追加。
- logging_setup: 既存ハンドラがある場合に一度閉じてから再設定することで二重出力を防止。

Changed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

Notes / Known issues / TODOs
- risk_adjustment.apply_sector_cap:
  - price_map に価格がない（0.0）の場合、エクスポージャーが過少見積りされブロックが外れる恐れがある。将来的に前日終値等でフォールバックする案あり（TODO コメントあり）。
- position_sizing:
  - 銘柄ごとの lot_size を将来的にサポートする予定（現状は全銘柄共通で引数 lot_size を使用）。
- research/factor_research:
  - ファイルの最後で calc_momentum の実装が途中で切れている（スナップショットのため未完）。このモジュールの完成と単体テストの追加が必要。
- run_monitoring, run_execution:
  - 停止フラグ・pid ファイル・kill flag 関連の挙動は実運用で検証が必要（特に本番 env=live 時の取り扱い）。
- 環境変数自動ロード:
  - プロジェクトルートが特定できない場合は自動ロードをスキップするため、配布先での動作確認を推奨。

Developers
- 各 CLI / スクリプトは setup_logging を最初に呼び出して統一的なログ管理を行っています。ログ出力はデフォルトで stdout と logs/<app>.log（日次ローテート）に出力されます。
- process_priority, set_cpu_affinity は権限や OS に依存するため、CI や権限の低い環境では警告をログ出力してスキップします。

お問い合わせ・貢献
- バグ報告、要望、パッチはリポジトリの Issue / Pull Request をご利用ください。

--- End of CHANGELOG ---