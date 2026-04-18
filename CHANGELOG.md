Keep a Changelog に準拠した形式で、コードベースから推測した変更履歴を日本語で作成しました。現状のリリースバージョンは 0.1.0（__version__ に基づく）として記載しています。

CHANGELOG.md
=============
All notable changes to this project will be documented in this file.

The format is based on "Keep a Changelog" and this project adheres to Semantic Versioning.

[Unreleased]

[0.1.0] - 2026-04-18
--------------------

Added
- 全体
  - 初期リリース (v0.1.0) を追加。パッケージのバージョンは src/kabusys/__init__.py にて定義。
- 起動スクリプト
  - run_monitoring.py を追加。
    - SystemMonitor をポーリングする監視ループを実装。デフォルトポーリング間隔は 60 秒。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（不正値はデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - data/stop_requested.flag の検知で安全にループを終了する。
    - プロセス優先度を起動直後に "high" に設定。
  - run_execution.py を追加。
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、MockBrokerClient を利用可能（BrokerClientFactory により抽象化）。
    - 停止フラグ (data/stop_requested.flag) の検知で安全にエンジン停止。
    - エンジンはスレッドで起動し、PID ファイルを ExecutionEngine に渡して管理。
    - init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。
- 設定関連
  - src/kabusys/config.py を追加。
    - .env 自動ロード機能（プロジェクトルートの .env/.env.local を読み込み。OS 環境変数は保護）。
    - 複雑な .env パーシング実装（export プレフィックス対応、クオート内エスケープ、インラインコメント処理など）。
    - Settings クラスを導入。J-Quants / kabu API / DB パス /監視閾値 / 環境判定（is_live/is_paper/is_dev）等のプロパティを提供。
    - PAPER_FILL_MODE のバリデーションや paper_sqlite_path、kill フラグ等の設定プロパティを含む。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動 .env ロードの無効化オプションをサポート。
- 設定ツール
  - config_setup.py を追加。
    - 対話式ウィザードで .env ファイルの初期作成・更新を支援。
    - シークレット項目はマスクして表示、既存値の再利用やデフォルトをサポート。
    - .env 読み書きのヘルパを提供（_read_env/_write_env）。
  - validate_config.py を追加。
    - 起動前に必須環境変数・config/*.yaml・パス等の検証を行う CLI。--strict オプションで警告を FAIL 扱いにできる。
    - KABUSYS_ENV=live に対する追加確認（LINE 設定や Kill Switch の自動クリアに対する警告）を実施。
- ロギングとプロセス制御
  - utils/logging_setup.py を追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続するフォールバックを実装。
    - ログレベル・ログディレクトリの解決順序を定義（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py を追加。
    - psutil を利用して Windows/Linux/macOS に対してプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）を抽象化して設定。
    - CPU affinity 設定関数 set_cpu_affinity を実装（コア数指定）。
    - 権限不足や未対応プラットフォーム時には警告ログを出して安全にスキップ。
- Portfolio（銘柄選定・配分・発注株数）
  - portfolio/portfolio_builder.py を追加。
    - select_candidates: スコア降順 + signal_rank によるタイブレークで候補抽出。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア全0時は等金額にフォールバック）。
  - portfolio/risk_adjustment.py を追加。
    - apply_sector_cap: セクター毎の既存エクスポージャーを計算し上限超過セクターの候補除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じた資金乗数を返す（未知レジームはフォールバックで 1.0）。
  - portfolio/position_sizing.py を追加。
    - calc_position_sizes: allocation_method（"risk_based"/"equal"/"score"）に対応した発注株数算出。
    - lot_size（単元株）丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap のスケーリング処理を実装。
    - スケーリング時の端数処理で残余キャッシュを使って lot 単位で追加配分するアルゴリズムを実装。
- Tools
  - tools/paper_verification_report.py を追加。
    - Paper Trading の検証レポートを生成する CLI（PAPER_TRADING_SQLITE_PATH を参照）。
    - 稼働率・注文成立率・送信率・レイテンシ（平均/最大/P95）等を集計し、閾値に基づく PASS/FAIL 判定を出力。
    - P95 計算ユーティリティを実装。SQL の日付フィルタリングと各テーブルへの耐障害性（OperationalError のハンドリング）あり。

Changed
- .env の自動読み込み順序を明確化（OS 環境 > .env.local > .env）。既存の OS 環境変数は保護され、.env.local は .env を上書き可能。
- ログ出力のストリームを stderr ではなく stdout に設定（cron/タスクスケジューラ等での扱いやすさ向上）。
- run_*.py スクリプトは起動直後にプロセス優先度を "high" に設定してから主要初期化を実行するように統一。
- DB 初期化（init_monitoring_db）は冪等に呼び出し、監視テーブルの存在を保証するようにした。

Fixed
- .env 解析の堅牢性向上。
  - export プレフィックスのサポート、クオート内のバックスラッシュエスケープ処理、インラインコメント判定（クォートあり/なしでの挙動差異）の取り扱いを実装し、実運用でありがちな .env の書式差に耐えるようにした。
- process_priority / set_cpu_affinity において、権限不足や未対応プラットフォームの場合に例外で落ちないように例外処理を追加（警告ログで継続）。
- logging_setup にてログディレクトリ作成失敗時のフォールバックを実装（ファイルハンドラ作成失敗時にコンソール出力のみで継続）。

Notes / Known issues
- src/kabusys/research/factor_research.py はファクター計算（Momentum 等）のモジュール骨格と定数や設計方針を実装済み。コード末尾に実装途中に見える箇所（calc_momentum の続き）が存在するため、ファクター計算の完全実装は今後の作業を要する可能性あり。
- Execution 関係（ExecutionEngine / BrokerClientFactory / OrderManager 等）はエントリポイントから組み立てて起動するロジックを含むが、外部ブローカー統合部分や ExecutionEngine の詳細実装は本 changelog の対象スナップショットから完全には把握できない点がある。

以上が現コードベースから推測した初期リリース（v0.1.0）の主な追加・変更・修正点です。必要であれば各ファイルごとにより詳細な説明（関数単位の変更ログや使用例、CLI オプションの例など）を追加します。どのレベルの詳細が必要か教えてください。