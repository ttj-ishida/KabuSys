# Changelog

すべての注目すべき変更点を記録します。フォーマットは "Keep a Changelog" に準拠します。

## [Unreleased]

### Added
- run_monitoring スクリプトを改善:
  - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔の上書きを導入。無効な値はデフォルト（60秒）にフォールバックして警告を出力する。
  - 停止フラグファイル（data/stop_requested.flag）検知による安全なループ終了処理を追加。
  - SystemMonitor の初期化と SQLite / DuckDB 接続を統一的に行う起動フローを確立（ログ記録・例外安全な接続クローズ）。

- run_execution スクリプトを追加 /改善:
  - `KABUSYS_ENV=paper_trading` 時に本番 DB と完全に分離した Paper Trading 用 DB（data/paper_trading.db）を使用する仕様を明確化。
  - BrokerClientFactory によるブローカークライアント抽象化を利用し、paper/live 環境の切り替えを容易に実現。
  - エンジン（ExecutionEngine）を別スレッドで実行し、停止フラグ検知で安全に停止する仕組みを導入。PID ファイルの取り扱いを追加。

- 環境設定まわり:
  - config.py: .env 自動読み込み機構を実装（プロジェクトルート検出: .git / pyproject.toml 基準）。読み込み順序は OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
  - .env パーサーを強化して `export KEY=val` 形式、クォート文字内のエスケープ、インラインコメント等に対応。
  - Settings クラスを提供し、アプリケーション設定（DB パス、API トークン、Paper Trading 設定、各種閾値など）をプロパティ経由で安全に取得できるようにした。

- 設定支援ツール:
  - config_setup: 対話式ウィザードで .env を生成／更新する CLI を追加。既存値の再利用、シークレットのマスク表示、保存前確認などを実装。
  - validate_config: .env および config/*.yaml の簡易検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、YAML のパース検証（PyYAML があれば）を行う。`--strict` オプションで警告も失敗扱いにできる。

- ポートフォリオ構築関連（純粋関数群）を追加:
  - portfolio.portfolio_builder: シグナルの上位選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
  - portfolio.risk_adjustment: セクター集中制限適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - portfolio.position_sizing: position sizing ロジック（risk_based / equal / score）、単元株丸め、aggregate cap のスケーリングと端数配分ロジックを実装。

- ユーティリティ:
  - utils.logging_setup: ルートロガー設定ユーティリティを導入。コンソール stdout と日次ローテートのファイルハンドラ（TimedRotatingFileHandler）を組合せ、ログディレクトリ作成失敗時のフォールバック処理を実装。
  - utils.process_priority: Windows / POSIX の差分を吸収してプロセス優先度（nice / Windows priority class）および CPU affinity 設定を行うユーティリティを追加。権限不足時の安全なスキップ、対応 OS のチェックあり。

- 分析 / レポート:
  - tools.paper_verification_report: Paper Trading 用 SQLite を読み、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）等を集計して PASS/FAIL 判定付きレポートを出力する CLI を追加。P95 計算、期間フィルタ、各種閾値定義を実装。

- 研究用モジュール（雛形）:
  - research.factor_research にモメンタム等のファクター計算方針を実装。DuckDB 接続を受け取り prices_daily / raw_financials を基にファクター計算を行う設計（モジュール内での定数・スキャン窓定義などを追加）。

### Changed
- ロギング設定のデフォルトを整備:
  - ログ出力先として stdout を優先（StreamHandler）、LOG_DIR 環境変数でログフォルダを指定可能。既存ハンドラをクリアしてから設定することで二重出力を防止。

- 実行スクリプトの優先度設定:
  - run_monitoring / run_execution の起動直後に set_process_priority("high") を呼び出すことで、プロセス優先度の設定を自動化（プラットフォーム依存の落とし所を utils.process_priority で吸収）。

### Fixed
- .env 読み込みでの例外処理強化（ファイル読み込み失敗時に警告を出して処理継続）。
- logging_setup: ログディレクトリ作成やファイルハンドラ作成に失敗した場合にプロセスが止まらないようにフォールバック処理を追加。

---

## [0.1.0] - 2026-04-19

初回リリース（ベースライン機能群）。

### Added
- コア機能:
  - 自動売買システム KabuSys の初期モジュール群を追加（monitoring、execution、portfolio、research、tools）。
  - パッケージ初期バージョンを __version__ = "0.1.0" として設定。

- 監視 / 実行:
  - SystemMonitor を用いた監視ループの起動スクリプト（run_monitoring）。
  - ExecutionEngine を用いた注文実行スクリプト（run_execution）と関連コンポーネント（OrderManager / OrderRepository / Reconciler / RiskManager）。

- 環境管理:
  - Settings クラスによる環境変数からの構成取得（DB パス、API トークン、環境種別など）。
  - 環境自動読み込み（.env / .env.local）と .env パーサー。

- 設定ツール:
  - 対話式 .env ウィザード（config_setup）と設定検証ツール（validate_config）。

- ポートフォリオ構築:
  - 候補選定、重み計算、ポジションサイズ計算、セクターキャップ、レジーム乗数の純粋関数群。

- ユーティリティ:
  - ログ設定ユーティリティ（utils.logging_setup）。
  - プロセス優先度および CPU affinity 設定ユーティリティ（utils.process_priority）。

- レポート / 解析:
  - Paper Trading レポート生成ツール（tools.paper_verification_report）。
  - DuckDB を利用する研究用ファクターモジュール（research.factor_research）の雛形。

### Changed
- なし（初回リリース）。

### Fixed
- なし（初回リリース）。

---

注意事項・補足
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と完全に分離する設計です。Paper 用 DB パスは環境変数 `PAPER_TRADING_SQLITE_PATH` で上書き可能です。
- .env ファイルはセキュリティ上 Git に含めないでください（config_setup のヘッダにも注意喚起あり）。
- プロセス優先度／CPU affinity の一部操作は権限が必要な場合があり、失敗時は警告ログによりスキップされます。
- DuckDB / PyYAML 等の外部ライブラリがない環境では関連機能の一部（YAML 検証等）がスキップされます。