# Changelog

すべての重要な変更はこのファイルに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated / Removed / Security: 該当する場合に記載

## [Unreleased]

（現在保留中の変更はここに記載します）

---

## [0.1.0] - 2026-04-21

初回公開リリース。以下の主要機能・ユーティリティ・CLI を含みます。

### Added
- 基本アプリケーションパッケージとバージョン情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 実行エントリ / 実行関連スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）へ記録し、MockBrokerClient を使用する設計をサポート。
    - 起動時にプロセス優先度を high に設定し、停止フラグ（data/stop_requested.flag）と pid ファイル（data/execution.pid）を扱う。
    - ExecutionEngine の依存コンポーネント（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler）を組み立ててバックグラウンドスレッドで実行する。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグの検出によりループ終了。監視用 DB（SQLite）および DuckDB 接続を確立して SystemMonitor を1周期ずつ実行する。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を利用する設計。

- 設定管理
  - config.py: 環境変数 / .env 自動読み込みおよび Settings クラスを実装。  
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）により .env/.env.local をロード（OS 環境変数優先、.env.local は上書き）。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
    - .env のパースはシングル/ダブルクォート、バックスラッシュエスケープ、export プレフィックス、インラインコメント等に対応。
    - 各種設定プロパティ（J-Quants トークン、kabuAPI 設定、DB パス、監視しきい値、環境判定メソッド等）を提供し、値の妥当性チェックを実施。
  - settings オブジェクトを公開（from kabusys.config import settings）。

- 設定関連 CLI
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。  
    - 主要環境変数の質問・既存値の読み込み・マスク表示（シークレット）・保存機能を提供。
  - validate_config.py: 起動前設定検証ツールを追加。  
    - 必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、config/*.yaml の存在チェック（PyYAML があればパース検証）を行う。
    - --strict モードで警告も FAIL 扱いできる。

- ロギングユーティリティ
  - utils/logging_setup.py: 統一的なログ設定関数 setup_logging を追加。  
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app>.log）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL / 引数で上書き可能。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。

- プロセス優先度・CPU affinity ユーティリティ
  - utils/process_priority.py: set_process_priority、set_cpu_affinity を実装。  
    - Windows/Linux/macOS 等を抽象化して優先度を設定。権限不足などで失敗した場合は警告を出して安全にスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。  
    - スコアが全て 0 の場合は等金額にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。  
    - apply_sector_cap は当日売却予定の銘柄を除外する機能、unknown セクターは制限を適用しない等の挙動。
    - calc_regime_multiplier は bull/neutral/bear のマップと未定義時のフォールバックを提供。
  - portfolio/position_sizing.py: 株数計算ロジック（risk_based / equal / score）を実装。  
    - 単元株（lot_size）丸め、per-stock 上限・aggregate cap（available_cash によるスケールダウン）、cost_buffer（手数料・スリッページ見積）を考慮。
  - portfolio/__init__.py で上記関数をエクスポート。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレードのパフォーマンス/安定性検証レポート作成スクリプトを追加。  
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を算出し、PASS/FAIL を判定するしきい値を提供。
    - DB パスは引数 --db または環境変数 PAPER_TRADING_SQLITE_PATH、デフォルトは data/paper_trading.db。
    - P95 計算、日付範囲フィルタ、N/A 処理等を実装。

- 研究モジュール（ファクター計算）スケルトン
  - research/factor_research.py: Momentum / Value / Volatility / Liquidity といったファクター計算器の基礎を実装（DuckDB 使用想定）。  
    - モメンタム計算（calc_momentum）などの設計と定数を定義。DuckDB 接続を受けて prices_daily / raw_financials を参照する方針。

- DB 初期化ユーティリティ呼び出し
  - 複数の起動スクリプトで monitoring 用テーブルが存在することを保証するため init_monitoring_db(sqlite_conn) を呼び出す実装を導入（冪等）。

### Changed
- .env 読み込みポリシーの明確化（config.py）
  - 自動ロードの優先順位: OS 環境 > .env.local > .env。既存 OS 環境変数は保護される（上書き禁止）。
  - .env パーサーを堅牢化し export プレフィックスやクォート内エスケープ、インラインコメントの扱いを改善。

- ログ出力の強化
  - 全起動スクリプトから setup_logging を呼び出す運用を採用し、出力の一貫性を確保。

- Execution / Monitoring の DB 分離方針
  - paper_trading 環境では Execution は paper_trading 専用 SQLite を使用し、本番 DB とデータを分離。Monitoring は環境にかかわらず本番 sqlite_path を使用する設計で固定（監視データは一元管理する目的）。

### Fixed
- 例外・障害時の堅牢化
  - run_monitoring.py のポーリングループ内で monitor.check_once() が例外を投げてもループを継続するように例外捕捉を追加。
  - ログディレクトリ作成失敗時にファイルハンドラ作成をスキップしてもアプリケーションが継続するように処理を調整。

### Notes / その他
- セキュリティ注意
  - .env ファイルにはシークレット（API トークン等）を保存しないか、必ず Git から除外することを README で明示することを想定（config_setup.py にも警告コメントを含む）。
- 将来の拡張箇所（TODO）
  - position_sizing: 銘柄毎の lot_size をサポートするためのマスタ拡張を計画。
  - risk_adjustment.apply_sector_cap: price 欠損時のフォールバック価格（前日終値や取得原価）の導入を検討。
  - research/factor_research の完全実装（SQL クエリと集計ルーチンの追加）。
  - ExecutionEngine の Execution/Risk/Order 周りは外部ブローカー対話のテストカバレッジ強化が必要。

---

今後のリリースでは、テストカバレッジ、ドキュメント（API 仕様・設計ドキュメントの整備）、および research モジュールの完成、ExecutionEngine の安定化（フェイルセーフ・再試行ポリシー）の強化を優先予定です。必要があればこの CHANGELOG を更新して更に細かい差分を記録します。