# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

- リリース日付は ISO 8601 形式を使用します（YYYY-MM-DD）。

## [Unreleased]
（現在のリポジトリ状態に対する未リリースの変更はここに記載します）

## [0.1.0] - 2026-04-19
初回リリース。日本株自動売買フレームワーク「KabuSys」のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、設定管理・検証ツール、および Paper Trading 検証ツールを追加。

### Added
- 基本メタ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境に依存せず本番用 `sqlite_path` を使用。
    - 停止フラグ（data/stop_requested.flag）検知でループを安全に終了。
    - SQLite / DuckDB 接続を確立し、監視用 DB 初期化を行う。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は専用の paper_trading DB（data/paper_trading.db）を使用し、MockBrokerClient を利用して本番 DB と完全分離。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応し、デーモンスレッドでエンジンを実行・停止可能。
- 設定管理
  - config.py
    - 環境変数ラッパ `Settings` を提供（J-Quants、kabu API、LINE、DB パス、監視閾値、環境モード等）。
    - 自動 `.env` ロード機能を実装（プロジェクトルート判定: .git または pyproject.toml を探索）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - `.env` のパースはクォート、エスケープ、コメント（インライン）等に対応。
    - 各種設定値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を行う。
  - config_setup.py
    - 対話式ウィザードで `.env` を初期作成 / 更新する CLI を追加。
    - シークレット項目はマスク表示、既存値の利用、確認プロンプト、ファイル書き出し機能を実装。
- 設定検証ツール
  - validate_config.py
    - 起動前に `.env` と config/*.yaml の妥当性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV や LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、YAML パース検証（PyYAML があれば実行）等を実施。
    - `--strict` オプションで警告を FAIL 扱いにできる。
- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - 統一ロギング設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app>.log、30日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしコンソール出力のみで継続。
    - ログレベルの解決順: 引数 > 環境変数 > デフォルト。
  - utils/process_priority.py
    - プロセス優先度設定（Windows の priority class、POSIX の nice）と CPU affinity 設定ユーティリティを追加。
    - 対応 OS の差分を吸収し、失敗時は警告ログでスキップする堅牢性を実装。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順、タイブレーク）、等金額重み、スコア重みの計算関数を追加。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を追加。
    - 未知レジームは警告を出してフォールバック。
  - portfolio/position_sizing.py
    - position sizing ロジックを追加（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウン（スケーリング＋端数処理）の実装。
    - 手数料・スリッページ考慮のため cost_buffer パラメータを提供。
- Execution サブシステムの簡易統合
  - run_execution.py で組み立てるコンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）の呼び出しを実装（設定値は初期化時に注入される）。
  - RiskManager のデフォルト設定例を導入（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
- 監視・モニタリング基盤
  - monitoring_db 初期化（init_monitoring_db を起動スクリプトで呼び出し、監視テーブルの存在を保証）。
  - run_monitoring.py で SystemMonitor を初期化し単発チェック（check_once）を周期実行。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite DB から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数）を集計してレポートを標準出力に出力するスクリプトを追加。
    - 閾値に基づく PASS/FAIL 判定を実装（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200 ms）。
    - 日付範囲フィルタ（--from / --to）と DB パスの引数/環境変数対応を実装。
- リサーチ（ファクター計算）
  - research/factor_research.py（骨組み）
    - DuckDB 接続を受け取り、prices_daily / raw_financials を用いたモメンタム・ボラティリティ・バリュー等のファクター計算モジュールを追加（モジュール設計と定数・仕様を実装）。一部関数は継続実装が必要（ファイル末尾で未完）。
- パッケージエクスポート
  - portfolio パッケージから主要関数を __all__ で公開。

### Changed
- ログの標準出力先を stderr ではなく stdout に設定（cron/Task Scheduler からのリダイレクト運用を考慮）。

### Fixed
- .env パースの堅牢化
  - クォート内のバックスラッシュエスケープやインラインコメント処理に対応。
  - export KEY=val 形式に対応。
- run_monitoring/run_execution のリソースクリーンアップ
  - finally ブロックで SQLite/DuckDB 接続をクローズするようにしてプロセス終了時の資源リークを回避。

### Notes / ドキュメント的注記
- apply_sector_cap の価格欠損時の扱いについて TODO を残しています（price が 0.0 の場合エクスポージャーが過少見積りとなるリスク）。将来的に前日終値等をフォールバック価格として採用する検討が必要です。
- position_sizing では現時点で単元株数（lot_size）は全銘柄共通の引数で扱っています。将来的に銘柄別 lot_map をサポート予定（TODO コメントあり）。
- research/factor_research.py はモジュール設計・定数は整っていますが、ファイル末尾に未完の実装箇所が存在します（継続実装が必要）。

### Security
- 本リリースでは機密情報（API トークンやパスワード）を .env に保存する設計を採用しています。`.env` は絶対にリポジトリへコミットしないでください（config_setup のヘッダにも注意書きを追加済み）。

---

将来的リリースでは以下を予定しています（例）:
- factor_research の完全実装とユニットテスト追加。
- ExecutionEngine / BrokerClient 周りのモックとインテグレーションテスト整備。
- 銘柄単位の lot_size サポートと価格フォールバック改善。
- 監視・アラートの LINE 連携の実装・検証。

README やユーザ向けドキュメントに起動手順、環境変数一覧、運用上の注意（Kill Flag／PID の扱い等）を追加することを推奨します。