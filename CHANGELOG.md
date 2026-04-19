# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」準拠です。  

リリース日はファイル作成時点の推測に基づき記載しています。

---

## [Unreleased]
- 今後のリリースで追記予定

---

## [0.1.0] - 2026-04-19
初回公開（推測）。以下はコードベースから推測した本リリースの主要な追加・仕様です。

### 追加
- 起動スクリプト / CLI
  - run_execution.py: 実行エンジン（ExecutionEngine）起動用スクリプトを追加。プロセス優先度設定、DB接続、Broker クライアントの生成、ExecutionEngine のスレッド起動／停止判定（stop flag）などを行う。
  - run_monitoring.py: SystemMonitor ポーリングループ起動用スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - validate_config.py: .env および config/*.yaml の事前検証ツールを提供。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスや YAML ファイルの存在・パースチェック、--strict モードをサポート。
  - config_setup.py: .env の対話式ウィザード。既存 .env 読込、秘密値のマスク表示、生成テンプレートの保存を行う。
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成ツール。稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL を判定する。

- 設定・環境管理
  - config.Settings クラスを導入。環境変数から各種設定（J-Quants、kabu API、DB パス、Paper Trading 用パス、閾値、ログレベル等）を取得。
  - .env 自動ロード機構を実装（プロジェクトルートの検出は .git / pyproject.toml を基準）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装は export プレフィックス、クォート（シングル／ダブル）とバックスラッシュエスケープ、インラインコメントの扱いなどを考慮。

- データベース／Paper Trading 分離
  - Settings に paper_sqlite_path / PAPER_FILL_MODE 等を追加。KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離する仕様を実装（Execution の起動フローに反映）。

- ロギング・プロセス管理ユーティリティ
  - utils.logging_setup.setup_logging(): stdout 出力用 StreamHandler と日次ローテーション（TimedRotatingFileHandler、30 日保持）のファイルハンドラをルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみ継続。
  - utils.process_priority: クロスプラットフォームでのプロセス優先度設定（Windows の優先度クラス / POSIX の nice 値）、CPU affinity 固定機能を提供。権限不足や未対応環境では警告を出してフォールバック。

- Portfolio 構築関連（純粋関数群）
  - portfolio.portfolio_builder: シグナルの候補選定（score 降順、signal_rank タイブレーク）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights。全スコア 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment: セクター集中制限 apply_sector_cap（既存保有を考慮して過剰セクターの候補を除外）、市場レジームに基づく投下資金乗数 calc_regime_multiplier（bull/neutral/bear マップ、未知値は 1.0 でフォールバック）。
  - portfolio.position_sizing: 発注株数計算（allocation_method に応じて "risk_based" / "equal" / "score" をサポート）、単元株丸め（lot_size）、per-stock 上限・aggregate cap（available_cash によるスケールダウン）や cost_buffer を用いた保守的見積り、残差分配のロジックを実装。

- 監視・モニタリング
  - monitoring 初期化呼び出し（init_monitoring_db）を Execution/Monitoring 起動時に実行して監視テーブルの存在を保証（冪等）。
  - run_monitoring のポーリングループは停止フラグ（data/stop_requested.flag）による終了、例外発生時のロギングと次ポーリングまで待機を行う。

- 実行エンジン（Execution）周り
  - ExecutionEngine の起動スキーム（スレッド実行、PID ファイル管理、stop flag による停止、Paper Trading でのモックブローカ使用を考慮）を反映する起動スクリプトを用意。
  - RiskManager のデフォルト設定例（max_position_pct, max_utilization, rate_limit_per_sec, circuit breaker, max_drawdown 等）をコード中に示す形で導入。initial_portfolio_value は broker.get_available_cash() を使用して初期化。

- 分析・リサーチ
  - research/factor_research.py にてファクター計算基盤を追加（モメンタム・MA200 乖離・ATR・出来高等を想定）。comments にて計算方針を明記。モメンタム計算関数 calc_momentum の実装が開始されている（途中で切れているため未完の可能性あり）。

### 変更
- （初回リリースのため該当なし）

### 修正
- 環境変数の妥当性検証・フォールバック処理を強化
  - MONITOR_POLL_INTERVAL が不正な場合にデフォルト（60 秒）へフォールバックして警告を出す処理を追加。
  - PAPER_FILL_MODE の値検証を実装し、不正値で例外を投げるように明確化。
  - LOG_LEVEL / KABUSYS_ENV の値検証を Settings および validate_config で統一的に行う。

### 既知の注意点 / 破壊的仕様
- run_monitoring は「環境にかかわらず」Settings.sqlite_path（本番用の SQLite パス）を使用する実装がなされている。すなわち KABUSYS_ENV が paper_trading の場合でも monitoring は本番 sqlite を参照する仕様になっているため、運用時は DB パスの取り扱いに注意が必要（意図的実装か要確認）。
- process_priority / cpu_affinity の設定は OS 権限やプラットフォーム依存で失敗する可能性があり、その場合は警告を出力して処理を続行する（安全フォールバック）。
- research/factor_research.py の実装が途中で終わっている箇所が存在する（このファイルは更なる実装が必要）。

### セキュリティ
- .env ファイルの生成テンプレートと README コメントで「.env は絶対に Git にコミットしないこと」を明記。
- config_setup の対話入力ではシークレット項目をマスク表示して取り扱いを配慮。

---

今後のリリース候補（例）
- research モジュールの完全実装（ファクター計算ロジック完了・テスト追加）
- ExecutionEngine / Broker のモック・実ブローカの統合テスト、API レスポンスのモニタリング拡充
- monitoring の設定を環境ごとに切り替え可能にするオプション（現在は production sqlite_path 固定）
- 単体テスト・CI 設定の追加、型チェック／静的解析の強化

---