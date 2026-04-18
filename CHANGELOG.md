# Changelog

すべての注記は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

初回公開リリース。コードベースから推測される主な機能・改善・修正点を以下にまとめます。

### Added
- 全体
  - パッケージ初期化とバージョン情報の追加（kabusys/__init__.py に `__version__ = "0.1.0"`）。
  - 豊富なモジュール群と CLI ツールを実装し、自動売買システムの基盤を提供。
- 設定・環境
  - Settings クラスによる環境変数／設定の一元管理を実装（src/kabusys/config.py）。
    - .env 自動ロード機能（プロジェクトルート = .git または pyproject.toml を探索）。
    - .env と .env.local の読み込みルール（OS 環境変数を保護して上書き順を制御）。
    - 各種プロパティ（J-Quants トークン、kabu API パスワード、DB パス、PAPER_FILL_MODE、閾値、環境フラグ等）を提供。
    - 必須環境変数未設定時に明確な例外を送出する `_require` を提供。
  - `.env` パーサを強化（引用符付き値のエスケープ処理、export プレフィックス、行末コメント処理など）に対応。
  - インタラクティブな環境設定ウィザードを実装（src/kabusys/config_setup.py）。
    - .env の生成・更新を対話的に行える。秘密値はマスク表示。保存前の確認を実施。
    - .env のテンプレート形式で書き出し（Git コミット禁止注記を含む）。
  - 設定検証 CLI を実装（src/kabusys/validate_config.py）。
    - 必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス、config/*.yaml の存在や YAML パース（PyYAML インストール有無に応じて）などをチェック。
    - `--strict` オプションで警告をエラー扱いにできる。
- 起動スクリプト / 実行管理
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）を追加。
    - プロセス優先度を高優先（high）に設定して起動。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading SQLite DB（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド実行と停止フラグ監視（data/stop_requested.flag, data/execution.pid）を実装。
    - リスク設定（RiskConfig）のデフォルト値を設定し、初期ポートフォリオ値に broker.get_available_cash() を使用。
  - 監視（Monitoring）起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告ログを出力。
    - 監視処理は本番の sqlite_path を常に使用して監視テーブルを初期化（init_monitoring_db）。
    - 停止フラグ（data/stop_requested.flag）の検知でループ終了、KeyboardInterrupt による安全終了処理を実装。
- ロギング・プロセス管理
  - 統一ロギング設定ユーティリティを実装（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と日次ローテートする TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーへ設定。
    - ログディレクトリ解決（引数 > 環境変数 LOG_DIR > デフォルト logs/）と作成を試み、失敗時はファイル出力をスキップしてコンソール出力継続。
    - 既存ハンドラのクリーンアップ（重複設定の防止）。
  - プロセス優先度と CPU affinity のユーティリティを実装（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux, macOS, FreeBSD）差分を吸収して優先度（high/normal/low）を設定、また CPU コア数を固定する set_cpu_affinity を提供。
    - 権限不足や非対応環境では警告ログを出して処理をスキップ。
- ポートフォリオ構築（純粋関数群）
  - 銘柄選定と重み（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順、タイブレーク: signal_rank）、calc_equal_weights、calc_score_weights（スコア全0 の場合は等配分にフォールバック）を実装。
  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap：既存保有のセクター暴露を計算し、max_sector_pct 超のセクターから新規候補を除外（"unknown" セクターは無視）。
    - calc_regime_multiplier：レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告後 1.0 でフォールバック。
  - 株数決定・丸めロジック（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes：allocation_method（risk_based / equal / score）に基づく発注株数算出、単元（lot_size）で丸め、per-stock 上限と aggregate キャップ（available_cash）に基づくスケーリングと残余配分ロジックを実装。
    - cost_buffer によるコスト見積りを加味した保守的な算出をサポート。
- 監視／モニタリング DB 初期化
  - init_monitoring_db 呼び出しにより監視テーブルの存在を保証（冪等に作成）。
- Paper Trading 検証レポートツール
  - tools/paper_verification_report.py を追加。
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / デフォルト data/paper_trading.db）からデータを集計してレポートを生成。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率、API レイテンシ（avg, max, P95）など。
    - Pass/Fail 基準値を定義（例: 稼働率 >= 99%、P95 <= 200ms 等）して判定を出力。
    - 日付フィルタ（--from / --to）と DB パス指定（--db）に対応。
- リサーチ（部分実装）
  - research/factor_research.py にモメンタム等のファクター計算基盤を追加（DuckDB 接続を受け取る設計）。ファイルは途中までの実装（calc_momentum の開始）を含む。

### Changed
- 実行・監視のデフォルト DB 挙動
  - 監視（run_monitoring）は KABUSYS_ENV に関わらず「production」相当の sqlite_path（Settings.sqlite_path）を使用する旨を明示（監視データは本番 DB に保存する設計）。
  - 実行（run_execution）は KABUSYS_ENV=paper_trading 時に paper_sqlite_path を使用して本番 DB と完全に分離する（テスト／検証用の運用分離）。
- ログ出力の標準化
  - 全起動スクリプトで setup_logging を呼び出し、ログの一貫性を確保するように変更。

### Fixed
- 環境変数パース / 値検証
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）を検出して警告を出し、デフォルト値にフォールバックするように実装（run_monitoring._get_poll_interval）。
  - PAPER_FILL_MODE のバリデーションを厳格化（有効値: instant/partial/never/reject）し、不正値は ValueError を送出。
  - Settings.env の不正値チェックを追加（有効値: development / paper_trading / live）。
- ロバストネス
  - ロギング設定やファイルハンドラの作成が失敗した場合にフォールバック（コンソールのみ）して処理を継続する設計に改良。
  - process_priority／set_cpu_affinity の呼び出しで権限不足や未対応システムの場合に警告ログを出して安全にスキップするように修正。
  - validate_config が PyYAML 未インストール時に YAML 検証をスキップし、警告を出すように実装（依存性がない環境でも実行可能）。

### Security
- .env の扱いに関する注意喚起を config_setup の出力に明記（.env を Git にコミットしないこと）。
- secrets（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）はウィザードでマスク表示し、ファイル出力テンプレートにも注意書きを付与。

### Documentation / Developer experience
- 各モジュールに詳細な docstring と使用例を追加（run scripts、logging_setup、config_setup、portfolio モジュール等）。
- CLI（config_setup, validate_config, tools/paper_verification_report）の使用方法を docstring/コメントに記載。

### Known limitations / TODO
- research/factor_research.py は calc_momentum 以降が未完（ファイル末尾で中断）。全ファクター（Value, Volatility, Liquidity）の実装継続が必要。
- position_sizing の price フォールバック（price が欠損する場合の扱い）は TODO コメントが残っている（前日終値や取得原価のフォールバックを検討）。
- 将来的に lot_size を銘柄別に扱う拡張（stocks マスタへの lot_size 挿入）を想定した設計になっているが未実装。
- ログファイル生成やディレクトリ作成の失敗に関するより詳細な監視／通知は未実装（今後の改善候補）。

---

（注）上記は与えられたソースコードから推測した変更履歴の要約です。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。