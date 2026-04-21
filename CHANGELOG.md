# Changelog

すべての変更は Keep a Changelog の書式に従っています。重要な変更点のみ日本語で要約しています。

全体方針: 初期公開リリースとして、環境設定・検証ツール、実行/監視ランナー、ポートフォリオ構築ロジック、ユーティリティ類、および Paper Trading 検証レポート生成を含む一連のコンポーネントを実装しました。

## [Unreleased]

- ワークインプログレス: research/factor_research.py にファクター計算ロジックを実装中（calc_momentum 等）。部分的に実装済みだがまだ完成していない関数あり。

---

## [0.1.0] - 2026-04-21

Initial release

### Added
- 基本アプリケーション情報
  - パッケージバージョンを `__version__ = "0.1.0"` に設定（src/kabusys/__init__.py）。

- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合はペーパートレード用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全に分離。
    - Engine を別スレッドで実行し、data/stop_requested.flag を検知して安全に停止する処理を実装。
    - 起動時に process priority を "high" に設定する呼び出しを行う。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告出力。
    - 監視 DB (monitoring) は環境にかかわらず本番用 sqlite_path を使用（監視は本番 DB を参照する設計）。
    - 停止フラグ検知と KeyboardInterrupt のハンドリングによるグレースフルシャットダウンに対応。
    - init_monitoring_db を呼び出して監視テーブルの存在を保証。

- 環境設定関連
  - config_setup.py: 対話式 .env 設定ウィザードを実装。
    - J-Quants / kabuAPI / DB パス / LINE 通知など主要項目を対話的に設定可能。
    - .env の読み書きロジックを提供（既存値の読み込み、シークレットマスク表示、保存確認など）。
  - config.py: 環境変数ロードと Settings クラスを実装。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）に基づき `.env` / `.env.local` を自動的に読み込み（環境変数により無効化可能）。
    - .env パーサは引用符やエスケープ、インラインコメント処理に対応。
    - 各種設定プロパティ（DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID/KILL フラグ関連、閾値等）を提供。環境値検証（有効値チェック）あり。
    - Settings インスタンスを `settings` としてエクスポート。

- 設定検証 CLI
  - validate_config.py: .env および config/*.yaml の起動前検証ツールを実装。
    - 必須環境変数の存在チェック、KABUSYS_ENV の妥当性チェック、LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、YAML のパース検証（PyYAML の有無による分岐）、本番モード時の追加ガード（LINE 設定確認や KILL_FLAG_CLEAR_ON_START の警告）などを実行。
    - `--strict` オプションで警告を FAIL 扱いにすることが可能。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank でタイブレーク）でソートして上位 N を選択。
    - calc_equal_weights: 等金額配分 (1/N)。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等金額にフォールバックして警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック。既存保有のセクター比率が上限を超える場合、新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime による投下資金乗数（bull/neutral/bear をマッピング、未知値は警告の上フォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method に応じた発注株数計算。risk_based, equal, score の各方式をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）に基づくスケールダウンと残余キャッシュを使った端数調整ロジックを実装。
    - cost_buffer による保守的コスト見積りを組み込み。

- ログ・プロセスユーティリティ
  - utils/logging_setup.py
    - 共通のログ設定ユーティリティを追加。StreamHandler を stdout に出力、TimedRotatingFileHandler による日次ローテーション（デフォルト logs/、30 日保持）を提供。
    - 既存ハンドラのクリーンアップ処理、ログレベル/ログディレクトリの解決ロジックを実装。
  - utils/process_priority.py
    - プロセス優先度設定 (high/normal/low) と CPU affinity 設定ユーティリティを追加。Windows / POSIX の差分を吸収し、権限不足や未対応 OS では警告を出してスキップする実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ等を算出して PASS/FAIL 判定を出力。
    - デフォルト閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）。
    - 日付フィルタ（--from/--to）と DB パスのオーバーライド（--db / PAPER_TRADING_SQLITE_PATH）をサポート。
    - latency の P95 算出、SQL の存在エラー時のフォールバック処理を実装。

- Execution サブシステム（依存関係の注記）
  - run_execution から BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等の組み立てを行う（各クラスは別モジュールで実装される想定）。RiskConfig における既定値と broker.get_available_cash() を初期ポートフォリオ値として使用。

### Changed
- （設計）監視と実行はプロセス優先度を起動直後に "high" に設定するように統一。これにより監視/発注プロセスの優先度が向上。

### Fixed
- MONITOR_POLL_INTERVAL の不正な値（非整数・0 以下）に対して警告を出し、デフォルト値にフォールバックする処理を追加（run_monitoring.py）。
- .env 読み込みの堅牢化:
  - export プレフィックス対応、引用符内のエスケープ対応、コメント扱いの改善（config._parse_env_line）。
  - .env の読み込み失敗時に warnings を出すように変更（ファイル IO エラー時の安全化）。
- logging_setup:
  - ログディレクトリ作成失敗時に file handler をスキップしてコンソールのみで継続するように修正。

### Security
- .env の取り扱いについて注意喚起コメントを config_setup.py で追加（.env を絶対に Git にコミットしないよう注記）。

### Notes / Known issues
- research/factor_research.py はファクター計算のための基盤を追加済みだが、ファイル内の一部関数（calc_momentum 等）が未完（ソースが途中で切れている）。今後のリリースで完成させる予定。
- run_execution/run_monitoring から呼び出す内部コンポーネント（ExecutionEngine, SystemMonitor 等）の詳細は別モジュールに依存。これらのテスト・結合は注意して行ってください。
- process_priority/set_cpu_affinity は権限やプラットフォーム依存のため、実行環境によっては動作しない（警告を出して継続）。

---

今後の予定:
- research モジュールの完成（ファクター計算の詳細実装とユニットテスト）。
- Execution/Monitoring の統合テスト、エンドツーエンド動作検証。
- さらなるドキュメント（運用手順、デプロイ手順、監視メトリクス解説）の整備。

--------------
この CHANGELOG はソースコードから推測して作成しています。実際の変更履歴やリリース日付はリポジトリのコミット履歴に基づいて調整してください。