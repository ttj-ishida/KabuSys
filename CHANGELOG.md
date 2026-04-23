CHANGELOG
=========

フォーマット: Keep a Changelog 準拠（日本語）
リリース日付はコードベースから推測した更新内容に基づき付与しています。

Unreleased
----------

- なし

0.1.0 - 2026-04-23
------------------

Added
- 基本アプリケーション情報
  - パッケージバージョンを __init__.py にて 0.1.0 に設定。

- 実行用エントリスクリプト
  - run_execution.py を追加。
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（data/paper_trading.db など）を使用して本番 DB と分離。
    - BrokerClientFactory により環境に応じたブローカークライアントを生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立ててエンジンを起動。スレッドで実行し、data/stop_requested.flag により安全に停止可能。
    - 実行中の PID を data/execution.pid に保存する設計（pid_file の扱い）。
    - リスク制御のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を導入。

  - run_monitoring.py を追加。
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を参照して監視 DB を初期化（init_monitoring_db）。
    - data/stop_requested.flag によりループを終了。KeyboardInterrupt にも対応。
    - 起動時にプロセス優先度を "high" に設定する呼び出しを行う。

- 設定管理・ウィザード・検証ツール
  - config.py を追加。
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env のパースロジック（コメント、export プレフィックス、引用符・エスケープ処理、インラインコメント処理等）を実装。
    - Settings クラスを提供し、環境変数から各種設定（J-Quants、kabu API、DB パス、監視しきい値、環境判定フラグ等）を安全に取得。
    - PAPER_FILL_MODE のバリデーションや DB パスの Path 型変換、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
  - config_setup.py を追加（対話式ウィザード）。
    - .env の初期作成・更新を対話式にサポート。既存 .env の読み込み、既定値・選択肢・シークレットマスキング表示、確認後に .env を上書き。
    - 出力テンプレートは .env に書き込む形式を定義（Git へコミットしない旨を明記）。
  - validate_config.py を追加（検証 CLI）。
    - .env と config/*.yaml の存在・基本整合性チェックを実行。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ存在確認、YAML のパースチェック（PyYAML が無ければ警告）、本番用ガード（KILL_FLAG_CLEAR_ON_START や LINE 通知設定の確認）などを実装。
    - --strict オプションで警告をエラー扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py を追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定する共通関数 setup_logging() を提供。
    - LOG_LEVEL / LOG_DIR の解決やログディレクトリ作成失敗時のフォールバック（コンソール出力のみ）を考慮。
  - utils/process_priority.py を追加。
    - プラットフォーム差分を吸収する set_process_priority(level)（high/normal/low）と set_cpu_affinity(cpu_count) を実装。Windows/Linux/Unix を考慮し、失敗時は警告でスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全スコア 0 の場合は等金額へフォールバックし WARNING）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクターエクスポージャが max_sector_pct を超える場合に同セクターの新規候補を除外するロジック（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に基づき投下資金の乗数（1.0/0.7/0.3）を返す。未知のレジームは警告を出して 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: weights, candidates, portfolio_value, available_cash, current_positions, open_prices 等を受け取り、allocation_method（"risk_based"/"equal"/"score"）に応じた発注株数を計算。lot_size（単元）丸め、1銘柄上限、aggregate cap（available_cash）によるスケールダウン、cost_buffer を考慮した保守的見積もり、残余配分の再割当アルゴリズムを実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py を追加。
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH または --db 指定）を参照して検証レポートを生成。
    - システム安定性（稼働率: uptime_pct）、注文成功率（Filled / Created）、送信率（Sent / Created）、リスク却下数、API レイテンシ（avg/max/P95）を集計。
    - P95 計算ロジック、日付フィルタ（--from / --to）対応、存在しない DB への対応メッセージを提供。
    - Pass/Fail 基準を定義（稼働率 >= 99%、成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms）と判定ロジックを実装。

- 研究モジュール（骨格）
  - research/factor_research.py を追加（ファクター計算設計と一部実装）。
    - Momentum / Value / Volatility / Liquidity 等の計算を DuckDB の prices_daily, raw_financials テーブルベースで行う設計。
    - calc_momentum のインターフェースが導入（関数は実装途中でファイル末尾が切れているが、設計コメントと定数が含まれる）。

Changed
- 監視・実行の DB 初期化を共通化
  - init_monitoring_db(sqlite_conn) を run_execution と run_monitoring の起動時に呼び出し、監視テーブル存在を冪等に保証。

- ログ出力の一元化
  - 各起動スクリプトで setup_logging(app_name=...) を呼ぶ設計によりログの収集/ローテーションが統一。

Fixed
- （実装上の安全策・フォールバックを多数追加）
  - 無効な環境変数値に対するフォールバック（例: MONITOR_POLL_INTERVAL、PAPER_FILL_MODE、LOG_LEVEL 等）と警告出力を追加。
  - プロセス優先度・CPU affinity 設定に失敗した場合は警告を出して処理を継続するようにした。
  - ログディレクトリ作成失敗時にはファイルハンドラの作成をスキップしてコンソール出力のみで継続。

Notes / 動作上の注意
- .env 自動読み込みはプロジェクトルート検出に依存します（.git または pyproject.toml）。テスト等で自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は監視用 DB（Settings.sqlite_path）を環境にかかわらず使用します。run_execution は paper_trading 環境時に paper_sqlite_path を使用します（本番 DB との完全分離を意図）。
- config_setup で生成される .env は機密情報を含むため Git にコミットしないでください（ヘッダに注意喚起を追加済み）。
- Paper Trading 検証レポートの基準値（稼働率等）は tools/paper_verification_report.py 内で定数化しており、必要に応じて調整してください。

今後対応予定（推奨）
- research/factor_research.calc_momentum 等の未完部分の完成化。
- 銘柄毎の lot_size を取り扱うための拡張（stocks マスタによる個別単元数対応）。
- price の欠損時のフォールバック（前日終値や取得原価など）を position_sizing / apply_sector_cap に導入。
- より詳細な単体テストと CI の導入（設定ファイルパースや .env ウィザードの対話処理のテスト戦略検討）。

--- 
（本 CHANGELOG は、提供されたソースコード内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある場合があります。）