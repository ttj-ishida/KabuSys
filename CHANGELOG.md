# Changelog

すべての重要な変更は Keep a Changelog の形式で記載しています。  
タグ付けは Semantic Versioning に従います。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

Added
- 初回リリース（パッケージバージョン: 0.1.0）。
- 全体
  - パッケージ公開: kabusys（日本株自動売買システム）の基本モジュール群を追加。
  - DuckDB / SQLite を用いた分析・監視用のデータ層を採用。デフォルトパスは data/kabusys.duckdb / data/monitoring.db。
- 実行用スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV に応じて paper_trading 用 DB を分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory を用いて本番/モックブローカーを選択。
    - 実行時にプロセス優先度を "high" に設定。
    - 実行中の PID を data/execution.pid に保存する想定（pid_file パス）。
    - 停止フラグ (data/stop_requested.flag) の検出による安全な停止処理を実装。
    - ExecutionEngine 組立時のデフォルト RiskConfig 値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker_* 等）を設定。initial_portfolio_value は broker.get_available_cash() を参照して初期化。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし、警告を出力。
    - 監視は環境に関わらず本番用 sqlite_path を使用（monitoring の DB は常に同一の監視 DB を参照する設計）。
    - 停止フラグ (data/stop_requested.flag) によりループを終了。
    - プロセス優先度を起動直後に "high" に設定。
- 設定管理
  - config.Settings クラスを追加（環境変数経由で設定取得）。
    - J-Quants / kabuステーション / LINE / DB / 監視閾値等のプロパティを提供。
    - KABUSYS_ENV の有効値チェック（development / paper_trading / live）。
    - PAPER_FILL_MODE のバリデーション（instant / partial / never / reject）。
    - paper_sqlite_path / pid_file_path / kill_flag_path 等を Path 型で取得。
  - .env 自動ロード機構を追加（プロジェクトルートを .git または pyproject.toml で探索）。
    - 読み込み優先順: OS 環境 > .env.local > .env。
    - OS 環境変数を保護するため protected セットを導入。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途）。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメント処理などに対応。
- 設定ユーティリティ
  - config_setup: 対話式 .env 作成ウィザードを追加。
    - 複数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START, LINE 関連など）を扱う。
    - 既存 .env の読み込み、シークレットのマスク表示、保存確認、テンプレート形式での書き出し機能を実装。
  - validate_config: 起動前検証 CLI を追加。
    - 必須/任意環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML 利用。未インストール時は警告）。
    - KABUSYS_ENV=live に対する追加ガード（LINE 通知設定の確認、KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告も失敗扱いにできる。
- ロギング / プロセスユーティリティ
  - utils.logging_setup.setup_logging を追加。
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定。
    - ログ出力先の解決: 引数 > 環境変数 LOG_DIR > デフォルト logs/。
    - ログレベル解決: 引数 > 環境変数 LOG_LEVEL > デフォルト INFO。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップし、コンソールのみで継続。
    - StreamHandler は stdout を使用（cron 等でのリダイレクトを想定）。
  - utils.process_priority を追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）間の差分を吸収してプロセス優先度を設定（high/normal/low）。
    - set_cpu_affinity によりプロセスを最初の N コアに固定する機能を提供（権限不足や未対応 OS では警告を出してスキップ）。
    - 権限不足時は警告を出力し安全にフォールバック。
- ポートフォリオ構築（純関数群）
  - portfolio.portfolio_builder: 銘柄選定と重み計算を追加。
    - select_candidates: スコア降順で上位 N を選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額およびスコア加重。全スコアが 0 の場合は等配分にフォールバックして警告を出力。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック。既存保有のセクターエクスポージャーに基づき特定セクターの新規候補を除外。unknown セクターは制限しない。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（デフォルト/未知は 1.0、neutral=0.7、bear=0.3）。未知レジームは警告と共にフォールバック。
  - portfolio.position_sizing:
    - calc_position_sizes: 発注株数決定ロジック（allocation_method: risk_based / equal / score）。
      - risk_based: risk_pct, stop_loss_pct に基づく株数計算。
      - equal/score: weight に基づく配分。
      - 各銘柄の per-position 上限（max_position_pct）や aggregate 上限（available_cash / max_utilization）を考慮。
      - lot_size（単元株）で丸め、cost_buffer を考慮した保守的なコスト見積もりを実装。
      - aggregate cap を超える場合は比例縮小し、残余キャッシュで lot_size 単位の再配分を行う。
- 分析 / リサーチ
  - research.factor_research: ファクター計算モジュールを追加（momentum / value / volatility / liquidity の設計に基づく）。
    - DuckDB 接続を想定し prices_daily / raw_financials テーブルのみを参照する方針。
    - 現状モジュールの冒頭・定数・関数 API を追加（calc_momentum 等、詳細実装の続きあり）。
- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH 環境変数（または --db オプション）で DB を指定可能。
    - 期間指定 --from / --to（YYYY-MM-DD）に対応。
    - 出力指標: 稼働率(uptime), 注文成功率(fill_rate), 送信率(send_rate), P95 レイテンシなど。
    - PASS/FAIL 判定基準（稼働率 99%, 成功率 90%, 送信率 95%, P95 latency <= 200ms）を定義。
    - DB 内のテーブルが存在しない場合は安全に N/A を返す実装。

Changed
- （初回リリースのため変更履歴はなし）

Fixed
- （初回リリースのため修正履歴はなし）

Deprecated
- （該当なし）

Removed
- （該当なし）

Security
- （該当なし）

Notes / 備考
- 多くのモジュールは外部リソース（kabuステーション API、J-Quants、ローカル DB）に依存します。テスト時は環境変数で設定分離（PAPER_TRADING_SQLITE_PATH / KABUSYS_ENV 等）を行ってください。
- .env は機密情報（API トークン・パスワード）を含むため、絶対にリポジトリにコミットしないでください（config_setup のヘッダにも注意書きあり）。
- process_priority / cpu_affinity の呼び出しは権限や OS に依存するため、権限不足時には警告を出して処理を続行します。

--- 
（本 CHANGELOG はコードベースからの推測に基づいて作成されています。実際の変更・日付はリリース管理ポリシーに従って調整してください。）