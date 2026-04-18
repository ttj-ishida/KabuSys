# Changelog

すべての重要な変更は Keep a Changelog に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース。プロジェクトの基本機能とユーティリティ群を実装しました。

### Added
- 基本バージョン情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 設定管理
  - `kabusys.config.Settings` クラスを実装。
    - .env/.env.local の自動読み込み（OS環境変数優先、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - 複雑な .env パースをサポート（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱い）。
    - 多数の設定プロパティを提供（J-Quants、kabuAPI、LINE、DuckDB/SQLite パス、Paper Trading 関連、監視閾値、環境種別など）。
    - `paper_fill_mode` の検証（有効値チェック）や `env` の検証を実施。

- 環境設定ウィザード CLI
  - `kabusys.config_setup` を追加。
    - 対話式ウィザードで .env を初期作成・更新できる。
    - シークレット項目はマスク表示、既存値の再利用、保存確認機能を実装。

- 設定検証 CLI
  - `kabusys.validate_config` を追加。
    - 必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML がある場合）パース検証。
    - `--strict` オプションで警告を失敗扱いにできる。

- 起動スクリプト
  - `run_execution.py`
    - ExecutionEngine の起動フローを実装。
    - Paper Trading 環境時は専用 SQLite（`PAPER_TRADING_SQLITE_PATH` / `data/paper_trading.db`）を使用し本番 DB と分離。
    - BrokerClientFactory によるブローカーの生成、OrderRepository、OrderManager、RiskManager、Reconciler 組立て、ExecutionEngine のスレッド実行/停止ロジックを実装。
    - 停止フラグ（data/stop_requested.flag）検出と PID ファイル（data/execution.pid）対応。
  - `run_monitoring.py`
    - SystemMonitor の初期化とポーリングループを実装。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒、値検証あり）。
    - 監視は環境にかかわらず本番用の sqlite_path を使用する旨を実装。
    - 停止フラグ検出でループを終了し、例外時はログ出力して次回ポーリングに継続。

- ロギングユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。
    - LOG_DIR / LOG_LEVEL の解決順、既存ハンドラのクリーンアップ、ログ出力失敗時のフォールバックを実装。

- プロセス優先度/CPU 固定ユーティリティ
  - `kabusys.utils.process_priority` を追加。
    - `set_process_priority(level)` で Windows / POSIX を吸収して優先度設定（高/通常/低）。
    - `set_cpu_affinity(cpu_count)` で最初の N コアにピン留め（利用不可時は警告でスキップ）。
    - 権限不足や未対応環境に対する安全なフォールバックを実装。

- ポートフォリオ構築モジュール
  - `kabusys.portfolio`
    - `portfolio_builder`:
      - 候補選定（score 降順、signal_rank でタイブレーク）、等重み・スコア加重の重み生成。スコア合計が 0 の場合は等配分へフォールバック（WARNING）。
    - `risk_adjustment`:
      - セクター集中制限（apply_sector_cap）: 既存保有比率に基づき新規候補を除外（unknown セクターは除外対象外）。
      - レジーム乗数（calc_regime_multiplier）: "bull"/"neutral"/"bear" に対応、未知値は警告して 1.0 にフォールバック。
    - `position_sizing`:
      - 複数の配分方式（risk_based, equal, score）に対応した株数算出ロジック。
      - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash に基づくスケーリング）、cost_buffer を考慮した保守的見積を実装。
      - 価格欠損時のスキップやログ出力、スケールダウン時の端数処理（残差分配）を実装。

- Execution まわりのリスク管理等
  - `run_execution` 内で `RiskManager` にデフォルト `RiskConfig` を設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker など）。
  - `initial_portfolio_value` をブローカの利用可能現金から初期化。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を追加。
    - Paper Trading DB（デフォルト: data/paper_trading.db）からシステム安定性、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計してレポート出力。
    - P95 計算実装、閾値に基づく PASS/FAIL 判定（稼働率、成功率、送信率、P95 レイテンシなど）。
    - CLI オプションで期間指定（--from/--to）、DB パス指定（--db）。

- 研究用ファクター計算フレームワーク
  - `kabusys.research.factor_research` を追加（DuckDB 接続を受け、prices_daily / raw_financials を参照する想定）。
    - モメンタム / Value / Volatility / Liquidity 系ファクターの計算方針を定義（関数実装は進行中、設計ドキュメントへの参照あり）。

### Changed
- N/A（初回リリースのため既存変更はなし）

### Fixed
- 入力値・環境変数の堅牢化
  - `MONITOR_POLL_INTERVAL` の負値や非整数入力時にデフォルトへフォールバックして警告を出す。
  - `PAPER_FILL_MODE` の不正値検出時に ValueError を送出。
  - .env 読み込み失敗時に警告を出して処理継続。
  - ログディレクトリ作成失敗時にファイル出力をスキップしてコンソールログのみで継続。

### Security
- 秘密情報（API トークン / パスワード）は .env に記載する設計。`config_setup` の注意書きで .env を Git にコミットしないよう明記。

---

注記:
- 本 CHANGELOG はコードベースから推測して作成しています。実際のリリースノートとして用いる場合は、変更点の正確な反映および日付・担当者等の追記を推奨します。