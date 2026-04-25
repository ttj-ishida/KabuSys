# Changelog

すべての重要な変更点をこのファイルで管理します。  
フォーマットは「Keep a Changelog」に準拠しています。  

なお、本リリースはソースコードから推測して作成した初期リリースノートです（自動生成／推測に基づくため表現や細部は実際のコミット履歴と差異がある場合があります）。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-25

概要:
初期公開リリース。日本株自動売買システム (KabuSys) のコアユーティリティ、実行/監視スクリプト、設定管理、ポートフォリオ構築ロジック、各種ツール類を追加。

### Added
- パッケージの基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として導入。

- 実行・監視エントリポイント
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、Paper 用 SQLite（デフォルト: `data/paper_trading.db`）に完全に分離して記録する動作をサポート。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止用フラグファイル (`data/stop_requested.flag`) と実行 PID ファイル (`data/execution.pid`) の取り扱いを実装。
    - スレッドで ExecutionEngine をデーモン実行し、停止フラグ検知で安全に停止するロジックを実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告ログを出力。
    - 監視は環境にかかわらず本番用の sqlite_path（`Settings.sqlite_path`）を使用する設計。
    - 停止フラグ検出でループを終了し、KeyboardInterrupt による終了をログ出力してクリーンに DB をクローズ。

- 設定管理・ウィザード・検証
  - config.py
    - プロジェクトルート自動検出（.git または pyproject.toml）を導入し、.env / .env.local の自動読み込みを実装（OS 環境変数の保護あり）。
    - 値のパースロジックを強化（export プレフィックス対応、シングル/ダブルクォートとエスケープ、インラインコメントの取り扱いなど）。
    - 多数の設定プロパティを `Settings` クラスとして公開（DB パス、KABUSYS_ENV、ログレベル、Paper モード設定、監視閾値、PID/KILL フラグパス等）。
    - Paper Trading 用の挙動制御（`paper_sqlite_path`, `paper_fill_mode`）を追加。
  - config_setup.py
    - 対話式 .env 作成／更新ウィザードを追加。主要設定項目（環境、API トークン、DB パス、ログレベル、Kill フラグ設定など）に対応。既存 .env の読み込みとマスク表示を行う。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。必須環境変数・KABUSYS_ENV の妥当性・ログレベル・DB パスの親ディレクトリ存在確認、config/*.yaml の存在／パースチェック（PyYAML 利用）などを実施。`--strict` オプションで警告をエラー扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに一貫したログ設定を提供するユーティリティを追加。
    - stdout 出力（StreamHandler）および日次ローテーション（TimedRotatingFileHandler）を組み合わせて設定。ログディレクトリの自動作成、ファイルハンドラのフォールバック処理を実装。
    - ログレベル・ログディレクトリ解決順を仕様化（引数／環境変数／デフォルト）。
  - utils/process_priority.py
    - Windows と POSIX（Linux / macOS 等）を吸収するプロセス優先度設定 API を追加（high/normal/low）。
    - CPU affinity 設定用の `set_cpu_affinity` を追加。
    - 権限不足や未対応プラットフォーム時は警告ログを出してフォールバック。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルの候補選定（スコア降順、タイブレークは signal_rank）`select_candidates`。
    - 等金額配分 `calc_equal_weights`、スコア加重配分 `calc_score_weights`（スコアが全て 0 の場合は等金額にフォールバック）を追加。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する `apply_sector_cap`（既存保有のセクター比率に応じて当日の候補から除外）。
    - 市場レジームに応じた投下資金乗数を返す `calc_regime_multiplier`（bull/neutral/bear のマッピングと未知レジームのフォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数決定ロジック `calc_position_sizes` を追加（risk_based / equal / score の allocation_method に対応）。
    - 単元株丸め、1銘柄上限、aggregate cap（利用可能現金を超える場合のスケールダウンと端数配分）、コストバッファ考慮などを実装。

- 研究・分析ユーティリティ
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュールを追加（モメンタム・ボラティリティ・流動性・ファンダメンタル等の計算を想定）。（ファイルは途中まで実装されている箇所あり）

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。
    - 指標: 稼働率（uptime）、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）等を算出して PASS/FAIL 判定を行う。
    - デフォルトしきい値:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - DB パスはコマンドラインオプション `--db`、環境変数 `PAPER_TRADING_SQLITE_PATH`、デフォルト `data/paper_trading.db` の順で解決。

- モジュールエクスポート
  - package のトップレベル __all__ と portfolio モジュールの明示的エクスポートを追加。

### Changed
- （初回リリースにつき変更履歴はなし）

### Fixed
- （初回リリースにつき修正履歴はなし）

### Deprecated
- （初回リリースにつき非推奨事項はなし）

### Removed
- （初回リリースにつき削除事項はなし）

### Security
- （初回リリースにつきセキュリティ関連の注記はなし）

---

注記:
- .env の自動読み込みはプロジェクトルート検出に依存する（.git か pyproject.toml を探索）。自動読み込みを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 実運用時は .env を絶対にリポジトリにコミットしないでください（config_setup のヘッダにも注意書きあり）。
- run_monitoring/run_execution は停止フラグ（data/stop_requested.flag 等）や PID 管理により外部プロセス管理と連携する設計です。運用ポリシーに合わせたファイルパス設定やアクセス権限管理を推奨します。