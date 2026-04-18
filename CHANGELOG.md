# Keep a Changelog
すべての変更は https://keepachangelog.com/ja/ のフォーマットに準拠して記載しています。

<!-- NOTE:
  この CHANGELOG は提供されたソースコードから推測して作成した初期リリースの変更履歴です。
  実際のコミット履歴がある場合はそちらを優先してください。
-->

## [0.1.0] - 2026-04-18

### 追加
- 初期リリース。KabuSys 自動売買フレームワークのコア機能を実装。
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを実装。BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動とデーモン スレッド管理を行う。
    - paper_trading 環境時は専用の SQLite（PAPER_TRADING_SQLITE_PATH, デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。MockBrokerClient を利用する設計を想定。
    - 停止用フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）をサポート。停止フラグ検知で安全にエンジン停止を行う。
    - RiskManager のデフォルト構成（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。デフォルトポーリング間隔は 60 秒（MONITOR_POLL_INTERVAL 環境変数で上書き可能）。
    - 監視は環境にかかわらず production 用 sqlite_path を使用する仕様（監視データの一貫性確保）。
    - 停止フラグ検知でループを終了し、例外発生時はログを残して次ポーリングへフォールバック。

- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml に基づいて探索）。OS 環境変数を保護するための上書き制御を実装。
    - .env のパースは export 形式、クォートやエスケープ、インラインコメントに対応する堅牢な実装。
    - Settings クラスを提供し、各種設定値（J-Quants / kabu API / DB パス / paper trading 設定 / 監視閾値 / ログ設定 等）をプロパティ経由で取得。値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を行う。
    - settings = Settings() をモジュールレベルで提供。

- 設定関連ツール
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を実装。シークレットはマスク表示、選択肢・デフォルト・説明を表示。保存前の確認プロンプト付き。
  - validate_config.py
    - 起動前に環境変数・config/*.yaml を検証する CLI を実装。必須環境変数の有無、プレースホルダ検出、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在チェック（PyYAML 未インストール時は検証スキップ）、本番環境（live）向けの警告を実装。
    - --strict オプションで警告を FAIL として扱う機能を追加。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - すべての起動スクリプトで共通して使用できるロギング設定ユーティリティを実装。stdout への StreamHandler と 日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30日保持）をルートロガーに設定。既存ハンドラをクリアして二重設定を防止。
    - ログレベル / ログディレクトリは引数・環境変数・デフォルトの優先順位で解決。ログディレクトリ作成失敗時はファイル出力を無効化してコンソールのみで継続。
  - utils/process_priority.py
    - psutil を用いたプロセス優先度設定（Windows と POSIX を吸収）。set_process_priority("high"|"normal"|"low") と set_cpu_affinity(N) を提供。権限不足や未対応 OS では警告を出してスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルのソートと候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は警告を出して等配分にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。unknown セクターは上限チェック対象外、未知レジームはフォールバックで 1.0。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数を計算する calc_position_sizes を実装。allocation_method（"risk_based" / "equal" / "score"）をサポートし、lot_size（単元株）丸め、max_position_pct、max_utilization、cost_buffer（手数料・スリッページ見積り）、aggregate cap に基づくスケーリング、端数処理（残差に基づく追加配分）を備える。

- 分析 / レポート
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを実装。SQLite（PAPER_TRADING_SQLITE_PATH）からシステム稼働率、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を集計し、閾値に基づく PASS/FAIL を判定して出力。
    - CLI で期間指定（--from, --to）と DB パス指定（--db）をサポート。

- リサーチ（ファクター計算）基盤
  - research/factor_research.py（スキャフォールド／モジュール実装中）
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルを使用してモメンタム・バリュー・ボラティリティ・流動性ファクターを計算する方針。モメンタム計算ロジックの初期実装（関数シグネチャや定数）を含む（実装は継続中）。

### 変更
- （初期リリースのため該当なし）

### 修正
- （初期リリースのため該当なし）

### 削除
- （初期リリースのため該当なし）

### セキュリティ
- （初期リリースのため該当なし）

注記:
- 本 CHANGELOG はソースコードの実装内容から推測して作成した概要です。細かい動作や設計上の注意点（例: 価格欠損時の取り扱い、ファイル/ディレクトリ作成権限、psutil による優先度設定の権限問題など）はコード内の docstring やログメッセージに記載されています。実運用前に validate_config や config_setup、ユニットテストで挙動を確認してください。