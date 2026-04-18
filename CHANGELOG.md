CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

Unreleased
----------

(なし)

0.1.0 - 2026-04-18
------------------

Added
- 基本機能の初期実装を追加（初回リリース）。
- 実行 / 監視関連エントリポイント
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - デフォルトでプロセス優先度を "high" に設定し、デーモンスレッドでエンジンを実行。data/stop_requested.flag による停止、data/execution.pid への PID 書き込みを想定。
    - init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告出力。
    - 監視は環境にかかわらず production の sqlite_path を使用する仕様（監視は本番情報を参照するため）。
    - 停止フラグ (data/stop_requested.flag) の検出で安全にループ終了。
- 設定管理
  - kabusys.config
    - .env 自動読み込み機能（.env / .env.local）を追加。OS 環境変数は保護される（上書きされない）。
    - .env パーサーは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントをサポート。
    - Settings クラスを提供（各種環境変数アクセスのラッパー）。KABUSYS_ENV / LOG_LEVEL 等の値検証、PAPER_FILL_MODE のバリデーション、paper_sqlite_path / duckdb_path / sqlite_path 等のパスプロパティ、kill/ pid ファイル関連プロパティを実装。
    - settings シングルトンをエクスポート。
- 設定支援 CLI
  - kabusys.validate_config
    - .env / config/*.yaml の起動前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV の整合、DB パスの親ディレクトリ存在チェック、PyYAML がなければ YAML 検証をスキップする旨の警告等。
    - --strict オプションで警告も失敗扱いにできる。
  - kabusys.config_setup
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。シークレット項目はマスク表示、保存前の確認プロンプトあり。
- ツール
  - kabusys.tools.paper_verification_report
    - Paper Trading 用検証レポート生成スクリプトを追加。SQLite（PAPER_TRADING_SQLITE_PATH）から稼働率、注文成功率、送信率、レイテンシ（P95）等を集計し PASS/FAIL 判定を行う。CLI オプション --from / --to / --db に対応。
- ポートフォリオ構築関連（純粋関数群）
  - kabusys.portfolio.portfolio_builder
    - select_candidates: スコア降順で上位 N を選択（タイブレークに signal_rank を使用）。
    - calc_equal_weights, calc_score_weights: 等金額配分およびスコア正規化配分（全スコアが 0 の場合は等配分にフォールバック）。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限による候補除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に基づき投下資金乗数を返す。未知レジームはフォールバックして 1.0。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: allocation_method("risk_based"/"equal"/"score") に従って発注株数を算出。単元（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウン、cost_buffer を用いた保守的見積り、残余キャッシュを用いた再配分ロジックを実装。
- ユーティリティ
  - kabusys.utils.logging_setup
    - setup_logging を追加。ルートロガーを初期化して StreamHandler(stdout) と TimedRotatingFileHandler（日次、30日保持）を追加。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - kabusys.utils.process_priority
    - set_process_priority / set_cpu_affinity を追加。Windows/Linux/macOS を抽象化してプロセス優先度・CPU affinity を設定。psutil ベースでアクセス拒否等は警告でスキップ。
- パッケージ情報
  - __version__ = "0.1.0" を設定。

Changed
- なし（初回リリース）

Fixed
- init_monitoring_db を idempotent に呼び出して監視テーブルの存在を保証するようにした（run_execution/run_monitoring）。
- 各種起動スクリプトで DB 接続を finally ブロックで確実にクローズするよう実装。

Notes
- 実行方法の例:
  - 監視ループ: python -m kabusys.run_monitoring
  - エンジン起動: python -m kabusys.run_execution
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- デフォルトの DB / ログパス等:
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視): data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - ログ: logs/<app_name>.log
- 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

今後の改善候補（未実装／TODO）
- portfolio.position_sizing: 銘柄ごとの lot_size を stocks マスタなどで扱えるよう拡張。
- price フォールバック: apply_sector_cap 等で price が欠損した場合の代替価格取得ロジック。
- research モジュールの各種ファクター計算実装の完了（calc_momentum の続き等）。
- テストカバレッジと CI の整備。

---
上記はコードベースの内容から推測して作成した CHANGELOG です。必要があれば項目の追加・修正（カテゴリ分けや詳細追記）を行います。