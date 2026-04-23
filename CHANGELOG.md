# Keep a Changelog

すべての注目すべき変更点を時系列で記録します。本ファイルは Keep a Changelog の形式に準拠しています。

フォーマット:
- Unreleased: 次回リリースに向けた未リリースの変更（現状なし）
- バージョンごとに Added / Changed / Fixed / Deprecated / Removed / Security のカテゴリで記載

## [Unreleased]
- なし

## [0.1.0] - 2026-04-23
初回公開リリース。

### Added
- パッケージ初期導入
  - パッケージバージョンを設定: kabusys.__version__ = "0.1.0"

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を設定可能（デフォルト 60 秒）。
    - 停止フラグによる安全終了（data/stop_requested.flag）。
    - プロセス優先度を High に設定して起動。
    - monitoring 用の SQLite 初期化（init_monitoring_db）と DuckDB 接続を行う。
    - check_once() 実行時の例外保護とログ出力を実装。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db）を利用し、本番 DB と分離して動作。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て。
    - デフォルトの RiskConfig を定義（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）。
    - デーモンスレッドで Engine.run_session を起動し、停止フラグ検知で安全に停止・終了する仕組み。
    - 実行中の PID を data/execution.pid に保存するための pid_file 指定に対応。

- 設定/環境管理
  - config.py
    - .env ファイル自動ロード機能を導入（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env / .env.local の読み込み順序と OS 環境変数の保護（上書き禁止）を実装。
    - .env の各行パーサー（引用、export 形式、インラインコメント処理）を実装し堅牢に読み込めるようにした。
    - Settings クラスを提供し、環境変数アクセスをプロパティとして型付きで統一。
    - PAPER_FILL_MODE のバリデーション、KABUSYS_ENV / LOG_LEVEL のバリデーション、各種パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH 等）のプロパティを追加。

  - validate_config.py
    - 起動前に .env と config/*.yaml の状態を検査する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ確認、config/*.yaml の存在と YAML パース検査（PyYAML がない場合は警告）を実装。
    - KABUSYS_ENV=live に対する追加ガード（LINE 通知設定・Kill Switch の設定確認）。
    - --strict モードで警告を失敗に昇格可能。

  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。
    - 秘匿値のマスク表示、選択肢サポート、既存 .env の読み込みと Enter による再利用、保存前の確認などを実装。
    - .env ファイルのテンプレート生成（コメント付き）を実装。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 全アプリケーションで共通のロギングセットアップ関数 setup_logging を追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）でログをファイルに出力する（logs/<app_name>.log）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続する堅牢性を実装。
    - ログレベル決定順（関数引数 > LOG_LEVEL 環境変数 > デフォルト）を提供。

  - utils/process_priority.py
    - プラットフォーム差を吸収してプロセス優先度を設定するユーティリティを追加（psutil を利用）。
    - Windows / POSIX（Linux, Darwin, FreeBSD）対応の優先度マップを実装。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity も追加（権限・実装未対応時は警告にフォールバック）。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - 候補選定(select_candidates)、等分配(calc_equal_weights)、スコア加重(calc_score_weights) を追加。スコアが全て 0 の場合のフォールバックを実装。

  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有比率が閾値を超える場合の候補除外）を追加。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear マッピング、未知レジームは警告の上フォールバック）。

  - portfolio/position_sizing.py
    - 株数計算 calc_position_sizes を実装。allocation_method に "risk_based", "equal", "score" をサポート。
    - 単元株（lot_size）丸め、per-stock 上限・aggregate cap のスケールダウン、cost_buffer を用いた保守的見積り、残差に基づく追加配分ロジックを実装。
    - 価格欠損時のスキップやデバッグログを追加。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計。
    - 閾値に基づく PASS/FAIL 判定を行い、標準出力へ整形レポートを出力。日付フィルタ（--from/--to）と DB パス指定（--db）をサポート。
    - P95 計算や NULL ハンドリング、データ不足時の N/A 表示を考慮。

- リサーチ（実装途中）
  - research/factor_research.py
    - モメンタム等ファクター計算の基礎を追加。DuckDB 経由で prices_daily / raw_financials を参照する設計。
    - calc_momentum の実装開始（ファイル末尾で未完。今後続きの実装予定）。

### Changed
- 設定の自動読み込みの挙動を明文化
  - .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
  - 読み込みの優先順は OS 環境変数 > .env.local > .env（.env.local は上書き可能）として実装。

- ログ設定のデフォルト挙動
  - ログ出力先を stdout に統一しており、サーバ起動タスクとリダイレクト運用を容易にする設計へ変更。

### Fixed
- run_monitoring のポーリング間隔取得関数で不正な MONITOR_POLL_INTERVAL 値（非整数・0 以下）を検出し、デフォルト値にフォールバックして警告ログを出すように修正。これにより time.sleep に渡す際の ValueError を回避。

- Paper Trading モード時の DB 分離を明確化（execution/run が paper_trading 用 DB を使用するように修正/明文化）。

### Deprecated
- なし

### Removed
- なし

### Security
- 秘匿情報の扱いに関する注意書きを config_setup の .env テンプレートに記載（.env を絶対にコミットしない旨）。


## 注記 / 既知の制限
- research/factor_research.py の calc_momentum 実装は途中で終わっており、完全なファクター算出は未完。今後のリリースで継続実装予定。
- 一部の機能（プロセス優先度設定・CPU affinity）は OS 権限や psutil の環境依存のため、アクセス権限不足や未対応環境では警告を出してスキップします。
- config/*.yaml の内容検証は PyYAML に依存。環境に PyYAML がない場合は構文チェックがスキップされ、警告が表示されます。

以上が、コードベースから推測して作成した CHANGELOG.md の内容です。追加で日付を変更したい、あるいは各項目をより詳細に分割したい場合は指示してください。