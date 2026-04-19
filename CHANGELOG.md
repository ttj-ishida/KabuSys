CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に準拠して記載しています。

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-19
--------------------

Added
- 基本アプリケーション初版を追加。
  - パッケージバージョン: __version__ = "0.1.0"
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper 用専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成を導入（モックと本番の切替）。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine をスレッドで実行。停止フラグ検出で安全に終了。
    - RiskManager のデフォルト設定値をコード内で定義（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。initial_portfolio_value を broker.get_available_cash() で取得して初期化。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時にはデフォルトにフォールバックし警告を出力。
    - 停止フラグファイル（data/stop_requested.flag）検出でループ終了。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
- 設定・環境関連
  - config.py
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）。
    - .env/.env.local の読み込み順序と上書きルール（OS 環境変数保護、.env.local が優先等）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - Settings クラスを追加し、各種環境変数アクセスをプロパティ化（J-Quants、kabu API、DB パス、paper_fill_mode のバリデーション等）。
  - config_setup.py
    - .env 作成・更新の対話式ウィザードを追加（秘密項目のマスク、選択肢、既存値の読み込み、保存）。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ有無チェック、config/*.yaml の存在・パースチェック（PyYAML 未インストール時はスキップ）等。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定する setup_logging を提供。
    - LOG_LEVEL / LOG_DIR 環境変数、引数での上書き対応。ログディレクトリ作成失敗時はファイル出力をスキップし警告を出力。
  - utils/process_priority.py
    - set_process_priority(level) で Windows/Linux/macOS の優先度設定を抽象化（psutil 使用）。アクセス拒否や未対応環境では警告を出力してスキップ。
    - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアにピンする機能を提供（エラー時は警告してスキップ）。
- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio/portfolio_builder.py
    - select_candidates(): BUY シグナルのスコア降順ソートと上位選出（同点時は signal_rank でタイブレーク）。
    - calc_equal_weights(), calc_score_weights(): 重み計算。スコア総和が 0 の場合は等金額配分へフォールバックし WARNING を出力。
  - portfolio/risk_adjustment.py
    - apply_sector_cap(): 既存保有のセクター比率に基づき、上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier(): 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を返す。未知レジームは 1.0 にフォールバックして警告。
  - portfolio/position_sizing.py
    - calc_position_sizes(): allocation_method ("risk_based", "equal", "score") に応じた発注株数計算を実装。
    - 単元株（lot_size）で丸め、1銘柄上限（max_position_pct）・投下資金上限（max_utilization）・aggregate cap（available_cash）に基づくスケーリングを実装。cost_buffer による保守的推定にも対応。
    - price 欠損時のスキップやログ出力に配慮。
- データベース / 分析
  - DuckDB 統合（duckdb 接続を必要箇所で使用）。run_execution/run_monitoring は duckdb_path を使用して接続。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite から各種指標（稼働率、注文成功率、送信率、レイテンシ P95 等）を集計してレポート出力。
    - デフォルト閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義し PASS/FAIL を判定。
    - 日付フィルタ（--from/--to）対応。DB ファイルが存在しない場合はエラーメッセージを表示。
    - P95 計算の実装を含む。
- 研究用モジュール（研究／因子算出）
  - research/factor_research.py（ファクター計算基盤を実装。モメンタム等の指標定義を含む。calc_momentum 実装の開始）
    - DuckDB の prices_daily / raw_financials を利用する設計。戻りは (date, code) ベースの dict リストを想定。
    - 一部実装（定数や関数の枠組み）あり。詳細実装は継続中。

Changed
- 既存設計に従い、ログ出力を stdout に統一（cron/Task Scheduler で stdout/stderr をリダイレクトしやすくするため）。
- 環境ファイル読み込みロジックを堅牢化（export 形式、クォート・エスケープ、インラインコメント処理などに対応）。

Fixed
- ポーリングループで MONITOR_POLL_INTERVAL の 0 以下の値により time.sleep が例外を投げる問題に対処。0 以下・不正値はデフォルト（60 秒）にフォールバックして警告。

Security
- .env の取り扱いに関する注意書きを config_setup の生成ファイルに明記（.env を絶対にコミットしない旨）。

Notes / Known issues
- research/factor_research.calc_momentum の実装が途中で終わっているファイル断片が見られます（続きの実装が必要）。
- 一部の TODO（price の欠損時のフォールバック価格利用、lot_size を銘柄別にする等）がコード内に残っています。将来的な拡張ポイントとして残しています。

References
- 実行スクリプト: src/kabusys/run_execution.py, src/kabusys/run_monitoring.py
- 設定管理: src/kabusys/config.py, src/kabusys/config_setup.py, src/kabusys/validate_config.py
- ユーティリティ: src/kabusys/utils/*
- ポートフォリオ関連: src/kabusys/portfolio/*
- ツール: src/kabusys/tools/paper_verification_report.py
- 研究用: src/kabusys/research/factor_research.py

----- 

（この CHANGELOG は提供されたコードベースから機能・振る舞いを推測して作成しています。実際のコミット履歴や意図と差異がある可能性があります。）