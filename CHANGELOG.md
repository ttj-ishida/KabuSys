# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
このプロジェクトの初回リリースとして、以下の内容を 0.1.0 として記録します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-17

### Added
- 基本パッケージとバージョン
  - パッケージ初期化: kabusys.__version__ = 0.1.0。

- 設定管理
  - kabusys.config: 環境変数/.env を読み込む Settings クラスを追加。
    - プロジェクトルートを .git または pyproject.toml から自動探索して .env 自動読み込みを実施（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント対応など堅牢に処理。
    - Settings 経由で J-Quants / kabuAPI / DB パス / PID/kill フラグパス /閾値等の設定を取得でき、妥当性チェック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を行う。
    - デフォルトのパス: DuckDB `data/kabusys.duckdb`、SQLite `data/monitoring.db`（paper_trading 時は `data/paper_trading.db` を利用）。

- 設定操作用 CLI
  - kabusys.config_setup: 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
    - J-Quants トークン、kabu API パスワード、DB パス、実行環境など主要項目を対話的に設定・保存。
  - kabusys.validate_config: 起動前検証 CLI を追加。
    - 必須環境変数の存在確認、KABUSYS_ENV や LOG_LEVEL の妥当性、DB パス親ディレクトリの存在、config/*.yaml の存在・パース（PyYAML インストール時）等をチェック。
    - --strict オプションで警告を FAIL 扱いにできる。

- 実行 & 監視ランナー
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定（utils/process_priority を使用）。
    - 環境が `paper_trading` の場合は Paper Trading 用の専用 SQLite DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory の抽象化により実際のブローカークライアントと Mock クライアントを環境に応じて切り替え。
    - Engine をデーモンスレッドで実行し、プロジェクト直下の data/stop_requested.flag による外部停止制御をサポート。PID ファイル書き込みに対応。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用（監視は本番環境データ参照の想定）。
    - 起動時にプロセス優先度を "high" に設定。stop フラグによる安全終了処理と例外ハンドリングを実装。

- モニタリング DB 初期化
  - monitoring.monitoring_db:init_monitoring_db を呼び出して監視テーブルの冪等な初期化を行う（run_execution/run_monitoring から使用）。

- ユーティリティ
  - utils/process_priority: クロスプラットフォームのプロセス優先度設定ユーティリティを追加。
    - Windows: psutil の優先度定数を利用（存在しない場合はフォールバック）。
    - POSIX: nice 値で制御（Linux/Mac/FreeBSD をサポート）。
    - 例外発生時は警告を出して処理をスキップする安全設計。
    - set_cpu_affinity: プロセスを先頭 N コアにピン止めするユーティリティを追加。

- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio モジュールを追加:
    - portfolio.portfolio_builder:
      - select_candidates: BUY シグナルのソートと上位 N 抽出（スコア降順、同点は signal_rank でタイブレーク）。
      - calc_equal_weights / calc_score_weights: 等金額およびスコア加重の重み計算。全スコアが 0 の場合は等金額にフォールバックして WARNING をログ出力。
    - portfolio.risk_adjustment:
      - apply_sector_cap: セクター集中上限（max_sector_pct）を評価し、上限を超えるセクターの新規候補を除外。'unknown' セクターは上限対象外。
      - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を提供。未知の値はフォールバック（1.0）して警告。
    - portfolio.position_sizing:
      - calc_position_sizes: allocation_method に応じて発注株数を計算（"risk_based", "equal", "score"）。
      - lot_size（単元株）で丸め、max_position_pct や max_utilization などの制約を考慮。
      - cost_buffer を用いた約定コスト保守見積りと、available_cash 超過時のスケーリング処理（端数は残差順に lot 単位で追加配分）を実装。

- リサーチ / ファクター計算
  - kabusys.research.factor_research:
    - DuckDB を用いたモメンタム / ボラティリティ系ファクター計算機能を追加。
    - calc_momentum / calc_volatility 等を実装（MA200、1M/3M/6M リターン、ATR20、20日平均出来高等）。
    - prices_daily / raw_financials テーブルのみを参照する純粋関数設計。

- ツール
  - kabusys.tools.paper_verification_report:
    - ペーパートレード検証用レポート生成スクリプトを追加。
    - デフォルト DB: PAPER_TRADING_SQLITE_PATH / data/paper_trading.db。
    - 指標: 稼働率 (uptime_pct), 注文成功率(fill_rate), 送信率(send_rate), P95 レイテンシ 等。
    - Pass/Fail 判定基準を追加（稼働率 >= 99.0%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200 ms）。
    - 日付範囲フィルタ (--from / --to) と --db オプションをサポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- .env 読み込み周りの堅牢化
  - export プレフィックス、クォート内エスケープ、行内コメントの扱いを改善。
  - .env の読み込み失敗時に警告を出すように変更し、プロセス全体のクラッシュを防止。

- プロセス優先度設定の堅牢化
  - 未対応 OS や権限不足時に例外ではなく警告でスキップするように実装。

### Notes / Migration
- デフォルトのファイルパス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - PID / flag: data/execution.pid / data/stop_requested.flag 等
- モニタリングは意図的に本番 sqlite_path を参照する設計です。Paper トレードと監視 DB を分離したい場合は設定を調整してください。
- run_execution は BrokerClientFactory を通してブローカークライアントを生成します。paper_trading 環境では Mock クライアントが使用され、実際の発注は行われません（DB は paper_trading 用に分離されます）。
- .env を含む機密情報は絶対にリポジトリにコミットしないでください。config_setup による生成ファイルに関する注意喚起をウィザードが行います。

---

参照: 各モジュールの docstring / ログメッセージに実装意図や使用方法のヒントを記載しています。必要であれば各機能ごとの詳細なリリースノートや移行手順を作成します。