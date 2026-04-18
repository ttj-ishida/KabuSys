# Changelog

すべての注記は Keep a Changelog 規約に従っています。  
このプロジェクトはセマンティック バージョニングを使用しています。

## [Unreleased]

---

## [0.1.0] - 2026-04-18

### Added
- 初回リリース。日本株自動売買システム "KabuSys" の基本コンポーネントを追加。
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、ブローカークライアント生成、各種マネージャー（OrderManager, RiskManager, Reconciler）組立て、エンジンスレッド管理、停止フラグ（data/stop_requested.flag）検知ロジック、PID ファイル管理を実装。
    - KABUSYS_ENV=paper_trading 時は専用の Paper Trading DB を使用（デフォルト: data/paper_trading.db）して本番 DB と完全分離。MockBrokerClient を利用する想定。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 監視は KABUSYS_ENV に関係なく本番の sqlite_path を使用するよう設計。
- 設定管理
  - config.py
    - .env 自動読み込み機構（.env / .env.local）を追加。OS 環境変数を保護（上書き防止）する仕組みを実装。
    - .env パーサは `export KEY=...`、クォート文字とバックスラッシュエスケープ、インラインコメントの扱いに対応。
    - Settings クラスを提供。J-Quants / kabu API / DB パス / 各種監視閾値 / 実行環境（KABUSYS_ENV）などのプロパティとバリデーションを含む。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）を実装。
    - 環境変数による動作切替（is_live, is_paper, is_dev）を提供。
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を追加。既存 .env の読み込み、シークレットマスク表示、書き込み機能を実装。
  - validate_config.py
    - 起動前チェック用 CLI を追加。必須環境変数、KABUSYS_ENV 値、LOG_LEVEL、DB パス、config/*.yaml の存在・パースチェック、Live 環境向けガード（LINE 設定や Kill Flag 設定）などを検証。--strict モードで警告も失敗扱いにできる。
- ロギング/プロセスユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。stdout ストリームハンドラと日次ローテーション（TimedRotatingFileHandler）でファイル出力（logs/<app_name>.log）を行う。LOG_LEVEL / LOG_DIR による設定、既存ハンドラのクリア処理を実装。
  - utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定ユーティリティを追加（high/normal/low）。CPU affinity 設定関数も提供。権限不足や未サポート環境時は警告を出して安全にスキップする。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（score 降順、タイブレークルール）、等配分・スコア加重配分の関数を実装（calc_equal_weights, calc_score_weights, select_candidates）。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジームに応じた投資乗数（calc_regime_multiplier）を実装。unknown セクターの扱いや、未知レジームのフォールバックを定義。
  - portfolio/position_sizing.py
    - 発注株数計算ロジック（risk_based / equal / score）を実装。単元株（lot_size）での丸め、per-position と aggregate のキャップ、cost_buffer による保守的見積り、スケーリングと残差配分アルゴリズムを含む。
- 研究用モジュール（部分実装）
  - research/factor_research.py
    - DuckDB 上の prices_daily/raw_financials を利用したファクター計算基盤を追加（モメンタム / MA200 / ATR / 流動性等の仕様を定義）。calc_momentum 等の関数設計を含む（実装途中の箇所あり）。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。system_status, trade_logs, risk_logs から稼働率・注文成功率・送信率・レイテンシ等を集計し、閾値（稼働率>=99%、成立率>=90%、送信率>=95%、P95<=200ms）に基づいて PASS/FAIL 判定を出力。--from / --to / --db オプションに対応。
- 監視 DB 初期化
  - monitoring_db.init_monitoring_db を run_* 起動時に呼び出し、監視用テーブルの存在を保障（冪等）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

### Notes / Known limitations / TODO
- apply_sector_cap 内で price が欠損（0.0）だとエクスポージャーが過少見積りされる可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する旨をコメントで残しています。
- research/factor_research.py はモメンタム算出などを含む設計があるものの、ファイル末尾で実装が途中（切れている）ため、完全な計算ロジックの追加が必要です。
- process_priority/set_cpu_affinity は環境により権限エラーが発生するため、権限不足時は警告を出して処理をスキップする実装になっています（安全志向）。
- .env の自動読み込みはデフォルトで有効。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用してください。
- 初期設定や本番運用時は validate_config を使って設定検証を行い、KILL_FLAG_CLEAR_ON_START 等の Live 環境向け設定を注意してください。

---

（今後のリリースでは、各機能の API/内部仕様変更・バグ修正・パフォーマンス改善などをセマンティックバージョニングに沿って記載します。）