# CHANGELOG

すべての重要な変更点は Keep a Changelog のガイドラインに従って記録します。  
このファイルはコードベースの現在の状態から推測して作成した変更履歴です（実装に基づく要約）。

なお、バージョンはパッケージ定義（kabusys.__version__ = "0.1.0"）に合わせています。

## [Unreleased]

### Added
- 開発用ユーティリティ群を追加
  - 環境設定ウィザード CLI（kabusys.config_setup）
    - .env の対話式作成・更新を支援するウィザード。
    - 各種キー（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH など）を扱うテンプレートを提供。
    - 秘匿項目はマスク表示、保存前の確認プロンプトあり。
  - 設定検証 CLI（kabusys.validate_config）
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML 利用）等を行う。
    - --strict オプションで警告を失敗として扱える。
  - run_execution 起動スクリプト（kabusys.run_execution）
    - ExecutionEngine を起動するためのエントリポイント。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用して本番 DB と分離（PAPER_TRADING_SQLITE_PATH）。
    - BrokerClientFactory 経由でブローカークライアントを組み立て、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて実行。
    - 停止フラグ (data/stop_requested.flag) の検出および PID ファイル管理に対応。
  - run_monitoring 起動スクリプト（kabusys.run_monitoring）
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視 DB は環境にかかわらず本番 sqlite_path を使用するという設計。
    - stop フラグ検出で安全にループを終了。
  - Paper Trading 向け検証レポート生成ツール（kabusys.tools.paper_verification_report）
    - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から稼働率、注文成功率、送信率、P95 レイテンシ等を集計してレポートを出力。
    - 日付フィルタ (--from/--to) と --db オプションをサポート。
    - PASS/FAIL 判定の閾値（稼働率、成功率、レイテンシ等）を定義。
  - ポートフォリオ構築モジュール（kabusys.portfolio）
    - portfolio_builder: シグナル選定（select_candidates）、等配分・スコア配分（calc_equal_weights / calc_score_weights）。
    - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに基づく乗数（calc_regime_multiplier）。
    - position_sizing: 発注株数算出（calc_position_sizes） — risk_based / equal / score の各方式に対応し、単元株（lot_size）・aggregate cap・コストバッファ等を考慮。
  - ロギング・プロセス管理ユーティリティ（kabusys.utils）
    - logging_setup: StreamHandler（stdout）と日次ローテーションファイルハンドラ（TimedRotatingFileHandler）を設定。ログレベル・ログディレクトリは引数/環境変数で制御。
    - process_priority: Windows / POSIX の違いを吸収してプロセス優先度（high/normal/low）および CPU affinity を設定するユーティリティ。
  - 設定管理モジュール（kabusys.config）
    - .env 自動読み込み（.env → .env.local、OS 環境変数は保護）および柔軟な .env パース（クォート、エスケープ、export 形式対応）。
    - Settings クラスで各種環境変数をプロパティとして提供（DB パス、API トークン、閾値、フラグ等）。
  - research モジュールのファクター計算開始（kabusys.research.factor_research）
    - DuckDB を利用したモメンタム / ボラティリティ / ボリューム等のファクター計算の骨組みを提供（prices_daily/raw_financials を想定）。P95 等の統計ユーティリティ実装。

### Changed
- ロギングの挙動改善
  - ログディレクトリ作成に失敗した場合はファイル出力を無効化して標準出力への出力にフォールバックするように改善（起動失敗を回避）。
- 環境変数ロードの安全性強化
  - 自動ロード時に OS 環境変数を上書きしないよう保護セットを導入（.env ファイル読み込みで protected を考慮）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。

### Fixed
- .env パーサーの堅牢化
  - export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱い等に対応。
- 起動スクリプトの安定化
  - run_execution/run_monitoring ともにプロセス優先度を最初に設定し、例外発生時に DB 接続を確実にクローズするように改善。
  - run_execution は paper_trading 環境で本番 DB を汚さないよう専用 SQLite を使用するよう修正。
- validate_config の堅牢化
  - PyYAML が未インストールの場合は YAML 検証をスキップし警告を出力するように変更（依存関係がなくても実行可能）。
  - config/*.yaml の存在チェックとパース結果の情報/警告/エラー分類を追加。
- position_sizing の集約キャップ処理
  - 合計コストが利用可能現金を超える場合にスケールダウンし、端数処理（lot 単位での再配分）を行うロジックを実装して過剰注文を防止。

### Security
- .env を絶対にリポジトリにコミットしない旨をドキュメント（config_setup の生成ヘッダ）で明示。

### Internal / Misc
- パッケージバージョンを定義（kabusys.__version__ = "0.1.0"）。
- ドキュメント的コメント（PortfolioConstruction.md / StrategyModel.md 等の参照）をコード内に追記して設計の根拠を明示。
- 一部の TODO コメントで将来の拡張点（銘柄別 lot_size、価格フォールバックなど）を記載。

---

## [0.1.0] - 2026-04-23

初期リリース（推測）。上記 Unreleased の内容をベースに配布可能な最小構成をまとめたもの。

### Added
- 基本機能一式を公開（設定管理、起動スクリプト、Execution/Monitoring エントリ、ポートフォリオ構築、リスク調整、株数算出、ロギング・プロセスユーティリティ、Paper Trading 検証レポート、設定ウィザード・検証ツール、研究用ファクター計算の骨組みなど）。
- DuckDB / SQLite を用いたデータ処理基盤の利用を想定したコネクション管理。

### Fixed
- 各種デフォルト値の明確化（MONITOR_POLL_INTERVAL=60、LOG_LEVEL=INFO、DB パスのデフォルト等）。
- 停止フラグ / PID ファイルの扱いを安定化。

（注）実際のコミット履歴がないため、ここに記載した日付・分類はコード内容から推測して作成した要約です。実際のリリースノートを作る場合はコミットログ・PR コメント・リリース日を基に調整してください。