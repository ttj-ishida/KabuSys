CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

最新
----

### [0.1.0] - 2026-04-19

Added
-----
- 初期リリース: KabuSys 自動売買システムの基本コンポーネントを追加。
- 設定関連
  - Settings クラスによる環境変数ベースの設定管理を追加（kabusys.config）。
  - .env 自動読み込み機能を導入（プロジェクトルート検出: .git / pyproject.toml を基準）。
  - .env パーサーを強化（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応）。
  - config_setup CLI を追加（対話式ウィザードで .env の作成・更新）。
  - validate_config CLI を追加（起動前の環境変数・config/*.yaml の静的検証）。
- 実行ランナー
  - run_execution スクリプトを追加。ExecutionEngine 起動用。paper_trading 環境では MockBrokerClient を使用し専用 DB（data/paper_trading.db）に記録。
  - run_monitoring スクリプトを追加。SystemMonitor ポーリングループ起動用。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。
  - 停止制御用フラグファイル（data/stop_requested.flag / data/kill.flag）に対応。
- データベース / 分析
  - DuckDB・SQLite のパス設定と接続処理を追加（Settings で管理）。
  - 監視用 DB 初期化ユーティリティ（init_monitoring_db）呼び出しを実装し、監視テーブルの存在を保証。
- ポートフォリオ構築（純関数）
  - portfolio モジュールを追加:
    - portfolio_builder: 候補選定 (select_candidates)、等配分・スコア加重 (calc_equal_weights, calc_score_weights)。
    - risk_adjustment: セクター上限制御 (apply_sector_cap)、レジーム乗数計算 (calc_regime_multiplier)。
    - position_sizing: 発注株数計算（risk_based / equal / score の割り当て方式、単元株丸め、aggregate cap スケーリング、コストバッファ考慮）。
- 実行時ユーティリティ
  - logging_setup: ルートロガー設定ユーティリティを追加。コンソール出力（stdout）と日次ローテートファイル出力（TimedRotatingFileHandler）を設定。LOG_DIR/LOG_LEVEL に対応。
  - process_priority: プロセス優先度（Windows の優先度クラス / POSIX の nice）と CPU affinity 設定（set_process_priority, set_cpu_affinity）を追加。Windows / Linux / macOS で動作するよう実装。権限不足等はワーニングで安全にフォールバック。
- 実行制御 / リスク管理
  - ExecutionEngine の組み立て処理（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler）を実装。RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec 等）を追加。initial_portfolio_value を broker.get_available_cash() から初期化。
- ツール
  - tools/paper_verification_report: ペーパートレード DB から検証レポートを生成する CLI を追加。稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）を算出し、閾値に基づく PASS/FAIL 判定を行う。P95 計算や日付フィルタの扱いを実装。
- パッケージ情報
  - パッケージのバージョンを 0.1.0 として設定（kabusys.__version__）。

Changed
-------
- 監視・実行の既定挙動
  - 監視ループは停止フラグを検知して安全終了するように実装。例外は個別ポーリングでキャッチしてログ出力し、ループは継続。
  - 実行エンジンはデーモンスレッドで起動し、停止フラグを検知すると Engine.stop() を呼び安全終了を試みる。
- DB パスと環境分離
  - paper_trading 環境では paper_sqlite_path を使用し、本番監視 DB と分離するように変更（デフォルト: data/paper_trading.db）。

Fixed
-----
- .env 読み込みの頑健性向上（ファイル読み込み失敗時に警告を出し処理を継続）。
- logging_setup: ログディレクトリ作成失敗時はファイルハンドラをスキップし、コンソール出力のみで継続するよう改良（起動環境による安定性向上）。
- process_priority: 未対応 OS や権限不足時の例外をハンドリングし、安全にフォールバックするよう修正。

Deprecated
----------
- なし（初期リリースのため該当なし）。

Removed
-------
- なし（初期リリースのため該当なし）。

Security
--------
- なし（特別なセキュリティ修正は今回のコードからは検出されませんが、.env を絶対にコミットしない旨の注記を config_setup に明記）。

Notes / Known issues
--------------------
- research/factor_research.py はモジュール実装が一部未完（ファイル末尾で実装途中の記述あり）。ファクター計算機能は設計方針と定数を定義済みだが、すべての関数の完成が必要。
- position_sizing や risk_adjustment は現在「全銘柄共通の単元株数(lot_size)＝100」を前提としている。将来的な拡張（銘柄別 lot_size）は TODO 。
- 一部箇所で外部パッケージ（psutil, duckdb, PyYAML 等）に依存。これらがインストールされていない場合、一部機能（CPU affinity, DuckDB クエリ、YAML 検証等）が制限される。validate_config は PyYAML 非インストール時に YAML 検証をスキップする。

開発・運用ガイド
----------------
- .env はプロジェクトルートに配置し、絶対に Git 等へコミットしないこと。
- 起動前に python -m kabusys.validate_config で設定を検証することを推奨。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 に設定することを推奨（自動クリアは危険）。

署名
----
この CHANGELOG は提示されたコードベースの内容から推測して作成しました。実際の変更履歴（コミットログ等）と差異がある可能性があります。必要であれば、実際の VCS 履歴に基づいた正確な CHANGELOG へ調整します。