# Changelog

すべての注目すべき変更点をここに記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。  

注: 本 CHANGELOG は提示されたコードベースの内容から実装意図を推測して作成しています。

## [0.1.0] - 2026-04-18

### Added
- 初回リリース。以下の主要コンポーネントを追加。
- 起動スクリプト / デーモン
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - 環境に応じて paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を使用してブローカークライアントを生成（KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用する想定）。
    - ExecutionEngine の依存コンポーネント（OrderRepository、OrderManager、RiskManager、Reconciler）を組み立てて実行スレッドで run_session を実行。
    - 起動時にプロセス優先度を "high" に設定し、data/stop_requested.flag を検知して安全に停止する仕組みを搭載。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒、1 未満は無効扱いでデフォルトにフォールバック）。
    - 監視は常に本番の sqlite_path（monitoring DB）を使用する設計。
    - stop フラグ（data/stop_requested.flag）を検知してループを終了。

- 設定・検証・セットアップ
  - config.py
    - Settings クラスを実装。環境変数から各種設定（DB パス、API トークン、KABUSYS_ENV、ログレベル、各閾値など）を提供。
    - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。.env / .env.local の読み込み順序と保護された OS 環境変数の扱いをサポート。
    - .env 行のパースは export プレフィックス、クォート処理、インラインコメントの扱いなどを考慮して堅牢化。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、KILL_FLAG_CLEAR_ON_START など Paper/監視に関する設定を用意。
  - validate_config.py
    - 起動前に .env と config/*.yaml の設定ミスを検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在／パースチェック（PyYAML がない場合はスキップ）、本番時の追加ガードを実装。
    - --strict オプションで警告を失敗扱いにできる。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成／更新する CLI を追加。
    - 必須項目と推奨デフォルト、シークレット入力（マスク表示）に対応し、最終確認後に .env を書き出す。デフォルトはプロジェクト直下の .env。
    - .env の読み書きロジック（既存値の再利用、export付き行の対応、ファイルテンプレート）を提供。

- ロギング／プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ初期化関数 setup_logging を実装。
    - stdout への StreamHandler（stdout を使用）と、日次ローテーション（TimedRotatingFileHandler）で logs/<app_name>.log に出力。ローテーションは 30 日保持。
    - LOG_LEVEL / LOG_DIR の解決順やファイルハンドラ作成失敗時のフォールバックを考慮。
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度設定（"high"/"normal"/"low"）を実装。
    - Windows の優先度クラスと POSIX の nice 値を扱い、アクセス拒否や未対応 OS の場合は警告を出してスキップ。
    - set_cpu_affinity でカレントプロセスの CPU affinity を最初の N コアに固定する補助関数を追加。

- ポートフォリオ構築関連（純粋関数）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選択（タイブレークは signal_rank）。
    - calc_equal_weights, calc_score_weights: 等金額配分とスコア加重配分（スコア合計が 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクターごとの既存エクスポージャーが閾値を超えると当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: weights / candidates / portfolio_value / available_cash 等を受けて発注株数を計算。
    - allocation_method: "risk_based"（損切り率に基づくリスクベース）と "equal"/"score" をサポート。
    - lot_size（単元株）丸め、per-position および aggregate cap の制約、cost_buffer による保守的見積り、投資額が available_cash を超える場合のスケールダウンと端数処理（lot 単位での再配分）を実装。
    - 価格欠損時のスキップや上限計算の注意コメントあり。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数などを集計して判定（PASS/FAIL）を出力。
    - デフォルト閾値: 稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 latency <= 200 ms。
    - --from / --to / --db オプション対応。PAPER_TRADING_SQLITE_PATH 環境変数を優先して DB を参照。

- 研究モジュール（部分実装）
  - research/factor_research.py
    - ファクター計算（Momentum, Value, Volatility, Liquidity）設計の実装を開始。DuckDB を使用して prices_daily / raw_financials から計算する方針。
    - モメンタム関連の定数と calc_momentum の冒頭を実装（ファイル末尾で途切れあり。以降の実装が続く想定）。

- パッケージ初期化
  - __init__.py に __version__ = "0.1.0" を設定。主要モジュールを __all__ に追加。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- セキュリティ関連: .env の取り扱いに関する注意文（config_setup.py 内、.env を絶対に Git にコミットしない旨）を明記。

### Notes / その他の設計判断（ドキュメント的補足）
- 自動 .env ロードはプロジェクトルートが検出できない場合はスキップされるため、配布後やテスト環境での安全性が考慮されている。
- logging_setup は stdout を利用する設計（cron/Task Scheduler での出力リダイレクトを想定）。
- process_priority はプラットフォーム依存の失敗を穏やかに扱う（AccessDenied 等では警告を出して続行）。
- position_sizing の aggregate cap スケールダウン時の端数処理は再現性を保つためソートの安定性を考慮している。

---

将来的な変更（例）
- research/factor_research.py の未完実装を完了させる。
- strategy / execution の統合テスト、Paper と Live のさらなる差分テスト。
- 単体テスト・CI の整備（現在のコードからはテストフレームワーク設定が見えません）。

もし特定ファイルや変更点についてより詳しい説明や別フォーマット（英語版、GitHub リリース用ノート等）が必要であれば指示してください。