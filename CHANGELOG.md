Keep a Changelog に準拠した CHANGELOG.md（日本語、コードから推測）

すべての変更はソースコードの内容から推測して記載しています。実際のコミット履歴とは差異がある可能性があります。

## [0.1.0] - 2026-04-20

### Added
- 実行用スクリプトを追加
  - run_execution.py：ExecutionEngine 起動スクリプト。KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用して paper_trading 用 DB（data/paper_trading.db、環境変数で上書き可）に記録する。実行中は停止フラグ（data/stop_requested.flag）を監視して安全に停止可能。
  - run_monitoring.py：SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は本番の sqlite_path を用いる。

- 設定・環境管理
  - config.py：.env ファイル自動読み込み機構（プロジェクトルート検出 .git / pyproject.toml 基準）、行パーサの実装（コメント、export プレフィックス、引用符・エスケープ対応）、Settings クラス（環境変数の型変換・妥当性検査）を追加。
  - config_setup.py：対話式ウィザードで .env を作成・更新する CLI を追加（secret マスク・デフォルト値・選択肢対応）。.env の読み書きロジックを提供。
  - validate_config.py：起動前に .env や config/*.yaml の検証を行う CLI を追加。--strict オプションをサポート（警告を FAIL 扱いにできる）。PyYAML 未インストール時には YAML 検証をスキップして警告表示。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py：統一的なロギング設定ユーティリティを追加。StreamHandler（stdout）と日次ローテートの TimedRotatingFileHandler をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで動作。
  - utils/process_priority.py：Windows / POSIX（Linux, macOS 等）対応のプロセス優先度設定と CPU affinity 設定ユーティリティを追加。例外時は警告でスキップする安全設計。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py：候補銘柄選定（スコア降順）と等分配・スコア加重配分の重み計算を追加。全スコアが 0 の場合は等分配にフォールバック。
  - portfolio/risk_adjustment.py：セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を追加。レジーム不明時のフォールバック挙動やログ出力あり。
  - portfolio/position_sizing.py：株数計算ロジック（risk_based、equal、score ベース）、単元株（lot_size）丸め、per-stock 上限・aggregate cap のスケーリング、cost_buffer による保守的見積り、残差処理による端数配分ロジックを実装。
  - portfolio パッケージのエクスポート（select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier）。

- 解析・ツール
  - tools/paper_verification_report.py：Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を計算して PASS/FAIL 判定を出力。閾値（稼働率 99%、成功率 90% 等）を定義し CLI 引数で期間指定や DB パス指定をサポート。P95 算出ユーティリティ実装。

- データベース初期化
  - monitoring.monitoring_db.init_monitoring_db を起動時に呼び出して監視テーブルの存在を保証（冪等）。

### Changed
- ログ出力の出力先ポリシー
  - logging_setup でコンソール出力は stderr ではなく stdout を採用（Task Scheduler / cron 等での一本化を想定）。
  - ファイルハンドラ作成に失敗した場合でも StreamHandler にフォールバックする堅牢化を実施。

- .env 読み込みの優先度と保護
  - 自動ロード順序を OS 環境変数 > .env.local > .env に明示。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env の自動ロード時、既存 OS 環境変数は protected として上書きされないよう保護。

- 設定値の妥当性チェックを厳密化
  - Settings.paper_fill_mode に有効値チェックを追加（"instant" | "partial" | "never" | "reject"）。無効値は ValueError を送出。
  - Settings.env / Settings.log_level に対する妥当性チェックを実装し、不正値は明確なエラーメッセージを発生させる。

- run_monitoring/run_execution の起動フロー改善
  - 起動時に set_process_priority("high") を呼び出し、優先度を上げる処理を最初に実行するよう変更。
  - run_execution は paper_trading モード時に専用の SQLite（paper_sqlite_path）を使用して本番 DB と完全に分離。

### Fixed
- 環境変数パースの改善
  - export プレフィックス、引用符付き値（バックスラッシュエスケープ対応）、インラインコメントの扱いを正しくパースするよう修正。空行やコメント行のスキップを実装。

- モニタリングループの安定性
  - MONITOR_POLL_INTERVAL の値が 1 未満あるいは不正な場合にデフォルト値（60 秒）へフォールバックする検証を追加し、time.sleep に渡した際の ValueError を回避。

- process_priority の安全化
  - psutil による優先度設定で AccessDenied 等の例外が出た場合は警告ログを出して処理を継続するよう修正（起動失敗を防止）。

- データアクセスの例外耐性
  - paper_verification_report の各クエリ実行で sqlite3.OperationalError を捕捉して、テーブルが存在しない場合にデフォルト値で処理を継続するように堅牢化。

### Security
- .env ファイルの取り扱いに関する注意喚起を config_setup の生成ファイルヘッダに明記（.env を絶対に Git にコミットしないこと）。

### Notes / Internal
- research/factor_research.py はファクター計算（Momentum、Value、Volatility、Liquidity）を実装する設計が導入されているが、コードは部分的（ファイル末端で切れている断片）であり、計算実装の続きを含めた追加実装が必要。
- ExecutionEngine / BrokerClientFactory / OrderManager / RiskManager 等の詳細ロジックはソース内に依存関係として存在。起動スクリプトはそれらの初期化フロー（リスク設定、reconciler、pid ファイル管理等）を組み立てている。

---

今後の想定タスク（推奨）
- factor_research の未完実装部分の完成（calc_momentum 等の全実装）。
- ユニットテストの追加（.env パーサ、position_sizing の集約スケールロジック、apply_sector_cap の境界条件など）。
- ドキュメント（PortfolioConstruction.md 等）との整合性確認とサンプル設定ファイルの提供。
- CI での自動静的解析・型チェック（mypy/flake8 等）の導入。