# Changelog

すべての注目すべき変更を記録します。フォーマットは Keep a Changelog に準拠しています。  

現在のリリースバージョンは src/kabusys/__init__.py の __version__ に合わせて 0.1.0 としています。

## [0.1.0] - 2026-04-24

### 追加 (Added)
- 全体
  - 初期リリース。日本株自動売買システム「KabuSys」のコアユーティリティ・CLI・アルゴリズム群を追加。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor をポーリングする監視ループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視では KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する仕様。
    - 終了制御はプロジェクトの data/stop_requested.flag によるフラグ検知で行う。
    - 起動時にプロセス優先度を "high" に設定。

  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）に記録して本番 DB と分離。
    - ExecutionEngine は Thread で実行、停止フラグ (data/stop_requested.flag) の検知で安全停止。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
    - プロジェクトルート検出（.git または pyproject.toml）に基づいて .env/.env.local を自動読み込み（OS 環境変数は保護）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パースは export プレフィックス対応、クォートやバックスラッシュエスケープ、インラインコメント等に対応。
    - J-Quants / kabuAPI / LINE / DB / 監視閾値 / システム環境（KABUSYS_ENV, LOG_LEVEL）などのプロパティを提供。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH など Paper Trading 関連オプションをサポート。

  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
    - 入力ガイダンス、デフォルト表示、シークレット値マスク、保存確認機能を備える。

  - validate_config.py
    - 起動前に .env と config/*.yaml の基本的な妥当性チェックを行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL チェック、DB パスの親ディレクトリ存在確認、YAML ファイルの存在・パースチェック（PyYAML がある場合）等を実施。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 共通のロギング初期化ユーティリティを追加。
    - stdout StreamHandler と 日次ローテートする TimedRotatingFileHandler（デフォルト logs/）をルートロガーに設定。
    - 環境変数 LOG_LEVEL / LOG_DIR、引数による上書きをサポート。ファイル出力が作成できない場合はコンソールのみで継続。

  - utils/process_priority.py
    - Windows と POSIX(Linux/Mac/FreeBSD) に対応したプロセス優先度設定ユーティリティを追加。
    - set_process_priority(level) で "high"/"normal"/"low" を設定（権限不足など失敗時は警告でスキップ）。
    - set_cpu_affinity(cpu_count) により最初の N コアへのピンニングをサポート（未対応 OS や権限不足は警告でスキップ）。

- ポートフォリオ構築（Portfolio）
  - portfolio/portfolio_builder.py
    - BUY シグナルのソート・候補選定 (select_candidates) を追加。
    - 等金額重み (calc_equal_weights) とスコア加重 (calc_score_weights) を実装。スコア合計がゼロのときは等配分にフォールバックして警告。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を追加（既存保有時価を算出して上限超過セクターの候補排除）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear 対応、未知値は警告の上 1.0 でフォールバック）。

  - portfolio/position_sizing.py
    - ポジションサイズ計算 calc_position_sizes を実装（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - lot_size（単元）考慮、stop_loss からのリスクベース算出、per-position 上限・aggregate cap のスケーリング、cost_buffer（スリッページ・手数料想定）を反映。
    - 現金上限を超える場合のスケールダウンと端数処理（lot 単位での再配分ロジック）を実装。

- リサーチ・ファクター計算（部分実装）
  - research/factor_research.py
    - DuckDB 接続を受けてモメンタム等のファクターを計算するモジュール骨組みを追加（モメンタム計算のための定数・関数設計を含む）。（注: ファイル末尾で calc_momentum の実装が途中で切れているため追加実装が必要な箇所あり）

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード結果検証のためのレポート生成ツールを追加。
    - システム稼働率、注文成功率（Fill Rate）、送信率（Send Rate）、リスク却下数、API レイテンシ（平均/最大/P95）を算出して PASS/FAIL 判定を行う。
    - デフォルト DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。CLI 引数 --from/--to/--db をサポート。
    - 判定閾値（稼働率99%、Fill 90%、Send 95%、P95 レイテンシ 200ms）を定義。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 破壊的変更 (Breaking Changes)
- なし（初回リリース）

### 注意事項 / マイグレーションノート
- .env 自動読み込み
  - 起動時にプロジェクトルートの .env/.env.local が自動読み込みされます。OS の既存環境変数は保護され、.env.local は .env を上書きします。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading と Live の DB 分離
  - run_execution は paper_trading 環境時に専用の SQLite（PAPER_TRADING_SQLITE_PATH）を使い、本番用 SQLite を汚染しないように設計されています。
- ログ
  - デフォルトで logs/ に日次ローテートのログファイルを出力します。環境変数 LOG_DIR で変更可能。ファイル出力に失敗した場合はコンソール出力のみで継続します。
- 実行権限と OS 差異
  - process_priority や CPU affinity の設定は OS/権限に依存します。権限不足や非対応 OS では警告が出てスキップされます。

---

今後の予定（例）
- research/factor_research.calc_momentum の完了と他ファクター実装（Value/Volatility/Liquidity）。
- ExecutionEngine / BrokerClient 周りの統合テスト。
- monitoring の詳細テーブル定義・アラート送信機能の拡張。