# Keep a Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]
（なし）

## [0.1.0] - 初回リリース (initial)
リリース日: 未設定

### 追加 (Added)
- 基本アプリケーションの初期実装を追加。
  - pakage メタ情報:
    - kabusys.__version__ = "0.1.0"
- 実行用スクリプト:
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper_trading DB（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を利用する設計を想定。
    - ブローカークライアント生成は BrokerClientFactory 経由。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をスレッドで起動。
    - 停止制御用ファイル（data/stop_requested.flag）検出で安全に停止。起動時に停止フラグが既に存在する場合は起動を中止。
    - PID ファイル（data/execution.pid）を使用。
    - RiskManager に対するデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックし警告を出力。
    - 監視用 SQLite は環境にかかわらず本番 sqlite_path を使用（monitoring 用テーブルの初期化を実行）。
    - 停止フラグ（data/stop_requested.flag）検出でループを終了。
    - プロセス優先度を "high" に設定してから起動。

- 設定管理:
  - config.py
    - .env の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env / .env.local の読み込み順（OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード停止。
    - .env パースの堅牢化（export 記法、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどに対応）。
    - Settings クラスでアプリケーション設定をプロパティとして取得可能（DB パス、API トークン、環境判定フラグ、監視閾値等）。
    - PAPER_FILL_MODE のバリデーション、有効値: "instant" | "partial" | "never" | "reject"。
    - 環境種別（KABUSYS_ENV）および LOG_LEVEL のバリデーション。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI。
    - 秘匿項目はマスク表示、選択肢・デフォルト・説明を提示。
    - .env ファイルへの安全な書き出し機能を提供（git に .env を含めないよう注意書き）。
  - validate_config.py
    - 起動前の設定検証 CLI。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）、DB パスの親ディレクトリ存在確認、config/*.yaml の存在とパース確認（PyYAML が存在する場合）。
    - KABUSYS_ENV=live の場合の追加ガード（LINE 設定未指定や KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築ロジック（純粋関数群）:
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順かつ tie-breaker で signal_rank を使用して候補選定。
    - calc_equal_weights, calc_score_weights: 等重・スコア重み付け（全スコアが 0 の場合は等重にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中度の上限チェック。既存保有をセクター別に評価し、上限超過セクターの候補を除外（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジームに応じた乗数を返却（bull=1.0, neutral=0.7, bear=0.3、未知は 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: weight/candidates/portfolio_value 等を基に発注株数を計算。allocation_method として "risk_based" / "equal" / "score" をサポート。
    - リスクベース計算、単元株（lot_size）丸め、1 銘柄上限／aggregate cap（available_cash）でのスケーリング、コストバッファ（cost_buffer）考慮、端数処理（残差順で追加割付）を実装。

- ユーティリティ:
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティ。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30 日保持）をルートロガーに設定。
    - LOG_DIR 環境変数や引数でログ出力先を指定可能。ディレクトリ作成失敗時はファイル出力をフォールバックで無効化してコンソールのみで継続。
    - 既存ハンドラのクリーンアップ（重複設定防止）。
  - utils/process_priority.py
    - プロセス優先度設定（Windows / POSIX の差分吸収）。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。アクセス権がない場合は警告を出してスキップ。

- モニタリング / DB 初期化:
  - run_* や execution スクリプトで monitoring_db.init_monitoring_db を呼び出し、監視用テーブルが存在することを冪等的に保証する処理を組み込み。

- ツール:
  - tools/paper_verification_report.py
    - Paper Trading の検証レポートを生成する CLI。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）などを SQLite（paper_trading DB）から集計して表示。
    - 基準値（稼働率 99%、成功率 90%、送信率 95%、P95 <= 200 ms）を定義し、Pass/Fail 判定を出力。
    - 日付フィルタ (--from / --to)、DB パスのオーバーライド (--db) をサポート。

- リサーチ:
  - research/factor_research.py（計算方針と定数、モメンタム計算関数 calc_momentum の骨組みを追加）
    - Momentum / Value / Volatility / Liquidity に関する計算方針を実装する設計。DuckDB を使用して prices_daily / raw_financials を参照する想定。

### 変更点 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 注意事項 / 補足
- .env に機密情報（API トークンなど）を含めるため、config_setup の README にもある通り .env は絶対に Git にコミットしないでください。
- run_monitoring は監視 DB として Settings.sqlite_path を常に使用するため、監視データは環境に依らず同じ SQLite ファイルに保存されます。一方で run_execution は paper_trading 時に paper_sqlite_path を使用して本番 DB と分離します。
- process_priority / cpu_affinity は権限や OS に依存するため、アクセス権限不足時には警告を出して処理をスキップします。
- research/factor_research.py は一部実装が継続中（ファイル末尾が途中で切れている）ため、完全なファクター計算は今後の実装を待ってください。

---

開発・運用に関する問い合わせや追加要望があればお知らせください。必要に応じてバージョン毎の差分（コミット単位での変更点）をより詳細に記載できます。