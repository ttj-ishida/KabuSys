# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

### Added
- 実行用エントリポイントを追加
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を利用することで本番 DB と分離。
    - BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler 等の組み立てと、デーモンスレッドでのセッション実行を実装。
    - 起動前に停止フラグ (data/stop_requested.flag) を確認し、PID ファイル (data/execution.pid) を使用。
- 監視用エントリポイントを追加
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。不正値は警告しデフォルトへフォールバック。
    - Monitoring は KABUSYS_ENV に関わらず本番用 sqlite_path を使用して監視情報を記録。
    - 例外発生時にロギングしてループ継続する堅牢化。
- 設定管理・自動読み込み機能を追加
  - config.py:
    - .env / .env.local の順で自動読み込み（OS 環境変数を保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .git / pyproject.toml をプロジェクトルートの検出基準にして、自動ロードの対象を決定。
    - 複雑な .env の行パースを実装（export プレフィックス対応、クォート文字とバックスラッシュエスケープ、インラインコメント処理）。
    - Settings クラスを実装し、J-Quants / kabuAPI / LINE / DB / 監視閾値 等のプロパティアクセスを提供。環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を行う。
- 設定検証 CLI を追加
  - validate_config.py:
    - .env と config/*.yaml の起動前チェックを行う CLI を追加（--strict オプションで警告をエラー扱いにできる）。
    - 必須環境変数チェック、KABUSYS_ENV の整合性チェック、ログレベルチェック、DB パスの親ディレクトリ確認、YAML パース確認（PyYAML がある場合）、本番環境向けの追加ガード（LINE 通知設定や Kill Switch の注意喚起）を実装。
- 環境設定ウィザードを追加
  - config_setup.py:
    - 対話式に .env を作成・更新するウィザードを提供。既存 .env の読み込み、入力の再利用、秘密項目のマスク表示、保存前の確認等を実装。
    - .env の書式テンプレートを生成（Git にコミットしない旨のヘッダ付き）。
- ロギング・プロセス制御ユーティリティを追加
  - utils/logging_setup.py:
    - すべての起動スクリプトで共通利用できるログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせてルートロガーを構成。ログディレクトリ自動作成、既存ハンドラのクリーンアップ、ログレベル解決順を実装。
    - ファイルハンドラ作成失敗時はコンソールのみで継続。
  - utils/process_priority.py:
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加（psutil 依存）。CPU affinity を最初の N コアに固定する set_cpu_affinity も提供。
- ポートフォリオ構築関連モジュールを追加（純粋関数群）
  - portfolio/portfolio_builder.py:
    - 候補選定（スコア降順で上位 N）、等重配分、スコア加重配分を実装。スコアが全て 0 の場合は等重にフォールバックして警告。
  - portfolio/risk_adjustment.py:
    - セクター集中制限の適用（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジームはフォールバックで 1.0。
  - portfolio/position_sizing.py:
    - 銘柄ごとの発注株数算出を実装（risk_based / equal / score の allocation_method）。単元株丸め、per-stock 上限、aggregate cap（利用可能現金に基づくスケーリング）、cost_buffer（手数料・スリッページ見積り）を考慮。
  - portfolio/__init__.py で主要 API をエクスポート。
- Paper Trading 検証ツールを追加
  - tools/paper_verification_report.py:
    - ペーパートレード DB（デフォルト: data/paper_trading.db）から指標（稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数など）を集計し、閾値に基づく PASS/FAIL レポートを生成するスクリプトを追加。日付フィルタ、DB 存在チェック、指標の欠損に対する安全ハンドリングを実装。
- DuckDB/SQLite の統合と初期化
  - 監視・実行スクリプトで duckdb 接続を使用するように追加。init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。
- パッケージ初期バージョン宣言
  - __init__.py に __version__ = "0.1.0" を追加。

### Changed
- ロギングの既定挙動を統一
  - 全スクリプトで setup_logging を呼び出し、ログ出力を stdout と日次ファイルローテーションに統一。
- 環境ファイル読み込み順を明確化
  - OS 環境変数 > .env.local > .env の優先順を明文化し、OS 環境変数は保護され上書きされないように実装。
- 停止・Kill フラグの取り扱いを統一
  - run_monitoring/run_execution の両スクリプトで同様の停止フラグ（data/stop_requested.flag）チェックを実装し、優雅に終了するように変更。

### Fixed
- 不正な MONITOR_POLL_INTERVAL 値が time.sleep に渡ることで発生する例外を防止
  - _get_poll_interval() で 0 以下や非整数を検出し、警告してデフォルトにフォールバックするようにした。
- 監視ループ内の例外によるプロセス停止を防止
  - monitor.check_once() 呼び出しを try/except で保護し、例外発生時はログ出力の上で次回ポーリングに備えるようにした。
- .env パーサの堅牢化
  - クォート、エスケープ、インラインコメントなど複雑な .env 行を正しくパースするよう改善。

### Security
- .env ファイルについての注意書きを config_setup の出力に追加（.env を絶対に Git にコミットしない旨）。

### Internal
- code comments / TODO を追加して将来的な拡張点（銘柄別 lot_size の導入、price のフォールバック値の検討等）を明示。
- research/factor_research.py はモジュール骨子と定数群を追加（モメンタム等のファクター計算関数実装の続きあり）。  

---

注記:
- この CHANGELOG は与えられたコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートとは差異がある場合があります。必要があれば、特定のコミットや日付を反映するよう追記・修正してください。