# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [0.1.0] - 2026-04-18

初回リリース — 基本的な実行/監視/設定/ポートフォリオ/ユーティリティ群を導入。

### Added
- 全体
  - パッケージ初期バージョンを追加（__version__ = 0.1.0）。
  - DuckDB と SQLite を併用するデータ管理方針を導入（デフォルトパス: data/kabusys.duckdb, data/monitoring.db）。
- 実行コンポーネント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の際に paper_trading 用の専用 SQLite（data/paper_trading.db）を使用する実装。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて実行エンジンをスレッドで起動。
    - 停止フラグ（data/stop_requested.flag）検知処理、PID ファイル出力（data/execution.pid）対応。
    - RiskManager のデフォルトコンフィグを設定（max_position_pct, max_utilization, rate_limit_per_sec 等）。
- 監視コンポーネント
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する挙動。
    - 停止フラグ（data/stop_requested.flag）による安全停止、例外時のロギングを備える。
- 設定周り
  - config.py: 環境変数・設定管理クラスを追加（Settings）。
    - 自動 .env 読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env/.env.local の読み込み順序と保護（OS 環境変数は上書きされない）。
    - 必須変数チェック用の _require()、各種設定プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE 等）。
    - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の値検証を実装（不正時に ValueError を送出）。
  - config_setup.py: .env 初期作成・対話式ウィザードを追加（秘密値入力、デフォルト、選択肢サポート、保存機能）。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数や DB パス、config/*.yaml の存在・パース（PyYAML がない場合はスキップ）を検査。
    - --strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補選定と重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier（bull/neutral/bear を実装、未知レジームはフォールバック）。
  - portfolio/position_sizing.py: 発注株数算出ロジックを実装（risk_based / equal / score の配分方式、単元株（lot_size）丸め、aggregate cap によるスケールダウン、cost_buffer による保守見積り）。
- ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。
    - コンソール (stdout) と日次ローテートファイルハンドラ（TimedRotatingFileHandler、30日保持）をルートロガーに設定。
    - LOG_DIR 作成失敗時はファイル出力をスキップするフォールバックを実装。
    - 引数 / 環境変数 / デフォルトの優先順でログレベル・ディレクトリを解決。
  - utils/process_priority.py: プロセス優先度および CPU affinity 設定ユーティリティを追加（Windows / POSIX を吸収、psutil ベース）。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を提供。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。
    - 稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を算出し、閾値（稼働率 99%、成功率 90% 等）との比較で PASS/FAIL を出力。
    - DB パスは引数 --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。
- 研究用スケルトン
  - research/factor_research.py: ファクター計算モジュールの骨子を追加（モメンタム、MA200、ATR、出来高等の計算方針と定義を含む）。DuckDB を前提に prices_daily / raw_financials を参照する設計。

### Changed
- logging: ログは stdout に出力するよう統一（cron / Task Scheduler のリダイレクトを想定）。
- .env パースの堅牢化:
  - export プレフィックスのサポート、クォート内のバックスラッシュエスケープ対応、インラインコメントの取り扱いなどを実装。
  - .env.local を .env より優先して上書き（ただし OS 環境変数は保護）。
- Execution / Monitoring の起動フロー:
  - 起動直後にプロセス優先度を "high" に設定する処理を導入。
  - 監視は例外発生時でもループ継続して次回ポーリングまで待機する安定化処理を追加。

### Fixed
- .env 読み込み時の例外ハンドリングを改善（読み込み失敗で警告を出し続行）。
- logging_setup: ログディレクトリ作成失敗時にルートロガー未設定のために発生する問題を stdout/stderr に対する明示的メッセージで扱うように修正。

### Security
- .env ファイル生成テンプレートに Git にコミットしない旨の注意書きを明記（config_setup の出力ファイルヘッダ）。

### Notes / Implementation details
- Settings の検証は厳格で、不正な値（例: KABUSYS_ENV の未知値、PAPER_FILL_MODE の無効値、LOG_LEVEL の不正など）は ValueError を投げます。validate_config CLI を使って起動前にチェックすることを推奨します。
- run_monitoring は KABUSYS_ENV に関係なく monitoring 用の sqlite_path（Settings.sqlite_path）を使用します。運用時のデータ分離ポリシーに注意してください。
- run_execution は paper_trading 環境の際に paper_sqlite_path を使用して本番 DB と明確に分離します。
- position_sizing のスケールダウンロジックは lot_size（単元）単位で再配分を試み、残余キャッシュの配分は再現性を保つため安定ソートを使用しています。
- process_priority / set_cpu_affinity は権限やプラットフォームに依存し、設定に失敗した場合は警告ログを出力してスキップします（安全設計）。

もしリリースノートに追記したい変更点（既知の問題、将来追加予定の機能、CI / packaging の情報など）があれば教えてください。必要に応じて Unreleased セクションを追加します。