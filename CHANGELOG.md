CHANGELOG
=========

すべての注目すべき変更点を記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。  

各リリースの日付は、このコードベースのスナップショット日（2026-04-18）を使用しています。

0.1.0 - 2026-04-18
-----------------

初回リリース — KabuSys 基本モジュール群と CLI/ユーティリティを追加。

Added
- パッケージ基礎
  - パッケージバージョンを追加: kabusys.__version__ = "0.1.0"。
  - 公開 API (__all__) に主要サブパッケージを追加: data, strategy, execution, monitoring。

- 構成管理
  - 環境変数読み込み・設定管理モジュールを追加 (src/kabusys/config.py)。
    - プロジェクトルート検出ロジックを導入 (.git または pyproject.toml 基準) により CWD に依存しない自動 .env ロードを実現。
    - .env/.env.local の自動読み込み（OS 環境変数優先）。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env パーサは export 構文やクォート、エスケープ、インラインコメントの取り扱いに対応。
    - Settings クラスで各種設定プロパティを提供（J-Quants / kabu API / DB パス / ログ設定 / 監視閾値 等）。
    - PAPER_FILL_MODE の検証、有効値チェックを実装。
    - KABUSYS_ENV, LOG_LEVEL の検証ロジックおよび is_live/is_paper/is_dev ヘルパーを追加。
  - 設定ウィザード CLI を追加 (src/kabusys/config_setup.py)。
    - 対話式で .env を初期作成・更新可能。標準的な設定項目（KABUSYS_ENV, API トークン, DB パス, LOG_LEVEL 等）をサポート。
    - 既存 .env 読み込み・デフォルト利用・シークレットマスク表示・保存確認機能を実装。

