# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

なお、本 CHANGELOG は提示されたコードベースの内容から推測して作成しています（ソースコード中のコメント・挙動・デフォルト値等を基に要約）。実際のコミット履歴ではありません。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-25

初回リリース。本リリースでは自動売買システム KabuSys のコア機能群と関連 CLI / ユーティリティを実装しています。

### Added
- 基本パッケージ構成を追加
  - パッケージ: kabusys（バージョン情報: __version__ = "0.1.0"）
  - サブパッケージ: portfolio, execution, monitoring, utils, tools, research, config などのモジュール群を実装。

- 実行用エントリスクリプト
  - run_execution.py
    - ExecutionEngine を起動するスクリプト。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - stop フラグ（data/stop_requested.flag）・pid ファイル管理・スレッドでの Engine 実行と安全な停止処理を実装。
    - Execution 用のデフォルト RiskConfig を定義（max_position_pct, max_utilization, rate_limit_per_sec など）。

  - run_monitoring.py
    - SystemMonitor を定期ポーリングするスクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトへフォールバックして警告ログ出力。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用（明示的に分離されていないがコードで意図が示されている）。
    - stop フラグ（data/stop_requested.flag）検知でループを終了。

- 設定・環境変数まわり
  - config.py / Settings クラスを追加
    - .env 自動読み込み機能（プロジェクトルートを .git / pyproject.toml で探索）。
    - .env の読み込み順序: OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 高度な .env パーサ (.env 行の export 対応、クォート文字列のエスケープ処理、インラインコメントハンドリング等) を実装。
    - 多数のプロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, 各種閾値、KABUSYS_ENV 判定ロジック等）。
    - PAPER_FILL_MODE 値検証（instant/partial/never/reject のみ許容）。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新する CLI。
    - 多数の設定項目をプロンプトで扱い、シークレット値はマスクして表示、保存時のテンプレート出力を実装。

  - validate_config.py
    - 設定の検証 CLI。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在/パースチェック（PyYAML の有無で挙動分岐）、本番環境用のガードチェック（LINE 通知設定や KILL_FLAG_CLEAR_ON_START など）を実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを提供。
    - stdout への StreamHandler と日次ローテーション付き TimedRotatingFileHandler （デフォルト logs/<app_name>.log、30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決やディレクトリ作成失敗時のフォールバックを実装。

  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX 系）でプロセス優先度（nice / Windows priority class）を設定するユーティリティ。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供（アクセス権限がない場合は警告を出してスキップ）。

- ポートフォリオ構築ライブラリ（純粋関数群、DB参照なし）
  - portfolio/portfolio_builder.py
    - 銘柄選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア合計が 0 の場合は等配分にフォールバックして警告出力。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（売却予定銘柄を除外可能、"unknown" セクターは制限除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を実装（未知レジームは 1.0 にフォールバック）。

  - portfolio/position_sizing.py
    - 株数決定ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、per-stock 上限・aggregate cap、cost_buffer（手数料・スリッページ見積り）を考慮したスケーリング処理を実装。
    - aggregate スケールダウン時の端数配分アルゴリズム（fractional remainder に基づく lot 単位の追加配分）を実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の SQLite（PAPER_TRADING_SQLITE_PATH）から統計を抽出して検証レポートを生成する CLI。
    - 指標: 稼働率（uptime）, 注文成功率（fill rate）, 送信率（send rate）, API レイテンシ（avg/max/P95）等。
    - デフォルト閾値を定め、Pass/Fail を判定して出力。

- monitoring データベース初期化ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db を参照して起動時に監視テーブルの存在を保証する（冪等）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （本リリースで特記すべきセキュリティフィックスはなし。ただし .env は絶対にコミットしない旨を config_setup のヘッダに明示）

### Notes / Implementation details / TODO（コードから推測）
- research/factor_research.py はモメンタム等ファクター計算の実装を開始しているが、ソースが途中で切れている（calc_momentum の実装途中）。研究系モジュールは今後の拡張が想定される。
- run_execution/run_monitoring は stop フラグ（data/stop_requested.flag）で安全停止する仕組みを採用しているため、運用時は Stop/Kill 周りのファイル位置・運用手順に注意すること。
- process_priority や CPU affinity 操作は権限やプラットフォーム依存で失敗する可能性があるため、失敗時に警告ログでスキップする設計となっている。
- position_sizing 等の計算は lot_size を全銘柄共通と仮定している（将来的に銘柄別 lot サイズの導入を想定した TODO コメントあり）。
- Logging のファイルハンドラ作成に失敗した場合でもコンソール出力のみで継続するフォールバックを実装しており、コンテナ等でログディレクトリ権限に注意。

---

以上。リリース後の変更（バグ修正・機能追加）が出た場合は、本ファイルを更新して Unreleased → 次バージョンのリリースノートを追加してください。