CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠します。

リリース日付はコード内の参照や実装時点を基に推定しています。

Unreleased
----------

（なし）

0.1.0 - 2026-04-23
-----------------

Added
- 初回リリース: KabuSys 自動売買フレームワークの主要モジュールを追加。
  - 実行 / 監視ランナー
    - run_execution.py
      - ExecutionEngine を起動するエントリポイント。
      - KABUSYS_ENV=paper_trading 時は paper 用専用 SQLite（data/paper_trading.db、環境変数で上書き可）を使用して本番 DB と分離。
      - ブローカークライアントを BrokerClientFactory から生成し、OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて ExecutionEngine をスレッドで実行。停止フラグ（data/stop_requested.flag）で安全に停止可能。
      - 起動時にプロセス優先度を "high" に設定。
      - 実行 PID を data/execution.pid に書き出す仕組み（Engine 側の pid_file を利用）。
    - run_monitoring.py
      - SystemMonitor のポーリングループを起動するエントリポイント。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下はデフォルトにフォールバックして警告を出す）。
      - 監視は環境にかかわらず production の sqlite_path を使用（monitoring 用 DB の初期化を保証）。
      - 停止フラグ（data/stop_requested.flag）でループを終了可能。
  - 設定管理
    - config.py
      - .env 自動ロード（.env, .env.local）機能。プロジェクトルートの検出（.git または pyproject.toml）に基づくため CWD に依存しない。
      - .env パーサは export 形式、クォート文字列、インラインコメントの扱いを考慮した頑健な実装。
      - Settings クラス: J-Quants / kabu API / DB パス / PID/Kill flag 周り / 監視閾値 / 環境（development, paper_trading, live）等のプロパティを提供。PAPER_FILL_MODE のバリデーションを実装。
      - settings = Settings() をモジュールグローバルに提供。
    - config_setup.py
      - .env を対話式に作成・更新するウィザード CLI を実装。秘密項目はマスク表示し、保存前の確認を行う。
  - 検証ツール
    - validate_config.py
      - .env および config/*.yaml の存在 / 基本整合性をチェックする CLI。--strict オプションで警告も失敗扱いにできる。
      - 本番（KABUSYS_ENV=live）用の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）。
  - ツール
    - tools/paper_verification_report.py
      - ペーパートレード DB（デフォルト: data/paper_trading.db）から検証レポートを生成する CLI。
      - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ等を計算して PASS/FAIL 判定（閾値はソース内定義）。
  - ポートフォリオ構築（純粋関数群、メモリ内計算）
    - portfolio/portfolio_builder.py
      - select_candidates: スコア降順（同点時は signal_rank 昇順）で候補選定。
      - calc_equal_weights / calc_score_weights: 等金額配分およびスコア正規化配分（全スコアが 0 の場合は等重でフォールバック）。
    - portfolio/risk_adjustment.py
      - apply_sector_cap: 既存保有のセクター別エクスポージャを計算し、上限を超えるセクターの新規候補を除外（"unknown" セクターは除外せず）。
      - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear、未知は 1.0 でフォールバック）。
    - portfolio/position_sizing.py
      - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に基づく発注株数算出。単元株（lot_size）丸め、per-stock 上限（max_position_pct）や aggregate cap（available_cash）を考慮したスケーリング実装。cost_buffer による保守的コスト見積りと残余配分アルゴリズムを含む。
  - ユーティリティ
    - utils/logging_setup.py
      - StreamHandler を stdout に設定（cron 等との扱いを意識）、TimedRotatingFileHandler で日次ローテーション（30 日保持）。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - utils/process_priority.py
      - set_process_priority / set_cpu_affinity を提供。Windows と POSIX（Linux/Mac/FreeBSD）に対応し、psutil を用いて優先度や CPU affinity を設定。権限不足や未対応 OS は警告を出してスキップ。
  - リサーチ
    - research/factor_research.py（ファクター計算基盤）
      - DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity などのファクターを計算する目的で作成。モメンタム計算の設計・定数が実装済み（未完の箇所あり）。
  - パッケージ情報
    - __init__.py にバージョン __version__ = "0.1.0" を追加。

Changed
- （初回リリースのためなし）

Fixed
- （初回リリースのためなし）

Deprecated
- （初回リリースのためなし）

Removed
- （初回リリースのためなし）

Security
- .env は絶対に Git にコミットしない旨を config_setup のヘッダに明記。
- Settings._require() は必須環境変数未設定時に ValueError を投げ、起動前の明確な失敗を促す。

Notes / Implementation details
- DB 関連
  - SQLite と DuckDB を併用（監視・履歴は SQLite、分析は DuckDB を想定）。run_monitoring/run_execution はそれぞれ sqlite3 と duckdb 接続を生成して利用。
  - monitoring テーブルの初期化を init_monitoring_db() で保証（冪等）。
- 環境変数取り扱い
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD によって抑制可能。
  - .env の読み込みでは OS 環境変数を保護（.env.local を上書き可能だが既存の OS 環境変数は保護）。
- ロギング/運用
  - 全起動スクリプトで使用可能な統一ロギングセットアップを提供（アプリ名別にログファイルを切り分け）。
  - run_* スクリプトはいずれも起動直後にプロセス優先度を "high" に設定し、停止フラグ経由で安全に停止できる設計。

将来の改善候補（明示的メモ）
- factor_research.calc_momentum 等の未完部分の実装完了。
- position_sizing: 銘柄別単元（lot_size）のマスタ対応（現在は共通 lot_size）。
- apply_sector_cap の price フォールバック（price が 0 の場合の扱い改善）。
- ExecutionEngine / EngineConfig 周りの外部公開 API のドキュメント充実。

--- 

（この CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノートとして使用する場合は、変更の意図や日付等をプロジェクト実態に合わせて調整してください。）