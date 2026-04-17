CHANGELOG
=========

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

[0.1.0] - 2026-04-17
--------------------

### Added
- 初期リリース: KabuSys v0.1.0 を追加。
- 基本ランタイム・起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB（data/paper_trading.db または PAPER_TRADING_SQLITE_PATH）を使用し、MockBrokerClient を利用可能にする挙動を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番の sqlite_path を使用する仕様。
- 環境設定・検証 CLI
  - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI。主要な環境変数の対話入力・既存 .env の読み込み・マスク表示等をサポート。
  - validate_config.py: .env と config/*.yaml の整合性・存在チェックを行う検証 CLI。--strict オプションで警告を失敗扱いにできる。PyYAML 未導入時は YAML 検証をスキップして警告を出す。KABUSYS_ENV=live に対する追加ガード（LINE 設定漏れや Kill Switch 設定の警告）を実装。
- 設定管理モジュール
  - config.py: .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）・堅牢な .env パーサを実装。export プレフィックス、クォート値、インラインコメントの扱い、override/protected の考慮などをサポート。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。Settings クラスにアプリケーション設定プロパティを集約（DB パス、PID/kill フラグ、Paper Trading 設定、監視閾値など）。
- ポートフォリオ構築ライブラリ（純粋関数群、DB 非依存）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で候補選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（スコア合計が 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限。既存保有と当日売却予定を考慮し、上限を超えるセクターの新規候補を除外（"unknown" セクターは上限を適用しない）。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear のデフォルトマッピング、未知レジーム時はログ出力して 1.0 をフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: 重み・リスクベース等の複数アルゴリズムで発注株数を計算。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金に合わせたスケールダウン）、cost_buffer を用いた保守的見積り、スケールダウン後の残差配分ロジックを実装。
- ユーティリティ
  - utils.process_priority: プロセス優先度設定ユーティリティ。Windows と POSIX 系（Linux/Mac/FreeBSD）を吸収し、nice/priority クラスを適切に設定。set_cpu_affinity による CPU ピン留め機能を提供。権限不足や未対応 OS の場合は警告してスキップ。
- リサーチ（DuckDB を利用したファクター計算）
  - research.factor_research: Momentum / Volatility 等のファクター計算関数を追加。DuckDB 接続を受け prices_daily / raw_financials を参照してモメンタムや ATR 等を計算する設計（純粋関数、外部 API に依存しない）。
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプト。指定期間の稼働率、注文成功率、送信率、レイテンシ指標（平均/最大/P95）などを SQLite（PAPER_TRADING_SQLITE_PATH）から集計し PASS/FAIL 判定を行う。検証基準（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
- データベース初期化
  - monitoring.monitoring_db.init_monitoring_db を各起動スクリプトで呼び出し、監視テーブルの存在を保証（冪等）。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- .env パーサの堅牢化: クォートされた値のバックスラッシュエスケープ処理、export KEY=val 形式、インラインコメントの扱いなどを考慮。
- run_execution/run_monitoring: 起動直後に set_process_priority("high") を呼び出すことで優先度を上げるようにした（実行環境に依存して失敗時はログで通知して継続）。

### Deprecated
- （初回リリースにつき該当なし）

### Removed
- （初回リリースにつき該当なし）

### Security
- 環境変数取り扱いの注意喚起: config_setup にて .env を Git 管理しない旨のコメントを出力。Settings._require により必須環境変数未設定時は明示的にエラーを発生させることで起動前に検出可能。

Notes / 備考
- 監視用の SQLite（monitoring DB）と Paper Trading 用 DB は明確に分離されている。run_monitoring は監視の独立性確保のため KABUSYS_ENV に関わらず settings.sqlite_path（デフォルト data/monitoring.db）を使用する設計になっている点に注意してください。
- 多くのコンポーネント（ExecutionEngine／SystemMonitor／Broker クライアント等）は依存注入的に設計されており、テストやモック差し替えが容易です。
- 将来的な拡張点（コード中コメント）
  - position_sizing: 銘柄ごとの lot_size を持つマスタ導入のための拡張ポイント
  - risk_adjustment: 価格欠損時のフォールバック価格（前日終値や取得原価）を導入する余地

--- 

（以降の変更はこのファイルに記録してください）