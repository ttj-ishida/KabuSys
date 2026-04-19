CHANGELOG
=========

すべての重要な変更点はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。  

Unreleased
----------
（なし）

0.1.0 - 2026-04-19
------------------

Added
- 基本モジュール群を実装し初版として公開
  - 実行・監視用スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用し、MockBroker を利用して本番 DB と分離して実行可能。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。
  - 設定管理
    - config.py: Settings クラスを追加。環境変数読み込み（.env/.env.local 自動ロード機能）、必須キー取得、各種デフォルトパス（DUCKDB/SQLite/DATAS 等）、env/log level のバリデーションなどを提供。
    - config_setup.py: .env を対話式に作成・更新するウィザードを追加。シークレットマスク表示、選択肢、デフォルト値の扱い、.env のテンプレート書き出しをサポート。
    - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数・KABUSYS_ENV・LOG_LEVEL・DB パス・config/*.yaml の存在とパース（PyYAML があれば）・本番環境向けガード等を検査。--strict オプションで警告を失敗扱いにできる。
  - ロギング / プロセス管理ユーティリティ
    - utils/logging_setup.py: 共通ログ設定ユーティリティを追加。標準出力（stdout）用 StreamHandler と 日次ローテーション（TimedRotatingFileHandler, 30 日保持）をルートロガーに設定。LOG_DIR/LOG_LEVEL の解決とハンドラの再初期化を実装。
    - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定（Windows の priority class / POSIX の nice 値）と CPU affinity 設定ユーティリティを追加。権限不足や未対応 OS でのフォールバック/警告を実装。
  - ポートフォリオ構築用純粋関数群（DB 非依存）
    - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。全スコアが 0 の場合は等配分へフォールバック。
    - portfolio/risk_adjustment.py: セクター集中制限 (apply_sector_cap)、市場レジーム乗数 (calc_regime_multiplier) を実装。unknown セクターの扱い、レジーム別乗数マップ（bull/neutral/bear）を提供。
    - portfolio/position_sizing.py: position sizing ロジックを実装。allocation_method として "risk_based"/"equal"/"score" をサポート。単元株（lot_size）丸め、1 銘柄上限、aggregate cap によるスケーリング、cost_buffer を用いた保守的見積り、分配時の端数補正ロジック等を含む。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（P95）などを算出し PASS/FAIL 判定を行う。--from/--to/--db オプションと PAPER_TRADING_SQLITE_PATH 環境変数をサポート。既定の閾値を定義（例: 稼働率 >= 99%、P95 <= 200 ms 等）。
  - research
    - research/factor_research.py: ファクター計算モジュール（モメンタム/ボラティリティ/流動性/バリュー等）を実装予定の骨子を追加。DuckDB を用いた prices_daily/raw_financials 参照設計（一部実装開始。モメンタム計算のための定数・設計方針を含む）。  

Changed
- （初版リリースのためなし）

Fixed
- （初版リリースのためなし）

Notes / Implementation details
- .env 読み込み
  - プロジェクトルートは .git または pyproject.toml を辿って探索（__file__ ベース）。ルートが見つからない場合は自動ロードをスキップ。
  - .env のパースは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。_load_env_file は OS 環境変数を保護するための protected 引数を提供し、.env.local は上書きモードで読み込み可能。
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用。
- 実行時の挙動
  - run_monitoring: プロセス起動時に set_process_priority("high") を呼び出し優先度を上げる。監視ループは停止フラグ data/stop_requested.flag を監視して正常終了する。例外はループ内で捕捉・ログ出力し次回ポーリングまで待機。
  - run_execution: ExecutionEngine は BrokerClientFactory によりブローカークライアントを生成。paper_trading 環境時は paper_sqlite_path を用いて本番 DB と完全分離して実行する。実行スレッドは停止フラグによる安全停止をサポート。
- ログの取り扱い
  - stdout を StreamHandler に使用（cron 等のリダイレクトを想定）。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
- 互換性と安全ガード
  - Settings.env と LOG_LEVEL の値は許容値チェックを行い、不正値は ValueError を発生させて早期検出。
  - validate_config.py は本番環境（KABUSYS_ENV=live）向けに LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険な設定を警告する。

Security
- （該当なし。シークレット値は .env に格納する設計で、config_setup では .env を絶対にコミットしない旨を出力）

Deprecated / Removed
- （初版のため該当なし）

その他
- パッケージバージョンは src/kabusys/__init__.py にて "0.1.0" を設定。

もし追加で
- 各モジュールの公開 API 要約（関数一覧と引数/戻り値）
- CLI の使い方（具体的な例）
- 将来追加予定の機能や TODO
が必要であれば、その内容に合わせて CHANGELOG に追記できます。どのレベルの詳細を出力しますか？