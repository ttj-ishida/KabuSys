Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」規約に従って管理されています。

[0.1.0] - 2026-04-19
-------------------

初回リリース（コードベースから推測して作成）。主な追加点と実装の概要を以下に示します。

Added
- 全体
  - 初期ライブラリ構成の追加。パッケージバージョンは src/kabusys/__init__.py にて __version__ = "0.1.0"。
  - 基本的なディレクトリ構成と複数の起動スクリプト、ユーティリティ、ポートフォリオ構築、リサーチ機能を実装。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する実装。
    - 停止フラグ（data/stop_requested.flag）検知で安全終了。プロセス優先度を High に設定。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時には paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離し、MockBrokerClient を利用する想定（BrokerClientFactory に準拠）。
    - 起動前に停止フラグをチェックし、起動中も停止フラグでエンジン停止。PID ファイル管理（data/execution.pid）。
    - プロセス優先度を High に設定し、別スレッドで engine.run_session を実行。

- 設定関連
  - src/kabusys/config.py
    - 環境変数をラップする Settings クラスを提供。
    - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を探索）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
    - .env のパースは export 文、クォート、エスケープ、行末コメントなどに対応する堅牢な実装。
    - 各種プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE など）を提供し、値の妥当性チェック（列挙値チェックや例外スロー）を実装。
    - env/log レベル判定用のユーティリティ（is_live / is_paper / is_dev 等）。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成／更新する CLI を追加。
    - 複数項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 設定等）を対話的に設定可能。シークレット項目は表示をマスク。
    - .env のテンプレート書き出しを実装し、注意文（.env を Git にコミットしない等）を出力。

- 検証ツール
  - validate_config.py
    - .env および config/*.yaml の設定不備を起動前に検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV と LOG_LEVEL の妥当性、DB パス（親ディレクトリの存在）チェック、YAML ファイルの存在・パースチェック（PyYAML が無ければ検証をスキップして警告）。
    - --strict オプションで警告を失敗扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - setup_logging(app_name, log_dir, level) を提供。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。既存ハンドラの二重設定を防止する実装。
    - ログレベル・ログディレクトリの解決順を明示（引数 > 環境変数 > デフォルト）。
    - 標準出力に stdout を使うことで cron 等からのリダイレクト運用を想定。
  - utils/process_priority.py
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。
    - Windows と POSIX の差分吸収（psutil 利用）。権限不足や未対応 OS は警告ログを出してスキップする堅牢さを実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates(buy_signals, max_positions) : スコア降順で候補抽出。
    - calc_equal_weights, calc_score_weights : 等分配とスコア加重（スコア全0 の場合は等分配にフォールバックし警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap : セクター集中上限（max_sector_pct）を考慮して候補をフィルタリング。売却予定銘柄はエクスポージャ計算から除外。unknown セクターは上限適用外。
    - calc_regime_multiplier : レジーム（bull/neutral/bear）に応じた投下資金乗数を返却（未知の値はログ警告後 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes : allocation_method ("risk_based", "equal", "score") をサポートし、各銘柄の発注株数を計算。
    - 単元株（lot_size）での丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）に基づくスケーリング、cost_buffer（手数料・スリッページ見積り）に基づく保守的見積りを実装。
    - スケールダウン時に残差（fractional_remainder）を利用して lot_size 単位で公平に追加配分するロジックを実装。

- 監視 / モニタリング周り
  - run_monitoring および run_execution 内で monitoring_db.init_monitoring_db を呼び出し、監視テーブル等の存在を冪等に保証する処理を組み込み。
  - 停止フラグ / キルスイッチ（KILL_FLAG）・PID ファイルに対応。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を算出。
    - P95 計算ユーティリティ、日付フィルタ（--from / --to）と DB 指定（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）対応。
    - デフォルトのパスは data/paper_trading.db。合格閾値（例: 稼働率 >= 99.0%、P95 <= 200 ms 等）をスクリプト内定義。

- リサーチ
  - research/factor_research.py
    - ファクター計算の骨組み（モメンタム、MA200、ATR 等）の実装開始。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。

Changed
- （初回リリースのため該当なし）

Fixed
- logging_setup: StreamHandler に stdout を使用（cron/Task Scheduler からのリダイレクト運用に配慮）という運用上の改善を反映。

Security
- .env の取り扱いについて：config_setup が .env を生成する際に「.env を絶対に Git にコミットしないこと」を明示するテンプレートを出力。
- Settings._require により必須環境変数未設定時は ValueError を発生させることで起動前に明確に失敗させる挙動を採用。

Notes / Implementation details（コードからの推測）
- run_execution は paper_trading モード時に本番 DB と完全分離した専用 SQLite を使用する（PAPER_TRADING_SQLITE_PATH）。
- process_priority と logging の設定は各起動スクリプトで最初に適用されるため、ログや優先度関連は起動時に統一される設計。
- .env のパースは export 実装、クォート中のバックスラッシュエスケープ、インラインコメント処理等をサポートしており、現場でありがちな .env 書式のばらつきに耐性を持つ。
- portfolio の計算関数群は副作用なしの純関数設計で、単体テストが容易な構成になっている（DB参照なし）。

Acknowledgements
- この CHANGELOG は提供されたソースコードの内容から機能・挙動を推測して作成しています。実際のリリースノートとして使用する場合は、リリース担当者が差分や意図を確認のうえ修正してください。