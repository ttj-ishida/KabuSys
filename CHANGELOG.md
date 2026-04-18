# Changelog

すべての notable な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

現在のバージョン: 0.1.0（初期リリース）

[Unreleased]

## [0.1.0] - 2026-04-18

### Added
- 初期実装を追加。
  - 起動スクリプト
    - src/kabusys/run_execution.py
      - ExecutionEngine を起動するエントリポイント。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（data/paper_trading.db、環境変数で上書き可）を使用することで本番 DB と分離。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行い、別スレッドでエンジンを実行。停止フラグ（data/stop_requested.flag）検知で安全に停止。
      - 起動時にプロセス優先度を "high" に設定し PID ファイルを扱う。
    - src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプト。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告してデフォルトにフォールバック。
      - Monitoring は環境にかかわらず本番の sqlite_path を使用（監視データは一貫して本番 DB に記録）。
      - 停止フラグ検知、例外発生時のログ出力、リソースクリーンアップ（DB 接続のクローズ）を実装。

  - 設定関連
    - src/kabusys/config.py
      - Settings クラスで各種環境変数をプロパティとして提供（J-Quants / kabu API / DB パス / 監視しきい値など）。
      - プロジェクトルート検出（.git または pyproject.toml）に基づく .env 自動ロード機能を実装（.env / .env.local の読み込み順、OS 環境変数保護、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。
      - .env のパースは export プレフィックス、クォート、エスケープ、インラインコメント等に対応。
      - PAPER_FILL_MODE 等のバリデーション（有効値チェック）やパスの expanduser を標準化。
    - src/kabusys/config_setup.py
      - 対話式の .env 作成ウィザード。既存値の読み込み、シークレットマスク表示、保存前の確認、.env の安全なテンプレート出力をサポート。
    - src/kabusys/validate_config.py
      - 起動前の設定検証 CLI。必須環境変数の確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスや config/*.yaml の存在・パース検査、KABUSYS_ENV=live 時の追加ガードなど。
      - --strict オプションで警告も失敗（exit 1）扱いにできる。

  - ポートフォリオ構築関連（純粋関数群）
    - src/kabusys/portfolio/portfolio_builder.py
      - select_candidates: BUY シグナルをスコア降順で上位 N を選定。
      - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分。全スコアが 0 の場合は等分配にフォールバックし警告を出力。
    - src/kabusys/portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中上限チェック（既存ポジションの時価でセクター別エクスポージャーを算出し上限超過セクターの新規候補を除外）。"unknown" セクターは上限適用除外。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear のマッピング、未知レジームは 1.0 でフォールバック）。
    - src/kabusys/portfolio/position_sizing.py
      - calc_position_sizes: allocation_method に応じた注文株数決定（risk_based / equal / score）。損切り率・リスク許容率に基づく算出、単元（lot_size）丸め、1 銘柄上限・総投下上限（available_cash）に対するスケーリング、スケールダウン後の端数配分ロジック（再現性を考慮）を実装。cost_buffer により手数料/スリッページを保守的に見積もる。

  - ロギング・プロセスユーティリティ
    - src/kabusys/utils/logging_setup.py
      - ルートロガーに対して StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定するユーティリティ関数 setup_logging を提供。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続するフォールバックを実装。
      - stdout を使うことでスケジューラ起動時のリダイレクト運用を想定。
    - src/kabusys/utils/process_priority.py
      - psutil を用いたクロスプラットフォームのプロセス優先度設定（Windows と POSIX を吸収）。nice 値および Windows 優先度クラスのフォールバック取得、権限不足等の例外を捕捉して警告にフォールバック。
      - set_cpu_affinity で CPU コアのピン留め（利用可能コア数チェック、権限不足時は警告）。

  - モニタリング DB 初期化
    - src/kabusys/monitoring/monitoring_db.py（参照インポートあり）
      - 起動時に監視用テーブルが存在することを保証する init_monitoring_db を利用することで冪等にテーブルを作成。

  - ツール
    - src/kabusys/tools/paper_verification_report.py
      - ペーパートレード用 SQLite のデータから検証レポートを生成する CLI。稼働率（uptime）、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL を判定する閾値を定義。P95 の算出、日付フィルタ、DB 存在チェック、欠損テーブルへの耐性を実装。

  - パッケージ情報
    - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

### Changed
- 初回リリースのため変更履歴は該当なし（初期実装）。

### Fixed
- 設定パーサーの堅牢化（src/kabusys/config.py）
  - export プレフィックス対応、シングル/ダブルクォート内でのバックスラッシュエスケープ、インラインコメント処理、コメントの判定ルール等を実装。これにより .env の多様な記法に対して安全に値を読み込めるようになった。
- 環境変数のフォールバック・検証強化
  - MONITOR_POLL_INTERVAL の不正値は警告してデフォルトにフォールバックする実装を追加（run_monitoring）。
  - PAPER_FILL_MODE 等の列挙値チェックで不正な値は ValueError を投げるようにして早期検出。
- ロギング初期化処理の二重登録防止（既存ハンドラをクリアしてから再設定）。

### Security
- .env の扱いに関する注意を config_setup の出力ヘッダに明記（.env を絶対に Git にコミットしない旨）。
- validate_config により本番環境（KABUSYS_ENV=live）時の必須通知設定（LINE 等）や Kill Switch の設定確認を行うガードを追加。

### Notes
- デフォルトの DB / ログパス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視): data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - ログディレクトリ: logs/
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われ、テストや特殊ケースでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- run_monitoring は「監視データは本番 DB に常に書き込む」設計になっています。paper_trading と監視を完全に独立させたい場合は運用上の注意が必要です。

---

今後のリリースではマイナー修正、テスト追加、Strategy/Execution の詳細実装、ドキュメント強化等を予定しています。