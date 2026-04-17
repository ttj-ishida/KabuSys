# CHANGELOG

すべての注目すべき変更を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

現在のリリース方針:
- これが初回の公開リリースです。

## [Unreleased]

## [0.1.0] - 2026-04-17

初回リリース — 基本的な自動売買フレームワークのコア機能を追加しました。

### Added
- パッケージ情報
  - パッケージ初版を追加（kabusys, __version__ = 0.1.0）。

- 実行用スクリプト
  - run_monitoring.py
    - SystemMonitor をポーリングするデーモンループを提供。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止判定はプロジェクト直下の data/stop_requested.flag を監視。
    - 監視処理は sqlite（monitoring DB）と duckdb に接続して動作。監視データは本番の sqlite_path を使用（KABUSYS_ENV に依存せず本番 sqlite_path を参照する仕様）。
    - プロセス優先度を起動時に "high" に設定する処理を実行（utils.process_priority を使用）。
  - run_execution.py
    - ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。MockBroker を利用する想定の BrokerClientFactory を使用。
    - エンジンの PID ファイル管理、停止フラグ（data/stop_requested.flag）による安全停止、デーモンスレッド実行をサポート。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理・ユーティリティ
  - config.py
    - .env 自動ロード機能（プロジェクトルートを .git または pyproject.toml から検出）。
    - .env / .env.local の読み込み順（OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
    - export プレフィックスやクォート、コメントを考慮した .env パーサ実装。
    - Settings クラスによる環境変数ラッパー（J-Quants、kabu API、DB パス、Paper Trading 設定、監視閾値など）。値の検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）を実装。
    - paper_trading 専用の PAPER_TRADING_SQLITE_PATH（プロパティ: paper_sqlite_path）と PAPER_FILL_MODE（instant/partial/never/reject）のサポート。
  - config_setup.py
    - .env を対話式に作成・更新するウィザード CLI。
    - 主要な設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LINE など）を対話的に入力して .env を生成。
    - .env を生成するテンプレートと注意（.env を Git にコミットしないこと）の出力。
  - validate_config.py
    - 起動前チェック CLI。必須環境変数の存在、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認（PyYAML がインストールされている場合はパース検証）などを行う。
    - --strict モードで警告を FAIL 扱いにできる。
    - 本番（KABUSYS_ENV=live）の追加ガード（LINE 通知の未設定、KILL_FLAG_CLEAR_ON_START の危険設定を警告）。
  - utils/process_priority.py
    - クロスプラットフォームなプロセス優先度設定ユーティリティ（Windows の priority class と POSIX の nice 値を抽象化）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity() を提供。
    - 権限不足や未対応 OS に対するフォールバック/警告を実装。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - buy シグナルの候補選定 select_candidates（スコア降順、タイブレークは signal_rank）。
    - 等重み calc_equal_weights、スコア加重 calc_score_weights（全銘柄スコアがゼロの場合は等分配にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中上限を適用する apply_sector_cap（売却予定銘柄の除外、unknown セクターは適用除外）。
    - 市場レジームに基づく投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピングと未定義レジームのフォールバック）。
  - portfolio/position_sizing.py
    - position size / 株数計算 calc_position_sizes。
    - allocation_method として "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超えた場合のスケーリング）と残差処理（lot 単位で再配分）を実装。
    - cost_buffer による手数料・スリッページ保守的見積りをサポート。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプト。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を計算して PASS/FAIL 判定を出力。
    - デフォルト閾値: 稼働率 99.0%、成立率 90.0%、送信率 95.0%、P95 レイテンシ 200 ms。
    - 日付フィルタ --from / --to と DB パス指定 --db をサポート。既定の DB は PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。

- 研究・ファクター計算
  - research/factor_research.py
    - DuckDB 接続を用いたモメンタム・ボラティリティ等のファクター計算機能（momentum: 1m/3m/6m リターン、200 日 MA 乖離、volatility: ATR、出来高指標 など）。
    - DuckDB の SQL とウィンドウ関数で実装し、データ不足時は None を返す設計。

- DB 初期化ユーティリティ呼び出し
  - run_monitoring/run_execution 内で monitoring 用テーブルの存在を保証する init_monitoring_db(sqlite_conn) を呼び出す（冪等にテーブルを準備）。

### Changed
- なし（初回リリースのため該当なし）。

### Fixed
- なし（初回リリースのため該当なし）。

### Notes / Usage highlights
- 環境変数自動ロード
  - デフォルトでプロジェクトルートの .env を自動ロードします。OS 環境変数を上書きしたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading の分離
  - paper_trading 実行時は paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 monitoring DB と分離します。これにより履歴や検証が本番 DB に影響を与えません。
- プロセス優先度設定
  - 実行スクリプトは起動時にプロセス優先度を "high" に設定しようとします。権限がない環境では警告を出してスキップします。
- 停止制御
  - data/stop_requested.flag の存在で実行ループやエンジンの停止をトリガーします（手動での停止運用に使用）。
- Config/Validation
  - validate_config により本番運用前に設定ミスを検出可能。PyYAML がない場合は YAML 検証はスキップされます（警告表示）。
- API トークン・シークレット
  - config_setup により .env を対話的に作成できます。生成した .env は絶対に Git にコミットしないでください。

---

今後の予定（例）
- Execution/Monitoring コンポーネントの E2E テスト、Broker クライアント実装の拡充、ログ/メトリクス統合、リトライ/サーキットブレーカーの強化等を予定しています。

（注）本 CHANGELOG は提供されたソースコードから実装意図を推測して作成しています。実際の振る舞い・外部モジュール（BrokerClientFactory、ExecutionEngine、SystemMonitor、init_monitoring_db 等）の詳細は該当ファイル実装に依存します。