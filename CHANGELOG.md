# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
このファイルは主にコードベースの初期機能追加・実装内容をソースコードから推測してまとめたものです。

全般のルール: 変更はカテゴリ別に整理（Added / Changed / Fixed / Removed）。

## [0.1.0] - 2026-04-23

### Added
- 基本パッケージの初期実装を追加（__version__ = 0.1.0）。
- 実行系スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを実装。
    - KABUSYS_ENV による paper_trading モードの分離（MockBrokerClient を使用し、専用 SQLite（data/paper_trading.db）に記録）。
    - PID ファイル (data/execution.pid) と停止フラグ (data/stop_requested.flag) による起動・停止制御。
    - スレッドで engine.run_session をデーモン実行し、停止フラグ検知で安全停止。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler などの依存コンポーネントの組み立てを実装。
    - DuckDB/SQLite 接続の初期化と監視テーブルの準備（init_monitoring_db 呼び出し）。
- 監視系スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループを実装。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 停止フラグ (data/stop_requested.flag) による安全終了。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する実装方針。
- 設定管理
  - config.py
    - .env ファイル自動読み込み（プロジェクトルートの検出: .git または pyproject.toml を起点）。
    - .env のパースロジック（コメント、クォート、export 形式対応）、自動ロードの無効化フラグ (KABUSYS_DISABLE_AUTO_ENV_LOAD)。
    - Settings クラスで環境変数をプロパティ化（DB パス・LOG_LEVEL・KABUSYS_ENV 等）、入力検証（例: PAPER_FILL_MODE の有効値チェック、KABUSYS_ENV の有効値チェック）。
    - settings = Settings() のグローバルインスタンスを提供。
- 設定ユーティリティ
  - config_setup.py
    - 対話式の .env 作成/更新ウィザードを実装（必須項目・秘密項目のマスク表示・デフォルト値・選択肢対応）。
    - .env の読み書きロジックを実装（既存値継承、保存前の確認プロンプト）。
  - validate_config.py
    - 起動前の設定検証 CLI を実装（必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パースチェック（PyYAML が無ければ警告））。
    - --strict オプションで警告を FAIL 扱いにする機能。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのソートと上位 N 選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化配分（全スコア 0 の場合は等金額にフォールバック、警告を出力）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限の適用（既存保有と当日売却予定を考慮）。"unknown" セクターは制限を適用しない仕様。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear のマップ、未知レジームは警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 発注株数決定ロジックを実装（allocation_method = "risk_based" / "equal" / "score" をサポート）。
    - 単元株（lot_size）丸め、per-position 上限・aggregate cap（利用可能現金に応じたスケーリング）を実装。
    - cost_buffer（手数料・スリッページ予備）を考慮した保守的なコスト見積りとスケーリング分配ロジック（端数配分のための残差ソートによる追加配分）。
- ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定関数 setup_logging を実装（stdout StreamHandler と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定）。
    - LOG_LEVEL / LOG_DIR 環境変数と引数で優先度を解決。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - クロスプラットフォームなプロセス優先度設定（Windows の priority class / POSIX の nice 値）、および CPU affinity 設定用の関数を提供。
    - アクセス許可エラーや未対応 OS 時は警告を出して安全にスキップ。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを実装。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均・最大・P95）を集計。
    - 基準値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL を判定して出力。
    - コマンドライン引数で期間指定（--from / --to）および DB パス指定（--db）に対応。環境変数 PAPER_TRADING_SQLITE_PATH を優先的に利用可能。
- 研究用モジュール（部分実装）
  - research/factor_research.py
    - ファクター計算モジュールの骨格を追加（Momentum, Value, Volatility, Liquidity を想定）。
    - DuckDB 接続を受けて prices_daily / raw_financials を参照する設計方針と定数を実装。
    - モメンタム計算（関数 calc_momentum）のヘッダとドキュメントを追加（実装途中）。

### Changed
- なし（初期リリースのため該当なし）

### Fixed
- なし（初期リリースのため該当なし）

### Removed
- なし

---

注記:
- ここに記載した内容はソースコードのコメント・ドキュメント文字列および実装から推測してまとめています。実際の運用上の振る舞いや追加の依存関係（例: BrokerClient 実装、SystemMonitor 内部、ExecutionEngine 実装の詳細など）は別途コードベースの他ファイルを参照してください。
- research/factor_research.py はファイル末尾で実装途中で切れているため、完全実装が必要です。