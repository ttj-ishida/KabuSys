CHANGELOG
=========
すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています。
https://keepachangelog.com/ja/1.0.0/

[Unreleased]
-------------

（現在なし）

[0.1.0] - 2026-04-18
--------------------

Added
- 初期リリース: kabusys パッケージを追加。
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
- 起動スクリプト / サービス
  - run_execution.py
    - ExecutionEngine の起動エントリポイントを追加。
    - プロセス優先度を"high"に設定。
    - KABUSYS_ENV=paper_trading の場合は paper 用 SQLite（data/paper_trading.db または PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離。
    - BrokerClientFactory により実環境/モックブローカーを切り替え。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、EngineConfig で当日の日付を指定して ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）を扱う仕組みを実装。停止時は安全にシャットダウン。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視では KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する（監視専用 DB を統一して使用する設計）。
    - stop フラグファイル検知でループ終了、例外発生時はログ出力して次ポーリングへ継続。
- 設定 / 開発支援
  - config.py
    - .env 自動ロード機能を追加（プロジェクトルートの .env / .env.local を読み込み、OS 環境変数を保護）。
    - .env ファイルの柔軟なパース（export プレフィックス、シングル/ダブルクォート、インラインエスケープ、コメント処理）。
    - Settings クラスを実装し、各種設定（J-Quants トークン、kabu API、DB パス、paper_trading 関連、監視閾値、環境名、ログレベル等）をプロパティ経由で取得・バリデーション可能に。
    - PAPER_FILL_MODE の妥当性チェック、KABUSYS_ENV / LOG_LEVEL の検証を実装。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加（マスク表示、デフォルト・選択肢サポート、保存確認）。
    - .env 書き出しテンプレートおよび注意文（.env を Git にコミットしない旨）を含む。
  - validate_config.py
    - 起動前設定検証ツールを追加（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ確認、config/*.yaml の存在/パース確認（PyYAML があれば））。
    - --strict モードで警告も失敗扱いに可能。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START 設定の注意喚起）。
- ロギング / 実行環境ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテート）を設定するユーティリティを追加。
    - LOG_LEVEL / LOG_DIR の解決順を実装。既存ハンドラの二重設定を防止するため一旦クリアする。
    - ファイル出力用ディレクトリ作成失敗時はコンソール出力のみでフォールバック。
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（high/normal/low）を設定するユーティリティを追加。Windows と POSIX (Linux/macOS/FreeBSD) を吸収。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加（存在しない環境や権限不足時は警告ログでフォールバック）。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄選定（select_candidates）、等金額配分（calc_equal_weights）、スコア重み配分（calc_score_weights）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジームに基づく資金乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py
    - position size 計算（risk_based / equal / score）を実装。単元株丸め、1 銘柄上限、aggregate cap のスケーリング、cost_buffer を考慮した安全な配分ロジックを含む。
  - package エクスポート（kabusys.portfolio）を整備。
- 解析 / ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）。
    - 稼働率、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなどを集計し、閾値に基づく PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ、見やすいテキスト出力を提供。
- その他
  - monitoring_db 初期化関数 init_monitoring_db を実行開始時に呼び出すことで監視テーブルの冪等初期化を保証（monitoring と execution の両方から呼出し）。

Changed
- ロギングのデフォルト挙動を stdout に統一（cron / Task Scheduler での運用を想定して stderr ではなく stdout を使用）。
- 監視プロセスは監視用 DB（Settings.sqlite_path）を明示的に使用するように設計。これにより監視データは環境に依存せず一貫して集計可能。

Fixed
- 起動時のハンドラ二重登録を回避するためのログハンドラ再設定処理を追加。
- ExecutionEngine 起動前に監視テーブルが存在することを保証（init_monitoring_db の呼び出しを追加）。

Security
- config_setup の生成 .env に対して「.env は絶対に Git にコミットしないこと」という注意を明示。

Notes / Migration
- 環境変数の自動読み込み:
  - デフォルトでプロジェクトルートの .env / .env.local が自動読み込みされます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 重要な環境変数:
  - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD は必須です。validate_config で事前チェックを強く推奨します。
  - MONITOR_POLL_INTERVAL で監視ポーリング間隔を秒単位で指定できます（正の整数）。不正値はデフォルト 60 秒にフォールバックします。
  - PAPER_FILL_MODE（instant|partial|never|reject）と PAPER_TRADING_SQLITE_PATH を用いてペーパートレード動作を制御できます。
  - KILL_FLAG_CLEAR_ON_START=1 を本番環境で設定すると Kill Switch が起動時に自動クリアされます。live 環境では 0 を推奨します。
- Paper Trading と本番 DB は明示的に分離されています。paper_trading モード時は paper_sqlite_path が使用され、本番の monitoring.db を汚すことはありません。

Known issues / Limitations
- DuckDB / PyYAML 未インストール環境では、該当する機能（YAML 検証や DuckDB ベースの解析）がスキップまたは一部制限されます（validate_config / research / analysis 系）。
- 一部モジュールは将来的な拡張（例: 銘柄ごとの lot_size マスタ化、価格フォールバックロジック等）を想定した TODO コメントを残しています。

References
- 実行例:
  - 設定検証: python -m kabusys.validate_config [--strict]
  - 環境作成ウィザード: python -m kabusys.config_setup
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---