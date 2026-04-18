# Changelog

すべての変更は Keep a Changelog のフォーマットに従って記載しています。  
初回リリース相当の状態を、ソースコードから推測してまとめています。

全般的な注記
- 日付はソース内の参照や現在日付（2026-04-18）を基準に付与しています。  
- 記載内容はコードから推測した機能・挙動の説明であり、実際のリリースノート作成時は実環境での確認を推奨します。

## [0.1.0] - 2026-04-18

### Added
- 基本パッケージの初期実装を追加。
  - パッケージ名: kabusys
  - バージョン情報: src/kabusys/__init__.py にて `__version__ = "0.1.0"` を定義。

- 環境設定・ロード機能
  - `.env` 自動読み込み機能を実装（プロジェクトルートは .git / pyproject.toml で探索）。
  - .env の柔軟なパース処理を実装（コメント、export 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント取り扱いなどに対応）。
  - 自動読み込みを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - Settings クラスを実装し、環境変数から各種設定を取得する一元管理を追加（DB パス、API トークン、paper trading 用設定、監視しきい値など）。

- CLI / 設定ツール
  - 対話式 .env ウィザード: `python -m kabusys.config_setup` を提供。
    - `.env` の初期作成・更新を対話式で実施。秘密値のマスク表示、選択肢サポート、既存値の再利用に対応。
  - 設定検証 CLI: `python -m kabusys.validate_config` を提供。
    - 必須環境変数の有無、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の有無と（PyYAML があれば）パース検証、本番環境向けの追加ガード等を実行。
    - `--strict` を指定すると警告も失敗扱いにできる。

- 実行エンジン / 監視デーモン起動スクリプト
  - ExecutionEngine 起動スクリプト: `src/kabusys/run_execution.py`
    - KABUSYS_ENV が `paper_trading` の場合は paper 用 SQLite を使用し、本番 DB とは分離（PAPER_TRADING_SQLITE_PATH を上書き可能）。
    - BrokerClientFactory 経由でブローカークライアントを切替（実ブローカー / MockBroker）。
    - Engine をスレッドで起動し、プロセス間停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）を扱う。
    - リスクマネージャ（RiskManager）と Reconciler、OrderManager、OrderRepository の組み立てを行う。
  - Monitoring 起動スクリプト: `src/kabusys/run_monitoring.py`
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計（監視データは本番 DB に集約する想定）。
    - SystemMonitor の check_once() をポーリングで実行し、例外発生時はログを残して次ポーリングへ継続。
    - 停止フラグや KeyboardInterrupt を検知して安全にクリーンアップ。

- 監視 DB 初期化ユーティリティ
  - `init_monitoring_db` を使用して monitoring 用のテーブルが存在することを保証（冪等）。

- ロギングユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を追加。
    - stdout（StreamHandler）と日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリの自動作成処理を行い、作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続するフェイルセーフあり。
    - LOG_LEVEL / LOG_DIR の環境変数・引数による解決順を実装。

- プロセス優先度・CPU affinity ユーティリティ
  - `kabusys.utils.process_priority` を追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収してプロセス優先度（high/normal/low）の設定を行う。
    - CPU affinity を最初の N コアに固定する機能を提供。
    - 権限不足や未対応プラットフォーム時は警告を出し安全にスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定（select_candidates）: スコア降順、同点は signal_rank でタイブレーク。
    - 等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights、全スコアが 0 の場合は等配分へフォールバック）。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限（apply_sector_cap）: 既存ポジションのセクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外（"unknown" セクターは無視）。
    - レジーム乗数（calc_regime_multiplier）: bull/neutral/bear に対する投下資金乗数を実装（未知レジームは警告と共に 1.0 フォールバック）。
  - `kabusys.portfolio.position_sizing`
    - 複数方式の株数決定（risk_based / equal / score）を実装。
    - 単元（lot_size）丸め、per-position 上限、aggregate cap（available_cash を超える場合のスケーリング）と残差処理により再配分を行う。
    - cost_buffer による保守的見積もりを考慮。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を追加。
    - Paper Trading の SQLite DB（デフォルト data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95））を集計してレポート出力。
    - P95 計算、期間フィルタ（--from / --to）、閾値（稼働率 99% など）に基づく PASS/FAIL 判定を実装。

- リサーチ（ファクター計算）モジュール（初期実装）
  - `kabusys.research.factor_research` を追加（モメンタム / ATR / ボラティリティ等のファクター計算の骨組み）。
  - DuckDB 接続を受け取り prices_daily / raw_financials からファクターを算出する設計。

### Changed
- なし（初回実装想定のため既存からの変更は特記なし）。

### Fixed
- なし（初回実装想定のためバグ修正履歴は特記なし）。

### Deprecated
- なし。

### Removed
- なし。

### Security
- API トークン等（J-Quants / kabuステーション）は .env に秘密値として格納する設計。config_setup は .env を生成する際に「絶対に Git にコミットしないこと」を明示。
- 設定検証により、本番環境（KABUSYS_ENV=live）で通知設定等が未設定の場合に警告を出すガードを追加。

---

注意・補足（コードから推測した運用上のポイント）
- 監視（run_monitoring）は「環境にかかわらず」本番 sqlite_path を使う設計になっているため、本番監視データと paper_trading データを混在させないよう運用時に注意が必要です（paper_trading は run_execution で別 DB を使う）。
- process_priority は権限や OS によっては設定失敗する可能性があるため警告ログによりフォールバックする実装になっている。
- .env パーサはかなり厳密に実装されている（クォート内のエスケープ、インラインコメント処理等）。特殊文字を含むトークンを .env に書く際は期待通りに読み込まれるか確認してください。
- LoggingSetup はログディレクトリの作成に失敗した場合もコンソールログで動作を継続するため、ファイル出力不可時の挙動に依存する運用は避けること。

この CHANGELOG はソースコードの内容から推測して作成したものであり、実際のコミット履歴やリリースプロセスに合わせて追記・修正してください。