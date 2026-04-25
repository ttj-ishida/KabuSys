CHANGELOG
=========

この CHANGELOG は Keep a Changelog のフォーマットに準拠しています。  
以下は提示されたコードベースの内容から推測して作成した変更履歴（日本語）です。

なお、記載はコード内容に基づく推測であり、実際のコミット履歴やリリースノートと完全に一致しない場合があります。

[Unreleased]
------------

- 既知の制限 / TODO
  - research.factor_research.calc_momentum の実装が途中で切れている（未完）。
  - position_sizing の lot_size を銘柄別に扱う拡張（stocks マスタの導入）や price のフォールバック（前日終値等）の実装が未着手。
  - 一部コメントに将来的な改善案が残っている（price フォールバック、lot_map 等）。

0.1.0 - 2026-04-25
------------------

Added
- 初期リリース: KabuSys 基本機能群を追加。
  - 実行・監視ランナー
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（data/paper_trading.db）を利用し、MockBrokerClient を使用して本番 DB と分離する挙動をサポート。
      - 起動時にプロセス優先度を "high" に設定するフローを追加。
      - 停止フラグ（data/stop_requested.flag）と PID ファイルを扱う制御を実装。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境に関わらず本番 sqlite_path を使用する設計。
  - 設定・環境管理
    - config.py: .env 自動読み込み（.env / .env.local）と Settings クラスを実装。多くの設定プロパティ（DB パス、API トークン、閾値、環境判定等）を提供。
      - .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
      - 環境変数のパースはクォート、エスケープ、コメントに対応する堅牢な実装。
      - PAPER_FILL_MODE 等の許容値チェック実装。
    - config_setup.py: 対話式 .env 作成ウィザードを実装（.env の読み書き・項目定義）。
    - validate_config.py: 起動前に .env と config/*.yaml の設定検証を行う CLI を実装（--strict オプションあり）。
  - ロギング・プロセス管理ユーティリティ
    - utils/logging_setup.py: 統一ログセットアップを実装。stdout ストリームハンドラと日次ローテーション（TimedRotatingFileHandler）を設定。LOG_DIR 作成失敗時のフォールバック対応あり。
    - utils/process_priority.py: クロスプラットフォームでプロセス優先度（nice / Windows priority）と CPU affinity 設定のユーティリティを追加。権限不足時は警告を出して安全にスキップする。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア合計が 0 の場合は等分配にフォールバック。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下倍率（calc_regime_multiplier）を実装。未知のレジームはフォールバック挙動あり。
    - portfolio/position_sizing.py: allocation_method（"risk_based"/"equal"/"score"）に基づく発注株数計算を実装。単元株丸め、1 銘柄上限、aggregate cap（利用可能現金超過時のスケーリング）を実装。コストバッファ（手数料・スリッページ見積り）を考慮。
    - portfolio/__init__.py で上記関数をエクスポート。
  - Execution 周り（設計上の組み立て）
    - run_execution でのコンポーネント組み立てを実装（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine）。RiskManager にデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を用意し、初期ポートフォリオ値は broker.get_available_cash() を利用。
  - monitoring/ と tools/
    - monitoring_db 初期化ユーティリティ（init_monitoring_db）を使用して監視テーブルの作成を保証（冪等処理）。
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出し PASS/FAIL 判定を行う。閾値はソース内定数で定義。
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールを追加。モメンタム、MA200 乖離、ATR、ボラティリティ等の計算方針を記載（calc_momentum は実装の続きが必要）。

Changed
- デフォルト設定と防御的実装を多めに導入
  - ログ設定: 既存ハンドラをクリアしてから設定することで二重出力を防止。
  - .env パーサー: export プレフィックス、クォート・バックスラッシュ、インラインコメント等に対応。
  - run_monitoring: MONITOR_POLL_INTERVAL の不正値に対してデフォルトへフォールバックし警告を出す実装を追加。
  - run_execution/run_monitoring: 起動時にプロセス優先度を最初に設定するように統一。
  - DB 接続: DuckDB と SQLite を併用（分析用と監視/発注ログ分離）。paper_trading モード時は SQLite を分離してデータの混在を防止。
  - ExecutionEngine 起動前に停止フラグをチェックして不要起動を回避する安全策を追加。

Fixed
- 例外・権限周りの安全化
  - process_priority.set_process_priority で権限不足（psutil.AccessDenied 等）の場合に警告してスキップするように変更（クラッシュ回避）。
  - logging_setup: ログディレクトリ作成に失敗した場合にファイルハンドラをスキップし、コンソール出力のみで継続するフェイルセーフを追加。
  - 各種 DB クエリ系ツール（paper_verification_report）でテーブル欠如や OperationalError を捕捉して null/デフォルト値を返すようにして堅牢化。

Security
- シークレット扱いの環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE_CHANNEL_ACCESS_TOKEN）は .env ウィザードでマスク表示するなど取り扱い上の注意を促す文言を導入。README や .env ヘッダには「.env を絶対に Git にコミットしないこと」と明記。

Notes / その他
- 多くのモジュールは「DB を参照しない純粋関数」設計としている（portfolio や position sizing 等）。これによりテスト容易性を高めている。
- コード中に将来的改善（価格フォールバック、銘柄別 lot_size、calc_momentum の完成など）を示す TODO コメントがある。
- バージョンはパッケージ __init__.py によって 0.1.0 に設定。

参考（実装上の主な挙動）
- 停止制御: data/stop_requested.flag を検知すると監視ループ・エンジンを終了する。
- ロギング: stdout と日次ローテートログ（logs/<app_name>.log）を利用。LOG_DIR の作成に失敗した場合は stdout のみ。
- Paper Trading: 設定が paper_trading の場合、発注・約定挙動はモックで処理し専用 SQLite に記録して本番 DB と分離。

----- 

以上。必要であれば実際のコミット単位の CHANGELOG への分割、各ファイルごとのより詳細な変更点や例（設定例、CLI の使い方）を追加で作成します。どの粒度で出力するか指示してください。