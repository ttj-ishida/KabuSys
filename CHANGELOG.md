# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルは、現在のコードベースから推測できる機能追加・改善点・修正点をまとめたものです（変更履歴の推定）。実際のコミット履歴ではありません。

## [0.1.0] - YYYY-MM-DD
初回リリース（推定）。主要な機能群とユーティリティを実装。

### 追加
- 基本パッケージとバージョン情報を追加
  - kabusys.__version__ = "0.1.0"

- 設定・環境変数管理
  - kabusys.config.Settings クラスを実装。J-Quants / kabu API / LINE / DB /監視・システム設定などをプロパティ経由で取得。
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - 読み込み優先順位を OS 環境 > .env.local > .env に設定。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサを強化（export プレフィックス、シングル/ダブルクォートサポート、インラインコメント処理、空行/コメント行無視）。
  - 必須環境変数未設定時に ValueError を投げる _require() を実装。

- 設定ツール（CLI）
  - kabusys.config_setup: 対話式ウィザードで .env を生成・更新する CLI を追加。
    - 各設定項目の説明表示、既存値の再利用、シークレットマスク、選択肢サポート、保存確認などを実装。
    - .env の書式でファイル保存（Git へのコミット禁止コメントを含むテンプレート）。

- 設定検証（CLI）
  - kabusys.validate_config: .env および config/*.yaml の検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、YAML ファイルの存在とパース検証（PyYAML 利用可時）。
    - KABUSYS_ENV=live に対する追加ガード（LINE 設定未設定や KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告を FAIL 扱いにできる。

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用（settings.paper_sqlite_path）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動と停止（stop flag/ PID ファイルの扱い）を実装。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を組み込み、初期ポートフォリオ値を broker.get_available_cash() から取得。

  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視 DB は環境に関わらず本番 sqlite_path を使用する旨の挙動。
    - stop_requested.flag による安全な停止検出と終了処理。
    - check_once() 内の例外を捕捉してループ継続する耐障害性を実装。

- ロギング / ログ管理ユーティリティ
  - kabusys.utils.logging_setup.setup_logging を実装。
    - stdout へ StreamHandler を出力（cron 等からのリダイレクトを考慮して stderr でなく stdout を使用）。
    - 日次ローテーションの TimedRotatingFileHandler を追加（デフォルト logs/<app_name>.log、30 日分保持）。
    - LOG_LEVEL / LOG_DIR 環境変数と引数による上書き対応。
    - ログディレクトリ作成失敗時にはファイルハンドラをスキップしコンソール出力だけで継続するフォールバック。

- プロセス優先度 / CPU affinity ユーティリティ
  - kabusys.utils.process_priority.set_process_priority / set_cpu_affinity を実装。
    - Windows / POSIX (Linux, Darwin, FreeBSD) を吸収し、psutil を用いて nice 値や HIGH_PRIORITY_CLASS を設定。
    - アクセス権限不足や未サポートの環境では警告を出してスキップする堅牢性。
    - 有効レベル: "high", "normal", "low"。

- ポートフォリオ構築関連（純関数群）
  - kabusys.portfolio.portfolio_builder
    - select_candidates: スコア降順 + signal_rank によるタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等ウェイト・スコア加重配分（スコア全てが 0 の場合は等分配へフォールバック）。

  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: 同一セクターの既存保有比率が上限を超える場合に当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。売却予定銘柄を除外してエクスポージャー算出。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数（未知レジームは 1.0 にフォールバック）。

  - kabusys.portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based"/"equal"/"score") に基づく発注株数計算を実装。
      - 単元株丸め（lot_size）、1 銘柄上限、aggregate cap（available_cash）でスケールダウン、cost_buffer を考慮した保守見積り、残余キャッシュを用いた端数配分ロジックを実装。
      - risk_based: risk_pct / stop_loss_pct ベースで株数を決定し最大上限を適用。

- Paper Trading 関連ツール
  - kabusys.tools.paper_verification_report を追加。
    - PAPER_TRADING_SQLITE_PATH または --db で指定した paper_trading DB を集計し、稼働率・注文成功率・送信率・リスク却下数・API レイテンシ（avg/max/P95）を算出してレポート出力。
    - Pass/Fail のしきい値を定義（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）。
    - P95 計算、日付フィルタ（--from / --to）対応、データ欠損時の N/A 対応を実装。

- 研究用モジュール（実装開始）
  - kabusys.research.factor_research にモメンタム等のファクター計算の基礎を追加（DuckDB 経由で prices_daily / raw_financials を参照する設計）。
    - モメンタム / MA200 乖離 / ATR / 出来高系などの計算方針と定数を定義（実装は継続中）。

- DB 接続・分析
  - run 系スクリプトで sqlite3 と DuckDB を併用して接続（duckdb.connect を利用）。

### 変更
- なし（初回リリースのため特定の変更履歴なし。コード内には多くのフォールバック・検証ロジックが含まれるため、将来のリリースで変更履歴が発生する想定）。

### 修正 / 安定化
- 環境変数値の検証とフォールバックを改善
  - MONITOR_POLL_INTERVAL: 不正値や 0/負値の場合は警告を出してデフォルト（60 秒）にフォールバック。
  - PAPER_FILL_MODE: 有効値チェックを行い、不正値なら ValueError を送出して早期検出。
  - LOG_LEVEL / KABUSYS_ENV の不正値時に明確なエラー/警告を発生させる。
- ログ設定: ログディレクトリ生成失敗やファイルハンドラ作成失敗を安全に処理するよう改善。
- process_priority: プラットフォーム差異や権限不足を捕捉して警告とすることで、起動失敗を防止。

### 既知の制約 / 注意点
- .env の自動読み込みはプロジェクトルートが特定できない場合はスキップされる。
- run_monitoring は「監視 DB は環境にかかわらず本番 sqlite_path を使用する」挙動があるため、環境分離が必要な場合は運用上の注意が必要。
- position_sizing の lot_size は全銘柄共通を前提としており、将来的に銘柄別単元対応が予定されている（TODO コメントあり）。
- factor_research モジュールは設計方針が整備されているが、完全実装には追加の SQL/ロジックが必要（ファイル末尾が途中で切れていることから実装継続中と推定）。

### セキュリティ
- なし（特に示唆されるセキュリティ修正はコードからは読み取れず）。

---

注:
- 本 CHANGELOG は提供されたソースコードの内容から機能や仕様を推測して作成したものです。実際のコミット履歴や変更差分が存在する場合は、本ファイルを基に実際の履歴を補完・修正してください。