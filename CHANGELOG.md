# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
（コードから推測して作成した初期のリリースノートです）

全般のバージョンポリシー: SemVer 準拠を想定。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-19
初回リリース。KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、設定管理ツール、および検証・分析用スクリプトを実装。

### Added
- 基本情報
  - パッケージ初期バージョンを設定（kabusys.__version__ = "0.1.0"）。
- 起動スクリプト
  - run_execution: 実行エンジン（ExecutionEngine）起動スクリプトを追加。
    - プロセス優先度を「high」に設定。
    - KABUSYS_ENV に応じて paper_trading 用 DB を分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine をスレッドで実行。
    - data/execution.pid（PID ファイル）、data/stop_requested.flag（停止フラグ）を利用した起動・停止制御。
  - run_monitoring: 監視（SystemMonitor）ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番 sqlite_path（data/monitoring.db）を使用して監視テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）でループ終了。
- 設定管理
  - config.Settings クラスを実装。
    - 環境変数経由で各種設定を提供（J-Quants / kabu / DB パス / モード判定など）。
    - PAPER_FILL_MODE（paper trading の fill 動作）、PAPER_TRADING_SQLITE_PATH、各種閾値等のプロパティを実装。
    - env の検証（development / paper_trading / live）や LOG_LEVEL 検証を行う。
  - 自動 .env ロード機能を実装（プロジェクトルート検出: .git / pyproject.toml を探索）。
    - .env と .env.local の読み込み順序をサポート。OS 環境変数の保護機構あり。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - config_setup: .env 初期作成／更新の対話式ウィザードを追加。
    - 項目定義、既存 .env 読み込み、保存テンプレート生成を実装。
    - 秘密項目はマスク表示。Enter で既存値・デフォルトを利用可能。
- 設定検証
  - validate_config CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML があれば）パース検証を実施。
    - --strict オプションで警告も失敗扱いにできる。
    - 本番（live）向けの追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性）を実装。
- ロギング / プロセス制御ユーティリティ
  - utils.logging_setup.setup_logging を追加。
    - stdout 出力の StreamHandler と 日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR / app_name / LOG_LEVEL の優先解決を実装。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - 既存ハンドラのクリーンアップ（二重設定防止）を実装。
  - utils.process_priority を追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）を抽象化してプロセス優先度（high/normal/low）設定、CPU affinity の設定機能を提供（psutil に依存）。
    - 権限不足や未対応 OS では安全にスキップして警告出力。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのスコア降順ソート、上位 N 件抽出。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分。スコア合計 0 の場合は等配分へフォールバック（警告）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中を抑える候補フィルタ（既存保有のセクター比率に基づく除外）。"unknown" セクターは制限対象外。
    - calc_regime_multiplier: market regime による資金乗数（bull:1.0, neutral:0.7, bear:0.3）。未知レジームは 1.0 にフォールバック（警告）。
  - portfolio.position_sizing
    - calc_position_sizes: 複数の配分方式（risk_based / equal / score）に基づく発注株数計算。
    - 単元株（lot_size）丸め、per-position 上限（max_position_pct）、aggregate cap（available_cash）を考慮したスケーリングを実装。
    - cost_buffer を使った保守的なコスト見積り、残差を使った追加配分ロジック（安定的な再現性）を実装。
- 研究／分析ユーティリティ
  - research.factor_research（モジュールを追加）
    - Momentum ファクター計算のための定数と calc_momentum の骨子を追加（DuckDB 接続を想定）。※ファイルは途中までの実装（断片あり）。
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH（または --db）からデータを読み、システム稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を集計。
    - PASS/FAIL 判定と閾値（稼働率 >= 99%, fill_rate >= 90%, send_rate >= 95%, P95 <= 200ms）に基づく判定を実装。
    - 日付範囲フィルタ (--from / --to) をサポート。
- DB 初期化
  - monitoring.monitoring_db.init_monitoring_db の呼び出しを埋め込み（実行時に監視テーブルが存在することを保証、冪等処理）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / 注意事項
- .env 自動読み込みはプロジェクトルート検出に依存するため、配布後は期待通りに動作しない場合があります。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自前で環境変数をセットしてください。
- run_monitoring は監視 DB として settings.sqlite_path（デフォルト data/monitoring.db）を常に使用します。実行環境に関わらず同じ監視 DB を使う設計です。
- run_execution は paper_trading 実行時に専用の paper_trading DB（data/paper_trading.db）を使用して本番 DB と明示的に分離します。
- process_priority / CPU affinity の設定には psutil が必要です。権限やプラットフォームの制約により設定がスキップされる場合がある点に注意してください。
- research.factor_research はモジュールの骨格（Momentum の計算ロジックの一部）まで用意されていますが、完全実装ではない可能性があります。DuckDB を利用する設計のため、テーブル構造（prices_daily / raw_financials）が必要です。

---

（この CHANGELOG はコードの内容から推測して作成しました。実際のリリースノートやユーザー向けドキュメント作成時は、コミット履歴や開発者への確認を推奨します。）