- 設定検証ツール
  - validate_config CLI を追加 (src/kabusys/validate_config.py)。
    - 必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パス親ディレクトリ確認、config/*.yaml の存在およびパース検証（PyYAML が利用可能な場合）を実施。
    - --strict オプションで警告を FAIL 扱いにする機能を実装。
    - 本番環境向けのガード（LINE 通知設定の有無、KILL_FLAG_CLEAR_ON_START の危険な設定チェック）を追加。

- 実行/監視ランナー
  - 実行エンジン起動スクリプトを追加 (src/kabusys/run_execution.py)。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と完全分離する仕組みを導入。
    - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てを行う。
    - RiskManager にデフォルト設定を指定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）し、initial_portfolio_value をブローカーから取得して初期化。
    - PID ファイル管理、stop flag（data/stop_requested.flag）検出による安全停止処理を実装。
    - 実行エンジンを別スレッドでデーモン実行し、停止フラグ検出で engine.stop() を呼び出す制御ループを実装。
  - 監視（SystemMonitor）ポーリングループ起動スクリプトを追加 (src/kabusys/run_monitoring.py)。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトにフォールバックして警告を出力。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を明確化。
    - DB 初期化（init_monitoring_db）、DuckDB 接続、SystemMonitor.check_once() の単発実行と例外ハンドリング、停止フラグ検出処理を実装。
    - KeyboardInterrupt を捕捉して正常終了する処理を追加。

- 監視 DB 初期化ユーティリティとの連携
  - run_execution/run_monitoring で init_monitoring_db を呼び出し、監視テーブルが存在することを冪等に保証。

- ロギング
  - 統一的なログ設定ユーティリティを追加 (src/kabusys/utils/logging_setup.py)。
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定。
    - ログレベルおよびログディレクトリの解決順を定義（引数 > 環境変数 > デフォルト）。
    - 既存ハンドラを安全にクローズして再設定する仕組み、ログディレクトリ作成失敗時のフォールバックを実装。

- プロセス優先度 / CPU Affinity
  - クロスプラットフォーム対応のプロセス優先度ユーティリティを追加 (src/kabusys/utils/process_priority.py)。
    - Windows と POSIX (Linux/Mac/FreeBSD) の差分を吸収し、"high" / "normal" / "low" の指定で nice 値や Windows 優先度を設定。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応 OS の場合はログ警告でスキップ。

- ポートフォリオ構築ユーティリティ
  - 銘柄選定・重み計算モジュールを追加 (src/kabusys/portfolio/portfolio_builder.py)。
    - select_candidates（スコア降順で上位 N 選出）、calc_equal_weights、calc_score_weights（スコア合計0時に等配分へフォールバック）を実装。
  - セクター集中制限およびレジーム乗数モジュールを追加 (src/kabusys/portfolio/risk_adjustment.py)。
    - apply_sector_cap（既存保有を考慮したセクター別上限適用、"unknown" セクターの扱い）を実装。
    - calc_regime_multiplier（"bull"/"neutral"/"bear" に対する乗数マップ、未知レジームは 1.0 でフォールバック）を実装。
  - 株数決定・リスク制限・単元丸めモジュールを追加 (src/kabusys/portfolio/position_sizing.py)。
    - allocation_method ("risk_based" / "equal" / "score") をサポートした株数計算。
    - 単元（lot_size）考慮、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap スケーリング。
    - リスクベース計算（risk_pct, stop_loss_pct）および不足価格時のログスキップ、scale-down の際の端数配分ロジックを実装。
  - portfolio パッケージの __init__ で主要関数をエクスポート。

- Paper Trading 検証ツール
  - ペーパートレード検証レポート生成スクリプトを追加 (src/kabusys/tools/paper_verification_report.py)。
    - SQLite（PAPER_TRADING_SQLITE_PATH）から system_status / trade_logs / risk_logs を参照して各種指標（稼働率、注文成功率、送信率、リスク却下数、平均/最大/P95 レイテンシ）を算出。
    - P95 計算、閾値（稼働率 99%、成功率 90% 等）による PASS/FAIL 判定を実装。
    - コマンドライン引数 --from / --to / --db をサポート。DB が存在しない場合の分かりやすいエラーメッセージを出力。

- リサーチ / ファクター計算（初期）
  - factor_research モジュールを追加 (src/kabusys/research/factor_research.py)。
    - Momentum / Value / Volatility / Liquidity を想定した設計を導入。DuckDB の prices_daily / raw_financials を参照する方針。
    - モメンタム計算（calc_momentum）の雛形を作成（日時定数、スキャン幅等の定義）。実装は一部（ファイル末尾で途切れ）で継続予定。

Changed
- なし（初回リリースのため既存からの変更はなし）。

Fixed
- なし（初回リリース）。

Deprecated
- なし。

Security
- なし。

Notes / 備考
- run_execution は paper_trading モード時に本番 DB を使わず data/paper_trading.db を使用することで本番と完全分離を意図しています。デフォルト .env 値や設定ウィザードの説明を参照してください。
- ログ出力は標準出力（stdout）に加え、logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。
- process_priority と set_cpu_affinity は権限やプラットフォームに依存するため、失敗時は警告ログを出力して安全にフォールバックします。
- .env の自動ロードは CWD に依存しない設計ですが、プロジェクトルートが検出できない場合は自動ロードをスキップします。自動ロードを完全に無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- factor_research は設計方針と定数を含む実装を開始していますが、完全実装は継続中です（このリリースではモジュールの雛形を含む）。

今後の計画（例）
- factor_research の完全実装（DuckDB クエリ実装、Zスコア正規化との統合）。
- ExecutionEngine / SystemMonitor の単体テスト充実および例外発生時のリカバリ改善。
- 銘柄別 lot_size マスタ対応や position_sizing のさらなる堅牢化。
- Paper Trading / MockBroker の動作検証とレポート指標の拡張。

--- 

(翻訳注: 本 CHANGELOG は提供されたコードスナップショットの内容から推測して作成しています。実際のコミット履歴や設計ドキュメントに基づく変更履歴と差異がある可能性があります。)