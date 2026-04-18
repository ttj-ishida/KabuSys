CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

注: 以下の履歴は、提示されたコードベースの内容から機能追加・設計方針・修正点を推測して作成しています。

Unreleased
----------

- （現時点で未リリースの作業はありません）

[0.1.0] - 2026-04-18
-------------------

Added
- 全体
  - パッケージの初期バージョンを追加。__version__ を "0.1.0" に設定。
  - DuckDB と SQLite を併用するデータ基盤を導入（duckdb: 分析用、sqlite: 監視/トレードログ用）。
  - ログ管理の統一ユーティリティを追加（kabusys.utils.logging_setup.setup_logging）。
    - stdout 出力（StreamHandler）と日次ローテーションのファイル出力（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ自動作成、ログレベル解決（引数 > 環境変数 > デフォルト）。
- 設定管理
  - .env 自動読み込み機能を追加（プロジェクトルート判定は .git / pyproject.toml を基準）。
  - .env パーサーを実装（export プレフィックス対応、シングル/ダブルクォート対応、インラインコメント処理、保護された環境変数上書き制御）。
  - Settings クラスを追加し、アプリ設定をプロパティ経由で取得可能に（J-Quants / kabuAPI / DBパス / paper trading 設定 / 閾値 / 環境判定など）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
- 実行・監視スクリプト
  - run_execution スクリプトを追加（ExecutionEngine の起動ラッパー）。
    - KABUSYS_ENV=paper_trading の場合、専用 paper_trading DB を使用し MockBrokerClient を利用して本番 DB と完全分離。
    - ブローカー抽象化（BrokerClientFactory）により実ブローカー/モックの切替を実現。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組立てと起動フローを実装。
    - エンジンは別スレッドで run_session を実行。data/execution.pid に PID を出力し、 data/stop_requested.flag による停止をサポート。
    - RiskManager に対するデフォルト RiskConfig を設定（max_position_pct 等のデフォルト値を含む）。
  - run_monitoring スクリプトを追加（SystemMonitor のポーリングループ起動）。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計（監視データは本番 DB に集約）。
    - stop フラグ検知でループを終了、例外発生時もログ出力して次ポーリングへ継続。
- ユーティリティ
  - プロセス優先度設定ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows / POSIX（Linux, macOS 等）に対応し、nice / priority class を抽象化。
    - CPU affinity 設定関数（set_cpu_affinity）を追加。
    - 権限不足や非対応環境に対しては安全にフォールバックして警告ログを出力。
- 開発運用支援ツール
  - config_setup: 対話式 .env 作成ウィザードを追加（各設定項目の説明・既存値の再利用・シークレットマスク付き表示）。
  - validate_config: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 値検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認（PyYAML があればパース検証）。
    - --strict モードで警告を FAIL 扱いにできる。
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率・注文成功率（fill rate）・送信率（send rate）・P95 レイテンシ等を算出し、PASS/FAIL を判定する閾値を定義。
    - P95 計算、日付フィルタ、DB 存在チェック、各種 SQL クエリを実装。
- ポートフォリオ構築（純関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア順で候補選定（タイブレークに signal_rank を使用）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分を実装（全スコア 0 時は等配分にフォールバックし警告）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限ロジックを実装（当日売却予定銘柄はエクスポージャーから除外、"unknown" セクターは上限適用除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジームは 1.0 でフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算を実装。
      - risk_based: 許容リスク率・損切り率を用いて各銘柄の基準株数を算出。
      - equal/score: 各銘柄の重みに基づく割当計算。
      - 単元（lot_size）での丸め、1銘柄上限、aggregate cap（available_cash）を超える場合のスケールダウンと端数処理（残余での lot 単位追加配分）を実装。
- 研究用モジュール（骨格）
  - research.factor_research: モメンタム等のファクター計算のための骨格を追加（定数・設計方針・calc_momentum の導入開始）。DuckDB の prices_daily / raw_financials テーブルを想定。

Changed
- モニタリング
  - 監視ループが MONITOR_POLL_INTERVAL 環境変数を尊重するようになり、0 以下や不正な値はデフォルト（60 秒）へフォールバックして安全化。
- .env の自動ロード順序
  - OS 環境変数 > .env.local > .env の優先順位でロードするよう仕様化（.env.local は override=True）。
  - OS 環境変数は protected として .env の上書きを防止。

Fixed
- ロギング
  - 既存ハンドラが存在する場合は一度 flush/close してからルートロガーのハンドラを再設定することで二重出力を防止。
- process_priority
  - 未対応 OS や権限不足時の例外をキャッチして警告ログ出力するようにし、起動失敗に繋がらないように修正。

Notes / Design decisions
- 監視データは運用上の理由で KABUSYS_ENV に左右されず本番の sqlite_path を使う設計になっている（意図的な仕様）。
- Paper Trading は本番 DB と完全に分離する（デフォルト data/paper_trading.db）。発注は MockBroker 経由でシミュレーション保存される。
- 多くのコンポーネントは副作用を避けるため純粋関数として実装（portfolio モジュール等）。これにより単体テストが容易になる設計を志向。

補足
- コードの一部（研究モジュール calc_momentum 等）は実装が途中で切れている可能性があります。必要に応じて追加実装・テストを推奨します。