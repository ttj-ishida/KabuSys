# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。  
詳細な実装はソースコードを参照してください。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-17

初回リリース。以下の主要機能・ユーティリティを追加しました。

### Added
- 基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 設定管理
  - 環境変数 / .env の自動読み込み機構を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可）。
  - .env の読み取り/パース処理を堅牢化（export 形式対応、クォートとエスケープ対応、インラインコメント処理など）。
  - Settings クラスを実装し、環境変数をプロパティで提供（J-Quants / kabu API / LINE / DB / 監視閾値 / システム設定等）。
  - `PAPER_FILL_MODE` の値検証、`PAPER_TRADING_SQLITE_PATH`（paper trading 用 DB パス）、各種しきい値（CPU/メモリ/ディスク）等を追加。

- CLI 補助ツール
  - config_setup: 対話式ウィザードで .env を作成・更新する CLI を追加（.env のテンプレート出力・既存値再利用・秘密値マスク表示）。
  - validate_config: .env と config/*.yaml の基本検証を行う CLI を追加。必須環境変数チェック、KABUSYS_ENV の妥当性、パス存在確認、YAML パース（PyYAML があれば）など。`--strict` オプションで警告を失敗扱いにできる。

- 実行・監視スクリプト
  - run_execution: ExecutionEngine の起動用スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合、paper_trading 専用の SQLite（`PAPER_TRADING_SQLITE_PATH`）を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine 起動処理を実装。
    - RiskConfig のデフォルト値を設定（max_position_pct, max_utilization, rate_limit_per_sec 等）し、初期ポートフォリオ値を broker.get_available_cash() から取得。
    - stop フラグ（data/stop_requested.flag）や pid ファイルの扱い、スレッドでのエンジン実行および停止処理を実装。
    - 起動時に監視テーブルの存在を保証するため init_monitoring_db を呼び出す。

  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告してデフォルトにフォールバック。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する（監視データは共通で管理）。
    - stop フラグの検出と安全なループ終了処理、例外発生時のログと継続ポリシーを実装。

- 監視 DB 初期化
  - init_monitoring_db 呼び出しを実行・監視双方で行い、監視テーブルの存在を冪等的に保証する仕組みを導入。

- ユーティリティ
  - process_priority: クロスプラットフォーム（Windows / POSIX 系）でプロセス優先度を設定するユーティリティを追加（set_process_priority）。権限不足や未対応 OS では安全にスキップされログ出力。
  - 同梱で CPU 固定用の set_cpu_affinity 関数（最初の N コアに固定）を追加。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分を実装。スコア合計が 0 の場合は等配分へフォールバック。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限を適用して候補をフィルタリング（unknown セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear）を返す。未知レジームは警告して 1.0 をフォールバック。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数決定ロジックを実装。lot_size（単元）丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap スケーリング、残差処理ロジックを実装。

- リサーチ（ファクター計算）
  - factor_research:
    - calc_momentum: DuckDB の prices_daily を用いたモメンタム指標（1M/3M/6M リターン、MA200 乖離）を実装。データ不足時の None 処理あり。
    - calc_volatility: ATR・平均売買代金・出来高比率などのボラティリティ／流動性指標を計算するための基盤を追加（実装は続く形）。
    - DuckDB 接続を用いた SQL ベースの高速計算を想定。

- ツール
  - paper_verification_report: paper trading 用 SQLite（デフォルト data/paper_trading.db）から検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等。
    - しきい値を定義（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200 ms）して PASS/FAIL を判定。
    - 日付フィルタ（--from / --to）と DB パス指定（--db / 環境変数）に対応。
    - DB にテーブルが無い場合のフォールバック処理（OperationalError の捕捉）。

### Changed
- （初回リリースのためなし）

### Fixed
- （初回リリースのためなし）

### Security
- .env を生成する README/テンプレートに「.env は絶対に Git にコミットしないこと」を明記（config_setup にて出力）。

### Notes / Implementation details / 動作上の注意
- run_execution:
  - paper_trading 環境では paper_trading 用 SQLite を使用して本番データと切り離す設計になっているため、実運用時に DB パス設定を確認してください。
  - ExecutionEngine 起動前に停止フラグが既に存在する場合は起動せず終了します。
- run_monitoring:
  - 監視は常に本番 sqlite_path を参照する設計です（KABUSYS_ENV に依存しない）。
  - MONITOR_POLL_INTERVAL に不正な値（0 以下や非数）を指定するとデフォルト（60 秒）にフォールバックし警告を出力します。
- process_priority / set_cpu_affinity:
  - 権限やプラットフォームにより処理がスキップされる場合があります（ログで通知）。
- factor_research は DuckDB のテーブル構成（prices_daily / raw_financials）に依存します。DuckDB ファイルパスは Settings.duckdb_path で指定します。
- validate_config は PyYAML が入っていない場合、YAML の内容チェックをスキップして警告を出力します。

---

参考: Keep a Changelog — https://keepachangelog.com/en/1.0.0/