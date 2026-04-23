# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  
現状の内容はコードベースから推測して作成した初期リリースの変更履歴です。

全般的な注記
- バージョンはパッケージ定義（src/kabusys/__init__.py）の __version__ = "0.1.0" に合わせています。
- 日付はこの CHANGELOG 作成時点（2026-04-23）を使用しています。
- 一部の実装は将来の拡張や既知の制約（例: research モジュールの未完）を注記しています。

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-04-23

### Added
- 基本アプリケーションおよび CLI / ランナー
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。スレッド上で engine.run_session を実行し、data/execution.pid に PID を管理。
    - 停止フラグ（data/stop_requested.flag）を検出して安全に停止する仕組みを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と分離する構成をサポート。
    - BrokerClientFactory を利用してブローカークライアントを組み立て、OrderRepository / OrderManager / RiskManager / Reconciler を統合して ExecutionEngine を構築。
    - RiskConfig のデフォルト値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義し、初期ポートフォリオ値を broker.get_available_cash() で取得して設定。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイントを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - data/stop_requested.flag を検知してループを終了。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視データを本番 DB に集約する設計）。

- 環境・設定管理
  - config.py
    - .env 自動ロード機能を追加（プロジェクトルート検出: .git または pyproject.toml 基準）。.env, .env.local の読み込み順を実装。
    - .env 行パーサーを実装（export プレフィックス対応、クォート/エスケープ処理、インラインコメント処理のルール）。
    - Settings クラスを導入し、環境変数をプロパティとして型付きに取得（DB パス、PID/kill flag、しきい値、env/log_level 判定など）。
    - PAPER_FILL_MODE の入力検証（instant/partial/never/reject のみ許容）や env 値検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）を実装。

  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を行う CLI を追加。
    - シークレット値は表示をマスクし、既存 .env の読み込み / Enter による既存値再利用をサポート。
    - .env を安全なフォーマットで書き出す機能を提供（書き出し時に Git へコミットしない旨の注意を含める）。

  - validate_config.py
    - .env と config/*.yaml の事前チェック CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在とパース検証（PyYAML 未インストール時は警告）を実行。
    - --strict オプションで警告を失敗扱いにできる。exit コードにより CI 等で利用可能。

- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順・タイブレークルール（score 降順、signal_rank 昇順）で上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分、スコア加重配分（全スコアが 0 の場合は等金額にフォールバックして警告）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限（max_sector_pct）を適用し、上限を超えるセクターの新規候補を除外。unknown セクターは除外対象外。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数を定義（bull=1.0, neutral=0.7, bear=0.3）、未知レジームは警告して 1.0 にフォールバック。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づき発注株数を算出。
    - 単元（lot_size）丸め、1銘柄上限（max_position_pct）や aggregate cap（available_cash）超過時のスケーリング、cost_buffer による保守見積り、スケールダウン後の残差配分ロジックを実装。
    - 価格欠損時はスキップする安全措置やログ出力を追加。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング初期化関数を提供。コンソール出力は stdout、日次ローテーション（TimedRotatingFileHandler）を logs/<app_name>.log に保存（30日保持）。
    - LOG_LEVEL, LOG_DIR の優先順位をサポートし、ログディレクトリ作成失敗時にファイル出力をスキップしてコンソールのみで継続するフォールバックを実装。

  - utils/process_priority.py
    - プラットフォーム非依存のプロセス優先度設定（Windows / POSIX 系の差分を吸収）。set_process_priority("high"|"normal"|"low") を提供。
    - set_cpu_affinity(cpu_count) を実装（指定なしはスキップ）。権限不足や未対応 OS では警告して安全にフォールバック。

- ツール類
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加。SQLite（paper_trading.db）からデータを集計して稼働率、注文成功率・送信率、リスク却下数、レイテンシ（avg/max/P95）を出力。
    - デフォルト閾値を設定（稼働率 >= 99%、注文成立率 >= 90%、送信率 >= 95%、P95 <= 200ms）し、PASS/FAIL 判定を出力。
    - CLI オプションで期間指定（--from/--to）と DB パス指定（--db）をサポート。

- research/factor_research.py（ファクター計算フレームワーク開始）
  - DuckDB を用いたファクター計算インターフェースを追加（モメンタム・MA200乖離・ATR・出来高系など設計コメントあり）。
  - calc_momentum 関数のインターフェースと設計（horizon/移動平均等）の骨組みを導入（実装途中を示す箇所あり）。

### Changed
- 監視/実行両ランナーでプロセス優先度を起動直後に High にセットする呼び出しを追加（utils.process_priority.set_process_priority を利用）。
- ログ出力は全スクリプトで setup_logging を呼び出して統一的に行うように変更。

### Fixed
- .env 読み込みの堅牢化
  - export プレフィックス、クォート付き値のエスケープ、インラインコメントの取り扱いなどを細かく処理することで .env のパース精度を向上。
- MONITOR_POLL_INTERVAL の不正値（0 以下や文字列）に対して例外を投げず警告してデフォルトに戻すフォールバックを追加。

### Known issues / Notes
- research/factor_research.py の一部実装が未完（ファイル末尾で途中）。今後ファクター計算ロジックの完成が必要。
- position_sizing の price 欠損時のフォールバック（前日終値や取得原価を使う等）は TODO としてコメントに記載。現在は欠損銘柄をスキップする挙動。
- 一部機能は環境（psutil の権限、ログディレクトリ書き込み権限、PyYAML の有無）に依存するため、起動環境の権限・依存ライブラリの整備を推奨。

### Breaking Changes
- なし（初期リリースのため後方互換に関する注意事項はなし）。

---

参考: 主なファイル・機能
- エントリポイント: src/kabusys/run_execution.py, src/kabusys/run_monitoring.py
- 設定: src/kabusys/config.py, src/kabusys/config_setup.py, src/kabusys/validate_config.py
- ポートフォリオ: src/kabusys/portfolio/*
- ユーティリティ: src/kabusys/utils/logging_setup.py, src/kabusys/utils/process_priority.py
- ツール: src/kabusys/tools/paper_verification_report.py
- パッケージバージョン: src/kabusys/__init__.py (__version__ = "0.1.0")

（必要であれば、各変更点をさらに詳細に分解したコミット単位の想定ログも作成します。）