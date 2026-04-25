# CHANGELOG

すべての notable な変更点を記録します。フォーマットは Keep a Changelog に準拠します。  

現在のリリース履歴:

- Unreleased は将来の変更のために残してあります。
- 初回リリースは v0.1.0（パッケージ版の __version__ に一致）です。

## [Unreleased]

### Added
- （今後の変更をここに記載）

---

## [0.1.0] - 2026-04-25

初回公開リリース。以下の主要機能・ユーティリティを追加しました。

### Added
- 全体
  - パッケージ初期バージョンを追加（kabusys/__init__.py: __version__ = "0.1.0"）。
  - プロジェクトルート自動検出機能を実装（.git または pyproject.toml を基準）し、.env 自動読み込みのベースを構築（kabusys.config）。
  - .env の読み書き・対話式ウィザードによる初期設定ツールを追加（kabusys.config_setup）。
  - 設定検証 CLI を追加。環境変数や config/*.yaml の存在・基本妥当性チェックを実行可能（kabusys.validate_config）。
  - ログ設定ユーティリティを実装。stdout 出力と日次ローテートのファイル出力を統一的に設定（kabusys.utils.logging_setup）。
  - プロセス優先度および CPU affinity 設定ユーティリティを追加（kabusys.utils.process_priority）。
  - 実行エントリスクリプトを追加:
    - 実行エンジン起動スクリプト（run_execution.py）。KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite を使用して本番 DB と分離し、MockBrokerClient を利用する想定。
    - 監視 (SystemMonitor) 起動スクリプト（run_monitoring.py）。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する挙動を明確化。
  - 停止管理: プロジェクト内 data ディレクトリの stop_requested.flag による停止フラグ検知を run scripts に導入。
  - ExecutionEngine 起動時の PID ファイル管理（data/execution.pid）をサポート。

- 設定（kabusys.config）
  - Settings クラスを実装して環境変数を型付きに取得できるようにした（データベースパス、ログレベル、KABUSYS_ENV 判定、paper_trading 用設定等）。
  - PAPER_FILL_MODE の妥当性検査（instant/partial/never/reject）を実装。
  - DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）、PID/KILL フラグ関連、閾値（CPU/MEM/DISK）等のプロパティを実装。
  - 自動 .env 読み込みは OS 環境変数を保護しつつ .env と .env.local を順序付けて読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応）。

- ポートフォリオ構築（kabusys.portfolio）
  - 銘柄選定・重み計算モジュール:
    - select_candidates: スコア降順 + tie-break で候補抽出。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分。スコアが全て 0 の場合は等分配にフォールバック。
  - リスク調整モジュール:
    - apply_sector_cap: セクター別の既存保有割合に基づく候補除外ロジック（unknown セクターは無視）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear とフォールバック）。
  - 株数決定・資金配分（position_sizing）:
    - calc_position_sizes: risk_based / equal / score の allocation_method に対応。単元株丸め、per-stock 上限、aggregate cap、コストバッファを考慮したスケーリングと端数処理を実装。

- 取引・監視関連
  - 監視用 DB 初期化ユーティリティ（init_monitoring_db）を使用するようにスクリプトを統合（monitoring 側と execution 側で冪等に初期化）。
  - ExecutionEngine の依存コンポーネント組立てを run_execution で実装（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の生成フローを定義）。
  - RiskManager のデフォルト設定を導入（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 関連, initial_portfolio_value を broker.get_available_cash() から取得）。

- ツール（kabusys.tools）
  - Paper Trading 検証レポート生成スクリプトを追加（kabusys.tools.paper_verification_report）。
    - 検証指標: 稼働率 (uptime)、注文成功率 (fill rate)、送信率 (send rate)、P95 レイテンシ 等。
    - CLI で期間指定 (--from / --to) と DB パス指定 (--db) が可能。デフォルトは PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。
    - 各指標の閾値を定義して PASS/FAIL 判定を行う（稼働率 >= 99%、fill_rate >= 90% 等）。

- 研究（kabusys.research）
  - ファクター計算モジュールを追加（factor_research）。DuckDB 接続を受け取り prices_daily / raw_financials テーブルから Momentum / Value / Volatility / Liquidity 系ファクターを算出する設計（モジュール冒頭と calc_momentum の形で実装開始）。（一部実装は継続中の箇所あり）

### Changed
- N/A（初回リリースのため過去との互換性変更はなし）

### Fixed
- N/A（初回リリース）

### Security
- .env を絶対にリポジトリにコミットしない旨をドキュメント化（config_setup がヘッダコメントで警告）。
- 対話式ウィザードではシークレット項目をマスク表示。

### Notes / Usage 注意事項
- 実行スクリプト:
  - 監視: python -m kabusys.run_monitoring（MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能。デフォルト 60 秒）
  - 実行エンジン: python -m kabusys.run_execution（KABUSYS_ENV による paper_trading モード判定、停止フラグは data/stop_requested.flag）
- 環境変数の自動ロード:
  - プロジェクトルートが検出できる場合に限り .env/.env.local を自動で読み込みます。
  - テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログ:
  - デフォルトで logs/<app_name>.log に日次ローテートで出力（最大 30 日分）。LOG_DIR 環境変数で変更可能。作成に失敗した場合は stdout のみで継続。
- Paper Trading:
  - paper_trading モードでは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を用いるため、本番 DB と完全分離可能。
  - PAPER_FILL_MODE により MockBrokerClient の約定挙動を制御（instant/partial/never/reject）。

### Breaking Changes
- 初回リリースのため破壊的変更はありません。

---

今後のリリースでは次を予定しています（例）:
- factor_research のファクター実装完了とユニットテスト追加
- ExecutionEngine / Monitoring 周りのエラーハンドリング強化と監視メトリクス拡張
- 単体テストと CI 設定の追加

ご要望があれば、リリースノートの粒度（もっと詳細なコミット毎／機能毎の分割）を調整できます。