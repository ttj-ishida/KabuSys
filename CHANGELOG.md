CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
形式は「Keep a Changelog」に準拠します。

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-19
--------------------

Added
- 基本リリース: パッケージ初期バージョンを公開（__version__ = "0.1.0"）。
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイル検知による安全停止、監視用 SQLite / DuckDB への接続初期化を行う。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用して本番 DB と分離。BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository, OrderManager, RiskManager, Reconciler を組み立ててエンジンをデーモンスレッドで実行。PID ファイル管理と停止フラグ検知に対応。
- 設定・環境管理
  - kabusys.config: Settings クラスを導入。環境変数の取得・検証ロジック（必須変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性判定等）を提供。
  - .env 自動読み込み: プロジェクトルートを探索して .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。OS 環境変数を保護するための上書き制御を実装。
  - .env パーサーの強化: export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、行内コメントの取り扱い等に対応。
  - config_setup.py: 対話式ウィザードで .env を作成/更新する CLI を追加。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在と YAML パース（PyYAML がある場合）などをチェック。--strict オプションで警告も失敗扱いにできる。
- ロギング
  - utils.logging_setup: 統一ロギング設定ユーティリティを追加。コンソール出力は stdout、日次ローテーションのファイル出力（TimedRotatingFileHandler）をサポート。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで動作。
- プロセス制御ユーティリティ
  - utils.process_priority: Windows/Linux/macOS を透過してプロセス優先度を設定するユーティリティを追加。CPU affinity を限定する set_cpu_affinity も実装。権限不足等の失敗を警告して安全にスキップする。
- ポートフォリオ構築（純関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順＋タイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分を提供（スコア合計が 0 の場合は等配分にフォールバックし警告）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（unknown セクターは除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull/neutral/bear をマッピング、未知値はフォールバックして警告）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に対応した発注株数計算。単元株丸め、per-position 上限、aggregate cap（利用可能現金を超える場合のスケールダウン）や cost_buffer を考慮した保守的見積り、残余配分アルゴリズムを実装。
- モニタリング・データベース
  - 監視用 DB 初期化（init_monitoring_db）を導入／利用してテーブル存在を保証（冪等）。
  - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計を明記（run_monitoring.py）。
- Execution リスク制御
  - RiskManager 初期設定（RiskConfig）にデフォルト閾値を設定し、利用可能現金を初期ポートフォリオ値から取得して初期化。
- ペーパートレード検証ツール
  - tools.paper_verification_report: ペーパートレード SQLite を読み、稼働率、注文成功率、送信率、リスク却下数、レイテンシ (avg/max/P95) 等を集計して評価レポートを出力する CLI を追加。閾値に基づく PASS/FAIL 判定を行う。P95 算出ロジックを実装。
- 研究用モジュール（着手）
  - research.factor_research: ファクター計算モジュールの骨子を追加（モメンタム等の定数・関数インターフェースを準備）。DuckDB と prices_daily/raw_financials を想定した設計。

Changed
- run_execution.py: paper_trading 環境では専用 SQLite を使用するようにして本番データと分離。init_monitoring_db を呼び出して監視テーブルが存在することを保証する（冪等動作）。
- logging_setup: 既存ハンドラがある場合は flush/close してからクリアし再設定するようにして二重設定を防止。
- process_priority: プラットフォーム非対応時や権限不足時に詳細な警告を出すよう改善。

Fixed
- .env 読み込み失敗時に警告を出すようにして起動の妨げにならないようにした（config._load_env_file）。
- 起動スクリプトで DB クローズ処理を finally ブロックに移動して確実にリソース解放するように改善（run_monitoring.py / run_execution.py）。

Security
- .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化できるようにし、テストや CI で意図しない環境注入を防止可能。

Known issues / TODO
- research.factor_research の実装は途中（calc_momentum の実装がファイル末尾で途中）であり、完全実装は今後の作業。本機能は現時点では experimental。
- position_sizing の価格欠損（price が 0.0）時の挙動について注記を残している（将来的に前日終値等のフォールバック価格を導入する予定）。
- 単元株数のハードコード（デフォルト lot_size=100）は将来的に銘柄別に拡張予定。

Notes
- 本リリースは初期機能群の整備と CLI/ユーティリティ類の充実を目的としたもので、実取引・本番稼働前には validate_config による設定検証と十分なテストを強く推奨します。