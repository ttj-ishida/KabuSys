KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠しています。  
さらに詳細な変更理由や設計メモは各モジュール内のドキュメントコメントを参照してください。

## [Unreleased]

（今後の変更用）

## [0.1.0] - 2026-04-24

初回公開リリース。

### Added
- 全体
  - パッケージ初版を追加（バージョン 0.1.0）。日本株自動売買システム「KabuSys」の基盤機能を実装。
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 設定管理
  - 環境変数・設定管理モジュールを追加（src/kabusys/config.py）。
    - .env 自動読み込み機能（プロジェクトルート検出: .git / pyproject.toml）。
    - 読み込み優先順位: OS 環境 > .env.local > .env。
    - 複雑な .env 行のパース対応（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント規則）。
    - 必須 env 取得ヘルパー _require、Settings クラスで全アプリ設定をプロパティとして提供（DB パス、API トークン、paper_trading 切替等）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。

- 設定関連 CLI
  - 対話式設定ウィザード（src/kabusys/config_setup.py）
    - .env ファイルの初期作成・更新を対話式に支援。シークレット項目のマスク表示、デフォルト値、選択肢対応。
    - 書き出しテンプレートを生成（.env に保存）。README 的なヘッダと注意文言を付与。
  - 設定検証ツール（src/kabusys/validate_config.py）
    - 起動前に .env と config/*.yaml を検証する CLI。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、YAML パース（PyYAML が未インストールの場合は警告）等。
    - --strict オプションにより警告を FAIL 扱いにできる。

- 実行スクリプト
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor を用いたポーリングループ。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV に関わらず本番用 sqlite_path を使用。
    - stop_requested.flag による安全な停止検知。
    - 起動時にプロセス優先度を high に設定。

  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - ExecutionEngine 起動ロジック。KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db 等）を使用し、MockBrokerClient を使って本番 DB と完全分離。
    - BrokerClientFactory 経由でブローカークライアントを作成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて Engine を起動。実行はデーモンスレッドで行い、stop_requested.flag の監視で停止。
    - PID ファイル管理（execution.pid）サポート。
    - 起動時にプロセス優先度を high に設定。

- 監視・DB 初期化
  - 監視用 DB 初期化ユーティリティ参照（monitoring_db の init_monitoring_db を呼び出す箇所を run_monitoring/run_execution に追加）により監視テーブルが存在することを冪等的に保証。

- ユーティリティ
  - 統一ログセットアップ（src/kabusys/utils/logging_setup.py）
    - コンソール出力（stdout）および日次ローテートファイル出力（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリの解決順: 引数 > LOG_DIR 環境変数 > デフォルト logs/。ファイルハンドラ作成失敗時はコンソールのみで継続。
    - ログレベル解決: 引数 > LOG_LEVEL 環境変数 > デフォルト INFO。
    - 既存ハンドラを安全にフラッシュ/クローズしてから再設定し、二重設定を防止。

  - プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX の差分を吸収してプロセス優先度を設定。
    - psutil を使い nice 値や Windows 優先度クラスを設定。権限不足や未対応 OS は警告してスキップ。
    - CPU affinity を最初の N コアに固定する関数を提供（エラーハンドリングあり）。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順で上位 N を選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア全て 0 の場合に等配分へフォールバック）。

  - セクター制約・レジーム調整（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター別エクスポージャーに基づき、新規候補を除外するロジック（unknown セクターは除外なし）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear -> 1.0/0.7/0.3）。未知のレジームは 1.0 にフォールバック（警告）。

  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method（risk_based / equal / score）に対応した発注株数計算。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap のスケールダウン、cost_buffer を考慮した保守的見積り、残余キャッシュによる端数配分などを実装。
    - price 欠損時のスキップ処理およびログ出力。

- リサーチ
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - Momentum / Value / Volatility / Liquidity の設計と計算方針を実装。DuckDB 接続を受け prices_daily / raw_financials を参照して計算する設計。
    - モメンタム計算関数 calc_momentum の骨組みを実装（対象期間やウィンドウ設定などの定数を定義）。
    - （注: ソースの末尾に未完の行があり、今後の実装・単体テストが想定される）

- ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
    - SQLite の paper_trading DB を読み、システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）を集計してレポートを標準出力に出力。
    - デフォルト基準値（稼働率 99%、注文成功率 90% など）に基づく PASS/FAIL 判定を実装。
    - 日付フィルタ（--from / --to）、--db オプション、環境変数 PAPER_TRADING_SQLITE_PATH に対応。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 機密情報（API トークン等）は .env に格納する設計。config_setup にて .env を生成する際は「絶対に Git にコミットしないこと」と明記。

Notes / Known issues
- research/factor_research.py の末尾に未完の箇所（途中で切れている行）があり、モメンタム計算関数の完全実装と単体テストが必要です。
- position_sizing の価格欠損時の挙動（price が 0.0 の場合、エクスポージャーが過少見積もられる）が TODO コメントとして残されています。将来的にフォールバック価格の導入を検討してください。
- 一部機能は外部モジュール（psutil、PyYAML、duckdb、jquants 等）に依存します。実行環境にこれらが不足すると一部チェックや機能がスキップ/警告となるため、デプロイ前に validate_config を実行して依存関係と設定を確認してください。

-- END --