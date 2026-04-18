# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
日付はリリース日時（YYYY-MM-DD）で記載します。

## [Unreleased]

（現在未リリースの変更はありません）

---

## [0.1.0] - 2026-04-18

初回公開リリース。以下の主要機能・ユーティリティを含みます。

### Added（追加）
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（data/paper_trading.db を既定）を使用し、本番 DB と分離して動作。
    - BrokerClientFactory により実運用 / モックブローカー（ペーパートレード）を透過的に選択。
    - ExecutionEngine をスレッドで実行し、data/stop_requested.flag による停止フラグ検出・エンジン停止をサポート。
    - 実行中 PID を data/execution.pid に保存する仕組み（pid_file を受け取る）。
    - リスク管理（RiskManager）用デフォルト設定を組み込んだ初期構成を追加。
  - run_monitoring.py
    - SystemMonitor を定期ポーリングで実行する監視プロセス起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB 初期化（init_monitoring_db）を実行し、duckdb への接続も確立。
    - data/stop_requested.flag による停止フラグ検出でループを安全に終了。
    - プロセス優先度を「high」に設定する処理を組み込み（set_process_priority 呼び出し）。

- 設定管理
  - config.py
    - .env 自動読み込み機能を追加（プロジェクトルートを .git / pyproject.toml 基準で探索）。
    - .env および .env.local の読み込み順とオーバーライドルールを実装（OS 環境変数は保護）。
    - .env パーサを強化：export プレフィックス、クォート文字とバックスラッシュエスケープ、行内コメント処理などに対応。
    - Settings クラスを追加し、環境変数への型変換・検証・既定値を提供：
      - DB パス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）
      - PAPER_FILL_MODE（"instant"|"partial"|"never"|"reject" の検証）
      - 各種閾値（CPU/MEMORY/DISK）
      - PID / Kill Flag 関連（KILL_FLAG_CLEAR_ON_START 等）
      - env 判定ユーティリティ（is_live / is_paper / is_dev）
  - config_setup.py
    - 対話式ウィザードで .env を生成 / 更新する CLI を追加。
    - J-Quants, kabuAPI, DB パス, ログレベル, Kill Switch 等の主要設定項目を対話的に入力・保存できる。

- 検証ツール
  - validate_config.py
    - .env と config/*.yaml の設定検証用 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベル・DB パスの存在チェック、YAML ファイルのパース（PyYAML が存在する場合）などを実行。
    - --strict オプションにより警告を失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに対して StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を統一的に設定するユーティリティを追加。
    - LOG_DIR / LOG_LEVEL の解決順を実装し、ディレクトリ作成失敗時はファイル出力をスキップして stdout のみで続行。
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。
    - CPU affinity を最初の N コアに固定する機能を追加（set_cpu_affinity）。

- ポートフォリオ構築・ポジションサイズ計算
  - portfolio/portfolio_builder.py
    - 候補選択（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を追加（既存ポジション・価格マップを元にセクターエクスポージャー算出）。
    - 市場レジームに基づく資金乗数 calc_regime_multiplier を追加（bull/neutral/bear のマッピング）。
  - portfolio/position_sizing.py
    - allocation_method ("risk_based" / "equal" / "score") に基づく発注株数算出を実装。
    - lot_size（単元株）考慮、max_position_pct, max_utilization, cost_buffer による総投下額のスケール調整、端数配分ロジックを実装。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）から検証レポートを生成する CLI を追加。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ、リスク却下数などの指標を計算して PASS/FAIL 判定を行う。
    - P95 計算、日付フィルタ、出力フォーマットを実装。

- リサーチ（ファクター計算）
  - research/factor_research.py
    - ファクター計算モジュールの骨組みを追加（モメンタム・ボラティリティ・バリュー等の設計と定数定義）。
    - calc_momentum の実装を開始（関数シグネチャとドキュメントを含む）。

### Changed（変更）
- ログ出力
  - logging_setup にてコンソール出力は stderr ではなく stdout に統一（cron/Task Scheduler 等でのリダイレクトを想定）。

### Fixed（修正）
- 環境読み込みの堅牢化
  - .env 読み込み時にファイル読み込み失敗で警告を出すようにしてクラッシュを回避。
  - .env の読み込み順と保護キー（OS 環境変数）を導入し、意図しない上書きを防止。

### Notes / Implementation details（補足・実装注記）
- run_monitoring は説明コメントの通り「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用」する設計になっています。対して run_execution は環境により paper_trading 用 DB を切り替えます（本番データの隔離を重視）。
- Settings.paper_fill_mode やその他の設定はバリデーションを含むため、環境変数の誤設定は起動時に早期に検出されます。
- position_sizing の aggregate cap と残差配分アルゴリズムは単元（lot_size）単位での再現性を重視した実装になっています。
- research/factor_research.py は現状で完全実装されていない関数（ファイル末尾が途中で終わるなど）があります。今後のリリースで完全な因子計算ロジックを追加予定です。

### Breaking Changes（互換性に注意すべき点）
- 本リリースは初回として後方互換性の破壊事項はありませんが、.env の自動読み込み／保護動作により従来の環境注入フローに影響が出る可能性があります。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化できます。

---

（以降のリリースでは Unreleased セクションに変更を積み上げてください）