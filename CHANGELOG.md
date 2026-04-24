CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
（コードベースから推測して作成しています。実際のコミット履歴と異なる場合があります）

Unreleased
----------

- ドキュメント・内部整理
  - 内部ユーティリティや CLI のログ出力・エラーメッセージの改善（詳細は各モジュール内のロギング参照）。
  - テスト・デバッグ用の環境変数制御を容易にするためのオートロード抑止フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）の導入。

0.1.0 - 2026-04-24
------------------

Added
- 基本機能の初期実装（初回リリース相当）。
  - 実行スクリプト
    - run_execution.py
      - ExecutionEngine 起動スクリプトを追加。BrokerClientFactory により実運用/ペーパートレードを切り替え可能。
      - KABUSYS_ENV=paper_trading の場合、専用のペーパートレード用 SQLite（default: data/paper_trading.db）を使用し、本番 DB と分離。
      - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) によるプロセス制御をサポート。
      - スレッドで ExecutionEngine.run_session を実行し、停止フラグ検知で安全に停止。
      - RiskManager のデフォルト構成を設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。initial_portfolio_value を broker.get_available_cash() から取得。
      - DuckDB を分析用接続として併用。
    - run_monitoring.py
      - SystemMonitor をポーリングにより常時監視する起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
      - 監視 DB は環境にかかわらず本番 sqlite_path を使用する設計。
      - 停止フラグ (data/stop_requested.flag) 検知でループを終了。
  - 設定管理
    - config.py
      - .env/.env.local の自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
      - export KEY=val、クォートやエスケープ、インラインコメントに対応する .env パーサを実装。
      - Settings クラスを実装し、各種環境変数（J-Quants、kabuAPI、DuckDB/SQLite パス、ペーパートレード設定、閾値、実行環境判定など）をプロパティとして提供。値検証とデフォルト解決を行う。
      - PAPER_FILL_MODE の検証（instant/partial/never/reject）や KABUSYS_ENV の有効値検査を実装。
  - 設定ユーティリティ・検証
    - config_setup.py
      - 対話式ウィザードで .env を初期作成・更新するツールを追加。シークレット項目はマスク表示、保存前に確認を行う。
      - デフォルト値と選択肢を用意し、ファイル出力はテンプレート形式で行う。
    - validate_config.py
      - 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 値チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML がない場合は警告）を行う。
      - --strict オプションで警告を FAIL 扱いにできる。
  - ログ・プロセス管理ユーティリティ
    - utils/logging_setup.py
      - ルートロガーを統一的に設定する setup_logging を実装。stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30日保持）を設定。既存ハンドラをクリアして二重登録を防止。
      - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - utils/process_priority.py
      - cross-platform なプロセス優先度設定（Windows の priority class / POSIX の nice）と CPU affinity 設定を実装。psutil を使用し、権限不足等のエラー時は警告を出してスキップする。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py
      - 候補選定 select_candidates（スコア降順、タイブレークは signal_rank）と配分重み calc_equal_weights / calc_score_weights（スコア合計が 0 の場合に等分配へフォールバック）を実装。
    - portfolio/risk_adjustment.py
      - apply_sector_cap：既存保有のセクター比率が閾値を超えている場合に当該セクターの新規候補を除外するロジックを実装（unknown セクターは除外対象外）。
      - calc_regime_multiplier：市場レジーム（bull/neutral/bear）に応じた投下資金乗数（1.0/0.7/0.3）を実装。未知レジームは警告を出して 1.0 にフォールバック。
    - portfolio/position_sizing.py
      - calc_position_sizes：allocation_method（risk_based / equal / score）に応じた発注株数決定ロジックを実装。
      - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap によるスケーリング、cost_buffer による保守的コスト見積り、端数の配分（remainders）などをサポート。
  - 分析・調査モジュール
    - research/factor_research.py
      - DuckDB の prices_daily / raw_financials を参照して Momentum / Value / Volatility / Liquidity 等のファクターを計算する基盤を実装（関数シグネチャと定数群を定義、モメンタム計算の骨子あり）。
  - ツール
    - tools/paper_verification_report.py
      - ペーパートレード結果を検証するレポート生成ツールを追加。PAPER_TRADING_SQLITE_PATH または --db で DB を指定。
      - システム安定性（稼働率）、注文成功率（fill/send）、リスク却下、API レイテンシ（平均/最大/P95）を算出し、閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を出力。
      - P95 は簡易実装（ソートして 95 パーセンタイルを選択）。
  - パッケージ情報
    - __init__.py に __version__ = "0.1.0" を追加（初期バージョン）。

Changed
- （初期リリースのため、既存機能の改善点を含む統合的な実装）
  - DB 周りは SQLite と DuckDB を用途に応じて使い分け（監視・履歴は SQLite、分析は DuckDB）。
  - run_monitoring と run_execution はプロセス優先度を起動直後に High に設定するワークフローを採用（権限不足時は警告）。

Fixed
- 各種フォールバック処理と警告を強化
  - 不正な MONITOR_POLL_INTERVAL・PAPER_FILL_MODE 等の環境変数値を検出した場合に警告を出し、既定値へフォールバックする挙動を導入。
  - ログディレクトリ作成失敗やハンドラ作成失敗時に安全にフォールバックしてコンソールログのみで継続するように修正。

Notes / Known limitations
- research/factor_research.py はファクター計算の骨格が含まれていますが、一部実装（データフェッチ範囲の最適化や欠損値処理など）が継続的に必要です。
- position_sizing の一部（lot_size を銘柄別に持たせる等）は将来的な拡張を想定しており、現状は全銘柄共通の単元株数（デフォルト 100）で動作します。
- Process priority / CPU affinity は実行環境の権限に依存します。設定に失敗した場合は警告を出してスキップします。
- .env パーサは多くのケースを扱いますが、極端に複雑な .env の記法（特殊なエスケープや複数行値など）は未対応です。

Contributing
--------------
この CHANGELOG はコードから推測して生成しています。実際の変更履歴と差分がある場合は、正確なコミットログに基づいて修正してください。