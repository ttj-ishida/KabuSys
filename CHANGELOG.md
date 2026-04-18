Changelog
=========

すべての日付は YYYY-MM-DD 形式です。  
このファイルは Keep a Changelog の形式に準拠しています。  

## [0.1.0] - 2026-04-18
初回リリース。

### Added
- 全体
  - パッケージ初期リリース。バージョンは `kabusys.__version__ = "0.1.0"`。
  - プロジェクトルート自動検出機能を実装（`.git` または `pyproject.toml` を探索）し、.env 自動読み込みの基盤を追加。

- 設定・環境管理
  - Settings クラスを導入し、環境変数経由でアプリ設定を一元管理（J-Quants / kabuAPI / DB パス / ログ / しきい値など）。
  - .env ファイルの自動読み込み:
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化対応。
    - .env ファイル読み込み時に既存の OS 環境変数を保護する仕組みを導入。
  - .env パーサーの強化:
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱いなどに対応。

- 起動・管理用 CLI
  - config_setup: 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - シークレット項目は表示をマスクして入力を促す。
    - 書き出しテンプレートとコメント付きの .env 生成をサポート。
  - validate_config: 起動前検証用 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、DB パスの親ディレクトリ存在チェック、YAML ファイル（PyYAML 利用時）のパース検証、live 環境向けの追加ガードを実施。
    - `--strict` オプションでワーニングを失敗扱いにできる。

- 実行エンジン / 監視ランナー
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading のときは paper 用の SQLite（`data/paper_trading.db`）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（paper/live 切替）。
    - ExecutionEngine をデーモンスレッドで実行し、プロジェクトルートの stop フラグ（data/stop_requested.flag）で安全に停止可能。
    - PID ファイル（data/execution.pid）サポート。
  - run_monitoring: SystemMonitor（監視）起動スクリプトを追加。
    - 環境にかかわらず監視は本番用 sqlite_path を使用して監視データを一元管理。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトへフォールバック。
    - 停止フラグ / KeyboardInterrupt の安全なクリーンアップ処理を実装。

- 監視 DB 初期化
  - monitoring_db 初期化呼び出しを導入（起動時に監視テーブルの存在を保証）。

- ロギング・プロセス管理ユーティリティ
  - utils.logging_setup:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション・30日保持）を設定するユーティリティを追加。
    - 既存ハンドラを一旦クローズしてから再設定することで二重登録を防止。
    - LOG_DIR のディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils.process_priority:
    - psutil を用いたプロセス優先度設定ユーティリティを追加（Windows / POSIX の差分を吸収）。
    - CPU affinity 設定関数も実装（利用可能コア数を考慮し、安全に処理）。
    - 権限不足や未対応 OS の場合は警告をログに出しフォールバックする。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder:
    - 候補選定（スコア降順、signal_rank によるタイブレーク）、等金額配分、スコア重み配分を実装。
    - スコアが全て 0 の場合は等分配にフォールバックして警告を出す。
  - portfolio.risk_adjustment:
    - セクター集中制限（apply_sector_cap）を実装。既存ポジションのセクター暴露を計算し上限超過セクターの新規候補を除外。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear とフォールバック）。
  - portfolio.position_sizing:
    - 複数の配分方式（risk_based, equal, score）に基づいて単元株（lot）丸め、1 銘柄上限、aggregate cap（利用可能現金を超える場合のスケールダウン）を実装。
    - コストバッファ、手数料・スリッページ考慮、残余キャッシュを用いた端数調整ロジックを実装。

- Paper Trading 検証ツール
  - tools.paper_verification_report:
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を参照し、システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均・最大・P95）を集計してレポート出力する CLI を追加。
    - P95 計算、期間フィルタ（--from/--to）、閾値による PASS/FAIL 判定を実装。
    - データ欠損時の耐性（該当テーブルがない場合でもレポートを生成）を確保。

- リサーチ（骨格）
  - research.factor_research:
    - ファクター（Momentum, Value, Volatility, Liquidity）計算モジュールの骨格・定数群を追加。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
    - モメンタム（1M/3M/6M、MA200 乖離）計算用の関数シグネチャを準備（実装はファイル内で継続中）。

### Changed
- なし（初回リリースのため新規追加中心）。

### Fixed
- 監視スクリプトの堅牢性向上:
  - MONITOR_POLL_INTERVAL に不正な値が指定された場合に警告を出し、time.sleep に渡せるデフォルト値へフォールバックするようにした（ValueError 回避）。
  - 監視ループ内で monitor.check_once() が例外を投げてもループを継続し、スタックトレースをログ出力するようにして一時的な障害に耐性を持たせた。

### Security
- .env ファイルは生成時に注意書きを付与（「絶対に Git にコミットしないこと」）し、シークレット項目はウィザードでマスク表示するなど誤開示リスクを軽減。

### Internal
- ファイル・ディレクトリのパス解決に Path.expanduser() を使用してユーザーフレンドリーに。
- ログ設定やプロセス優先度設定は起動初期に呼び出すように統一し、起動スクリプト間で同一の挙動を確保。

---

今後の予定（例）
- factor_research の完全実装（各ファクター計算・正規化）
- ExecutionEngine / BrokerClient の詳細なユニットテスト整備
- 単体テスト、CI ワークフローの追加
- モニタリング・アラート（LINE 通知）周りの拡張（閾値超過での通知など）

もし特定ファイルや変更点について詳しい説明や別フォーマット（英語版、リリースノート風）での出力をご希望でしたらお知らせください。