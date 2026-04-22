# Changelog

すべての変更は「Keep a Changelog」に準拠して記載しています。日付・バージョンはコードベース（現状）から推測して作成しています。

注: 以下はリポジトリ内のコードを読み取り推測した初期リリースの変更履歴です。実際のコミット履歴ではありません。

## [0.1.0] - 2026-04-22

追加 (Added)
- 基本アプリケーション骨格を実装
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 実行用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを実装。プロセス優先度設定、SQLite/DuckDB 接続、Broker クライアント生成、各種コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）の組み立て、スレッド実行と stop フラグ監視をサポート。
    - Paper Trading (KABUSYS_ENV=paper_trading) 時は専用 SQLite（data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）を使用し、本番 DB と分離。
    - 起動時に停止フラグ（data/stop_requested.flag）を検出した場合は起動を中止。
    - PID ファイル管理（data/execution.pid）をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。

- 設定管理
  - config.py: 環境変数 / .env 自動読み込みユーティリティ、Settings クラスを追加。
    - .env 自動ロード: プロジェクトルート（.git または pyproject.toml）を基に .env / .env.local をロード（OS 環境変数を保護）。
    - 複数の設定プロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEMORY/DISK 閾値, KABUSYS_ENV, LOG_LEVEL 等）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - KABUSYS_ENV と LOG_LEVEL の検証とユーティリティプロパティ（is_live/is_paper/is_dev）。

- 設定関連 CLI
  - config_setup.py: .env 初期作成・対話ウィザードを実装。
    - 対話入力・既存 .env 読み込み・シークレット項目のマスク表示・保存機能。
    - デフォルトと選択肢を提示する項目定義を備える（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）。
  - validate_config.py: 起動前設定検証 CLI を実装。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DB パスや config/*.yaml の存在とパース（PyYAML がない場合は警告）、本番環境向けの追加ガード（LINE トークンや KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング・ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - stdout 出力の StreamHandler と日次ローテーション（TimedRotatingFileHandler）によるファイル出力（logs/<app_name>.log）を設定。
    - ログディレクトリ生成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR の解決順を実装。日次バックアップ 30 日保持。

- プロセス優先度・CPU 固定ユーティリティ
  - utils/process_priority.py: set_process_priority / set_cpu_affinity を実装。
    - Windows / POSIX（Linux, Darwin, FreeBSD）差異を吸収し、失敗時は警告を出力してスキップ。
    - set_process_priority("high"|"normal"|"low") を提供。set_cpu_affinity(N) は最初の N コアに固定（N が None の場合は何もしない）。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順・タイブレークに signal_rank を利用して上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等重配分とスコア加重配分（全スコアが 0 の場合は等重へフォールバック、警告出力）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクターごとの既存保有エクスポージャーに基づき新規候補を除外するロジックを実装（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは警告とともに 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算を実装。
      - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）超過時のスケーリングと端数配分アルゴリズムを実装。
      - cost_buffer による保守的コスト見積もりをサポート。
      - risk_based モードではリスク額（risk_pct）と stop_loss_pct を用いて株数を算出。

- 研究 / ファクター計算基盤（実装断片）
  - research/factor_research.py: モメンタム・ボラティリティ等のファクター計算を開始（DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計）。（注: ファイル後半は未完の箇所がある可能性あり）

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを実装。
    - PAPER_TRADING_SQLITE_PATH または --db で DB 指定可能。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を集計し PASS/FAIL を判定する閾値を定義（デフォルト: uptime >= 99%, fill_rate >= 90%, send_rate >= 95%, P95 <= 200 ms）。
    - P95 計算、期間フィルタ、出力フォーマットを実装。

変更 (Changed)
- .env パースの堅牢化
  - config._parse_env_line にてクォート文字の扱い、バックスラッシュエスケープ、コメント判定（クォート無しの '#' の扱い）等を考慮したパーサを実装。export キーワードにも対応。
  - _load_env_file にて既存 OS 環境変数を保護する protected 引数を導入し、.env.local での上書き制御を実現。

- ログ出力のデフォルトを stdout に統一
  - logging_setup で StreamHandler を stdout にセット（cron/Task Scheduler 等でのリダイレクトを想定）。

修正 (Fixed)
- DB 接続・監視周りの堅牢化
  - run_monitoring.py / run_execution.py で init_monitoring_db を呼び出し、監視テーブルが存在することを保証（冪等）。
  - run_execution.py は paper_trading 環境時に専用 DB を使用し、本番 DB と完全分離することで誤発注リスクを低減。

- プロセス優先度・CPU 固定のエラーハンドリング改善
  - psutil による権限不足や未実装 API を捕捉して警告出力しプロセスを継続する挙動に。

既知の問題 (Known issues)
- portfolio/risk_adjustment.apply_sector_cap の価格フォールバック
  - price_map に価格がない場合（0.0）はエクスポージャーが過小見積もられる可能性があり、TODO コメントで前日終値などのフォールバックを検討する旨がある。
- research/factor_research.py はファイル末尾が未完と思われる部分がある（コアロジックの続きが欠落している可能性あり）。
- 一部のファイルは外部依存（psutil, duckdb, PyYAML など）に依存する。PyYAML 未導入時は validate_config の YAML 検査がスキップされる（警告）。

破壊的変更 (Breaking Changes)
- 初回リリースにつき該当なし。

セキュリティ修正 (Security)
- なし（初期実装）。

その他メモ
- デフォルト挙動やパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_DIR: logs/
  - MONITOR_POLL_INTERVAL デフォルト: 60 秒
- 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- validate_config CLI で --strict を使うと警告も失敗扱い（exit 1）になるため、本番デプロイ前のチェックに便利。

今後の改善候補（推奨）
- price フォールバックロジックの追加（前日終値 / 取得原価など） — apply_sector_cap / position_sizing の精度向上。
- research/factor_research の完成・テスト追加。
- 単元株（lot_size）を銘柄別に持てる設計（stocks マスタに lot_size を持たせるなど）。
- 単体テスト・統合テストの整備（特に資金配分・端数配分ロジック、スケールダウンアルゴリズム）。
- ドキュメント（README、運用手順、デプロイ手順）の整備。

----- 

以上。必要であれば、各モジュールごとの詳細な変更箇所（関数一覧・引数説明・想定入力/出力）やリリースノートの英語版・短縮版を生成します。どのレベルの詳細が必要か教えてください。