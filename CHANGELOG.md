# CHANGELOG

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

全般:
- バージョニングは SemVer を想定します（このリリースは初期リリース扱い）。
- 主要な CLI とユーティリティ、ポートフォリオ構築ロジック、Execution/Monitoring の起動スクリプト等を含む初回公開相当のセットアップを行いました。

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーションパッケージを追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の Paper Trading DB を使用（デフォルト: data/paper_trading.db）。
    - BrokerClientFactory を用いてブローカークライアントを構築し、OrderRepository / OrderManager / RiskManager / Reconciler を組み上げて ExecutionEngine を起動。
    - 停止制御: data/stop_requested.flag を監視し停止要求があればエンジンを停止。
    - 起動時にプロセス優先度を "high" に設定。
    - 実行中は execution.pid に PID を書き込む（pid_file を使用）。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正な値の場合はデフォルトへフォールバックし警告を出力。
    - 監視 DB は環境に依らず本番 sqlite_path を使用（monitoring 用テーブルの初期化を実施）。
    - 停止フラグ（data/stop_requested.flag）でループを終了。

- 設定管理
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env / .env.local の読み込み順序を実装（OS 環境変数を保護する仕組みあり）。
    - .env の行パーサを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いを考慮）。
    - Settings クラスを提供し、各種環境設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE, PID_FILE_PATH, KILL_FLAG_*、しきい値など）をプロパティで取得可能。
    - KABUSYS_ENV / LOG_LEVEL のバリデーションと is_live / is_paper / is_dev のヘルパーを追加。

- 設定支援・検証ツール
  - config_setup.py
    - 対話式ウィザードで .env の作成・更新を支援する CLI を追加。
    - シークレット項目は入力時に表示をマスク（保存時は平文で .env に書き出すが、注意書きを出力）。
    - デフォルト値や選択肢、説明文を表示してユーザー入力を促す。
  - validate_config.py
    - 起動前に環境変数や config/*.yaml の存在・基本整合性をチェックする CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML がある場合は）パース検証を行う。
    - --strict モードで警告を失敗扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - すべての起動スクリプトから共通して使えるログ設定ユーティリティを追加。
    - コンソール出力は stdout を使用、ファイルは日次ローテーション（TimedRotatingFileHandler）で保存。LOG_DIR / LOG_LEVEL で上書き可能。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみで継続する安全な実装。
  - utils/process_priority.py
    - Windows と POSIX 系（Linux/Mac/FreeBSD）でのプロセス優先度設定（nice / Windows priority class）を吸収するユーティリティを追加。
    - CPU affinity 設定関数も提供。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - シグナルから候補選定（スコア降順 / same-score タイブレーク）と等金額・スコア加重の重み計算を実装。
    - スコアが全て 0 の場合は等金額にフォールバックし警告出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有と売却予定を考慮して新規候補を除外。
    - レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear のマッピング、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - allocation_method ("risk_based", "equal", "score") に基づく株数決定ロジックを実装。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金に基づくスケーリング）を実装。
    - cost_buffer（手数料/スリッページ想定）を加味した保守的見積り、残差処理による追加配分ロジックを実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading DB（デフォルト: data/paper_trading.db）から稼働率、注文成功率、送信率、リスク却下件数、レイテンシ（平均/最大/P95）を集計してレポート出力する CLI を追加。
    - 基準値（稼働率 99%, 成立率 90%, 送信率 95%, P95 レイテンシ 200ms）を用いた PASS/FAIL 判定を出力。
    - --from/--to/--db オプション対応。

- Research / Factor 計算（着手）
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity を計算する方針と定数を追加。
    - calc_momentum の計算開始処理（設計・定数）を導入（実装は続きがある設計段階）。

- パッケージ初期化
  - __init__.py で __version__ = "0.1.0" を追加。主要サブパッケージを __all__ で公開。

### Changed
- ログ出力の統一
  - すべての起動スクリプトが setup_logging を呼び出して統一的にログ出力を行うように統合。
  - コンソールは stdout を使用する方針に統一（cron 等からのリダイレクトに配慮）。

- DB 初期化の冪等性
  - 起動時に init_monitoring_db を呼ぶことで monitoring テーブルが存在することを保証（冪等な初期化）。

### Fixed / Robustness
- 環境ファイルのパース堅牢化
  - _parse_env_line で export プレフィックス、クォート内のエスケープ、インラインコメントの扱いを改善。無効行はスキップ。

- ポーリング間隔の安全化
  - MONITOR_POLL_INTERVAL が不正（整数でない、0 以下など）の場合にデフォルトにフォールバックして警告を出すようにして time.sleep の例外を防止。

- プロセス優先度設定の例外耐性
  - set_process_priority / set_cpu_affinity は権限不足や未サポート OS の場合に警告を出して安全にスキップするよう強化。

- ファイル・ディレクトリ作成失敗の安全処理
  - ログディレクトリ作成失敗時はファイル出力を無効化して stdout のみで継続。

### Removed
- （この初回リリースにおける破壊的な削除は無し）

### Known issues / Notes
- research/factor_research.calc_momentum は途中実装の状態（ファイル末尾が未完/続きあり）。計算ロジックの完成が必要。
- portfolio.position_sizing の価格欠損時のフォールバック（前日終値など）は TODO コメントとして残してあります。価格欠損があると期待どおりの配分とならない可能性があるため、実運用前に補完ロジックを導入することを推奨します。
- .env に機密情報が平文で保存される点に注意（.env は絶対に Git にコミットしない旨をヘルプに明記）。
- Paper Trading と本番 DB は意図的に分離しているが、設定ミスによる DB の混同を防ぐため validate_config での確認を推奨します。

---

今後の予定（次バージョンで想定）
- factor_research の完全実装とユニットテスト追加
- 各モジュールのユニットテスト整備（設定パーサ、position sizing のエッジケース、process_priority のモックテスト等）
- ExecutionEngine / SystemMonitor の統合テストとブローカークライアント抽象化の改善
- ロギング・メトリクスの可観測性強化（メトリクス export など）

もし特定ファイルの差分に基づくより詳細なリリースノート形式（例: 変更前後のコード断片、コミットハッシュ等）をご希望でしたら、差分情報を提供してください。