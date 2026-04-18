# Changelog

すべての重要な変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  
リリース日付はコードベースから推定したものを使用しています。

## [Unreleased]

### Added
- 全体
  - パッケージ初期構成を追加。パッケージバージョンは `__version__ = "0.1.0"`。
  - 統一ログ設定ユーティリティを追加（kabusys.utils.logging_setup）。stdout への出力と日次ローテーションファイルログ（TimedRotatingFileHandler）を標準化。ログディレクトリ作成に失敗した場合はフォールバックしてコンソール出力のみで継続。
  - プロセス優先度/CPU affinity 設定ユーティリティを追加（kabusys.utils.process_priority）。Windows/Linux/macOS を吸収し、アクセス権エラーや未対応 OS の場合は警告を出して安全にスキップする。
  - 環境設定管理を実装（kabusys.config）。.env 自動ロード（.env, .env.local、OS 環境変数優先）、クォート・エスケープ対応の .env パーサ、各種設定プロパティを提供（DB パス、API トークン、監視閾値など）。
  - 対話式 .env 作成ウィザードを追加（kabusys.config_setup）。既存 .env の読み込み、シークレットマスク表示、保存確認まで対応。
  - 設定検証 CLI を追加（kabusys.validate_config）。必須環境変数、KABUSYS_ENV, LOG_LEVEL, DB パス、config/*.yaml の存在および YAML パース（PyYAML がある場合）を検証。--strict オプションで警告を FAIL 扱いにできる。
- 実行・監視
  - 実行エンジン起動スクリプトを追加（kabusys.run_execution）。プロセス優先度を "high" に設定、Paper Trading モード時は専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離、ブローカークライアントのファクトリを利用して ExecutionEngine をスレッドで実行。停止フラグ（data/stop_requested.flag）と PID ファイル管理に対応。
  - 監視ループ起動スクリプトを追加（kabusys.run_monitoring）。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に依らず本番 sqlite_path を使用。停止フラグ検出でループ終了。例外発生時もログを出して次ポーリングまで待機。
  - 監視 DB 初期化フック（init_monitoring_db）を両スクリプトで呼び出して、監視テーブルの存在を保証（冪等）。
- 実装コンポーネント（execution）
  - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等の組み立てロジックを整備。RiskConfig にデフォルト値を設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）。RiskManager 初期化時にブローカーから初期ポートフォリオ現金を取得して使用。
- ポートフォリオ構築
  - ポートフォリオ関連の純粋関数群を追加（kabusys.portfolio.*）:
    - portfolio_builder: 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights、スコア合計が 0 の場合は等配分へフォールバック）。
    - risk_adjustment: セクター集中制限（apply_sector_cap、売却予定銘柄の除外対応、"unknown" セクターは上限適用除外）、市場レジームに応じた投下倍率（calc_regime_multiplier、未定義レジームは警告して 1.0 にフォールバック）。
    - position_sizing: 株数決定ロジック（calc_position_sizes）。risk_based / equal / score の配分方式をサポート。単元株（lot_size）丸め、max_position_pct による per-stock 上限、投下合計が利用可能現金を超える場合のスケーリング（端数処理で lot 単位の再配分）を実装。手数料・スリッページ考慮の cost_buffer パラメータをサポート。
- 研究・解析
  - ファクター計算モジュール（kabusys.research.factor_research）を追加。Momentum / Value / Volatility / Liquidity 系ファクターを DuckDB の prices_daily / raw_financials を参照して算出する設計（関数は日付ベースの計算を前提）。（ファイルは一部実装途上）
- ツール
  - Paper Trading 検証レポート生成ツールを追加（kabusys.tools.paper_verification_report）。PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を読み、稼働率・注文成功率・送信率・リスク却下数・API レイテンシ（平均/最大/P95）を集計して PASS/FAIL 判定を行う。閾値はソース内で定義（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）。
  
### Changed
- 設定ロードの挙動
  - .env の自動ロードは OS 環境変数上書きを防ぐために protected set を利用。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
- ロギング
  - ログハンドラの二重登録を防ぐため、既存ハンドラを flush/close のうえクリアしてから再設定する仕様に変更。ログレベル決定ロジックを関数引数→環境変数→デフォルトの順に統一。
- 実行フロー
  - run_execution は paper_trading モードで専用 DB を使用し、init_monitoring_db を呼び出して監視テーブルの存在を担保するように変更（本番 DB との混同防止）。

### Fixed
- .env パーサの改善
  - シングル/ダブルクォート内でのバックスラッシュエスケープを正しく解釈するよう修正。コメント判定の微妙なケース（# の前にスペースがある場合のみコメントとみなす）に対応。
- process_priority/set_cpu_affinity の堅牢化
  - psutil の環境差分（Windows 固有定数の未定義など）に対して getattr を使用してフォールバックし、AttributeError 等が発生しても警告を出してスキップするように変更。

---

## [0.1.0] - 2026-04-18

### Added
- 初回公開リリースとして以下の主要機能を実装・公開:
  - 環境設定読み込み・管理（kabusys.config）と .env ウィザード（kabusys.config_setup）。
  - 設定検証ツール（kabusys.validate_config）。
  - 実行（ExecutionEngine）起動スクリプト（kabusys.run_execution）と監視ループ起動スクリプト（kabusys.run_monitoring）。
  - ログ設定ユーティリティ（kabusys.utils.logging_setup）とプロセス優先度ユーティリティ（kabusys.utils.process_priority）。
  - 注文管理・リスク管理・リコンサイラー等の実行周りコンポーネントの組み立てロジック。
  - ポートフォリオ構築ライブラリ（選定・配分・リスク調整・株数決定）。
  - DuckDB を用いたリサーチ/ファクター計算の下地（kabusys.research.factor_research）。
  - Paper Trading 向け検証レポート生成ツール（kabusys.tools.paper_verification_report）。
  - パッケージエクスポート（kabusys.portfolio の __all__ 等）。

### Changed
- 初期設計・API の確定（モジュール分割、CLI 入口、DB 分離方針など）。

### Fixed
- N/A（初回リリース）

---

注:
- 本 CHANGELOG はコードベースの内容から推定して作成しています。実際のリリースノートや履歴管理ポリシーに合わせて適宜修正してください。