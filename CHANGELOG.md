# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このリポジトリの初期リリースとして、バージョン 0.1.0 を登録します。

フォーマット:
- Added: 新機能
- Changed: 変更点（既存機能の変更）
- Fixed: 修正（バグフィックス）
- Removed: 削除

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-18

### Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージバージョンは src/kabusys/__init__.py にて "0.1.0" を設定。

- 環境設定管理 (src/kabusys/config.py)
  - Settings クラスを導入し、環境変数から各種設定を取得するインターフェースを提供。
  - 自動 .env ロード機能:
    - プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動読み込み。
    - OS 環境変数は保護され、.env.local は上書き（.env は上書きしない）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パースロジックを実装（export プレフィックス、クォート文字列、インラインコメント等を考慮）。
  - 各種プロパティを提供（例: duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, 各しきい値、env/log_level 判定等）。
  - PAPER_FILL_MODE のバリデーション（"instant"|"partial"|"never"|"reject"）。
  - env 値（development/paper_trading/live）や LOG_LEVEL の妥当性チェック。

- 設定ウィザード CLI (src/kabusys/config_setup.py)
  - .env の対話式作成/更新ウィザードを実装。
  - 秘密情報はマスクして表示、選択肢やデフォルト提示、保存前確認を行う。
  - 書き出しフォーマットはヘッダコメント付きで .env を生成。

- 設定検証 CLI (src/kabusys/validate_config.py)
  - .env と config/*.yaml の存在・基本妥当性を検査する CLI を提供。
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ確認、PyYAML が無い場合のパーススキップ、KABUSYS_ENV=live 時の追加ガードを実装。
  - --strict オプションで警告も失敗扱いにできる。

- 実行エンジン起動スクリプト (src/kabusys/run_execution.py)
  - ExecutionEngine を起動するエントリポイントを実装。
  - 起動時にプロセス優先度を "high" に設定。
  - paper_trading モード時は専用の paper_sqlite_path（data/paper_trading.db デフォルト）を使用し、本番 DB と隔離。
  - BrokerClientFactory を利用しブローカクライアントを生成（paper_trading の場合は Mock を想定）。
  - OrderRepository、OrderManager、RiskManager（デフォルト RiskConfig を含む）、Reconciler を組み立ててエンジンをスレッド起動。
  - 停止フラグ（data/stop_requested.flag）と pid ファイル（data/execution.pid）による安全な起動/停止制御を実装。

- 監視起動スクリプト (src/kabusys/run_monitoring.py)
  - SystemMonitor のポーリングループの起動スクリプトを実装。
  - 起動時にプロセス優先度を "high" に設定。
  - monitoring 用 DB は環境に関係なく本番 sqlite_path を使用（monitoring 用テーブルの初期化を保障）。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
  - 停止フラグ（data/stop_requested.flag）検出でループを退出、例外発生時はログを出して次ポーリングへ継続。

- ロギングユーティリティ (src/kabusys/utils/logging_setup.py)
  - setup_logging 関数を提供。全起動スクリプトから統一的に使用する想定。
  - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。
  - 既存ハンドラをクリアして二重設定を防止、LOG_DIR 環境変数や引数でログ保存先を指定可能。
  - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみ継続。

- プロセス優先度 / CPU affinity ユーティリティ (src/kabusys/utils/process_priority.py)
  - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。
  - Windows / POSIX（Linux/macOS/FreeBSD）を吸収し psutil 経由で設定。権限不足や未対応 OS 時は警告ログでスキップ。

- ポートフォリオ構築モジュール (src/kabusys/portfolio/*)
  - portfolio_builder:
    - select_candidates: スコア降順 + signal_rank で候補選定。
    - calc_equal_weights, calc_score_weights（スコアゼロ時は等金額にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクターごとの既存エクスポージャーが閾値を超える場合に候補を除外（"unknown" セクターは無視）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear、未知レジームはフォールバックと警告）。
  - position_sizing:
    - calc_position_sizes: allocation_method ("risk_based","equal","score") に基づく株数計算。lot_size 単位で丸め、per-position と aggregate の上限、cost_buffer を用いた保守的見積り、スケーリングと残余の再配分ロジックを実装。

- Paper Trading 検証レポートツール (src/kabusys/tools/paper_verification_report.py)
  - paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）から各種指標を集計する CLI ツール。
  - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、リスク却下数、平均/最大/P95 レイテンシ等。
  - デフォルトしきい値を定義し、PASS/FAIL 判定を出力。
  - 日付フィルタ (--from/--to) と --db オプションをサポート。

- リサーチ／ファクター計算基盤 (src/kabusys/research/factor_research.py)
  - DuckDB 接続を受け、prices_daily / raw_financials を用いてモメンタム等のファクター計算を行う設計を導入（モメンタム: 1M/3M/6M、MA200 乖離等）。
  - 設計方針と定数を定義し、将来的なファクター拡張に対応する基盤を準備。

- 監視 DB 初期化フック参照 (src/kabusys/monitoring/* を参照するコード)
  - init_monitoring_db を呼び出して監視テーブルの冪等な初期化を行う（実装ファイルは別途）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Notes / 運用上の重要点
- デフォルトのパス/値:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db
  - ログディレクトリ: logs/
  - default poll interval: 60 秒（MONITOR_POLL_INTERVAL で上書き可能）
- 本番（live）運用時の注意:
  - validate_config のライブガードが LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の危険設定を警告する。
  - run_execution は paper_trading の場合に DB を完全分離して運用する（本番 DB に影響しない）。
- 停止制御:
  - data/stop_requested.flag の存在を検出して各プロセスが安全に停止する仕組みを導入。
  - run_execution は PID ファイル（data/execution.pid）を利用。
- ログ:
  - コンソール出力は stdout を使用（cron 等からのリダイレクトを意識）。
  - ログファイル作成に失敗した場合はコンソールのみで継続（起動失敗しない）。

---

今後のリリースでは以下を予定しています（例）:
- 監視・実行ロジックのテスト補強（モック注入の改善）
- モジュール間インターフェースのドキュメント化（API レベル）
- research/factor_research の完全実装とユニットテスト追加

もし CHANGELOG に追加したい特定の変更点や日付修正の希望があれば教えてください。