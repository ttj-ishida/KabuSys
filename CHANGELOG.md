CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
日付はリポジトリ内のコードから推測した初期リリース日を設定しています。

Unreleased
----------

特になし。

[0.1.0] - 2026-04-19
--------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基盤機能を追加。
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - プロセス優先度を "high" に設定して起動。
    - KABUSYS_ENV が paper_trading の場合、Paper Trading 用の専用 SQLite（data/paper_trading.db、環境変数で上書き可）を使用して本番 DB と完全分離する設計。
    - BrokerClientFactory によるブローカークライアント切り替えを実装（実運用/モックの切替を想定）。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立て、ExecutionEngine をスレッドで実行。停止フラグ (data/stop_requested.flag) を検知して安全に停止する処理を実装。
    - PID ファイル管理（data/execution.pid）に対応。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告ログを出力。
    - 停止フラグ (data/stop_requested.flag) を検知してループを終了。
    - 監視処理は環境にかかわらず本番 sqlite_path（data/monitoring.db）を使用する方針。

- 設定・環境管理
  - config.py
    - Settings クラスによる環境変数アクセスを集中管理。
    - .env 自動ロード機構を実装（プロジェクトルートを .git または pyproject.toml を基準に探索）。.env → .env.local の順で読み込み、OS 環境変数は保護（上書き防止）。
    - .env の堅牢なパース実装（export プレフィックス、シングル/ダブルクォート内でのエスケープ処理、インラインコメントの解析等に対応）。
    - 各種設定プロパティ（DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE の検証、KABUSYS_ENV/LOG_LEVEL の妥当性チェック等）を提供。
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。秘密値のマスク表示、選択肢サポート、既存 .env の読み込みと Enter での再利用を提供。
    - .env ファイルテンプレートを出力し、生成時の注意（.env を Git にコミットしない等）を明示。
  - validate_config.py
    - 起動前に .env と config/*.yaml の妥当性を検証する CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 値チェック、DB パス親ディレクトリの存在確認、YAML パース（PyYAML が利用可能な場合）などを行う。
    - --strict オプションで警告を FAIL 扱いにできる。

- ユーティリティ
  - utils/logging_setup.py
    - 共通のログ設定ユーティリティを提供。ルートロガーを初期化し、コンソール（stdout）出力と TimedRotatingFileHandler による日次ローテーション（30日分）を設定。
    - LOG_LEVEL / LOG_DIR の解決優先順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度設定と CPU affinity 設定をサポート。
    - アクセス権限や未対応 OS の場合は警告を出して安全にフォールバック。

- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順でソートして上位を選出（タイブレークに signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を提供。スコア合計が 0 の場合は等金額にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限ロジック。既存ポジションを基にセクター別エクスポージャを計算し、上限超過セクターの候補を除外。"unknown" セクターは制限対象外として扱う。
    - calc_regime_multiplier: 市場レジーム ("bull", "neutral", "bear") に応じた投下資金乗数を返却。未知レジームは警告して 1.0 をフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method("risk_based","equal","score") に基づく株数決定ロジックを実装。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash によるスケールダウン）、cost_buffer（手数料・スリッページ見積り）を考慮したスケーリングと再配分ロジックを搭載。
    - 価格欠損や不正データ時はスキップしてログを残す。

- 監視・モニタリング関連
  - monitoring_db 初期化呼び出し（init_monitoring_db）を run_execution/run_monitoring 起動時に行い、監視テーブルが存在することを保証（冪等）。
  - SystemMonitor の単回チェック check_once をポーリングで定期実行（例外発生時はログに例外を出力して継続）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。SQLite（デフォルト data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計してレポートを標準出力へ出力。
    - 判定基準（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200ms）を定義して PASS/FAIL を表示。
    - 日付範囲指定（--from/--to）と DB パス指定（--db / 環境変数）に対応。
  - research/factor_research.py（ファクター計算基盤）
    - Momentum, Value, Volatility, Liquidity 等のファクター計算方針と定数を定義。DuckDB 接続を受け価格・財務テーブルから計算する設計。モジュール途中まで実装あり（モメンタム計算の骨子）。

Changed
- なし（初期リリースのため追加が中心）。

Fixed
- なし（初版リリース）。

Deprecated
- なし。

Removed
- なし。

Security
- .env ファイルを生成する際に「.env を絶対に Git にコミットしないこと」を明記。自動読み込み時に OS 環境変数を保護する仕組みを実装（protected set）し、.env による既存 OS 環境の上書きを制御。

Notes / その他の設計判断
- .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。プロジェクトルートが特定できない場合は自動ロードをスキップする（パッケージ配布後の CWD 非依存性を考慮）。
- ログは stdout を使う方針（cron/タスクスケジューラで stdout/stderr を一本化してリダイレクトする慣習への配慮）。
- process_priority は権限不足や未対応 OS 時に例外を投げず警告してスキップする安全設計。
- ポートフォリオ／オーダー関連ロジックは純粋関数で実装され、DB 参照を行わないため単体テストを容易にする設計になっている。

今後の改善候補（コードから推測）
- research/factor_research.py の未完了部分（モメンタム計算の実装完了）。
- 単体テストと CI の追加（ロジックは純粋関数中心だがテストが見当たらない）。
- price 欠損時のフォールバック（前日終値やマスタ値）や銘柄別 lot_size のサポート（TODOコメントあり）。
- 実運用向けのより厳密なエラー通知（LINE 通知の活用など）。
- ExecutionEngine / SystemMonitor の詳細なログ・メトリクス収集拡張。

--- 

（この CHANGELOG は提供されたコードの内容から推測して作成しました。実際のコミット履歴とは異なる場合があります。）