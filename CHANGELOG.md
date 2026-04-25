# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

フォーマットの変更履歴は次の優先順位で記載されています: Added, Changed, Fixed, Deprecated, Removed, Security。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-25
初回リリース。

### Added
- 基本アプリケーション情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 起動 / 実行用スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト配下の `data/stop_requested.flag` ファイルの存在で制御。
    - Monitoring は環境（KABUSYS_ENV）に関係なく本番用の sqlite_path を使用する旨を明記。
    - DuckDB 接続との併用、監視 DB 初期化処理を実行。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は専用（分離された）SQLite（デフォルト: data/paper_trading.db）を使用。
    - Broker クライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、エンジンのスレッド実行・停止制御を実装。
    - 起動時に `data/stop_requested.flag` が存在する場合は起動しない。

- 設定・環境変数管理
  - config.py
    - .env 自動読み込み機能（プロジェクトルート検出ロジック: .git または pyproject.toml を探索）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動読み込みを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - .env のパース実装を提供（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理対応）。
    - Settings クラスで各種設定（J-Quants / kabu API / LINE / DB パス / 監視しきい値 / 環境種別判定等）をプロパティとして定義。
    - Paper Trading 向け設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）をサポート。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - 入力の既存値読み取り、シークレットマスク表示、選択肢チェック、保存確認を実装。
    - .env 書き込みテンプレートを提供（Git に .env を含めないよう注意書きあり）。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在および（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や Kill Flag の自動クリア設定を警告）などを実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一ロギング設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテートする TimedRotatingFileHandler（デフォルト logs/、30 日保持）をルートロガーに設定。既存ハンドラの二重設定を防止。
    - ログレベル・ログディレクトリの解決ルール（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - プロセス優先度設定ユーティリティを追加（Windows / POSIX の差分吸収）。
    - set_process_priority(level: "high"|"normal"|"low") を提供（Windows の priority class / POSIX の nice を使用）。
    - set_cpu_affinity(cpu_count) で CPU affinity 固定の補助関数を提供（psutil に依存。権限不足などは警告でスキップ）。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - BUY シグナルから候補選定（select_candidates）を追加（スコア降順、同点は signal_rank 小さい方優先）。
    - 等金額配分 calc_equal_weights、スコア加重 calc_score_weights（スコア全0 の場合は等分にフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を追加（既存ポジションのセクター比率が上限を超える場合、新規候補を除外。unknown セクターは除外対象外）。
    - レジームに応じた投入資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をマッピング、未知レジームは警告の上 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - ポジションサイズ計算 calc_position_sizes を追加。以下をサポート:
      - allocation_method: "risk_based" / "equal" / "score"
      - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）適用
      - aggregate cap（available_cash）を超える場合のスケーリングと残差配分（lot 単位）
      - cost_buffer（スリッページ・手数料見積り）考慮
      - price 欠損時のスキップ、ログ出力による通知
    - 汎用的でテストしやすい純粋関数実装（副作用なし）。

- 研究・ファクター計算（骨子）
  - research/factor_research.py（モメンタムなどファクター計算の骨組み）
    - DuckDB 接続を受け取り、prices_daily / raw_financials テーブルからファクターを計算する設計。
    - モメンタム（1M/3M/6M）、MA200 乖離、ATR、出来高指標等を想定した定数と計算方針を定義。
    - （ファイル末尾で関数定義が途中で切れているが、設計としてファクター計算機能を導入）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）を集計し、以下の指標をレポート出力:
      - システム稼働率（uptime）、エラー数、総ポーリング数
      - 注文成功率（Filled / Created）、送信率（Sent / Created）
      - リスク却下数（risk_logs）
      - レイテンシ（avg, max, P95）
    - P95 計算、日時フィルタ（--from/--to）、閾値による PASS/FAIL 判定を実装。
    - DB が存在しない場合のエラーメッセージとパス解決ロジック（--db / 環境変数 / デフォルト）を実装。

- DB 関連
  - run_* スクリプトやツール類で sqlite3 と DuckDB を併用する実装を追加。監視テーブル初期化用の init_monitoring_db 呼び出しを各所で行い、監視テーブルの冪等初期化を保証。

### Changed
- （初回リリースのため履歴なし）

### Fixed
- （初回リリースのため履歴なし）

### Deprecated
- （なし）

### Removed
- （なし）

### Security
- （なし）

---

注記:
- .env の自動読み込みはプロジェクトルートが特定できない場合はスキップされます（配布後も CWD に依存しない仕組み）。
- 実行スクリプトは stop/kill フラグファイルを用いた外部制御（ファイルによる停止）を採用しており、運用時の安全停止を想定しています。
- process_priority や cpu_affinity の設定は権限や OS の差異により失敗する可能性があり、その場合は警告ログを出してスキップします。

もしリリースノートに付け加えてほしい観点（既知の制限、手順、互換性情報など）があればお知らせください。