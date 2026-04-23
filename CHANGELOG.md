# Changelog

すべての非互換性のある変更はここに記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。

全てのバージョンはセマンティックバージョニングを使用します。

## [Unreleased]

（現在未リリースの変更はなし）

## [0.1.0] - 2026-04-23

初回リリース。

### Added
- 基本アプリケーションパッケージ kabusys を追加。
  - バージョン情報: __version__ = "0.1.0"
- 環境・設定管理
  - Settings クラス（kabusys.config）を実装。環境変数から各種設定を取得するプロパティを提供（J-Quants トークン、kabuステーションの設定、DB パス、監視閾値、実行環境など）。
  - .env 自動ロード機構を実装（プロジェクトルートの検出: .git または pyproject.toml。優先順位: OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - .env パースロジックを実装（コメント、export 形式、シングル/ダブルクォート、エスケープ対応）。
- 設定ウィザード CLI（kabusys.config_setup）
  - 対話式ウィザードで .env を作成／更新する機能を追加。
  - 主要設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LINE 関連など）をサポート。
  - .env の読み書きロジックを実装。
- 設定検証 CLI（kabusys.validate_config）
  - 起動前に必須環境変数や config/*.yaml、パス等を検証するコマンドを追加。
  - --strict オプションで警告を失敗扱いにできる。
  - YAML パーサ未インストール時は警告を出し検証をスキップする。
  - 本番環境向けの追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告等）を実装。
- 起動スクリプト
  - 実行エンジン run_execution.py を追加。
    - KABUSYS_ENV=paper_trading の場合、Paper Trading 用 DB を使用して本番 DB と分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory を用いたブローカークライアント作成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、ExecutionEngine の起動ループを実装。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）対応。
    - 起動時にプロセス優先度を "high" に設定。
  - 監視プロセス run_monitoring.py を追加。
    - SystemMonitor を用いたポーリングループを実装。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトへフォールバック）。
    - 監視は KABUSYS_ENV に関係なく本番 sqlite_path を使用する仕様。
    - 停止フラグ検出および例外発生時のログ出力/継続動作を実装。
- ロギングユーティリティ（kabusys.utils.logging_setup）
  - setup_logging を追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（1日ローテーション、30世代保持）を設定。
    - LOG_DIR 指定や作成失敗時のフォールバック（ファイルハンドラ無効化）に対応。
    - 既存ハンドラのクリーンアップ（flush/close）を行い二重登録を防止。
- プロセス優先度・CPU affinity ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level) を追加。Windows / POSIX を吸収して優先度設定を行う（psutil を使用）。権限不足や未対応 OS の場合は警告を出してスキップ。
  - set_cpu_affinity(cpu_count) を追加。利用可能コア数を越える場合の挙動やエラーハンドリングを実装。
- Portfolio 構築モジュール（kabusys.portfolio）
  - portfolio_builder: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア合計が 0 の場合は等配分にフォールバック。
  - risk_adjustment: セクター上限適用 (apply_sector_cap)、レジーム乗数計算 (calc_regime_multiplier)。regime: "bull"/"neutral"/"bear" に対応。未知レジームはフォールバック（1.0）して警告を出力。
  - position_sizing: 発注株数決定ロジック (calc_position_sizes) を実装。allocation_method ("risk_based", "equal", "score")、lot_size、max_position_pct、max_utilization、cost_buffer に基づく集約キャップとスケーリング（端数処理は lot 単位で実施）。
  - これらを package レベルで再エクスポート。
- Research / ファクター計算（kabusys.research.factor_research）
  - ファクター計算モジュールを追加（Momentum, Value, Volatility, Liquidity の計画と一部実装）。DuckDB 接続を受け取り prices_daily, raw_financials を参照して計算する設計。
  - （注）ファイル末尾で実装途上の箇所が存在（将来的に完成予定）。
- Paper Trading 検証ツール（kabusys.tools.paper_verification_report）
  - ペーパートレード用 SQLite DB から稼働率、注文成功率、送信率、レイテンシ等を集計し、PASS/FAIL レポートを出力する CLI を実装。
  - レポートの基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。--from/--to/--db オプションをサポート。

### Changed
- .env 自動読み込みの挙動
  - プロジェクトルートが見つからない場合は自動ロードをスキップするように変更（配布後の環境で安全に動作）。
  - OS 環境変数は保護され、.env.local は .env の上書きとして読み込まれる。
- ログ出力
  - StreamHandler は stdout を使用（stderr ではない）。cron 等からの出力リダイレクト運用に配慮。
  - ログディレクトリ作成失敗時はファイル出力を無効化してコンソールログのみで継続するフォールバックを実装。
- run_monitoring のポーリング間隔設定
  - MONITOR_POLL_INTERVAL の不正値（非整数、0/負値）は警告を出してデフォルト 60 秒にフォールバックするよう変更。

### Fixed
- 環境変数パースの堅牢化
  - export 形式、クォート内のエスケープ、行内コメントの扱いなどを改善。
- process_priority / cpu_affinity の例外処理強化
  - psutil による権限不足や未実装関数での例外を捕捉し、警告を出して安全にスキップするようにした。
- DB 初期化の冪等性
  - init_monitoring_db が複数起動コンテキスト（execution / monitoring）から呼ばれても問題ないように利用。

### Known issues / Notes
- research.factor_research モジュールは設計方針および一部計算を実装済みですが、ファイル末尾に未完の実装箇所（切断）があります。今後のリリースで完成予定です。
- position_sizing の lot_size は現状グローバル固定（デフォルト 100）。将来的に銘柄ごとの単元対応を検討中（TODO コメントあり）。
- Monitoring は意図的に KABUSYS_ENV に依存せず本番 sqlite_path を使用します。テストや paper_trading と分離したい場合は別途設定・実行方法を検討してください。

### Security
- 初版のため、機密情報（API トークン等）は .env を通じて取り扱う設計。.env を絶対にリポジトリへコミットしない旨を設定ウィザードの出力に明記。

---

今後の予定:
- research モジュールの完成（すべてのファクター計算を実装）
- 単体テストと CI の整備
- broker クライアント / ExecutionEngine の耐障害性向上とメトリクス充実