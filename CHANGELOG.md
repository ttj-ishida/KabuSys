CHANGELOG
=========

すべての変更は Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）準拠で記載しています。

既知の自動推測事項:
- この履歴は提供されたソースコードから機能追加・設計意図を推測して作成しています。
- 実際のコミット履歴やリリースノートとは差異がある可能性があります。

Unreleased
----------
（現在なし）

0.1.0 - 2026-04-24
-----------------

Added
- 全体
  - 初回リリース相当の基本機能群を追加。
  - パッケージ version を `__version__ = "0.1.0"` として定義。

- 起動スクリプト
  - 実行エンジン起動スクリプト: run_execution.py を追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離する処理を実装。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager/Reconciler/RiskManager を組み立てて ExecutionEngine をスレッドで起動。
    - 停止制御: data/stop_requested.flag を検知するとエンジン停止。起動時に同フラグがある場合は起動をスキップ。
    - PID ファイル（data/execution.pid）をサポート。
    - RiskManager 用のデフォルト RiskConfig を設定（max_position_pct, max_utilization, rate_limit_per_sec 等）。

  - 監視ループ起動スクリプト: run_monitoring.py を追加。
    - SystemMonitor を sqlite（monitoring DB）と DuckDB に接続して初期化・ポーリング実行。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は「環境（KABUSYS_ENV）」に関わらず本番 sqlite_path を使用する旨の挙動（コード上明示）。

- 設定・環境管理
  - config.py を追加 / 拡充
    - プロジェクトルートを .git または pyproject.toml を基準に自動検出し、.env/.env.local を自動読み込み（OS 環境変数が優先）。
    - .env パーサ（export 対応、クォート内のエスケープ処理、インラインコメント対応）を実装。
    - 環境変数取得のラッパー Settings クラスを提供（各種必須/任意設定、型変換、バリデーションをサポート）。
    - PAPER_FILL_MODE（paper trading の fill 挙動）などの明示的な有効値チェックを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。

  - 環境設定ウィザード CLI: config_setup.py を追加
    - 対話式に .env の初期作成・更新を支援するウィザードを実装。
    - シークレット項目は表示をマスク、.env のテンプレート／書式を出力する _write_env を実装。

  - 設定検証 CLI: validate_config.py を追加
    - 起動前に必須環境変数や config/*.yaml の存在・パース（PyYAML があれば検証）をチェック。
    - プレースホルダ値の検出や本番環境（KABUSYS_ENV=live）向けの追加警告を実装。
    - --strict オプションで警告を FAIL とするモードを提供。

- ツール
  - Paper Trading 検証レポート: tools/paper_verification_report.py を追加
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト: data/paper_trading.db）から集計して検証レポートを出力。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率、P95 レイテンシなどを計算し、閾値に基づく PASS/FAIL 判定機能を追加。
    - CLI オプションで期間指定（--from, --to）および DB パス指定（--db）に対応。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）: score 降順、同点時は signal_rank によるタイブレーク。
    - 重み算出: 等分配（calc_equal_weights）とスコア加重（calc_score_weights）。全スコアが 0 の場合は等分配にフォールバックして警告を出力。

  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）: 既存ポジションのセクター比率に基づき新規候補を除外するロジックを実装（"unknown" セクターは除外対象外）。
    - レジーム乗数（calc_regime_multiplier）: "bull" / "neutral" / "bear" をマップし、未知レジームはログ警告とともに 1.0 にフォールバック。

  - portfolio/position_sizing.py
    - position size 計算（calc_position_sizes）:
      - risk_based（リスクベース）と equal/score（配分ベース）両方式をサポート。
      - 単元株（lot_size）で丸め、1 銘柄上限・合計投下上限（available_cash）を考慮。
      - cost_buffer を考慮した保守的なコスト見積りと、合計が available_cash を超えた際のスケールダウン／残差配分アルゴリズムを実装。
      - 価格欠損（price が None/<=0）の銘柄はスキップする防御的実装。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30世代保持）を設定するユーティリティを提供。
    - 既存ハンドラをクリアして二重設定を防止、LOG_DIR 環境変数またはデフォルト logs/ を使用。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。

  - utils/process_priority.py
    - プロセス優先度（set_process_priority）と CPU affinity（set_cpu_affinity）設定ユーティリティを追加。
    - Windows（psutil の priority constants）と POSIX（nice 値）を吸収してプラットフォーム差分を隠蔽。権限不足や未対応 OS は警告を出してスキップ。

  - その他
    - パッケージの util / tools / portfolio / research ベースの雛形実装を多数追加。

Changed
- なし（初回リリースであるため変更履歴は初出として記載）。

Fixed
- なし（初回リリース）。

Deprecated
- なし。

Removed
- なし。

Security
- なし特記事項。ただし .env は「絶対に Git にコミットしないこと」としてテンプレートに注意書きを追加。

Notes / Breaking changes / Important behaviors
- run_monitoring はコード上、環境（KABUSYS_ENV）にかかわらず「本番 sqlite_path（Settings.sqlite_path）」を使用して監視データを記録します。テスト/開発で分離したい場合は設定や DB パスに注意してください。
- run_execution は paper_trading 環境で専用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使う実装になっており、本番データと分離されています。
- 自動 .env ロードはデフォルトで有効。自動ロードを抑止するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Settings のプロパティはバリデーションを行い、不正な値（例: KABUSYS_ENV や LOG_LEVEL の不正値、PAPER_FILL_MODE の不正値）では ValueError を送出します。起動前に validate_config を実行して検証することを推奨します。
- ログは標準出力（stdout）とファイルの両方に出力されます。ログディレクトリの作成に失敗した場合はファイル出力は無効化され、標準出力のみになります。
- process_priority の設定は権限不足・プラットフォーム未対応時に警告を出してスキップします。必ずしも成功する保証はありません。

Known issues / TODO（コードから推測）
- research/factor_research.py はモメンタム計算や他のファクター計算の実装があり途中で切れている（スニペット末尾で未完）。ファクター群全体の実装・テストが必要。
- price が欠損（0.0 や None）の場合の挙動に注意: 現状はスキップや過少見積りにつながる可能性があり、前日終値などのフォールバック価格を導入することが想定されている（TODO コメントあり）。
- portfolio の将来的拡張として銘柄毎の lot_size（単元）サポートや更なる資金配分ロジックの改善が検討されている旨コメントあり。

補足: 環境変数一覧（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (監視 DB、デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト data/paper_trading.db)
- LOG_LEVEL (デフォルト INFO)
- LOG_DIR (ログ出力ディレクトリ、デフォルト logs/)
- MONITOR_POLL_INTERVAL (監視ポーリング間隔、デフォルト 60)
- PAPER_FILL_MODE (instant | partial | never | reject)
- KILL_FLAG_CLEAR_ON_START (0|1)

--- 
以上。必要であれば各変更点の詳細な説明や、README・リリースノートの追記用テキストを生成します。どの項目を展開しますか？