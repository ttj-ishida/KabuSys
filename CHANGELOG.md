# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
日付は本リリース作成日です。

全般的な注記:
- 本リリースはパッケージの初期公開相当の機能群をまとめたものです。
- デフォルト設定・ファイルパスは data/（SQLite, paper_trading DB）および logs/（ログ）等を想定しています。
- DuckDB / SQLite をデータ層として利用する設計です。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-18

### Added
- 基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` に設定。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値や 0/負値はデフォルトにフォールバックし警告を出力。
    - 停止制御はプロジェクトルート/data/stop_requested.flag によるフラグファイル方式を採用。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を使用して起動（monitoring テーブル初期化を実行）。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBroker を利用し、paper_trading 用 DB（data/paper_trading.db）へ記録して本番 DB と完全分離。
    - ブローカーファクトリ（BrokerClientFactory）、OrderManager/OrderRepository、RiskManager、Reconciler を組み合わせて ExecutionEngine を起動。
    - エンジンは別スレッドで実行され、stop flag に応じて engine.stop() を呼び出して安全に終了する。
    - 起動時にプロセス優先度を "high" に設定。実行中は PID ファイルを data/execution.pid に出力。
- 設定関連
  - config.py
    - 環境変数読み込み・管理クラス `Settings` を追加。
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。.env / .env.local の読み込み順序をサポートし、OS 環境変数は保護（上書きされない）される。
    - .env のパースで `export KEY=val`、クォート文字列（シングル/ダブル、バックスラッシュエスケープ）、インラインコメント処理などをサポート。
    - 多数の設定プロパティを提供（J-Quants, kabu API, LINE, DB パス, 監視閾値, 環境判定メソッド等）。
    - PAPER_FILL_MODE のバリデーション、有効値チェック（instant/partial/never/reject）。
  - validate_config.py
    - 環境変数と config/*.yaml の存在・基本検証を行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、YAML パースチェック（PyYAML がインストールされている場合）を実施。
    - KABUSYS_ENV=live の場合の追加ガード（LINE 設定確認や KILL_FLAG_CLEAR_ON_START の警告）を実装。
    - --strict オプションで警告を FAIL 扱いにできる。
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
    - J-Quants / kabu API シークレット項目等のマスク表示、選択肢・デフォルト提供、キャンセル/確認フローを提供。
    - 保存先 .env のフォーマットとテンプレート生成を実装（.env は絶対に Git にコミットしない旨の注意文を含む）。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 共通ログ設定ユーティリティ `setup_logging(app_name, log_dir, level)` を追加。
    - stdout に StreamHandler を出力（cron/Task Scheduler のリダイレクト運用を考慮して stderr ではなく stdout を採用）。
    - 日次ローテーション（TimedRotatingFileHandler）を追加し、ログファイルを `<log_dir>/<app_name>.log` に保存。デフォルトは logs/、30 日分保持。
    - 既存ハンドラのクリア処理やログディレクトリ作成失敗時のフォールバック（コンソールのみ）を実装。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）を設定するユーティリティを追加。
    - CPU アフィニティ設定関数 `set_cpu_affinity` を提供（最初の N コアへ固定）。権限不足や未対応環境では警告を出してスキップ。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順、signal_rank でタイブレーク）。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコア 0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中を検出し、新規候補を除外するロジック（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear。未知レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）ごとに発注株数を計算。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash）でのスケールダウン、cost_buffer（手数料・スリッページの概算）を考慮した安全なスケーリング処理を実装。
    - risk_based モードでのリスクベース算出（risk_pct, stop_loss_pct を用いた目標株数計算）を実装。
- モニタリング / 実行関連 DB 初期化
  - monitoring_db.init_monitoring_db 呼び出しによる監視テーブルの冪等な初期化（監視と実行の両スクリプトで呼出し）。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。
    - 稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を集計し、閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づき PASS/FAIL 判定を行う。
    - 日付フィルタ（--from/--to）および DB パス指定（--db / 環境変数）をサポート。
- リサーチ（断片）
  - research/factor_research.py（ファクター計算基盤の実装を開始）
    - Momentum / Value / Volatility / Liquidity 等の計算方針を実装予定。モジュール構造と定数を導入（モメンタム計算関数 calc_momentum の雛形を含む）。

### Changed
- 環境変数自動読み込みの挙動
  - OS 環境変数は保護され、.env.local の override が許可されるが既存の OS 環境変数は上書きされないように設計。
- ログ出力の既定挙動
  - 起動スクリプトは setup_logging を統一的に使用することで、コンソールとファイルの二重出力を標準化。

### Fixed
- （なし：初期リリースのためバグ修正履歴なし）

### Removed
- （なし）

### Security
- シークレット値（J-Quants, KABU API パスワード, LINE トークン等）は .env に保存し .git にコミットしないことをウィザード内で明示。CLI の入力表示ではマスク処理を行う。

---

注記・既知の制約:
- research/factor_research.py の実装は途中で切れている（calc_momentum の実装が完了していない可能性あり）。今後のリリースで続きが追加されます。
- process_priority や CPU affinity の設定は権限やプラットフォーム依存で失敗することがあり、その場合は警告を出してスキップする設計です。
- .env の自動読み込みはプロジェクトルートが特定できない場合はスキップします（パッケージ配布後の柔軟性を確保）。

---

参考: 今後の予定（例）
- research モジュールの完全実装（ファクター計算の SQL 実装・検証）
- ExecutionEngine / BrokerClient の詳細実装と統合テスト
- 監視アラート（LINE 通知）や運用向けの運用ドキュメント整備

（必要であれば各ファイルごとの差分/コミット単位のより詳細な変更点も作成します。どの粒度で記載するか指示してください。）