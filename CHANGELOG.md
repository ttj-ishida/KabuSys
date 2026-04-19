# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

## [Unreleased]

### Added
- 開発用ユーティリティと起動スクリプト群を追加・整理
  - 実行系/監視系の起動スクリプトを追加
    - run_execution: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite を使用し MockBrokerClient を利用する仕組みをサポート。
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 設定関連 CLI を追加
    - config_setup: 対話式ウィザードで .env を作成 / 更新するユーティリティ。
    - validate_config: .env と config/*.yaml の事前検証ツール（--strict オプションで警告を失敗扱いにできる）。
  - Paper Trading 検証ツールを追加
    - tools/paper_verification_report: paper_trading DB を集計して稼働率・注文成功率・レイテンシなどをレポート化する CLI。
  - ポートフォリオ構築関連モジュールを追加
    - portfolio.portfolio_builder: 候補選定 / 等配分・スコア配分の関数。
    - portfolio.risk_adjustment: セクターキャップ適用、レジーム乗数計算。
    - portfolio.position_sizing: 各銘柄の発注株数計算（リスクベース／等配分／スコア配分のサポート、単元株丸め、aggregate cap スケーリング）。
  - utils モジュールを追加
    - utils/logging_setup: stdout と日次ローテートファイルハンドラを設定する共通ロギング初期化。
    - utils/process_priority: Windows/Linux/macOS を透過するプロセス優先度および CPU affinity 設定（例: 起動時に "high" を設定する呼び出しを利用）。
  - 設定読み込み / 管理
    - config.Settings: 環境変数ラッパー（必須項目のチェック・型変換・paper_trading 用パスやしきい値などを提供）。
    - 自動 .env ロード機能: プロジェクトルートを探索して .env / .env.local を自動で読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - 監視 DB 初期化の冪等化フック（init_monitoring_db が起動時に呼ばれるよう各起動スクリプトで利用）。

### Changed
- 実行時の既定動作の明示化
  - 監視（monitoring）は KABUSYS_ENV にかかわらず本番 sqlite_path を使用するように明示的に実装（監視データは本番 DB を参照）。
  - 実行エンジン（execution）は paper_trading 環境では専用の paper_trading DB を使用する（本番 DB と分離）。
- ロギングの標準化
  - 全起動スクリプトから utils.logging_setup.setup_logging を利用することでログ出力形式およびファイルローテーションを統一。
- process priority の設定を起動直後に行うよう統一（set_process_priority("high") を標準処理に追加）。

### Fixed
- .env パーサの堅牢化
  - クォートあり／なし、エスケープ文字、インラインコメント等に対して堅牢にパースするロジックを追加。
  - .env の読み込みでファイルが開けない場合に警告を発するように改良。
- ログディレクトリ作成失敗時のフォールバック
  - ログディレクトリ作成に失敗してもコンソール（stdout）出力は有効のままにし、ファイルハンドラだけ無効化して継続するように変更。
- プロセス優先度設定の互換性処理
  - Windows / POSIX 系（Linux, macOS, FreeBSD）を考慮した実装にし、権限制約等で失敗した場合は警告を出してスキップするように改善。
- ExecutionEngine 起動時の停止フラグ判定強化
  - 起動前に停止フラグが既に立っている場合は起動せず即時終了する安全策を追加。

### Known issues / TODO
- research.factor_research モジュールは実装途中（ファイル終端が断られているなど）で未完成の関数や不完全な実装が残っている。引き続きファクター計算ロジックの実装とテストを予定。
- position_sizing.calc_position_sizes 内の価格欠損（price が 0.0 の場合）の扱いで誤差が生じる可能性がある（コメントにあるフォールバック価格導入の TODO を残す）。
- 一部の TODO（銘柄ごとの lot_size 拡張など）は将来的な拡張項目として残している。

---

## [0.1.0] - 2026-04-19

初回公開リリース。

### Added
- 基本的な自動売買フレームワークのコア機能を実装
  - ExecutionEngine 起動処理、OrderManager / OrderRepository / Reconciler / RiskManager のインスタンス化フロー（起動スクリプトと依存注入）。
  - SystemMonitor のポーリング起動および DB 初期化。
  - Settings クラスによる環境変数ラップと主要設定（DB パス、ログレベル、環境識別、しきい値等）。
  - 対話式 .env ウィザード（config_setup）により初期設定を簡易化。
  - 設定検証ツール（validate_config）で起動前に環境変数・YAML 設定の欠落や誤りを検出。
  - ロギング設定ユーティリティ（stdout + 日次ローテートファイル）とログディレクトリ管理。
  - プロセス優先度 / CPU affinity ユーティリティ（Windows / POSIX 互換）。
  - ポートフォリオ構築関連（候補選定、重み計算、セクター制約、位置サイズ算出）。
  - Paper Trading 用の検証レポート生成ツール（tools/paper_verification_report）。
  - DuckDB / SQLite を利用したデータ接続の初期化と基本クエリ処理（ツールや監視で利用）。
- CLI エントリーポイントを複数実装（モジュール単体で実行可能に）。

### Changed
- N/A（初回リリースのため差分なし）。

### Fixed
- N/A（初回リリースのため過去バグの修正なし）。

### Security
- N/A

---

注記:
- 本 CHANGELOG はリポジトリ内のソースコード（コメント、ドキュメント文字列、実装）から推測して作成したものです。実際のコミット履歴やリリースノートが存在する場合はそれに基づいた更新を推奨します。