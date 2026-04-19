# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠し、日本語で記載しています。

フォーマット:
- Unreleased: 今後の変更予定
- 各リリースはバージョンと日付を持ち、Added / Changed / Fixed / Removed / Security などのセクションで差分を記載しています。

なお、以下の履歴は提供されたコードベースの内容から推測して作成したものです。

## [Unreleased]

- 進行中 / 未完成の実装・改善点を列挙しています（コード中の TODO や未完の関数に基づく）。
  - research.factor_research モジュールの実装が途中（ファイル切断により一部関数が未完）。
  - position_sizing: 将来的に銘柄ごとの lot_size を stocks マスタから読み込む拡張予定（TODO コメントあり）。
  - risk_adjustment: price 欠損時のフォールバックロジック（前日終値や取得原価等）の導入検討。
  - ログ出力やプロセス優先度設定でのエラー/権限不足時の挙動・通知強化（現状は警告ログでスキップ）。

---

## [0.1.0] - 2026-04-19

初回リリース。KabuSys 自動売買フレームワークの基礎機能を実装。

### Added
- コア: パッケージ初期バージョンを定義
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 環境・設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を読み込むユーティリティ。
    - 自動ロードの仕組み（プロジェクトルート検出: .git または pyproject.toml）。
    - .env パース機能（export 形式、引用符・エスケープ、インラインコメントの取り扱い対応）。
    - 設定必須チェック用の _require()、Settings クラス（各種環境変数プロパティ）を実装。
    - PAPER_FILL_MODE の妥当性チェック、paper_trading 用 DB パス、監視用しきい値等の設定を提供。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。

- 環境セットアップ / 検証用 CLI
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI。
    - デフォルト値、選択肢、シークレット入力マスク、保存確認を実装。
  - src/kabusys/validate_config.py
    - 起動前の設定検証 CLI。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認。
    - config/*.yaml の存在確認と PyYAML がある場合は YAML パースによる検証を行う（PyYAML 未インストール時は警告）。
    - 本番環境向けの追加ガード（LINE 通知設定確認、KILL_FLAG_CLEAR_ON_START の警告）を実装。
    - --strict フラグで警告を FAIL 扱いにできる。

- 起動スクリプト
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告ログでデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用（監視 DB を共通で利用）。
    - 停止フラグ（data/stop_requested.flag）を検出して安全終了。
    - 起動時にプロセス優先度を High に設定。

  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の専用 SQLite DB（data/paper_trading.db）に記録して本番 DB と分離。
    - 起動時にプロセス優先度を High に設定。
    - 停止フラグ・PID ファイル管理（data/execution.pid）に対応。
    - スレッドでエンジンを実行し、停止フラグ検知で engine.stop() を呼び安全停止。

- Execution / Broker / Risk 系基盤（起動スクリプトから利用）
  - 実行系の依存コンポーネント組み立て（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てとデフォルト設定）。
  - RiskManager のデフォルト構成（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。初期ポートフォリオ値は broker.get_available_cash() を使用。

- 監視 DB 初期化
  - src/kabusys/monitoring/monitoring_db.py へ init_monitoring_db を呼び出して監視テーブルの存在を保証（起動時に冪等に実行）。

- ポートフォリオ構築（純関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 昇順）で上位 N 件選択。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア加重配分（スコア合計が 0 の場合は等分配にフォールバック）。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有比率に基づくセクター集中上限チェック（max_sector_pct）と新規候補除外ロジック。unknown セクターは制限を適用しない。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（"bull":1.0, "neutral":0.7, "bear":0.3）。未知レジームは警告ログで 1.0 にフォールバック。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: 複数の割当方式（risk_based / equal / score）に基づき発注株数を計算。aggregate cap / cost_buffer を考慮してスケーリングと lot_size（単元株）丸めを実装。
    - スケールダウン時の再分配アルゴリズム（残余キャッシュを考慮した lot 単位での追加配分）を実装。

- ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - setup_logging: StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定する共通ユーティリティ。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップし、コンソールのみで継続。
    - ログレベルとログディレクトリの解決順を実装（引数 > 環境変数 > デフォルト）。
  - src/kabusys/utils/process_priority.py
    - set_process_priority: Windows / POSIX を吸収してカレントプロセスの優先度を変更。権限不足等で失敗した場合は警告ログでスキップ。
    - set_cpu_affinity: 指定コア数でプロセスをピン止めする機能（未指定時は no-op）。利用不可環境では警告でスキップ。

- ツール / レポート
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 検証レポート生成スクリプトを実装。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95）を集計。
    - Pass/Fail 基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）による判定を実装。
    - --from / --to / --db オプションで期間・DB を指定可能。DB の存在チェックとエラーハンドリングあり。

- research
  - src/kabusys/research/factor_research.py
    - ファクター計算モジュールの枠組みとモメンタム・ボラティリティ等の計算方針を実装。DuckDB 接続を受け、prices_daily / raw_financials テーブルのみを参照する設計。
    - 設定された窓幅（1M/3M/6M、MA200、ATR20、Volume20 など）の定数を追加。モメンタム計算関数 calc_momentum の骨格が開始されている（ファイル切断により一部未完）。

- エラーハンドリング / 安全停止
  - 停止フラグ（data/stop_requested.flag）検出により起動中プロセスを安全に停止する仕組みを複数スクリプトで実装（monitoring / execution）。
  - SQLite / DuckDB 接続の適切なクローズ処理を実装。

### Changed
- （初回リリースのため、過去の変更履歴はありません。上記はこのバージョンで導入された機能群です。）

### Fixed
- （初回リリースのため、過去のバグ修正履歴はありません。）

### Known issues / Notes
- research.factor_research.py がファイル末尾で切断されており、一部関数（calc_momentum の続きなど）が未完成。
- position_sizing の注記にあるとおり、価格欠損時のフォールバックロジックが未実装（TODO）。欠損 price に対しては現状 0.0 を使い、結果的に銘柄がスキップされる。
- process_priority / set_cpu_affinity は環境や権限に依存し、失敗した場合は警告ログでスキップする設計。
- ログディレクトリ作成失敗時はファイルハンドラが無効化されるが、その旨は stderr / ログでのみ通知される。
- Paper Trading 用 DB と本番監視 DB は意図的に分離しているが、運用時は環境変数設定に注意すること。

---

作成者注:
- 上記は提供されたソースコードのコメント・実装・TODO から推測してまとめた変更履歴です。実際のコミット履歴やリリースノートがある場合は、そちらを優先して反映してください。必要であれば、より詳細なリリースノート（例: 各関数のシグネチャ変更点、公開 API の安定性、マイグレーション手順など）を追加できます。