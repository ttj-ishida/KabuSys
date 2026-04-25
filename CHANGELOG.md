# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
現在のバージョンはパッケージ定義（kabusys.__version__）に合わせて v0.1.0 として初回リリース相当の内容をまとめています（作成日: 2026-04-25、コードベースから推測）。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-04-25

Added
- 基本アーキテクチャ実装
  - パッケージ初期リリース相当のモジュール群を追加。
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。

- 実行スクリプト / デーモン
  - run_execution.py
    - ExecutionEngine の起動スクリプトを実装。
    - プロセス優先度を起動直後に "high" に設定。
    - 環境に応じて paper_trading（モックブローカー）用の SQLite を分離して使用（settings.is_paper を参照）。
    - DuckDB と SQLite の両方に接続。
    - BrokerClientFactory を経由したブローカークライアント生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler 等を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）を監視し安全停止。
    - PID ファイル管理（data/execution.pid）に対応。
    - RiskManager の既定設定（max_position_pct、max_utilization、rate_limit 等）を実装。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に依らず本番用 sqlite_path を使用する設計。
    - 停止フラグ検知でループを終了、KeyboardInterrupt に対するハンドリングあり。

- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートの .env / .env.local を自動読み込み）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションをサポート。
    - .env の行パーサ（クォート／エスケープ／コメント処理）を独自実装。
    - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得:
      - 各種 API トークン、DB パス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）、ログ、閾値（CPU/MEM/DISK）等を取得。
      - env 値（development / paper_trading / live）の検証、paper_fill_mode のバリデーション等。

  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を実装。
    - 初期値、選択肢、シークレット入力の扱い、保存時確認を提供。
    - .env 書式テンプレートを生成（.env を誤ってコミットしない旨の注意書き含む）。

  - validate_config.py
    - 起動前の環境検証 CLI を実装。
    - 必須環境変数のチェック、KABUSYS_ENV の妥当性確認、ログレベルの検査、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および（PyYAML がある場合）パース検証を実施。
    - KABUSYS_ENV=live に対する追加ガード（LINE 設定の未設定警告、KILL_FLAG_CLEAR_ON_START の設定警告等）。
    - --strict モードで警告を失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio パッケージを追加
    - portfolio_builder.py
      - select_candidates: スコア降順でシグナルを選択。
      - calc_equal_weights: 等金額配分。
      - calc_score_weights: スコア正規化配分（全スコアが 0 の場合は等金額にフォールバック）。
    - risk_adjustment.py
      - apply_sector_cap: セクター集中上限を適用して候補を除外。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームは 1.0 でフォールバック。
    - position_sizing.py
      - calc_position_sizes: 重み／候補に基づく株数算出。risk_based, equal, score の allocation_method をサポート。lot_size（単元）で丸め、max_position_pct / max_utilization / cost_buffer を考慮した aggregate cap のスケーリング処理を実装。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定する統一ユーティリティ。
    - 既存ハンドラをクリアして二重設定を防止。LOG_LEVEL / LOG_DIR の解決順を実装。
    - ログディレクトリ作成失敗時のフォールバック（コンソールのみ）に対応。

  - utils/process_priority.py
    - プラットフォーム差を吸収したプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を実装。
    - Windows / POSIX（Linux, Darwin, FreeBSD）に対応。psutil 標準例外（AccessDenied 等）を捕捉して安全にフォールバック。

- 監視 / モニタリング DB 初期化 API
  - monitoring.monitoring_db.init_monitoring_db を呼び出すことで監視用テーブルを冪等に初期化（run_execution/run_monitoring から利用）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計してレポートを出力する CLI を実装。
    - 基準値（稼働率 99% など）に基づく PASS/FAIL 判定ロジックを含む。
    - 日付フィルタ（--from / --to）対応、P95 算出、データが不足する場合の安全ハンドリングあり。

- 研究（リサーチ）モジュール（部分実装）
  - research/factor_research.py
    - ファクター計算（モメンタム等）のための関数群を追加（DuckDB を使った prices_daily/raw_financials 参照想定）。ファイルは途中まで実装が見える（モメンタム計算などの骨格あり）。

Documentation / notes
- .env 取り扱いに関する注意:
  - config_setup が生成する .env を誤って VCS にコミットしないよう明記。
  - Settings._require は必須環境変数がない場合に ValueError を投げるため、validate_config で事前チェックを推奨。
- ログ出力:
  - StreamHandler は stdout を使用（cron 等で stdout/stderr を一本化してリダイレクトする運用を想定）。
- 監視用 DB の扱い:
  - run_monitoring は環境に依らず Settings.sqlite_path（本番監視 DB）を使う設計に注意。
- paper_trading の分離:
  - paper_trading 実行時は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録し、本番 DB とは完全に分離する仕様。

Fixed
- 初回リリースにつき過去のバグ修正は無し（コードベースからの推測による現状の既知挙動を反映）。

Changed
- 初回リリースにつき過去バージョンからの変更は無し。

Deprecated
- 初回リリースにつき該当なし。

Removed
- 初回リリースにつき該当なし。

Security
- 現状、機密情報（API トークン等）は .env 経由で管理する設計。.env を VCS に含めないことを厳守してください。

Known limitations / TODO（コード内コメントを基に推測）
- position_sizing.calc_position_sizes:
  - lot_size を銘柄ごとに持たせる拡張は未実装（将来的な拡張案あり）。
  - price が欠損（0.0）の場合のフォールバック価格ロジックは未実装（risk_adjustment にも同様の注記あり）。
- research/factor_research.py はファクター群の実装骨格があるが、完全な実装の確認が必要（ファイル末端が途中で切れている状態）。
- 一部のモジュール（monitoring.system_monitor、execution.execution_engine 等）はこの変更一覧のファイルから呼び出されているが、ここに含まれる実装や挙動の詳細は別ファイルに依存する。実運用前に統合テストの実施を推奨。

---

注: 本 CHANGELOG は与えられたコードベースの内容から実装・意図を推測して作成しています。実際のコミット履歴や過去のバージョンとの差分がある場合は、該当履歴に合わせて更新してください。