# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。フォーマットは Keep a Changelog に準拠しています。  

なお、本リポジトリの初期バージョンとして 0.1.0 をリリースしています。

## [Unreleased]

- 進行中:
  - research/factor_research.py のモメンタム計算等は実装途中（calc_momentum の実装が途中で終端しています）。今後のリリースで完成予定。

---

## [0.1.0] - 2026-04-11

初回リリース。自動売買システム KabuSys のコアユーティリティ、起動スクリプト、設定管理、ポートフォリオ構築、ツール類を含みます。

### Added

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading 用 SQLite DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を使って実行時に適切なブローカークライアント（Mock を含む）を生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて ExecutionEngine を起動。デーモンスレッドで run_session を実行し、停止フラグ (data/stop_requested.flag) を監視して安全に停止可能。
    - 起動時に pid ファイル (data/execution.pid) を扱う仕組みを導入。
    - RiskManager のデフォルト設定（max_position_pct や max_utilization 等）を設定し、初期ポートフォリオ値をブローカーから取得して設定。

  - run_monitoring.py
    - SystemMonitor をポーリングする監視スクリプトを追加。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正な値や 0 以下はデフォルトにフォールバックして警告を出す。
    - 監視は環境にかかわらず本番の sqlite_path を利用して監視テーブルを更新する（監視データは本番監視 DB に集約）。
    - 停止フラグ (data/stop_requested.flag) を検知してループを終了。check_once() 実行中の例外はログに出力してポーリングを継続する設計。

- 設定管理・CLI
  - config.py
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）を実装。
    - .env 自動読み込み（.env → .env.local の順、OS 環境変数を保護）を実装。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパースを強化（export プレフィックス対応、シングル/ダブルクォート対応、エスケープ処理、インラインコメント処理等）。
    - 設定ラッパー Settings クラスを提供（J-Quants トークン、kabu API、DB パス、paper_trading 用設定、監視閾値、KABUSYS_ENV/LOG_LEVEL の妥当性チェック等）。

  - config_setup.py
    - 対話式 .env 作成ウィザードを追加。既存 .env の読み込みとマスク表示、選択肢・デフォルトのサポート、生成テンプレートによる安全な .env 出力を提供。

  - validate_config.py
    - 起動前に設定不備を検出する検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガード等を実装。
    - --strict オプションで警告を失敗扱い（exit 1）にできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーを統一的に設定するユーティリティを追加。
    - stdout 出力用 StreamHandler と 日次ローテートする TimedRotatingFileHandler を設定。LOG_DIR / app_name に基づくファイル出力、ハンドラの重複防止、ログレベル解決ルールを実装。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。

  - utils/process_priority.py
    - Windows / POSIX の差異を吸収してプロセス優先度を設定する set_process_priority を追加（"high"/"normal"/"low"）。
    - CPU affinity を設定する set_cpu_affinity を追加。
    - psutil を利用し、権限や未サポート環境では警告出力して安全にスキップする。

- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio/portfolio_builder.py
    - シグナルの候補選定（select_candidates）と重み計算（等分配 calc_equal_weights、スコア加重 calc_score_weights）を実装。
    - スコア合計が 0 の場合は等配分にフォールバックし警告。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（既存保有のセクター露出に応じて当日の新規候補を除外）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をマッピングし、未知値はフォールバック）。

  - portfolio/position_sizing.py
    - allocation_method（"risk_based" / "equal" / "score"）に基づいて発注株数を計算する calc_position_sizes を実装。
    - 単元株丸め、1 銘柄上限、aggregate cap に基づくスケーリング、cost_buffer を考慮した保守的見積り、余り配分ロジック（fractional remainder に基づく lot 単位追加）を実装。

  - portfolio パッケージの __init__ で公開 API を整理。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均・最大・P95）を集計し、閾値に基づいて PASS/FAIL 判定を出力。
    - CLI オプション --from / --to / --db をサポート。DB がない場合のエラーメッセージやエラー耐性を実装。

- モジュール初期化
  - パッケージバージョンを src/kabusys/__init__.py に定義: __version__ = "0.1.0"

### Changed

- 監視 DB の取り扱い
  - run_monitoring.py は Monitoring 用の DB 接続で Settings.sqlite_path（本番の sqlite_path）を環境にかかわらず使用する設計。監視データは本番監視 DB に格納されるよう統一。

- .env / 環境変数処理の堅牢化
  - .env の自動読み込み（.env → .env.local）と、クォート・エスケープ・export 形式対応、OS 環境変数の保護（protected）による上書き制御を導入。
  - Settings クラスにおいて PAPER_FILL_MODE 等の入力値検証を導入し、不正な値は明示的にエラーを発生させる。

- ロギング挙動
  - すべての起動スクリプトから setup_logging を呼び出すことでログ設定を統一。Console は stdout を使用（stderr ではない）ため、cron 等で出力の収集が容易。

### Fixed

- .env 読み込み時のエラーを警告として扱うようにし、読み込み失敗時にプロセスを停止させない（warnings.warn）。
- run_monitoring のポーリング間隔に不正な値が設定された場合、安全にデフォルトにフォールバックして警告を出す。

### Security

- .env の生成テンプレートと .env に関する注意書きを config_setup で出力し、.env を誤ってコミットしないように注意喚起を追加。

---

変更点に関して不明点や特定機能の詳細説明（例: RiskConfig の各パラメータの意味、position sizing のスケーリング挙動、paper verification の閾値の調整方法など）が必要であれば、お知らせください。必要に応じて該当モジュール毎の詳細な変更履歴や使用例を追加します。