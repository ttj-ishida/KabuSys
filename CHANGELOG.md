CHANGELOG
=========
すべての重要な変更は Keep a Changelog の形式に従って記載します。  
なお、本 CHANGELOG は与えられたコードベースの内容から推測して作成したもので、実際のコミット履歴とは異なる場合があります。

Unreleased
----------
### Added
- 環境変数 MONITOR_POLL_INTERVAL による監視ポーリング間隔の上書き対応（不正値時はデフォルトにフォールバックして警告を出力）。
- データパスや設定読み込みの堅牢性向上（.env 自動ロードの保護、.env.local の上書き挙動）。
- run_monitoring/run_execution の停止制御にファイルベースの停止フラグ（data/stop_requested.flag）を導入（外部からの安全な停止が可能）。
- duckdb を利用した分析用 DB 統合（DuckDB 接続オブジェクトを各コンポーネントに注入）。

### Changed
- monitoring 用 DB 初期化処理を冪等化（init_monitoring_db を接続後に呼び出し、テーブル存在を保証）。
- 実行エンジン run_execution が paper_trading 環境時に専用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離する動作を明確化。
- プロセス優先度設定処理を起動直後に移動し、set_process_priority を共通ユーティリティ化（Windows/Linux の差分吸収）。

### Fixed
- .env パーサの改善（クォート付き値のエスケープ処理、インラインコメントの扱い、export プレフィックス対応）。

### Known issues / TODO
- position_sizing の単元株（lot_size）を銘柄別にするといった拡張は TODO コメントで残存。
- apply_sector_cap の価格欠損時にエクスポージャーが過少評価される可能性がある旨の注意コメントあり（将来的なフォールバック価格検討）。

0.1.0 - 2026-04-17
------------------
Initial release — 基本的な自動売買フレームワークを実装。

### Added
- 基本構成
  - パッケージ初期バージョンを 0.1.0 として定義（src/kabusys/__init__.py）。
  - Settings クラスによる環境変数/設定管理を実装（自動 .env 読み込み、必須チェック用 _require、各種パス・フラグ・しきい値をプロパティ化）。
  - .env 自動ロードの保護: OS 環境変数を保護しつつ .env と .env.local を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。

- CLI / ユーティリティ
  - config_setup: 対話式ウィザードで .env を生成/更新する CLI を追加。項目定義、既存値読み取り、保存フォーマットを含む（--env-file オプション対応）。
  - validate_config: 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリチェック、config/*.yaml 存在チェック（PyYAML 未導入時は警告）。--strict モードで警告を FAIL 扱い可能。
  - tools.paper_verification_report: ペーパートレード用検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL を判定（期間指定 --from/--to、DB 指定 --db 対応）。

- 実行/監視
  - run_execution: ExecutionEngine 起動用スクリプトを追加。BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて実行スレッドで起動。停止フラグ検知で安全に停止、PID ファイル管理。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能、監視 DB 初期化、停止フラグ検知・例外ハンドリングを実装。

- モジュール/アルゴリズム
  - portfolio モジュール（純粋関数群）
    - portfolio_builder: シグナル選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
    - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier。既知のレジーム: bull/neutral/bear、未知は警告して 1.0 にフォールバック）。
    - position_sizing: 株数決定ロジック（risk_based / equal / score 各方式）、単元株丸め、aggregate cap によるスケールダウン・端数処理。
  - research.factor_research: DuckDB の prices_daily/raw_financials を参照してファクター（モメンタム、ボラティリティ、流動性、Value 指標など）を計算する機能を追加。欠損データや行数不足に対する None 処理、P95 計算ユーティリティ等を実装。
  - tools.paper_verification_report にて P95 の算出と閾値判定を実装（空データ時の N/A ハンドリング等）。

- インフラ/ユーティリティ
  - utils.process_priority: プラットフォームを吸収するプロセス優先度設定ユーティリティ（Windows の priority class / POSIX の nice を扱う）。set_cpu_affinity による CPU affinity 設定も提供。権限不足や未対応環境では警告ログでフォールバック。

### Changed
- DB 関連
  - 監視用途の SQLite と分析用途の DuckDB を明確に分離。monitoring は環境に関わらず本番 sqlite_path を利用する旨がドキュメント化。
  - run_execution は paper_trading 環境なら paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と完全に分離する設計。

### Fixed
- .env パースロジックを強化（クォート付き文字列のエスケープ処理、インラインコメントの処理、export 接頭辞の扱い）。
- validate_config が不足している環境や設定ファイルのパースエラーを適切に検出・報告するよう改善。

### Security
- .env ファイルの生成時に注意書きを付与（.env を Git にコミットしないよう明記）。

### Notes / Limitations
- position_sizing の将来的拡張（銘柄別 lot_size マスタ導入）や、apply_sector_cap の価格欠損対策は TODO としてコード内に記載あり。
- 一部の YAML 検証は PyYAML に依存するため、環境によっては検証をスキップして警告を出力する（validate_config）。

Footnotes
---------
- 実行可能な CLI エントリポイント（推奨起動例）:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

- 主な環境変数（抜粋）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE, LOG_LEVEL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, KILL_FLAG_CLEAR_ON_START, MONITOR_POLL_INTERVAL

もし実際のコミット履歴やリリース日、より詳細な差分情報が提供可能であれば、CHANGELOG をそれに合わせて正確に更新できます。