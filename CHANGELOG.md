# Changelog

すべての可視的な変更は Keep a Changelog の形式に従って記載します。初回リリースとして v0.1.0 をまとめています（リリース日: 2026-04-24）。

フォーマット:
- Unreleased: 今後の変更（現時点では空）
- 各リリース毎に Added / Changed / Fixed / Deprecated / Removed / Security を記載

## [Unreleased]

---

## [0.1.0] - 2026-04-24

### Added
- 基本アプリケーション構成と起動スクリプトを追加
  - run_execution.py: ExecutionEngine の起動スクリプトを提供。KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用し、MockBrokerClient を利用する設計をサポート。停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による起動/停止制御を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを提供。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能。監視用 DB（SQLite）を環境にかかわらず本番 sqlite_path で初期化する挙動を明示。
  - tools/paper_verification_report.py: ペーパートレード用の検証レポート生成ツールを追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計し PASS/FAIL を判定するレポートを標準出力に出力。
- 環境設定まわり
  - config_setup.py: 対話式 .env ウィザードを追加。よく使う設定項目（KABUSYS_ENV、J-Quants トークン、kabu API パスワード、DB パス、LOG_LEVEL、Kill Switch 等）を対話的に作成・更新できる。
  - validate_config.py: 起動前に .env や config/*.yaml の基本的な妥当性を検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML のパース確認（PyYAML が無い場合は警告）や本番環境ガード等を実装。--strict オプションで警告も失敗扱いに可能。
  - config.py: 環境変数読み込み/管理モジュールを追加。プロジェクトルート自動発見（.git / pyproject.toml ベース）、.env および .env.local の自動ロード（OS 環境変数は保護）、エスケープ付きクォートや inline コメントに対応した .env パーサ、Settings クラスによるプロパティアクセス（各種パス、閾値、ペーパートレード設定等）。
- ポートフォリオ構築ユーティリティ（純関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコア降順、タイブレークロジック）、等金額・スコア加重の重み計算を実装。スコアが全て 0 の場合は等金額にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに基づく乗数（calc_regime_multiplier）を実装。セクター不明は除外せず、未知レジームはフォールバックで 1.0 を返す（警告を出力）。
  - portfolio/position_sizing.py: allocation_method（"risk_based" / "equal" / "score"）に基づく株数決定ロジックを提供。単元株（lot_size）で丸め、per-stock 上限や aggregate cap を考慮したスケーリング処理、手数料・スリッページ想定の cost_buffer、残差処理での再配分ロジックを実装。
  - portfolio/__init__.py: 上記機能をまとめて公開。
- ユーティリティ
  - utils/logging_setup.py: 一貫したログ設定ユーティリティを追加。stdout 出力（StreamHandler）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時にファイル出力をスキップするフォールバックを実装。
  - utils/process_priority.py: Windows / POSIX の差を吸収したプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。psutil を利用し、権限や未対応環境では警告を出して安全にスキップ。
- research/factor_research.py: DuckDB を用いたファクター計算モジュールを追加（モメンタムやMA200乖離、ATR、流動性等の計算方針を実装）。
- monitoring 初期化ヘルパー（monitoring.monitoring_db.init_monitoring_db）の使用箇所を各起動スクリプトで確実に呼び出すように統一。
- パッケージの基本情報
  - src/kabusys/__init__.py にバージョン情報 __version__ = "0.1.0" を追加。

### Changed
- ログ挙動の統一化
  - 全起動スクリプト（monitoring / execution 等）から utils.setup_logging を呼ぶことでログ出力のフォーマット・保存先・ローテーションが統一された。
- 環境変数ロードの優先度と保護
  - config.py で OS 環境変数を protected として .env や .env.local の上書きを制御する設計に変更（.env.local は .env を上書きするが OS 環境変数は上書きしない）。
- run_execution と run_monitoring の DB 接続ポリシーを明確化
  - run_execution: paper_trading モード時は paper_sqlite_path（デフォルト data/paper_trading.db）、それ以外は監視用 sqlite_path を使用。
  - run_monitoring: 監視は環境に依らず本番 sqlite_path を使用する方針を明示。

### Fixed
- .env パーサーの堅牢化
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い、空行/コメント行の無視などを実装し、実用的な .env の読み取り不具合を修正。
- MONITOR_POLL_INTERVAL の不正値ハンドリング
  - run_monitoring のポーリング間隔読み取りで 0 以下や非数の環境変数が設定された場合にデフォルト（60 秒）へフォールバックし、警告ログを出力するように変更。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

### Notes / Known issues
- research/factor_research.py は一部実装が長く続く設計になっており（ファイル末尾で処理が途切れている箇所がある）、将来的に追加実装・テストが必要。現在のモジュール設計は DuckDB の prices_daily / raw_financials テーブルを前提としているため、テーブルスキーマ・データ整備が必要。
- 一部の機能（例: BrokerClientFactory、ExecutionEngine、SystemMonitor、monitoring_db）は本 changelog のコードスナップショットから参照されるが、実装詳細は当該モジュール側に依存する。起動前に validate_config.py による検証を推奨。

---

開発中・運用時の補助:
- .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能（テスト時に有用）。
- 本番運用時は KABUSYS_ENV=live に注意（validate_config にて注意喚起を行う。LINE 通知設定や KILL_FLAG_CLEAR_ON_START=1 の設定は危険と警告される）。

もし特定機能（例: position_sizing のスケーリング詳細、paper_verification_report の閾値調整、.env パーサの振る舞い）について CHANGELOG に含めたい差分や追加説明があれば指示してください。