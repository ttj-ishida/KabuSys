# Changelog

すべての変更は Keep a Changelog のフォーマットに従います。  
このファイルは手元のコードベース（初期バージョン）から推測して作成しています。

注意: 日付・文言はコード内の実装に基づく推定です。

## [Unreleased]

## [0.1.0] - 2026-04-17
初回リリース。主要なコンポーネント、CLI、ユーティリティ類、およびポートフォリオ構築 / 検証ツールを導入。

### Added
- 基本パッケージ情報
  - パッケージバージョンを定義（kabusys.__init__.py: `__version__ = "0.1.0"`）。

- 環境設定 / 管理
  - Settings クラスによる環境変数ラッパーを実装（src/kabusys/config.py）。
    - .env の自動読み込み（プロジェクトルートベース、`.env` / `.env.local` の順、OS環境変数を保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env パーサは `export KEY=val`、クォート、エスケープ、インラインコメントをサポート。
    - 各種プロパティ（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視閾値 / 実行環境判定等）を提供。
    - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の値検証を実装。

  - 環境設定ウィザード CLI（src/kabusys/config_setup.py）
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - シークレット項目のマスク表示、選択肢・デフォルト対応、保存確認を実装。

  - 設定検証 CLI（src/kabusys/validate_config.py）
    - .env と config/*.yaml の事前検証ツール。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、YAML のパース（PyYAML があれば内容検証）を実施。
    - --strict オプションで警告を失敗扱いにできる。

- 実行系 & 監視プロセス
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - 起動時にプロセス優先度を "high" に設定。
    - Paper Trading 環境では MockBrokerClient を利用し、paper_trading 用に分離された SQLite（PAPER_TRADING_SQLITE_PATH）を使用（本番 DB と完全分離）。
    - ExecutionEngine の組み立て: BrokerClientFactory、OrderRepository、OrderManager、RiskManager（デフォルト RiskConfig 値を含む）、Reconciler、DuckDB 接続を接続して起動。
    - 停止フラグ（data/stop_requested.flag）検出で安全に停止。PID ファイル管理（data/execution.pid）。

  - 監視起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor の初期化とポーリングループ。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバックして警告）。
    - 監視は環境にかかわらず本番 sqlite_path（settings.sqlite_path）を使用して監視テーブルを初期化。
    - 停止フラグ検出でループ終了、例外時はログ出力して次のポーリングへ。

- 監視 DB 初期化
  - init_monitoring_db を経由して監視テーブルの冪等な初期化を保証（実行・監視両方から呼び出し、SQLite 接続を使用）。

- ポートフォリオ構築（純粋関数群、DB非依存）
  - 候補選定 & 重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順、signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights: スコアが全て 0 の場合は等配分にフォールバックし警告。

  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 現在ポジションに基づきセクター集中上限（max_sector_pct）を超えるセクターの新規候補を除外。unknown セクターは除外対象としない。
    - calc_regime_multiplier: market regime に応じた投下資金乗数を返す（"bull"=1.0、"neutral"=0.7、"bear"=0.3、未知は1.0にフォールバックして警告）。

  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に対応。
    - 単元株（lot_size）丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash）スケーリング、cost_buffer を考慮。
    - スケールダウン後の残余を利用した lot 単位での追加配分ロジックを実装。
    - 価格欠損時はスキップしてログ出力。

  - portfolio パッケージのエクスポートを整備（src/kabusys/portfolio/__init__.py）。

- 研究用ファクター計算（src/kabusys/research/factor_research.py）
  - DuckDB 接続を受け取り、prices_daily / raw_financials を参照して各種ファクターを計算する設計。
  - モメンタム（1M/3M/6M リターン、MA200乖離）、ボラティリティ（ATR20 等）計算の SQL 実装（営業日ベースのウィンドウ管理、データ不足時は None を返す）。
  - 長期ウィンドウのスキャンバッファ等を定義。

- ユーティリティ
  - プロセス優先度と CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）
    - set_process_priority(level): Windows と POSIX を吸収して優先度を設定。権限不足や未対応 OS では警告ログでスキップ。
    - set_cpu_affinity(cpu_count): 最初の N コアにプロセスを固定。引数検証と例外時の警告処理あり。

- 運用・検証ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
    - 指定期間の paper_trading SQLite DB から集計し、稼働率、注文成功率、送信率、P95 レイテンシ等を出力。
    - 合格基準（稼働率 99% 以上、成立率 90% 以上、送信率 95% 以上、P95 レイテンシ <= 200ms）を組み込み、PASS/FAIL 判定を出力。
    - --from / --to / --db オプション対応。DB が存在しない場合のエラーメッセージを出力。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （特記事項なし）

### Notes / Implementation details
- 多くのモジュールは外部依存（psutil、duckdb、PyYAML 等）を使うが、これらが利用できない場合は警告ログを出してフォールバックする設計。
- Paper Trading（KABUSYS_ENV=paper_trading）では本番DBと完全に分離された SQLite を用いることで安全性を確保。
- .env の自動ロードはプロジェクトルートを探索して行うため、配布後の環境でもカレントワーキングディレクトリに依存しない設計。
- run_* スクリプトは stop flag（data/stop_requested.flag）や PID ファイルを用いた運用向け制御を備える。

---

（必要に応じて各ファイルの変更差分や細かい実装ノートを追加できます。）