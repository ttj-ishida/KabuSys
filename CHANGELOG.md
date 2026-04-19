# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルは、コードベースから推測できる機能追加・改善点・挙動をまとめたリリースノートです。

全般的な注記
- リリース内容はソースコードの実装・ドキュメント文字列から推測してまとめています。実際のリリースノートと差異がある場合があります。

## [Unreleased]
- （現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-19
初回公開リリース。日本株自動売買フレームワーク「KabuSys」の基礎機能を実装しました。

### Added（追加）
- 基本パッケージ
  - パッケージメタデータ（src/kabusys/__init__.py）を導入（バージョン 0.1.0）。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
    - プロセス優先度を起動時に設定（high）。
    - KABUSYS_ENV=paper_trading の場合、専用の Paper Trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine の起動とスレッド管理、停止フラグ（data/stop_requested.flag）検出による安全停止を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ検知によるループ終了、例外発生時のログ出力とスリープ継続を実装。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用（設計上の注意）。
- 設定管理・ウィザード・検証
  - config.py: 環境変数/ .env の読み込みと Settings クラスを実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を起点）による .env 自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化可）。
    - .env パースは export プレフィックス、クォート（シングル/ダブル）およびエスケープ、インラインコメントの取り扱いに対応。
    - 各種設定プロパティにデフォルト値、妥当性チェック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実装。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを実装（複数の設定項目を対話的に設定し .env を生成）。
  - validate_config.py: 設定検証 CLI を実装。必須環境変数のチェック、ファイルパスの存在確認、config/*.yaml の存在・パース確認（PyYAML があれば内容検証）。--strict モードで警告を FAIL 扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N 件を選択。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア比率で重みを計算（全スコア 0 の場合は等分配にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中の上限チェック。既存保有を考慮して新規候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数決定ロジックを実装。
      - 単元株（lot_size）丸め、1銘柄上限・aggregate cap、cost_buffer を考慮したスケーリングと再配分処理を実装。
- ユーティリティ
  - utils.logging_setup
    - 標準ログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - 既存ハンドラのクリア処理を行い二重出力を防止。
    - LOG_DIR/LOG_LEVEL からの設定解決や、ログディレクトリ作成失敗時のフォールバック処理を実装。
  - utils.process_priority
    - set_process_priority / set_cpu_affinity を実装。Windows と POSIX（Linux/Mac/FreeBSD）で差分を吸収し、権限不足などで失敗した場合は警告を出してスキップ。
- ツール
  - tools.paper_verification_report
    - Paper Trading 用の検証レポート生成スクリプトを追加。システム稼働率、注文成功率/送信率、リスク却下数、API レイテンシ（P95 など）を計算して標準出力にレポートを表示。しきい値に基づく PASS/FAIL 判定を実装。
- DB 初期化連携
  - monitoring.monitoring_db.init_monitoring_db を起動コード（実行/監視）から呼び出して監視テーブル等の冪等な初期化を保証。
- Research（開始実装）
  - research.factor_research: モメンタム等のファクター計算モジュールを追加（DuckDB 経由で prices_daily / raw_financials を参照する設計）。（ファイルは途中までの実装）

### Changed（変更）
- ロギングの出力先とハンドラ挙動
  - ルートロガーの既存ハンドラを明示的に flush/close/削除してから再設定するように変更（多重ハンドラ登録を防止）。
  - StreamHandler が stdout を使用するように統一（cron/Task Scheduler 等でのリダイレクト運用を考慮）。
- .env の自動ロード順序
  - OS 環境変数を保護しつつ .env（.env.local）を読み込む挙動を実装。OS 環境変数が優先される。 .env.local は上書き可能。

### Fixed（修正 / 安全性改善）
- プロセス優先度設定はプラットフォーム差を吸収し、権限不足や未実装 API の場合でも例外を発生させず警告でスキップするように（安定性向上）。
- run_execution / run_monitoring の終了処理で SQLite / DuckDB 接続を確実にクローズするようにしました（finally ブロック）。

### Notes（注意事項）
- run_monitoring は設計上「監視」は本番用の sqlite_path を参照する仕様になっています（KABUSYS_ENV に依存せず本番 DB を使用）。環境分離を期待する場合は注意してください。
- PAPER_TRADING 環境では発注処理に MockBrokerClient 相当が使われ、paper_trading 用 DB を使用して本番 DB と完全分離されることを想定しています（run_execution の実装）。
- config.PAPER_FILL_MODE には "instant" / "partial" / "never" / "reject" の有効値があるため、無効値設定時は ValueError が発生します。
- validate_config により、起動前に必須環境変数や設定ファイルの不足を検出できます。特に本番環境（KABUSYS_ENV=live）では LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値を確認する警告が表示されます。

---

（翻訳注）この CHANGELOG はソースコードから推測して作成しています。実際のリリースノートとして使用する場合は、差分やコミットログを参照して補完してください。