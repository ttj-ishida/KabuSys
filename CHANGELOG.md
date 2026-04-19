# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」準拠で、セマンティックバージョニングに従います。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-19
初回リリース。自動売買システム「KabuSys」のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、検証ツール群を実装。

### Added
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor 用ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御にプロジェクト直下の data/stop_requested.flag を使用。
    - 監視は環境に関係なく本番用 sqlite_path を使用して初期化（init_monitoring_db を利用）。
    - duckdb 接続を生成して併用。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（data/paper_trading.db または PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル管理を実装。
    - プロセス優先度を起動時に "high" に設定。

- 設定周り
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env/.env.local の読み込み順序を実装（OS 環境変数を保護して上書き制御）。
    - 複雑な .env 行のパースに対応（export プレフィックス、クォート、エスケープ、インラインコメント）。
    - Settings クラスを追加し、環境設定（DB パス、API トークン、ペーパートレード設定、しきい値等）をプロパティとして提供。
    - PAPER_FILL_MODE の検証、有効値チェックを実装。
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
    - 既存 .env の読み込み、シークレットマスク表示、ファイル出力ロジックを実装。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリチェック、config/*.yaml の存在および YAML パース検証（PyYAML が利用可能な場合）を実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、デフォルト 30 日保持）をルートロガーに設定するユーティリティを追加。
    - LOG_LEVEL / LOG_DIR の解決順と、ログディレクトリ作成失敗時のフォールバック（コンソールのみ）を実装。
    - 既存ハンドラをクリアして二重設定を防ぐ。
  - utils/process_priority.py
    - psutil を使ったプロセス優先度設定（Windows / POSIX 向けの差分吸収）を追加。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
    - 権限不足や未対応 OS を考慮した安全なフォールバックと警告出力を実装。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア重み配分（calc_score_weights）を実装。
    - スコアが全て 0 の場合に等金額配分へフォールバックする挙動を定義。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装: 既存保有のセクター暴露を計算し、上限超過セクターの新規候補を除外。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（"bull"=1.0、"neutral"=0.7、"bear"=0.3、未知はフォールバック）。
  - portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 損切り率・許容リスク率に基づくリスクベースサイズ計算、単元（lot_size）丸め、1 銘柄上限・総額上限（available_cash）によるスケーリング処理を実装。
    - cost_buffer（手数料・スリッページ見積り）を考慮した保守的なコスト計算と、残余キャッシュによる再配分ロジックを実装。

- モニタリング DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を run_monitoring と run_execution の両方で呼び出し、監視テーブルの存在を保証（冪等）。

- 分析・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（Filled / Created）、送信率（Sent / Created）、リスク却下数、API レイテンシ（avg/max/P95）を集計して PASS/FAIL 判定を行う。
    - デフォルト閾値を定義（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）。
    - 日付フィルタ（ISO8601 UTC 範囲）対応、DB 存在チェック、SQL の実行時エラーを受けたときの安全なフォールバックを実装。

- 研究モジュール（部分実装）
  - research/factor_research.py
    - ファクター計算モジュールの骨組みを追加（モメンタム / MA200 / ATR / 出来高等の設計方針を記載）。
    - calc_momentum の実装開始（関数シグネチャ・定数などを定義）。注: ファイル末尾で実装が途切れているため未完成。

- パッケージ化
  - __init__.py にてバージョンを 0.1.0 に設定し、主要サブパッケージ（data, strategy, execution, monitoring）を __all__ に追加。

### Changed
- （初回リリースにつき変更履歴はなし）

### Fixed
- （初回リリースにつき修正履歴はなし）

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

備考:
- いくつかのモジュールは外部依存（psutil, duckdb, PyYAML）に依存します。利用環境に応じてインストールが必要です。
- research/factor_research.py は現状で途中実装の箇所があり、今後のリリースで完成予定です。