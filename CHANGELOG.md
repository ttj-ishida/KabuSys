# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」を準拠しています。

現在のバージョン: 0.1.0

---------------------------------------------------------------------

## [Unreleased]

（開発中の変更や次リリースで予定している作業を記載）

- factor_research モジュールの実装継続（ファイル末尾が未完了のため補完予定）
- 銘柄ごとの lot_size を stocks マスタから取得する設計への拡張（position_sizing の TODO）
- price フォールバック戦略の強化（risk_adjustment の TODO：価格欠損時の扱い）
- 自動テストや CI 向けの設定検証拡張（validate_config の厳格化オプション運用強化）

---------------------------------------------------------------------

## [0.1.0] - 2026-04-23

初回公開リリース。コードベースから推測される主要機能・実装内容をまとめています。

### Added
- 全体
  - パッケージ初期バージョンを追加（kabusys v0.1.0）。
  - __version__ を "0.1.0" に設定。

- 実行/監視ランナー
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を利用する想定。
    - ストップフラグ (data/stop_requested.flag) 検出で安全に停止。
    - プロセス優先度を最初に "high" に設定。
    - PID ファイルの管理（data/execution.pid）をサポート。
    - ExecutionEngine をスレッドで起動し、監視ループで停止フラグを監視。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する（監視 DB を常に一意化）。
    - ストップフラグ検出、例外の安全ハンドリング、DB 接続のクローズ処理を実装。

- 設定管理 / CLI
  - config.py: 環境変数管理クラス Settings を追加。
    - .env 自動ロード（プロジェクトルートを .git または pyproject.toml で検出）機能を実装。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パースはクォートや export プレフィックス、インラインコメントに対応。
    - 必須環境変数チェック用の _require を実装（未設定時は ValueError を送出）。
    - 各種プロパティを提供（DB パス、paper_trading 用 DB、PID/kill flag パス、しきい値、env/log_level 判定など）。
    - PAPER_FILL_MODE の値検証（"instant" | "partial" | "never" | "reject"）。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - 既存 .env 読み込み、項目ごとの入力、秘密値マスク表示、最終確認・保存機能を提供。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須/任意の環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および（PyYAML があれば）パース検証を実行。
    - --strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構築ライブラリ（pure functions）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を選択。
    - calc_equal_weights: 等金額配分重みを計算。
    - calc_score_weights: スコア比率に基づく重み計算（全スコアが 0 の場合は等金額にフォールバックして警告）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェックで新規候補を除外するロジック（"unknown" セクターは上限適用外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear マップ、未知のレジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に対応した発注株数計算。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）を満たすためのスケーリングと残差処理を実装。
    - cost_buffer による保守的なコスト見積りを考慮。

- ユーティリティ
  - utils/logging_setup.py:
    - 統一ログ設定ユーティリティを実装（StreamHandler は stdout、TimedRotatingFileHandler で日次ローテーション・30日保持）。
    - 既存ハンドラのクリア処理、環境変数 LOG_LEVEL/LOG_DIR からの解決、ファイル出力失敗時はコンソール出力へフォールバック。
  - utils/process_priority.py:
    - Windows と POSIX（Linux/Mac 等）の差異を吸収するプロセス優先度設定を実装（"high" / "normal" / "low"）。
    - set_cpu_affinity による CPU ピンニング機能を実装。
    - 権限不足や未対応 OS の場合は警告を出してスキップ。

- 監視 / DB 初期化
  - monitoring/monitoring_db (参照される init_monitoring_db): SQLite 接続に対する監視テーブル初期化（idempotent）を利用。起動スクリプトから呼び出し。

- Execution 内部コンポーネント（呼び出し元より確認できる形で追加されているコンポーネント）
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等を統合して ExecutionEngine を組み立てる形を採用。
  - RiskConfig のデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定し、初期 portfolio value を broker.get_available_cash() から取得して設定。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート出力ツールを追加。
    - system_status / trade_logs / risk_logs テーブルから稼働率、注文成功率、送信率、P95 レイテンシなどを集計して判定（PASS/FAIL）を行う。
    - 各種閾値: 稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。
    - 日付フィルタ（--from/--to）、DB パス上書き（--db）をサポート。
    - DB が存在しない・テーブル欠損時には N/A または適切に例外吸収して出力。

- research
  - research/factor_research.py:
    - ファクター計算骨格を追加（Momentum/Value/Volatility/Liquidity の算出方針と定数定義）。
    - DuckDB 接続で prices_daily / raw_financials を参照する設計を採用。
    - （注）ファイル末尾に未完の実装箇所あり（今後の拡張対象）。

### Changed
- ロギング
  - StreamHandler を stdout に出力するように設計（cron 等からの stdout/stderr 一括リダイレクト想定）。
  - ログレベル・ログディレクトリは引数 > 環境変数 > デフォルト の優先順位で解決。

### Fixed
- 設定の安全性・堅牢性
  - .env パースとロードで export/クォート/エスケープ/インラインコメントを適切に扱う実装により、環境変数取り込み時の誤認識を軽減。
  - MONITOR_POLL_INTERVAL の不正値を検出してデフォルトにフォールバックする処理を追加（負値や非数値による time.sleep エラー回避）。

### Notes / Known issues
- factor_research.py がファイルの途中で未完となっている箇所が存在（start_da で途切れ）。ファクター計算の完成が必要。
- risk_adjustment.apply_sector_cap のコメントにある通り、price が欠損（0.0）だった場合のエクスポージャー算出で過少見積りになる可能性があり、将来的に前日終値等のフォールバックを検討中。
- position_sizing では現状全銘柄共通の lot_size を使用する設計。銘柄別単元数の対応は TODO。
- process_priority/set_cpu_affinity は権限やプラットフォーム依存で失敗することがあるため、失敗時は警告ログを出してスキップする挙動にしてある。

---------------------------------------------------------------------

参考:
- リリース日付はコード内の日付や本 CHANGELOG 作成日を基に推測しています。
- 仕様や実装に関する詳細は各モジュールの docstring / コメントを参照してください。