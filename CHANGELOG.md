# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

値: 0.1.0 リリース日をソース内の例示日付に合わせて 2026-04-21 としています。

## [Unreleased]


## [0.1.0] - 2026-04-21

### Added
- プロジェクト初期リリースとして以下の主要機能・モジュールを追加。
- 設定管理
  - kabusys.config.Settings: 環境変数を扱う Settings クラスを導入。J-Quants / kabuステーション / LINE / DB /監視閾値などのプロパティを提供。
  - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` をロード。OS 環境変数を保護する仕組みを実装。`KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロードを無効化可能。
  - PAPER_FILL_MODE のバリデーション（有効値: instant|partial|never|reject）や KABUSYS_ENV / LOG_LEVEL の検証を実装。
- 環境設定ウィザード（CLI）
  - kabusys.config_setup: 対話式ウィザードで `.env` を作成・更新するツールを追加。シークレットのマスク表示・既存値の再利用・保存確認を実装。
- 設定検証ツール（CLI）
  - kabusys.validate_config: 起動前に環境変数や config/*.yaml の整合性を検証する CLI を追加。PyYAML の有無に応じた挙動、`--strict` フラグによる警告の FAIL 扱いを実装。
- 実行 / 監視 起動スクリプト
  - run_execution: ExecutionEngine 起動用スクリプトを追加。`KABUSYS_ENV=paper_trading` 時は専用の paper DB（data/paper_trading.db デフォルト）と MockBrokerClient を使用して本番 DB と分離。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番 sqlite_path を参照。
  - 両スクリプトとも起動時にプロセス優先度を "high" に設定（utils.process_priority）。
  - 停止制御用のフラグファイル（data/stop_requested.flag）と PID ファイル管理をサポート。
- ロギング・プロセスユーティリティ
  - kabusys.utils.logging_setup.setup_logging: ルートロガーへ StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定する共通ユーティリティを追加。ログディレクトリ作成失敗時のフォールバック処理あり。
  - kabusys.utils.process_priority: Windows / POSIX 間の差分を吸収してプロセス優先度（nice / HIGH_PRIORITY_CLASS）と CPU affinity 設定を行うユーティリティを追加。権限不足等の失敗は警告でスキップ。
- Execution 系コンポーネント（エンジン周り）
  - 実行系の骨組み（BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等）を組み合わせて起動できるようにした（run_execution からの起動フローを実装）。
  - RiskManager に既定の RiskConfig を設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker, max_drawdown 等）。初期ポートフォリオ値は broker.get_available_cash() から取得。
- モニタリング DB 初期化
  - kabusys.monitoring.monitoring_db.init_monitoring_db を呼び出して監視用テーブルの存在を保証（冪等）。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - kabusys.portfolio.portfolio_builder:
    - select_candidates: スコア降順 + signal_rank によるタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を実装。スコア合計が 0 の場合は等配分へフォールバック（警告）。
  - kabusys.portfolio.risk_adjustment:
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外する機能を追加。unknown セクターは除外対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（マップ化、未知レジームはフォールバック並びに警告）。
  - kabusys.portfolio.position_sizing:
    - calc_position_sizes: risk_based / equal / score の allocation_method をサポート。損切り・ロット丸め（lot_size）・1銘柄上限・max_utilization・aggregate cap（available_cash）・cost_buffer を考慮したスケーリングロジックを実装。スケーリング時の端数処理は fractional remainder に基づいて安定的に割当て。
- Paper Trading の検証ツール
  - kabusys.tools.paper_verification_report: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数を集計し、PASS/FAIL レポートを生成するスクリプトを追加。コマンドラインで日付範囲と DB パスを指定可能。P95 は適切なパーセンタイル計算を実装。
- リサーチ（骨組み）
  - kabusys.research.factor_research: DuckDB 接続を受け取り prices_daily / raw_financials を参照してモメンタム / Value / Volatility / Liquidity 等のファクターを計算する設計を導入（calc_momentum 等の関数枠組み含む、詳細実装は継続）。

### Changed
- ログ出力の標準化: 全起動スクリプトから setup_logging を呼び出すことでログの出力先とフォーマットを統一。
- run_execution / run_monitoring:
  - 起動時にプロセス優先度を高く設定するように変更（パフォーマンス向上を目的）。
  - run_monitoring は環境に依存せず監視用に本番 sqlite_path を使用するよう設計（監視は常に本番 DB を見る想定）。
- 設定ファイルの読み込み順序: OS 環境変数 > .env.local > .env の優先順位を明確化し、OS 環境変数は保護（上書き不可）。
- .env 生成フォーマット: config_setup による .env 書き出し形式を定義（コメント/セクション付きで安全に案内）。

### Fixed
- 例外処理強化:
  - run_monitoring のポーリングループで monitor.check_once() が例外を投げてもループを継続するように例外捕捉とログ出力を追加。
  - run_execution のスレッド監視で停止フラグ検知時に engine.stop() を呼び出して安全に停止する挙動を担保。
- DB 初期化の冪等性: init_monitoring_db 呼び出しでテーブル存在確認/作成を行い、複数回呼んでも安全な初期化に修正。
- ログハンドラの多重設定防止: setup_logging は既存ハンドラを flush/close してから再設定するようにしてダブルログ出力を防止。
- process_priority / CPU affinity のエラー耐性: 権限不足や未サポート OS の場合は警告を出して処理をスキップするように改善。

### Notes
- バージョン情報はパッケージルートで __version__ = "0.1.0" として定義。
- 一部モジュール（例: research.calc_momentum の内部実装など）は引き続き実装継続中の旨がコード内にコメントで残っています。
- config/*.yaml の厳密な中身検証は PyYAML の有無に依存（未インストール時はファイル存在チェックのみ実行）。

---

(参考) 本 CHANGELOG はソースコードから推測して作成しています。実際のリリースノート作成時は差分ベースのコミットログやリリースタグを参照して内容を精査してください。