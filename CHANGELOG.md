# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」準拠です。

## [0.1.0] - 2026-04-19

Added
- 初期リリースとして以下の機能群を追加。
  - 起動スクリプト
    - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用の SQLite（data/paper_trading.db）に記録して本番 DB と分離する挙動を実装。
    - run_monitoring.py: SystemMonitor のポーリングループを実行するスクリプト。MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能。Monitoring は環境にかかわらず本番 sqlite_path を使用する（監視用 DB の初期化処理を実行）。
  - 設定・環境管理
    - config.py: Settings クラスを導入し、環境変数経由で設定を取得。J-Quants、kabu API、LINE、DB パス、監視閾値、実行環境判定（development / paper_trading / live）などのアクセサを提供。
      - .env ファイルの自動ロード機能を実装（プロジェクトルートの検出に .git または pyproject.toml を利用）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
      - PAPER_FILL_MODE のバリデーション、paper_sqlite_path のサポートなどを追加。
  - 設定ツール・検証
    - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を追加。シークレットのマスク表示、デフォルト値、説明文、書き込み機能を提供。
    - validate_config.py: .env と config/*.yaml の事前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、YAML のパースチェック、live 環境向けの追加ガードを実装。--strict オプションで警告を FAIL 扱いにできる。
  - ポートフォリオ構築ライブラリ（純粋関数）
    - portfolio.portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights、全スコアが0の場合は等配分へフォールバック）。
    - portfolio.risk_adjustment: セクター集中制限適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier。bull/neutral/bear をマップ、未知のレジームでフォールバック）。
    - portfolio.position_sizing: position sizing ロジック（allocation_method に応じた risk_based / equal / score の実装）、単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）によるスケールダウン、cost_buffer を用いた保守的なコスト見積もり、残差を用いた再配分ロジックを実装。
  - ユーティリティ
    - utils.logging_setup: 統一ロギング設定ユーティリティを追加。stdout へ出力する StreamHandler と日次ローテーション（TimedRotatingFileHandler）でログファイルを出力。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - utils.process_priority: プロセス優先度と CPU affinity 設定ユーティリティ。Windows / POSIX(Linux / Darwin / FreeBSD) を吸収し、OS 非対応時や権限不足時は安全にフォールバック。
  - 開発/検証ツール
    - tools.paper_verification_report: Paper Trading 用の検証レポート生成 CLI を追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを計算し、閾値に基づく PASS/FAIL 判定を行う。--from/--to/--db オプションをサポート。
  - 研究用モジュール（下位モジュール）
    - research.factor_research（骨格実装）: DuckDB を用いたファクター計算（Momentum, Value, Volatility, Liquidity）を想定した設計。prices_daily / raw_financials テーブルを参照する方針。

Changed
- n/a（初期リリースのため既存機能の変更なし）。

Fixed
- n/a

Deprecated
- n/a

Security
- n/a

Notes / 実装上の重要点（ドキュメント的注意）
- run_monitoring は監視用テーブルを初期化するため init_monitoring_db を呼ぶが、Monitoring 系は常に Settings.sqlite_path（本番パス）を参照する仕様。運用時の DB パス設定に注意。
- run_execution は paper_trading モード時に paper_sqlite_path を使用して本番 DB と厳密に分離する設計。
- .env パーサ（config._parse_env_line）はシングル/ダブルクォート内でのバックスラッシュエスケープ、export プレフィックス、インラインコメント処理など実用的な仕様をサポート。
- ロギング設定はログディレクトリ作成に失敗しても stdout 出力は必ず行うため、ジョブスケジューラ環境でもログが失われにくい。
- process_priority.set_process_priority / set_cpu_affinity は権限不足や未対応 OS の場合に警告を出して安全にスキップする（サービスの起動失敗を防止）。
- position_sizing の aggregate cap スケーリングは lot_size 単位での切り捨て・残差配分ロジックを持ち、コスト見積りに cost_buffer を使うことで手数料・スリッページ分を保守的に考慮する。

内部
- パッケージバージョンを __version__ = "0.1.0" に設定。

今後の予定（提案）
- factor_research の完全実装（SQL クエリ・DuckDB 集計ロジックの完成）。
- monitoring.monitoring_db / SystemMonitor の詳細実装レビュー（現在は初期化呼び出しやループ制御が組み込まれている）。
- 各 CLI に対するユニットテストの追加、CI での自動検証の整備。
- ポートフォリオ構築ロジックの拡張（銘柄別 lot_size マスタの導入、価格フォールバック戦略）。

---  
（注）この CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のコミット履歴や変更履歴がある場合は、それに基づいて更新してください。