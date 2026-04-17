# CHANGELOG

すべての重要な変更点は Keep a Changelog の形式に従って記載しています。

注意: 以下はリポジトリ内のコード内容から推測して作成した変更履歴です。

## [Unreleased]

（特になし）

## [0.1.0] - 2026-04-17

Added
- 初回リリース。KabuSys 自動売買フレームワークの基礎機能を実装。
- 環境設定 / 管理
  - Settings クラスを実装し、環境変数から各種設定（J-Quants / kabuAPI / DB パス /監視閾値など）を読み取る機能を提供。
  - .env 自動読み込み機能を追加（プロジェクトルートの判定: .git または pyproject.toml）。OS 環境変数を保護して .env / .env.local を適切にマージする。
  - .env の行パーサーを強化（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント解析の改善）。
  - PAPER_FILL_MODE のバリデーションや KABUSYS_ENV / LOG_LEVEL の許容値チェックを実装。
- 対話式セットアップ・検証ツール
  - config_setup: 対話式ウィザードで .env を作成・更新する CLI を追加（必須項目・デフォルト・マスク表示など）。
  - validate_config: .env と config/*.yaml の整合性チェック CLI を追加。--strict オプションで警告をエラー扱いにできる。PyYAML 未インストール時のフォールバックメッセージ、production 環境向けの追加警告（LINE 通知未設定や Kill Flag 自動クリア設定など）を含む。
- 実行系 / 監視系ランチャー
  - run_execution: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite を使用して本番 DB と分離し、BrokerClientFactory を通して MockBrokerClient を利用可能。
    - 起動時にプロセス優先度を "high" に設定（utils のユーティリティを使用）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで起動。data/stop_requested.flag による停止制御や execution.pid の管理を実装。
    - RiskManager に初期デフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を用意し、初期ポートフォリオ値をブローカから取得して設定に反映。
  - run_monitoring: SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックしてログ出力。
    - 監視は常に本番 sqlite_path を使用（KABUSYS_ENV に依存しない挙動）。
    - 停止フラグ（data/stop_requested.flag）検知、例外ハンドリング、clean-up（DB 接続クローズ）を実装。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio.portfolio_builder: シグナルから候補選定（スコア降順、signal_rank によるタイブレーク）、等金額・スコア加重配分計算を実装。全スコア 0 の場合は等金額へフォールバックして警告を出力。
  - portfolio.risk_adjustment:
    - セクター集中制限 apply_sector_cap を実装（既存保有のセクターエクスポージャーを計算し、上限超過セクターの候補除外）。
    - レジームに応じた資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピングと未知レジーム時のフォールバック）。
  - portfolio.position_sizing:
    - 複数の配分方式（risk_based / equal / score）に基づく株数計算を実装。損切り幅・リスク許容度・単元株（lot_size）・コストバッファを考慮。
    - aggregate cap（利用可能現金を超える場合のスケーリング）と、小数端数処理（lot_size 単位での再配分アルゴリズム）を実装。
- 研究用ファクター計算
  - research.factor_research: DuckDB 接続を受け取り、prices_daily テーブルから Momentum / Volatility 等のファクターを計算する関数群（例: calc_momentum, calc_volatility）を追加。計算のスキャン範囲や欠損時の扱いについてドキュメントを含む。
- ユーティリティ
  - utils.process_priority:
    - プロセス優先度設定（Windows と POSIX を抽象化して set_process_priority を提供）。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を追加。
    - 権限不足や未対応環境では警告を出して安全にフォールバック。
- 検証 / レポートツール
  - tools.paper_verification_report:
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から検証用レポートを生成する CLI を追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを集計して PASS/FAIL 判定を行う。閾値はソース内で定義され、期間フィルタ（--from / --to）に対応。
    - P95 の計算、各種 SQL クエリ断片（system_status / trade_logs / risk_logs）と、データ欠損時の N/A 処理を実装。

Changed
- パッケージ初期化ファイルに __version__ = "0.1.0" を設定。

Fixed
- .env 読み込み時のエスケープやコメント処理を改善し、より実環境の .env 形式に対応（export プレフィックスや引用符内のバックスラッシュ等）。

Security
- .env を生成する際に README 的注意書き（.env を Git にコミットしない）を出力するテンプレートを実装（config_setup）。

Notes / Implementation details
- DB 関連:
  - 監視用 DB（SQLite）と分析用 DB（DuckDB）を明確に分離。paper_trading モードでは SQLite も分離して使用する設計。
  - monitoring_db の初期化関数（init_monitoring_db）を利用して監視テーブルの冪等な初期化を行う実装を組み込んでいる。
- 実行 / 監視の停止制御:
  - data/stop_requested.flag による外部停止トリガーを採用。
  - run_execution はスレッドでエンジンを動作させ、停止フラグ検知時に engine.stop() を呼び出して安全終了を試みる。
- ログ / 標準出力:
  - 各 CLI スクリプトは logging.basicConfig(level=logging.INFO) を使用して情報レベルでログ出力するようになっている。
- エラー耐性:
  - ポーリングループやレポート生成での SQL 実行時に OperationalError をキャッチして N/A / 0 として扱う等、実運用を意識した堅牢化が図られている。

既知の制約 / TODO（コード内コメントより）
- position_sizing: 銘柄ごとの lot_size を将来的に stocks マスタ等から取得する拡張を想定。
- risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積りされるリスクがあり、前日終値等のフォールバック導入を検討。
- research.factor_research / config.yaml の検証: PyYAML 未インストール時は YAML 内容検証をスキップするため、CI 等での導入時は要注意。

------------------------------------
この CHANGELOG はコードベースの実装内容から推測して作成しています。実際のリリースノートとして使用する場合は、コミット履歴やリリース担当者による確認・編集を推奨します。