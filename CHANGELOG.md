# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

現在のバージョン: 0.1.0

## [Unreleased]

（未リリースの変更はここに記載）

---

## [0.1.0] - 2026-04-18

初回リリース。自動売買システム KabuSys の基本機能を実装しました。主な追加点は以下の通りです。

### Added
- 基本パッケージ情報
  - パッケージメタ情報を追加（src/kabusys/__init__.py、__version__ = "0.1.0"）。

- 設定関連
  - Settings クラスを実装（src/kabusys/config.py）。環境変数から各種設定を安全に取得可能。
  - .env ファイルの自動読み込み機能を実装（.env /.env.local の優先度処理、プロジェクトルート検出）。
  - 高度な .env パーサ実装（引用符、エスケープ、`export` 形式、インラインコメント等に対応）。
  - 環境設定ウィザード CLI を実装（src/kabusys/config_setup.py）。対話式で .env を生成・更新可能。
  - 設定検証 CLI を実装（src/kabusys/validate_config.py）。必須環境変数・ファイル存在・本番用ガード等をチェック。`--strict` オプションで警告を失敗扱いにできる。

- ロギング・プロセス制御
  - 統一的なロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - コンソール出力は stdout、日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をサポート。
    - ログディレクトリ作成に失敗した際はファイル出力をスキップしてコンソール出力のみ継続。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX を吸収し、権限不足等を考慮して安全に処理。

- 実行・監視エントリポイント
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV による paper_trading モード切替をサポート。paper_trading の場合は専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止制御用のフラグファイル（data/stop_requested.flag）と PID ファイル（data/execution.pid）を使用。
  - SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する仕様。
    - ループ内での例外はキャッチしてログ出力し、次ポーリングへ継続。

- 監視 DB 初期化
  - 監視テーブル初期化ユーティリティを参照する呼び出し（init_monitoring_db）を各起動処理に組み込み、冪等に監視テーブルが存在することを保証。

- Paper Trading / 検証ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - システム稼働率、注文成功率・送信率、P95 レイテンシ、リスク却下数などを集計して PASS/FAIL 判定を行う。
    - DB パスはコマンドライン引数または環境変数（PAPER_TRADING_SQLITE_PATH）で指定可能。DB ファイル不存在時のエラーメッセージを表示。

- ポートフォリオ構築（純粋関数群）
  - 候補選定 / 重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順で上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア合計が 0 の場合は等配分にフォールバック）。
  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: セクター集中が閾値を超える場合に新規候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear をサポート、未知レジームはフォールバック）。
  - 目標株数計算・リスク制限（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method（"risk_based"/"equal"/"score"）に応じて発注株数を計算。単元株丸め、per-stock 上限、aggregate cap（available_cash に基づくスケーリング）、cost_buffer（手数料・スリッページ見積）を実装。

- 研究用ファクター計算（下ごしらえ）
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - モメンタム / MA200 / ATR / 出来高などを計算するための定数と関数群の骨子を用意。DuckDB 経由で prices_daily / raw_financials を参照する設計。

### Changed
- ログ出力の統一
  - すべての起動スクリプトで setup_logging を最初に呼ぶ運用を想定（app_name によりログファイル名を分離）。

- DB 接続管理
  - 起動スクリプトで SQLite / DuckDB 接続を確実に閉じる実装（finally ブロックで close）。

### Fixed
- 耐障害性の向上
  - モニターループや実行ループでの予期しない例外を捕捉してログに残し、プロセスが即時終了しないようにした（監視は次ポーリングへ継続、エンジンは停止フラグ読取で安全終了）。

- .env 読み込みの堅牢化
  - ファイル読み込み失敗時に警告を発しスキップするようにした（テスト環境等でリスク低減）。

### Notes / Implementation details
- Paper Trading と Live は DB を明確に分離（paper_trading: PAPER_TRADING_SQLITE_PATH / data/paper_trading.db、live/development: SQLLITE_PATH）。
- process_priority は権限不足や未対応 OS を考慮して安全にフォールバックする設計。
- calc_position_sizes のスケーリングおよび残差処理は lot_size 単位で安定再現性を確保するよう実装。
- validate_config は PyYAML 未インストール時に YAML 検証をスキップし、その旨を警告する。
- run_monitoring の停止は data/stop_requested.flag によって制御。run_execution も同様のフラグで起動/停止を制御。

---

注: 本 CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノート作成時はコミット履歴や CHANGELOG ポリシーに基づいて調整してください。