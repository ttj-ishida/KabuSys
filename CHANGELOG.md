CHANGELOG
=========

すべてのリリースは "Keep a Changelog" 形式に準拠し、セマンティックバージョニングを使用します。
このファイルは日本語で記載しています。

[Unreleased]
------------

- （未リリースの変更はここに記載）

[0.1.0] - 2026-04-20
-------------------

初期リリース。

Added
- 実行・監視用の起動スクリプトを追加
  - run_execution: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、Paper Trading 用 SQLite（data/paper_trading.db）を利用する仕組みをサポート。
  - run_monitoring: SystemMonitor のポーリングループを起動するスクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能（デフォルト 60 秒）。停止は data/stop_requested.flag を検出して行う。
- 設定関連ツールを追加
  - config_setup: 対話式 .env 作成/更新ウィザード（.env のテンプレート生成・保存機能）。
  - validate_config: .env と config/*.yaml の起動前検証 CLI。--strict オプションで警告をエラー扱いにできる。
- 設定管理モジュール (kabusys.config)
  - .env 自動読み込み機能（プロジェクトルートを自動検出して .env / .env.local を読み込む）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを強化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメント処理など）。
  - Settings クラスで多数の環境変数を型安全に提供（DB パス、ログレベル、Paper Trading 用設定、監視閾値など）。値検証（有効な列挙値チェックや必須変数チェック）を実装。
- ロギング・プロセスユーティリティ
  - utils.logging_setup: stdout への StreamHandler と 日次ローテーションする TimedRotatingFileHandler をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils.process_priority: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定ユーティリティを追加。権限不足や未対応 OS を考慮して安全にスキップする。
- ポートフォリオ構築ライブラリ (kabusys.portfolio)
  - portfolio_builder: 候補選定（スコア降順・タイブレーク）、等重/スコア重み算出を実装。
  - position_sizing: 複数の配分方式（risk_based / equal / score）に対応。単元株（lot_size）での丸め、max_position_pct / max_utilization による上限、cost_buffer を使った保守的コスト見積り、合計投資額が利用可能現金を超える際のスケールダウンと再配分ロジックを実装。
  - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装。unknown セクターは制限対象外として扱うなどの挙動を明記。
- 解析/リサーチ
  - research.factor_research: DuckDB を用いて定量ファクター（モメンタム / MA200 / ATR / 流動性 等）を計算するための下地を追加（prices_daily / raw_financials を参照する設計）。（実装の一部は継続中）
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。システム稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを集計し PASS/FAIL 判定を行う。デフォルトの DB は data/paper_trading.db。閾値はソース内で定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。

Changed
- データベース接続/初期化の挙動
  - run_monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視テーブルを初期化する（init_monitoring_db を実行）。
  - run_execution は paper_trading 環境時に paper_sqlite_path を使用して本番 DB と分離。いずれも duckdb への接続を行う。
- ログ出力の統一
  - すべての起動スクリプトで setup_logging を呼び出すことを想定。ログレベル解決順とログディレクトリ解決順を明文化。
- .env のロード戦略
  - OS 環境変数を保護する仕組み（protected set）を導入し、.env.local を上書き可能にするが OS 環境変数は上書きしない。

Fixed
- 環境変数の安全な取得
  - Settings._require により必須環境変数未設定時は明示的に ValueError を発生させて早期検出可能に。
- ログハンドラの二重設定防止
  - setup_logging で既存ハンドラを flush/close してからクリアすることで多重登録を防止。
- process_priority / cpu_affinity の失敗時の安全ハンドリング
  - 権限不足や未対応 API に対して警告を出し、処理を継続するように改善。

Notes / Usage Highlights
- 起動フラグ/停止制御
  - run_execution / run_monitoring ともに data/stop_requested.flag を監視して安全に停止できる。run_execution は data/execution.pid に PID を保存する仕組みを想定（Engine による）。
- 環境変数による挙動制御
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数、デフォルト 60）
  - PAPER_FILL_MODE（paper trading の約定方式: instant / partial / never / reject）
  - PAPER_TRADING_SQLITE_PATH（Paper Trading 用 DB のパス）
  - KILL_FLAG_CLEAR_ON_START（本番での自動 kill flag クリアの危険性について注意喚起）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動 .env ロードを無効化可能
- validate_config による起動前検証を推奨
  - 必須環境変数や config/*.yaml の存在・パースを検証し、本番 (KABUSYS_ENV=live) 向けの追加警告を行う。

Acknowledgements
- 初期実装段階のため、外部依存（psutil, duckdb, PyYAML 等）の有無によって一部機能の検査や挙動が変わります。ドキュメントやサンプル .env（.env.example）を参照のうえ環境を整えてください。

署名
- KabuSys チーム