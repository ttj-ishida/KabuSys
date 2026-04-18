Keep a Changelog 準拠の CHANGELOG.md（日本語）

全般注意:
- コードベースから推測して記載しています。実際のリリース履歴と差異がある場合があります。

Unreleased
---------
- 小さな改善・安定化
  - 監視ループのポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能に（0 以下や不正値はデフォルトにフォールバックして警告）。
  - ログ設定の堅牢化: ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力（stdout）にフォールバックする挙動を強化。
  - process_priority の例外処理を改善し、権限不足や未サポート環境でも起動を継続するように変更。

0.1.0 - 2026-04-18
------------------
Added
- 初期リリース: KabuSys v0.1.0 を追加。
  - 高レベル概要:
    - 日本株自動売買システムの基本モジュール群（設定管理、実行エンジン、監視、ポートフォリオ構築、検証ツール、ユーティリティ）。
- 設定管理
  - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - .env/.env.local の読み込み順序を実装（OS 環境変数を保護、.env.local は .env を上書き）。
  - .env パーサを実装：export プレフィックス対応、クォート文字列のエスケープ処理、コメントの扱い改善。
  - Settings クラスを提供し、環境変数取得・型変換・妥当性検証を集中管理（KABUSYS_ENV, LOG_LEVEL, 各種パスやしきい値を含む）。
- 設定ツール / 検証
  - 対話式環境設定ウィザード (kabusys.config_setup) を実装し、.env の初期作成・更新を支援。
  - validate_config CLI を実装し、必須環境変数・YAML 設定ファイル・パスの存在等の事前検証を提供。--strict オプションで警告を失敗扱いにできる。
- 実行・監視スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite を使用して本番 DB と完全分離。
    - BrokerClientFactory を用いて本番/モックブローカークライアントを切り替え。
    - OrderRepository, OrderManager, RiskManager（RiskConfig のデフォルト値あり）, Reconciler を組み合わせて Engine を構築。
    - stop フラグファイル（data/stop_requested.flag）や execution.pid を扱う仕組みを実装。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数で間隔を制御可能（デフォルト 60 秒）。
    - 監視用 DB 初期化 (init_monitoring_db) と duckdb 接続を行う。
    - 停止フラグ検知・例外時のログ出力など耐障害性を考慮したループ。
- 監視・DB
  - 監視テーブル初期化ユーティリティ（init_monitoring_db）を呼び出す形で DB 準備を保証（冪等）。
  - Monitoring 処理は環境にかかわらず本番 sqlite_path を使用する設計（監視は本番 DB を前提）。
- ロギング
  - utils.logging_setup: ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定する共通ユーティリティを追加。
  - ログレベル決定順とログディレクトリ解決の挙動を定義。
  - ファイル出力に失敗した場合もコンソール出力で継続可能。
- プロセス制御ユーティリティ
  - utils.process_priority: クロスプラットフォーム（Windows / POSIX）でプロセス優先度を設定する関数を追加。
  - CPU affinity 設定関数 set_cpu_affinity を提供（利用可能なコアに基づく固定、権限不足でフォールバック）。
- ポートフォリオ構築
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等配分にフォールバック。
  - portfolio.risk_adjustment: セクター集中制限を適用する apply_sector_cap を実装。unknown セクターは上限適用外。レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear およびフォールバック）。
  - portfolio.position_sizing: position sizing アルゴリズムを実装（risk_based / equal / score をサポート）。単元株丸め、1銘柄上限、aggregate cap（利用可能現金を超える場合のスケールダウンと端数処理）を実装。手数料・スリッページ見積りのための cost_buffer を考慮。
- リサーチ
  - research.factor_research: モメンタム等ファクター計算モジュールを追加（DuckDB 接続を受け prices_daily / raw_financials を参照する設計）。モメンタム計算の関数 calc_momentum を実装（実装は本リリース内での初期実装／一部省略の可能性あり）。
- ペーパートレード検証ツール
  - tools.paper_verification_report: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から集計し、稼働率・注文成功率・送信率・レイテンシ等を評価するレポート生成 CLI を追加。P95 計算、しきい値による PASS/FAIL 判定を実装。DB 存在チェックや OperationalError の耐性あり。
- モジュール初期化
  - パッケージバージョンを __version__ = "0.1.0" として設定。

Changed
- .env 読み込みにおける既存環境変数保護と .env.local の上書き挙動を明確化。
- ログ出力を stderr ではなく stdout に統一（cron / スケジューラとの相性を考慮）。
- run_execution/run_monitoring 起動時に process priority を最初に設定するよう順序を明確化。
- 設定検証ロジック (validate_config) を追加し、YAML パース可否により検証を柔軟にスキップ/警告する。

Fixed
- ログディレクトリ作成失敗時に例外で停止する問題を修正（警告出力してファイルロギングを無効化）。
- .env ファイル読み込みでファイルアクセスエラー時に適切に警告を出してスキップするよう修正。
- process priority / cpu affinity で権限不足や未対応 OS によるクラッシュを防止するため例外を捕捉して警告に留めるよう修正。
- Paper verification report で対象テーブルが存在しない場合の例外を捕捉して N/A を出力するようにした。

Security
- config_setup で生成される .env に対して「絶対に Git にコミットしないこと」と注記を追加（秘密情報保護の注意喚起）。

Notes / Known issues
- research.factor_research の実装は大規模データ前提で DuckDB を使用する設計だが、一部関数が未完（ファイル末尾で切れている箇所があるため追加実装が必要）。
- 本リリースはコードベースから推測した初期機能群の実装をまとめたものです。実運用前に validate_config による事前検証と、paper_trading モードでの十分な検証を推奨します。