CHANGELOG
=========

この変更履歴は "Keep a Changelog" の形式に準拠しています。  
各エントリは、コードベースから推測できる追加・変更点や挙動を日本語でまとめたものです。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更（互換性に影響する可能性があるもの）
- Fixed: バグ修正・堅牢化
- Security: セキュリティ関連

[Unreleased]
------------

（現時点のリポジトリでは未リリースの変更は特にありません）

[0.1.0] - 2026-04-19
-------------------

Added
- 基本パッケージの初期実装を追加
  - パッケージ情報:
    - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を設定。
- 起動スクリプト
  - run_execution.py: ExecutionEngine の起動ロジックを実装。KABUSYS_ENV によるペーパートレード分離、PID ファイル管理、stop フラグ監視、バックグラウンドスレッド実行をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL による間隔上書き、停止フラグ検出、例外ハンドリングを実装。
- 設定管理・ウィザード・検証
  - config.py: 環境変数の読み込みと Settings クラスを実装。
    - .env 自動ロード（.env, .env.local）をプロジェクトルート（.git または pyproject.toml 基準）から行う。無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 環境変数パースの堅牢化（export 句、クォート・エスケープ、インラインコメント処理等）。
    - 各種プロパティ（J-Quants、kabu API、DBパス、Paper Trading 関連、監視閾値、環境判定等）を提供。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを実装（既存値の読み込み・マスク表示・保存）。
  - validate_config.py: 起動前設定検証 CLI を実装。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスや config/*.yaml 存在チェック、live 環境向けのガード（LINE 設定や Kill Switch 設定）を提供。--strict モードで警告を失敗扱いにできる。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを実装。コンソール（stdout）と日次ローテートのファイルハンドラ（TimedRotatingFileHandler）を設定。ログディレクトリ作成失敗時はファイル出力をスキップ。ログレベル解決、既存ハンドラのクリーンアップを実施。
  - utils/process_priority.py: プロセス優先度（high/normal/low）設定と CPU affinity 設定関数を実装。Windows / POSIX の差分を吸収し、権限不足や未対応環境では警告を出してスキップする。
- Execution 周辺コンポーネント（起動時の組み立てロジック）
  - Execution 側で BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager、RiskManager（RiskConfig にデフォルト値）、Reconciler、ExecutionEngine の組み立てと実行停止ハンドリングを実装。paper_trading の場合は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
- 監視（Monitoring）
  - monitoring 側で init_monitoring_db を呼び出して監視用テーブルの存在を保証（冪等）。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を反映。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等配分へフォールバック（警告）。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。セクター上限ロジックと未定義セクターの扱い、レジーム別 multiplier マップ（bull/neutral/bear）を提供。
  - portfolio/position_sizing.py: 発注株数決定ロジック（allocation_method: risk_based, equal, score）を実装。損切り率、risk_pct、max_position_pct、max_utilization、lot_size、cost_buffer を考慮した計算、aggregate cap によるスケールダウンと残差ロジックを実装。
  - portfolio/__init__.py: 上記関数群をエクスポート。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から統計（システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ: avg/max/P95）を集計し、閾値に基づく PASS/FAIL レポートを出力する CLI を実装。P95 計算、期間フィルタ対応（--from/--to）、DB パス上書き (--db) をサポート。
- 研究用ファクターモジュール（骨格）
  - research/factor_research.py: DuckDB 接続を受け取りモメンタム等のファクター計算を行う設計の骨格を追加（モメンタム計算のパラメータ定義と関数プロトタイプを含む）。prices_daily / raw_financials テーブル参照を想定。

Changed
- デフォルトの監視ポーリング間隔を定め、環境変数 MONITOR_POLL_INTERVAL による上書きを実装（run_monitoring.py）。不正な値（0以下や非整数）はデフォルトにフォールバックし、警告を出す。
- ログ出力はデフォルトで stdout を使用するよう統一（cron や Task Scheduler での扱いに配慮）。ファイル出力はログディレクトリ作成が成功した場合のみ有効化。

Fixed / Hardened
- .env ファイルのパースを堅牢化（複数の引用符形式、エスケープシーケンス、inline コメントの解釈、export プレフィックス対応）。自動ロードをプロジェクトルート検出ベースにして CWD に依存しないよう改善。
- process_priority および set_cpu_affinity は権限不足や未対応 OS の場合に例外で落ちないよう例外処理を追加し、警告出力でスキップする挙動に統一。
- DB 初期化（init_monitoring_db）は冪等に呼び出しても安全に動作すること（Execution/Monitoring 起動時に保証する実装）。

Security
- .env の初期作成ウィザードで生成されるファイルに注意書きを追加（.env を絶対に Git にコミットしない旨）。

Notes / Implementation details
- ペーパートレードと本番は SQLite DB を分離（Settings.paper_sqlite_path / PAPER_TRADING_SQLITE_PATH）。
- Monitoring の実行は常に sqlite_path（本番向け）を使う設計。ペーパートレードでの監視と本番監視を意図的に分離する必要がある場合は別途設定を追加することを検討してください。
- risk_adjustment.apply_sector_cap は "unknown" セクターを上限適用の対象外とする（既知セクターのみ制限）。
- position_sizing の lot_size の将来的拡張として銘柄別単元サポート（stocks マスタ）が想定されている。
- research/factor_research.py は完全実装途中（モメンタム計算の続きを追加予定）。

Acknowledgements
- 初期リリースでは多数のモジュール（起動スクリプト、実行エンジン周辺、ポートフォリオ構築、監視、ユーティリティ、検証/設定ツール、分析ツール）が含まれます。各モジュールの詳細は該当ファイルの docstring コメントおよび関数ドキュメントを参照してください。

今後の予定（例）
- factor_research の完全実装（Momentum / Value / Volatility / Liquidity の算出ロジック）
- 単体テストの追加と CI 統合
- broker クライアントの抽象化を強化し、テスト容易性を向上
- 銘柄別 lot_size サポート、手数料/スリッページモデルの拡張
- monitoring と execution のさらなる分離・設定柔軟化

--- 
（この CHANGELOG はコードベースの実装内容から推測して作成しています。実際の設計意図や将来の変更に合わせて適宜更新してください。）