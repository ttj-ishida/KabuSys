# Changelog

すべての注目すべき変更点をこのファイルで管理します。  
フォーマットは「Keep a Changelog」準拠です。  

- リリース日付は ISO 8601 形式 (YYYY-MM-DD) を使用しています。
- 重大な変更があれば Breaking Changes を明示してください。

## [Unreleased]

## [0.1.0] - 2026-04-18
初回公開リリース。

### Added
- 全体
  - パッケージ初期版を追加。パッケージメタ情報として `kabusys.__version__ = "0.1.0"` を設定。
  - DuckDB / SQLite を用いたローカルデータ管理を前提にした自動売買システムの基本ユーティリティと CLI を実装。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを実装。
    - KABUSYS_ENV によって paper_trading モードでは専用の SQLite（デフォルト: data/paper_trading.db）を使用する分離を実装。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド実行と停止フラグ（data/stop_requested.flag）監視ロジックを実装。
    - プロセス優先度を初期に "high" に設定する処理を組み込み（utils.process_priority）。
    - PID ファイル管理用の _EXECUTION_PID（data/execution.pid）対応。

  - run_monitoring.py
    - SystemMonitor をポーリング実行するエントリポイントを実装。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視側は KABUSYS_ENV にかかわらず本番の sqlite_path（デフォルト: data/monitoring.db）を使用する仕様。
    - 停止フラグ（data/stop_requested.flag）の検知で安全にループを終了、例外時のログ捕捉と継続処理を実装。

- 設定管理
  - config.py
    - 環境変数・設定を集中管理する Settings クラスを実装。
    - .env/.env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml を探索）。既存 OS 環境変数を保護する override ロジックを実装。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどに対応。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / PID/kill flag / PAPER_FILL_MODE の検証など）。
    - KABUSYS_ENV、LOG_LEVEL 等の検証ロジックを内包。

  - config_setup.py
    - 対話式ウィザードで .env を初期生成・更新する CLI を実装。
    - デフォルト値、選択肢、秘密値マスク表示、既存値の再利用機能、保存確認などを備える。
    - 書き込みテンプレートに注意書き（.env を絶対に Git にコミットしない）を含める。

  - validate_config.py
    - 起動前に .env および config/*.yaml の問題を検出する CLI を実装。
    - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、YAML パース（PyYAML があれば詳細検証）などを実行。
    - --strict オプションで警告も失敗（exit(1)）として扱う。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定する共通セットアップ関数 setup_logging() を実装。
    - ログレベル・ログディレクトリの解決順を明示、既存ハンドラのクリーン再設定を行う。ログディレクトリ作成失敗時はファイル出力をスキップして標準出力のみで継続。
  - utils/process_priority.py
    - psutil を用いて Windows / POSIX（Linux, macOS 等）間の差分を吸収したプロセス優先度設定関数 set_process_priority(level) を実装。
    - CPU affinity を設定する set_cpu_affinity(cpu_count) を実装（アクセス拒否等は警告でスキップ）。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順、タイブレーク）、等比率 calc_equal_weights、スコア加重 calc_score_weights（全スコア=0 の場合はフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有を考慮し、上限超過セクターの候補除外）を実装。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear マッピング）を実装。未知レジームは警告して 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - weight / candidates / price 等から発注株数を算出する calc_position_sizes を実装。
    - risk_based / equal / score の配分方式をサポート、単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り、端数の再配分ロジック等を実装。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - システム稼働率、注文成功率（fill/send）、リスク却下数、API レイテンシ（avg/max/P95）を算出し、Pass/Fail 判定を行う。
    - CLI オプションで期間および DB パスを指定可能。PAPER_TRADING_SQLITE_PATH 環境変数をサポート。
    - P95 計算、欠損値処理、SQL 抽出時の日付フィルタ構築を実装。

- 研究用（分析）コード
  - research/factor_research.py
    - DuckDB 接続を受け取りモメンタム等のファクターを計算するモジュールのスケルトンを追加（モメンタム計算の定義・定数化を実装済み）。（注: ファイルは一部まだ実装途中の箇所あり）

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （該当なし）

---

注意・既知の制限 / TODO:
- research/factor_research.py はモメンタム計算の実装が途中で終了している箇所があり、今後の実装完了が必要です。
- position_sizing の価格欠損時のフォールバック（前日終値や取得原価等）は TODO コメントで示されており、将来的に改善予定です。
- process_priority / set_cpu_affinity は権限不足やプラットフォーム差異により動作しない場合があり、その場合はログで警告してスキップします。
- .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされます（配布後の環境での挙動に配慮）。

もしリリースノートに追加したい点や既知のバグ・注意事項があれば教えてください。必要に応じて CHANGELOG を更新します。