Keep a Changelog
=================

すべての注目すべき変更点をわかりやすく記録します。
フォーマットは「Keep a Changelog」に準拠します。

0.1.0 - 2026-04-19
------------------

初回リリース。リポジトリに含まれる主要な機能・ユーティリティ、CLI スクリプト、および実装上の設計意図をコードから推測してまとめています。

Added
- 基本アプリケーション情報
  - パッケージメタ情報: kabusys.__version__ = "0.1.0" を追加。

- 設定管理
  - Settings クラス（src/kabusys/config.py）
    - 環境変数経由で設定を一元取得するラッパー。
    - 自動的にプロジェクトルート（.git または pyproject.toml）を検出して .env / .env.local を読み込む機能（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - J-Quants / kabuステーション / LINE / DB / 監視 / システム関連の設定プロパティを提供。
    - PAPER_FILL_MODE（instant/partial/never/reject）や PAPER_TRADING_SQLITE_PATH、KILL_FLAG_CLEAR_ON_START、閾値類（CPU/MEM/DISK）などを扱う。

  - .env ファイルパーサー
    - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどに対応する堅牢なパーシング実装。

- 環境設定ウィザード CLI（src/kabusys/config_setup.py）
  - 対話式ウィザードで .env を生成 / 更新する機能。
  - デフォルト値や選択肢、シークレット入力の扱いをサポート。
  - 生成ファイルのテンプレート（.env の書式）を出力。

- 設定検証 CLI（src/kabusys/validate_config.py）
  - 起動前に .env と config/*.yaml を検証する CLI。
  - 必須環境変数の未設定／プレースホルダ検出、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、YAML の有無とパース検証（PyYAML がなければ警告）を実施。
  - --strict オプションで警告をエラー扱いにできる。

- 実行系 / 監視系起動スクリプト
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
    - 環境に応じて paper_trading 用 DB を分離して使用（settings.is_paper 判定）。
    - BrokerClientFactory によるブローカークライアント生成（実ブローカ or モックを切替）。
    - OrderRepository、OrderManager、RiskManager（RiskConfig）、Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）検出による安全停止、実行用 PID ファイルを管理。
    - スレッドでエンジンをデーモン実行し、停止フラグまたはスレッド終了を監視してシャットダウン。

  - SystemMonitor（監視）起動スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を設定（デフォルト 60 秒、0 以下は無効扱いしてデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計（監視 DB は環境に依存しない）。
    - stop フラグ検出で監視ループを終了、check_once の例外はログ出力してループ継続。

- ログユーティリティ（src/kabusys/utils/logging_setup.py）
  - setup_logging 関数を提供（全起動スクリプトで共通利用）。
  - stdout 出力（StreamHandler）と日次ローテート（TimedRotatingFileHandler、30 日分保持）をルートロガーへ設定。
  - ログディレクトリ自動作成（失敗時はファイル出力をスキップして stdout のみで継続）。
  - LOG_LEVEL / LOG_DIR の解決順・オーバーライドに対応。

- プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
  - set_process_priority(level) によるクロスプラットフォーム優先度設定（Windows / POSIX を抽象化）。
  - set_cpu_affinity(cpu_count) による最初 N コアへの固定。
  - psutil を利用し、権限不足や未対応環境では警告を出して安全にフォールバック。

- ポートフォリオ構築関連（src/kabusys/portfolio/）
  - portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順ソートと上位選択。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分（全スコア 0 の場合は等配分へフォールバック）。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中度チェックと候補除外ロジック（unknown セクターは除外しない）。
    - calc_regime_multiplier: market regime に応じた投入倍率（bull/neutral/bear）と未知レジーム時のフォールバックと警告。
  - position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算。損切り率・リスク許容率・最大ポジション比率・単元株（lot_size）丸め・手数料等を考慮した aggregate cap（利用可能現金に合わせたスケーリング）を実装。
    - スケールダウン時の端数調整アルゴリズム（lot_size 単位、残差に基づいて追加配分）を採用。

- Paper Trading 検証レポートツール（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から期間集計を行い、以下指標を計算して PASS/FAIL 判定を出力:
    - 稼働率（uptime%）閾値 99%
    - 注文成功率（Filled / Created）閾値 90%
    - 送信率（Sent / Created）閾値 95%
    - P95 レイテンシ閾値 200 ms
  - system_status / trade_logs / risk_logs を参照して統計を集計。P95 は簡易実装（ソートしてインデックス選択）で空データ安全に対応。
  - CLI による期間指定（--from / --to）と DB パス指定（--db）をサポート。

- 研究用ファクター計算基盤（src/kabusys/research/factor_research.py）
  - DuckDB 接続を受け取り prices_daily / raw_financials を参照して Momentum / Value / Volatility / Liquidity 系のファクター計算を行う設計。
  - モメンタム計算の骨子（1M/3M/6M リターン、MA200 乖離率）や ATR/VOL/VOLUME の定数、設計方針コメントを含む（実装は部分的）。

- その他ユーティリティ・細部実装
  - monitoring_db.init_monitoring_db 呼び出しを通じた監視テーブルの冪等初期化（監視・実行双方で保証）。
  - 実行関連での PID ファイル管理、停止フラグ検出（data/stop_requested.flag）による安全停止の共通パターン。

Changed
- （初回リリースのため「追加」が中心。既存機能からの変更点はなし）

Fixed
- （初回リリースのため該当なし）

Notes / Implementation details（コードから推測される重要な挙動）
- 監視プロセスは MONITOR_POLL_INTERVAL によってポーリング間隔を外部から制御可能。0 や負値を与えると無効扱いでデフォルト 60 秒にフォールバックして警告を出す。
- 実行エンジンは paper_trading 環境では MockBroker を用い、paper_trading 用 DB（data/paper_trading.db）へ記録して本番 DB と分離する設計。
- .env の自動読み込みはプロジェクトルートが見つからない場合はスキップされるため、パッケージ化後も環境に依存しない挙動を想定。
- ロギング設定はログディレクトリの作成に失敗してもコンソールログは維持して運用を妨げない堅牢性を重視。
- プロセス優先度 / CPU affinity は psutil による実装で OS によって権限や実装差があるため、失敗時は警告ログに留める設計。
- position_sizing のスケールダウンや lot_size の扱いは実運用を想定した安全弁（上限チェック、残差処理）を備える。

開発者向け補足
- 設定検証ツールは PyYAML がないと YAML のパース検証をスキップするため、CI 等で厳密チェックを行う場合は PyYAML を依存に含めることを推奨します。
- PAPER_FILL_MODE 等の環境変数は厳格な値チェックが入り、不正値は ValueError を投げます（起動時に早期検出される設計）。
- DuckDB / SQLite のパスは Settings から取得するため、環境変数での上書きが可能。ツール類はデフォルトパスを参照するため、運用環境では適切に設定してください。

今後の予定（推測）
- research.factor_research の完全実装（SQL/計算ロジックの完成）。
- strategy / execution の更なるユニット実装（エンジン内部ロジックの充実）。
- テストコード・CI セットアップ（現在コードにはテストが含まれていないように見えるため追加が想定される）。

以上がソースコードから推測した初回リリースの変更点一覧です。必要であれば、各モジュールごとにより詳しい変更点（関数仕様、例外挙動、環境変数一覧など）を追記します。