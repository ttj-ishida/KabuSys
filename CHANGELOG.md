# CHANGELOG

すべての重要な変更をここに記録します。  
フォーマットは「Keep a Changelog」準拠です。  

- リリースはセマンティックバージョニングに従います。  
- "Added", "Changed", "Fixed", "Deprecated", "Removed", "Security" のカテゴリを使用します。

## [0.1.0] - 2026-04-17
初回リリース

### Added
- 基本アプリケーションと実行ユーティリティを追加
  - パッケージ全体のバージョンを `kabusys.__version__ = "0.1.0"` として定義。
- 実行 / 監視プロセス用エントリポイントを追加
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV に応じて paper_trading 用の DB を分離して使用（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - data/execution.pid への PID 出力（pid_file パス）。
    - data/stop_requested.flag による停止フラグ監視で安全に停止可能。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔の上書き（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を参照し監視 DB を初期化。
    - 停止フラグ（data/stop_requested.flag）検知、KeyboardInterrupt による終了処理、DB接続のクローズを適切に実施。
    - プロセス優先度を起動時に "high" に設定。

- 設定管理とセットアップ
  - config.py
    - 環境変数を読み込む Settings クラスを追加（J-Quants / kabu API / DB パス / 監視閾値 等）。
    - プロジェクトルートの自動検出（.git または pyproject.toml）に基づく .env の自動読み込み（.env, .env.local、OS 環境変数優先）。
    - .env のパースはクォートやエスケープ、インラインコメントの扱いに対応。
    - 各種プロパティで入力値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
  - config_setup.py
    - 対話式 .env 作成ウィザードを追加。デフォルト値表示、シークレットマスク、保存機能を備える。
  - validate_config.py
    - 起動前設定検証 CLI を追加。
    - 必須環境変数、KABUSYS_ENV の検証、DB パスの親ディレクトリ確認、config/*.yaml の存在確認および YAML パース検証（PyYAML 利用時）、本番環境向け警告等を実施。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て 0 の場合は等金額配分へフォールバックし警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限適用（apply_sector_cap）：既存保有と価格マップからセクター別エクスポージャーを算出し、上限超過セクターの新規候補を除外。
    - レジームに応じた投下資金乗数（calc_regime_multiplier）："bull"/"neutral"/"bear" に対するマッピングと未知レジームのフォールバック。
  - portfolio/position_sizing.py
    - 株数算出ロジック（calc_position_sizes）：risk_based / equal / score の配分方式をサポート、単元株（lot_size）で丸め、per-stock 上限および aggregate cap（available_cash）に合わせたスケーリング、コストバッファ考慮、端数の再配分ロジックを実装。

- リサーチ / ファクター計算
  - research/factor_research.py
    - DuckDB 接続を受けるファクタ計算モジュールを追加（momentum, volatility 等）。
    - prices_daily テーブルを利用してモメンタム（1M/3M/6M、MA200乖離）、ATR、出来高・出来高比率などを計算するための SQL を実装。
    - データ不足時は None を返すよう安全に設計。

- ユーティリティ
  - utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定機能（set_process_priority）と CPU affinity 固定機能（set_cpu_affinity）を追加。
    - psutil を使い、権限不足や未対応 OS を考慮して安全にフォールバック。
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI を追加。
    - 指標: 稼働率 (uptime), 注文成功率 (fill_rate), 送信率 (send_rate), P95 レイテンシ 等を算出／Pass/Fail 判定する。
    - デフォルト DB パスは data/paper_trading.db、コマンドライン引数 --from/--to/--db をサポート。

- DB 関連
  - SQLite（監視用）および DuckDB（分析用）の接続をスクリプトで利用し、監視テーブルの初期化を冪等に行うユーティリティ (monitoring_db.init_monitoring_db を利用)。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数読み込み時に OS 環境変数は既存値として保護される設計（.env.local でも OS の値は上書き不可）。  
- .env を絶対に Git にコミットしないことを README/生成ヘッダで強調（config_setup の書き込みヘッダ）。

### Notes / 実装上の注意
- .env パーサはクォート内のバックスラッシュエスケープをサポートしますが、複雑なマルチラインや特殊なエスケープが必要なケースでは注意が必要です。
- apply_sector_cap はセクターが "unknown" の銘柄に対してはセクター上限を適用せず除外しない実装です（意図的な挙動）。
- calc_position_sizes は lot_size（単元株）で丸めます。将来的に銘柄毎の lot_map に拡張する余地があります（TODO コメントあり）。
- run_execution / run_monitoring は起動時にプロセス優先度を "high" に設定しますが、環境によっては権限不足で設定に失敗する場合があります（警告でフォールバック）。

---

今後の予定（例）
- ExecutionEngine / RiskManager の追加設定可視化、ユニットテスト整備。  
- ファクター群の追加（Value, Liquidity の完全実装）、Zスコア正規化パイプラインの統合。  
- 銘柄毎単元対応、手数料/スリッページの実運用パラメータ化。

もし特定の変更をより詳細に記載したい箇所があれば、どのファイル／機能について追記するか指定してください。