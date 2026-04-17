Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。
コード内容から推測できる追加点・仕様・注意点を記載しています。

なお、バージョンはパッケージの __version__ = "0.1.0" に合わせ、リリース日を現日時（2026-04-17）で設定しています。必要に応じて日付や文言を調整してください。

```
# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

## [Unreleased]

（未リリースの変更はここに記載）

## [0.1.0] - 2026-04-17

### Added
- 基本アプリケーション骨格を追加
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"
- 環境設定管理
  - 自動 .env 読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）
  - .env のパース機能を実装（export プレフィックス、クォート、エスケープ、コメント処理に対応）
  - 環境変数の自動ロード制御: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - Settings クラスを実装し、環境変数から各種設定を取得（検証・デフォルト値・型変換を含む）
    - J-Quants / kabuステーション / LINE / DuckDB / SQLite / Paper Trading 等の設定をプロパティで提供
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）
    - KABUSYS_ENV 値検証（development/paper_trading/live）
    - 各種しきい値（CPU/MEM/DISK）や PID/KILL フラグのパス設定を提供
- 設定ウィザード CLI
  - python -m kabusys.config_setup による対話式 .env 作成・更新機能
  - 既存 .env 読み込み、シークレットのマスク表示、保存確認などを実装
- 設定検証 CLI
  - python -m kabusys.validate_config で必須環境変数・パス・YAML ファイル存在等の検証を実装
  - --strict モードで警告を失敗扱いにできるオプション
  - 本番環境（KABUSYS_ENV=live）向けの追加チェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性）
- 実行 / 監視ランナー
  - run_execution.py: ExecutionEngine 起動スクリプト
    - paper_trading 環境では専用の paper_trading DB を使用し、本番 DB と分離
    - BrokerClientFactory によるブローカークライアント生成（モック対応）
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てと実行スレッド管理
    - 停止フラグ（data/stop_requested.flag）検出で安全停止
    - 実行 PID ファイル管理（data/execution.pid）
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視は環境に関わらず本番 sqlite_path を使用（監視 DB の一貫性を保つ）
    - 監視ループ中の例外を捕捉してログに記録し、ループを継続する堅牢化
- データベース統合
  - DuckDB 接続を利用（分析用 DB: DUCKDB_PATH）
  - SQLite 接続を利用（監視・注文履歴用: SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）
  - 監視テーブル初期化ユーティリティ init_monitoring_db の呼び出しを組み込み（冪等）
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア配分（calc_score_weights）
  - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジーム乗数（calc_regime_multiplier）
  - position_sizing: 発注株数決定（calc_position_sizes）
    - risk_based / equal / score の割当方式サポート
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（利用可能現金に基づくスケーリング）を実装
    - cost_buffer により手数料・スリッページを保守的に見積もるロジックを実装
- 研究モジュール（DuckDB 利用）
  - research.factor_research: モメンタム / ボラティリティ等のファクター計算を実装
    - mom_1m/mom_3m/mom_6m、MA200 乖離、ATR20、20日平均売買代金等の算出（prices_daily テーブル参照）
    - DuckDB のウィンドウ関数を利用した効率的な集計
- ユーティリティ
  - utils.process_priority: プロセス優先度（Windows/Linux の差分吸収）と CPU affinity 設定ユーティリティを実装
    - set_process_priority(level: "high"|"normal"|"low")
    - set_cpu_affinity(cpu_count: Optional[int])
    - 権限不足や未対応 OS を考慮したエラーハンドリングとログ出力
- ツール
  - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプト
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出・判定（閾値はソースに定義）
    - DB パスの上書き（--db オプション / PAPER_TRADING_SQLITE_PATH）

### Changed
- 初版のため該当なし（初回リリースで新規追加が主体）

### Fixed
- 初版のため該当なし

### Deprecated
- 初版のため該当なし

### Removed
- 初版のため該当なし

### Security
- 環境変数ファイル (.env) の生成スクリプトでシークレットをマスク表示し、.env を Git にコミットしない旨の注記を出力

### 注意 / 既知の制限（コード中の TODO / 実装上の注記）
- apply_sector_cap:
  - price_map に価格が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性がある旨をコメントで明記。将来的に前日終値や取得原価でのフォールバックを検討する必要あり。
- calc_position_sizes:
  - 現状は全銘柄共通の lot_size（単元株数）を想定。将来的に銘柄別 lot_map を利用する拡張が想定されている（TODO コメントあり）。
- process_priority / set_cpu_affinity:
  - 権限不足（psutil.AccessDenied）や未対応プラットフォームで設定に失敗した場合は警告ログを出力してフォールバックする実装。実行環境によって期待どおりの優先度設定が行えない可能性あり。
- run_monitoring:
  - MONITOR_POLL_INTERVAL に 0 または負数、非数を設定した場合はデフォルト（60 秒）にフォールバックして警告ログを出す実装。
- validate_config:
  - PyYAML が未インストールの場合、config/*.yaml の内容検証をスキップし警告を出力する設計（PyYAML を optional dependency にしている想定）。
- その他:
  - 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 1 に設定すると危険である旨を警告するチェックを実装。
  - 監視は常に monitoring.db（Settings.sqlite_path）を使用する設計になっているため、paper_trading と監視 DB の分離が必要な運用では注意が必要。

```

必要であれば以下を追加で作成できます：
- 変更差分を自動生成するためのコミットメッセージ→CHANGELOG マッピング案
- リリースノート（英語版）
- 各機能についての短いユーザードキュメント（CLI の使い方、環境変数一覧など）

どれを優先して作成しますか？