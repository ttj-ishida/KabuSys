# Changelog

すべての変更は「Keep a Changelog」の形式に従い、準拠した形で記載しています。バージョン番号はパッケージ定義（kabusys.__version__）に基づきます。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-18

### 追加 (Added)
- 初期リリース: KabuSys 自動売買フレームワークの基本コンポーネントを追加。
- 実行・監視用エントリスクリプトを追加。
  - run_execution.py: ExecutionEngine を起動する CLI。KABUSYS_ENV による paper_trading モード（MockBroker を使用、data/paper_trading.db へ記録）に対応。実行中の PID 管理、停止フラグによる安全停止、スレッド実行対応を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ開始スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する実装。
- 設定管理/ウィザード/検証 CLI を追加。
  - kabusys.config: .env 自動ロード機能（.env/.env.local）と堅牢な .env パース実装。プロジェクトルート検出（.git または pyproject.toml 基準）。設定値を property ベースで取得（J-Quants, kabuAPI, DB パス, PID/kill flag 等）。
  - kabusys.config_setup: 対話式ウィザードで .env を初期作成・更新する CLI を追加（項目定義、既存値の読み込み、保存）。
  - kabusys.validate_config: .env と config/*.yaml の静的検証 CLI を追加。--strict オプションで警告も失敗扱いにできる。PyYAML 未インストール時の挙動考慮。
- ポートフォリオ構築関連の純粋関数群を追加（DB 参照なし、メモリ計算）。
  - portfolio.portfolio_builder: 候補選定（select_candidates）・等金額/スコア加重（calc_equal_weights, calc_score_weights）。
  - portfolio.risk_adjustment: セクター上限の適用（apply_sector_cap）、市場レジームに応じた乗数計算（calc_regime_multiplier）。
  - portfolio.position_sizing: ポジションサイズ計算（calc_position_sizes）を実装。risk_based / equal / score の割当方式、単元株丸め、aggregate cap によるスケーリング、コストバッファ考慮を実装。
- 監視・実行の共通ユーティリティを追加。
  - utils.logging_setup: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（ログ日次ローテーション、デフォルト logs/）を設定するユーティリティを追加。LOG_LEVEL / LOG_DIR の解決順を実装し、ファイル出力失敗時にはコンソール出力のみで継続。
  - utils.process_priority: プラットフォーム差を吸収したプロセス優先度設定（Windows / POSIX 対応）、CPU affinity 設定を提供。psutil を利用し権限不足時のフォールバック警告を実装。
- Paper Trading 検証ツールを追加。
  - tools.paper_verification_report: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から期間指定でレポートを生成。稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL を判定する基準（デフォルト閾値を定義）を実装。
- 研究用ファクター計算の骨格を追加。
  - research.factor_research: モメンタム等ファクター計算のための定数と calc_momentum 等の骨格（DuckDB 接続を使う設計）を追加（実装途中のファイルあり）。
- パッケージ初期設定: src/kabusys/__init__.py にバージョンを追加（__version__ = "0.1.0"）および主要モジュールのエクスポート定義。

### 変更 (Changed)
- ロギングの挙動: コンソール出力に stdout を採用（cron/Task Scheduler などでリダイレクトしやすくするため）。
- .env ロード順の定義: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。

### 修正 (Fixed)
- （初期リリースのため明示的な bug fix は無し。実装上注意した点を下記に記載）
  - MONITOR_POLL_INTERVAL に不正値が指定された場合のフォールバック処理を追加（ログ警告とデフォルト使用）。
  - .env パースの堅牢化: export プレフィックス、クォート内エスケープ、行内コメント処理などに対応。

### 注意 / 補足 (Notes)
- 実行/監視プロセスはプロセス優先度を最初に "high" に設定しようと試みますが、権限不足やプラットフォーム制限時は警告を出して続行します。
- run_monitoring は監視 DB に関して「環境にかかわらず本番 sqlite_path を使用」する挙動になっています（意図的設計：監視は本番データ参照を前提）。
- run_execution は KABUSYS_ENV=paper_trading の場合、運用 DB と分離して PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用します。
- paper_verification_report は SQLite スキーマ（system_status, trade_logs, risk_logs 等）に依存します。該当テーブルが存在しない場合は該当指標を N/A / 0 として処理します。
- position_sizing の計算はいくつかの前提（lot_size 共通、価格欠損時のログ扱い等）に基づきます。将来的に銘柄別 lot_size や価格フォールバックの拡張を想定した TODO コメントがあります。

### 既知の制約 (Known issues)
- research.factor_research の実装が途中で終わっているファイルが存在します（calc_momentum の続きを実装する必要あり）。
- 一部コンポーネント（BrokerClientFactory、ExecutionEngine、SystemMonitor 等）は本コードベース内の他モジュールに依存しており、外部 API 連携や統合テストが必要です。
- DuckDB / PyYAML / psutil 等外部パッケージに依存。インポートできない場合は該当機能をスキップまたは警告する実装もありますが、完全な動作には必要パッケージのインストールを推奨します。

---

今後の予定:
- factor_research の完全実装。
- ユニットテスト・統合テストの追加。
- 配布・パッケージング（pip 配布等）用のメタデータ整備。