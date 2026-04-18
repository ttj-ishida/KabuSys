CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" の慣例に準拠します。
Semantic Versioning を採用します。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-18
--------------------

Added
- 基本アーキテクチャとコア機能を新規実装（初期リリース）。
  - パッケージメタ情報:
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - 起動スクリプト:
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプト。
      - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
      - 停止フラグファイル data/stop_requested.flag の検出でループ終了。
      - 監視は KABUSYS_ENV に関係なく本番用 sqlite_path を使用する（設計上の注意）。
    - run_execution.py
      - ExecutionEngine 起動スクリプト。
      - KABUSYS_ENV=paper_trading の場合は専用の Paper Trading SQLite（data/paper_trading.db）を使用して本番 DB と分離。
      - ブローカーの抽象化（BrokerClientFactory）を使用し、ExecutionEngine をスレッドで実行。停止フラグで安全停止。
  - 設定管理:
    - config.py
      - .env 自動読み込み機構（プロジェクトルートを .git / pyproject.toml で探索）。
      - .env / .env.local の読み込み順と OS 環境変数の保護ロジック。
      - export 形式、引用符付き値、インラインコメントなどに対応する堅牢な .env パーサを実装。
      - Settings クラスで各種設定値（パス、閾値、フラグ、API トークン等）をプロパティとして提供。値検証を行う（例: PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL）。
  - 設定支援ツール:
    - config_setup.py
      - 対話式ウィザードで .env を作成/更新する CLI。
      - シークレット値はマスク表示、既存値の再利用、確認プロンプト付きで安全に編集可能。
      - .env に保存する際にコミット禁止の注意コメントを付与。
    - validate_config.py
      - 起動前の設定検証 CLI。
      - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と YAML のパース（PyYAML があれば実行）などを検査。
      - --strict モードで警告を失敗扱い可能。
  - ロギング・プロセス管理ユーティリティ:
    - utils/logging_setup.py
      - ルートロガーを統一的に初期化する関数 setup_logging(app_name, log_dir, level) を提供。
      - stdout 出力用 StreamHandler（stdout を使用）と、日次ローテーションの TimedRotatingFileHandler を設定。既存ハンドラをクリアして二重登録を防止。
      - LOG_DIR / LOG_LEVEL による設定、ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - utils/process_priority.py
      - プラットフォーム差分を吸収したプロセス優先度設定 (set_process_priority) と CPU affinity 設定 (set_cpu_affinity)。
      - Windows / POSIX(nice) の両対応と、権限不足時の安全なフォールバック/警告。
  - ポートフォリオ構築関連モジュール（純粋関数群、DB 非依存）:
    - portfolio/portfolio_builder.py
      - select_candidates: スコア降順 + signal_rank によるタイブレークで候補選定。
      - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重（スコア合計が 0 の場合は等金額配分にフォールバック）。
    - portfolio/risk_adjustment.py
      - apply_sector_cap: セクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外（"unknown" セクターは制限除外）。
      - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear。未知はフォールバック 1.0）。
    - portfolio/position_sizing.py
      - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく発注株数計算。
      - 単元株 (lot_size) による丸め、1 銘柄上限、aggregate cap（available_cash）に対するスケーリング、cost_buffer による保守的見積り、残差処理による追加配分ロジックを実装。
  - リサーチ / ファクター:
    - research/factor_research.py
      - Momentum/Value/Volatility/Liquidity の計算を行うモジュール骨格を実装。DuckDB 接続を受け prices_daily / raw_financials テーブルを参照して計算する設計。
      - （注）ファイル末尾が途中で切れているため、実装は一部未完（モジュールは骨格・定数・関数シグネチャ多数を含む）。
  - ツール:
    - tools/paper_verification_report.py
      - Paper Trading 用 SQLite を解析して検証レポートを生成する CLI。
      - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を計算。
      - デフォルト閾値（例: uptime >= 99%，fill_rate >= 90%，P95 <= 200ms）に基づく PASS/FAIL 判定。
      - --from / --to / --db オプション対応。DB が存在しない場合はエラーメッセージを表示。
  - 監視 DB 初期化:
    - monitoring.monitoring_db.init_monitoring_db を使用して実行前に監視テーブル存在を保証（冪等）。

Changed
- N/A（初回リリースのため "Added" のみ）

Fixed
- N/A

Known issues / Notes
- research/factor_research.py は末尾が途中で切れており、いくつかの実装が未完です（calc_momentum の実装断片で終端）。今後のリリースで完了予定。
- 一部の外部モジュール（例: monitoring_db、SystemMonitor、ExecutionEngine の内部実装、BrokerClientFactory など）は本リリースに参照されているが、本 CHANGELOG で示したファイル群には含まれていない場合があります（別ファイルで実装済みの前提）。
- run_monitoring はコメントにある通り「監視は本番 sqlite_path を使用する」ため、誤って本番 DB を監視/変更してしまわないよう設定に注意してください。
- .env ファイルはセキュリティ上絶対にリポジトリにコミットしないでください（config_setup.py のヘッダにも明記）。

以上。