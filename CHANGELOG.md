CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

（現在なし）

0.1.0 - 2026-04-17
------------------

Added
- プロジェクト初期リリースとして基本機能を実装
  - 環境設定 / 起動用ユーティリティ
    - kabusys.config: .env 自動読み込み（プロジェクトルートは .git または pyproject.toml で検出）
      - .env と .env.local を OS 環境変数を保護しつつ読み込む仕組みを提供
      - export KEY=val 形式、クォート（シングル/ダブル）およびエスケープシーケンス、インラインコメントを正しくパース
    - kabusys.config_setup: 対話式ウィザードで .env を生成 / 更新する CLI（python -m kabusys.config_setup）
    - kabusys.validate_config: .env と config/*.yaml の設定検証 CLI（--strict オプションで警告を失敗扱いに）
      - PyYAML 未インストール時は YAML 検証をスキップして警告を出力
      - live 環境向けの追加ガード（LINE 通知設定や Kill Switch の注意喚起）
  - 実行 / 監視プロセス起動スクリプト
    - run_execution: ExecutionEngine 起動スクリプト
      - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite を使用し、本番 DB と分離
      - BrokerClientFactory によるブローカークライアント生成、ExecutionEngine の起動/停止制御（停止フラグ、PID ファイル管理）
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプト
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
      - 停止フラグ検知でループ終了、監視 DB 初期化処理を実行
  - ポートフォリオ構成 / 注文サイズ決定ロジック（純粋関数群）
    - portfolio.portfolio_builder
      - select_candidates: BUY シグナルをスコア降順で選定
      - calc_equal_weights / calc_score_weights: 等分配・スコア加重（スコア合計が0の場合は等分配にフォールバック）
    - portfolio.risk_adjustment
      - apply_sector_cap: セクター集中上限チェック（既存保有のセクター比率が閾値を超える場合は新規候補を除外）
      - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数
    - portfolio.position_sizing
      - calc_position_sizes: allocation_method に応じた株数決定（risk_based / equal / score）、lot_size に基づく丸め、aggregate cap によるスケーリングと端数配分
  - リサーチ / ファクター計算
    - research.factor_research: DuckDB を用いたモメンタム・ボラティリティ等のファクター計算（calc_momentum, calc_volatility 等）
      - prices_daily / raw_financials テーブルのみを参照する安全設計
  - 運用ツール
    - tools.paper_verification_report: ペーパートレード結果（monitoring / trade_logs / risk_logs）から検証レポート生成（P95、稼働率、成功率等）
      - デフォルト DB パスは data/paper_trading.db、期間指定オプションあり
  - ユーティリティ
    - utils.process_priority: クロスプラットフォームなプロセス優先度設定 / CPU affinity 設定（Windows / POSIX を吸収）
      - 権限不足や未サポート環境を考慮して警告ログで安全にフォールバック

Changed
- アプリケーション構成方針
  - 監視コンポーネント（run_monitoring）は KABUSYS_ENV に関係なく監視用の sqlite_path（デフォルト: data/monitoring.db）を使用するように明示
  - ペーパートレードは本番 DB と完全分離（settings.paper_sqlite_path／PAPER_TRADING_SQLITE_PATH）
- 起動時の振る舞い
  - run_execution / run_monitoring 起動時にプロセス優先度を "high" に設定する初期処理を追加（set_process_priority 呼び出し）

Fixed
- 設定読み込みの堅牢化
  - .env パーサーがクォート文字内のエスケープや export プレフィックス、インラインコメントを正しく扱うよう改善
  - .env 自動読み込み時に OS 環境変数を保護（既存キーは上書きされない / .env.local は override）
- エラー耐性の向上
  - psutil 操作（nice / cpu_affinity）での AccessDenied / NotImplementedError 等を捕捉してログ出力し、起動失敗としないように変更
  - run_monitoring の監視ループで check_once() 例外を捕捉してログを残し続行するように（安定稼働重視）
  - 各種レポート・クエリでテーブル欠如に対する例外処理を追加（OperationalError を捕捉して N/A / 0 を返す）

Documentation / Tooling
- パッケージメタ情報
  - __version__ を 0.1.0 に設定
  - kabusys パッケージの主要サブモジュールを __all__ でエクスポート

Notes / その他
- 設計指針として、発注や本番 API にアクセスしないリサーチ系関数や純粋関数群（ポートフォリオ・ポジション計算）を明確に分離しているため、ユニットテストやシミュレーションが容易
- 一部コメントに将来拡張（銘柄別 lot_size の導入、価格フォールバック等）を示唆
- 初回リリースのため、細かいパラメータ（デフォルト閾値、リスク設定等）はコード中の定数および設定から調整可能

今後の予定（例）
- strategy / execution 周りのユニットテスト拡充
- 銘柄別 lot_size 対応、価格フォールバックロジックの強化
- DuckDB を使ったファクター計算の最適化および追加ファクター実装

---