# Changelog

すべての変更は「Keep a Changelog」形式に従って記載しています。  
このファイルはコードベースから推測して作成した変更履歴です。

全般的な注意
- バージョン番号はパッケージ定義 (kabusys.__version__) に合わせています。
- 環境変数やファイルパスのデフォルト値はコード内の記述に準拠しています（例: data/ 以下のデフォルトパス等）。
- 実装上の挙動や CLI の使い方は各モジュールの docstring に基づいて記載しています。

## [0.1.0] - 2026-04-19

### 追加
- 基本パッケージ情報
  - パッケージエントリポイントとバージョンを追加（kabusys.__version__ = "0.1.0"）。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を利用し、paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離する動作をサポート。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を利用）。
    - 停止制御に stop_requested.flag と execution.pid を利用する仕組みを実装。
    - ExecutionEngine と関連コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler）の組み立てを行う。

  - run_monitoring.py
    - SystemMonitor（監視ループ）起動用スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトへフォールバックし警告を出す。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を使用する（監視テーブルへの永続化を想定）。
    - stop_requested.flag による監視ループの安全停止に対応。

- 設定管理
  - config.py
    - .env ファイル（.env / .env.local）の自動読み込みを実装（OS 環境変数を保護しつつ、.env.local は上書き可能）。
    - .env のパースは export 付き行、シングル/ダブルクォート、エスケープ、行内コメントなど幅広いケースに対応。
    - Settings クラスを導入し、各種設定値（J-Quants / kabu API / DB パス / 監視閾値 / 環境フラグ等）をプロパティ経由で提供。
    - PAPER_FILL_MODE のバリデーション（"instant" | "partial" | "never" | "reject"）や KABUSYS_ENV の許容値検証を実装。
    - デフォルトパス:
      - DUCKDB_PATH: data/kabusys.duckdb
      - SQLITE_PATH: data/monitoring.db
      - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
      - PID_FILE_PATH: data/execution.pid
      - KILL_FLAG_PATH: data/kill.flag

  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を追加。
    - 必須/任意の項目定義、マスク表示（シークレット）、選択肢サポート、保存前の確認などを実装。
    - デフォルトや既存値の再利用をサポートし、.env ファイルを書き出すヘルパーを提供。

  - validate_config.py
    - 起動前に .env と config/*.yaml の不足や不整合を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および（PyYAML があれば）パース検証を実施。
    - `--strict` オプションで警告を失敗として扱うモードを提供。
    - live 環境向けの追加警告（LINE 通知未設定、KILL_FLAG_CLEAR_ON_START の危険設定など）を実装。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ初期化関数 setup_logging を追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を持つファイルハンドラをルートロガーに設定。ファイルハンドラは logs/（デフォルト）または LOG_DIR 環境変数で指定。
    - ログレベルの解決順を実装（引数 > LOG_LEVEL > デフォルト "INFO"）。ローテーションは 30 日分保持。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで動作。

  - utils/process_priority.py
    - プラットフォーム非依存のプロセス優先度設定ユーティリティを追加（Windows / POSIX に対応）。
    - set_process_priority(level) で "high" / "normal" / "low" を指定可能。アクセス拒否など失敗時は警告でスキップ。
    - set_cpu_affinity(cpu_count) でプロセスを最初の N コアにピン留めする機能を実装（利用不可/権限不足時は警告）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルを score 降順、同点なら signal_rank でタイブレークして上位 N を選出。
    - calc_equal_weights: 等分配（1/N）。
    - calc_score_weights: スコア正規化配分。全スコアが 0 の場合は等分配へフォールバックし警告を出力。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクターごとの既存エクスポージャーが上限を超えている場合、新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を実装（"bull":1.0, "neutral":0.7, "bear":0.3）。未知のレジームは 1.0 にフォールバックして警告。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method に応じた発注株数計算を実装（"risk_based", "equal", "score"）。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate 上限（available_cash）によるスケーリング、cost_buffer による保守的見積りをサポート。
    - risk_based: リスク（risk_pct）とストップロス（stop_loss_pct）から株数を計算。
    - aggregate cap のスケーリングは残差配分ロジックで再現性のある割当てを行う。

  - portfolio/__init__.py
    - 上記関数群をパッケージエクスポートとしてまとめて公開。

- 研究・分析ユーティリティ
  - research/factor_research.py
    - ファクター計算モジュールの骨格を追加（Momentum / Value / Volatility / Liquidity を想定）。
    - calc_momentum のインターフェースと定数群（1M/3M/6M、MA200、ATR など）を実装開始（DuckDB 接続を受け取って prices_daily を参照する設計）。※実装はファイル末尾で続きがある想定（コードベースに一部未完の箇所あり）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。
    - デフォルト DB: data/paper_trading.db、または環境変数 PAPER_TRADING_SQLITE_PATH / --db オプションで指定可能。
    - 指標と閾値:
      - 稼働率 (uptime_pct) 閾値: 99.0%
      - 注文成功率 (fill_rate) 閾値: 90.0%
      - 送信率 (send_rate) 閾値: 95.0%
      - P95 レイテンシ閾値: 200 ms
    - system_status, trade_logs, risk_logs などのテーブルから集計し、PASS/FAIL を出力。
    - P95 の計算、NULL/データ不足の扱い、SQL の日付フィルタ生成を実装。

### 変更
- 仕様的な注意点を明確化
  - 監視系（run_monitoring）は KABUSYS_ENV に関係なく本番用の sqlite_path を使用する旨を明記。
  - run_execution は paper_trading 時に DB を分離する（本番 DB と完全分離されることを想定）。

### 修正
- n/a（初回リリースのため既存バグ修正は無し）

### 既知の制約・注意点
- research/factor_research.py の一部（calc_momentum 以下）がコード末尾で切れている/未完の可能性があるため、ファクター計算の完全実装は今後の作業が必要です。
- process_priority/set_cpu_affinity やログディレクトリ作成など、OS の権限や環境に依存する処理は失敗時に「警告を出してスキップ」する設計になっているため、想定どおり動作しない場合は権限や環境設定の確認が必要です。
- .env 自動読み込みはプロジェクトルートの検出に依存する（.git または pyproject.toml を探索）。プロジェクトルートが検出できない場合は自動読み込みをスキップします。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading と本番 DB の分離はデータ保護を目的とするが、設定ミスで本番 DB を参照してしまわないよう .env の確認を推奨します（python -m kabusys.validate_config を使用）。

### セキュリティ
- .env の取り扱いに関する注意書きを config_setup が生成するファイルヘッダに記載（.env を絶対に Git にコミットしない旨）。

---

今後の予定（候補）
- factor_research の完全実装（各ファクターの SQL/算出ロジック完成）。
- ExecutionEngine / Monitoring のユニットテスト拡充と外部依存のモックライブラリ整備。
- 銘柄別単元（lot_size）や取引コスト（手数料/スリッページ）を銘柄マスタで扱えるよう拡張。
- 監視・実行プロセスの systemd / サービス定義のサンプル追加。

（以上）