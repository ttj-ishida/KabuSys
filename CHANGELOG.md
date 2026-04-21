# Changelog

すべての重要な変更点をここに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。

全般:
- バージョン番号はパッケージルートの `__version__` に従います。

## [0.1.0] - 2026-04-21

### Added
- 初期リリース。KabuSys の基本機能群を追加。
- 起動スクリプト
  - `run_execution.py`：ExecutionEngine を起動するエントリポイント。プロセス優先度設定、SQLite / DuckDB 接続、Broker クライアント生成、OrderManager / RiskManager / Reconciler の組み立て、スレッドでのエンジン実行、停止フラグ（data/stop_requested.flag）と PID ファイル管理に対応。
  - `run_monitoring.py`：SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数で間隔上書き、停止フラグ検知、例外捕捉、KeyboardInterrupt の扱い。
- 設定管理 / CLI
  - `config.py`：.env 自動読込（`.env` → `.env.local`、OS 環境変数保護）、.env パース（export プレフィックス、クォート／エスケープ、インラインコメント対応）、Settings クラス（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視閾値 等のプロパティ）を追加。`KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化をサポート。
  - `config_setup.py`：対話式ウィザードで `.env` を生成・更新する CLI。シークレット入力のマスク表示、選択肢サポート、保存確認を実装。
  - `validate_config.py`：設定検証 CLI。必須環境変数・環境値（KABUSYS_ENV/LOG_LEVEL 等）・DB パスの存在確認、`config/*.yaml` の存在/パースチェック（PyYAML が無い場合は警告）、`--strict` フラグによる警告を FAIL 扱いにするモードを提供。
- ポートフォリオ構築モジュール（純粋関数群）
  - `portfolio.portfolio_builder`：
    - select_candidates：スコア降順で候補選定（同点時は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights：等金額配分・スコア加重配分（スコア合計 0 の場合は等金額にフォールバック）。
  - `portfolio.risk_adjustment`：
    - apply_sector_cap：セクター集中を抑えるフィルタ（sell_codes による売却予定銘柄除外、unknown セクターは除外しない）。
    - calc_regime_multiplier：市場レジームに応じた投下資金乗数（bull/neutral/bear）。
  - `portfolio.position_sizing`：
    - calc_position_sizes：allocation_method（risk_based / equal / score）に基づく株数算出、単元株丸め（lot_size）、1 銘柄上限・利用率上限、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ見積り）を考慮した安全な配分ロジック。
- ユーティリティ
  - `utils.logging_setup`：統一ログ設定。stdout 出力（StreamHandler）および日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。LOG_DIR 解決、既存ハンドラのクリア、ログレベル解決順（引数 → 環境変数 → デフォルト）を実装。ファイル出力に失敗した際のフォールバック処理あり。
  - `utils.process_priority`：Windows / POSIX の差分を吸収したプロセス優先度設定と CPU affinity 設定。権限不足や未サポート環境での安全なフォールバックと警告出力を実装。
- ツール
  - `tools.paper_verification_report`：Paper Trading 用の検証レポート生成スクリプト。稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）を計算し PASS/FAIL を判定。PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションで DB 指定が可能。
- 監視・実行系の DB 初期化
  - `monitoring.monitoring_db.init_monitoring_db`（起動スクリプトから利用）により、監視用テーブルの冪等な初期化を呼び出す（起動時の安全ガード）。
- リサーチ
  - `research.factor_research`：DuckDB を用いたファクター計算モジュール（モメンタム／MA200乖離／ATR／流動性等の設計を記載）。prices_daily / raw_financials を参照する設計。関数のインターフェースと定数が導入済み（実装途中の箇所あり）。

### Changed
- （初期リリースのためなし）

### Fixed
- （初期リリースのためなし）

### Notes / Important behaviors
- Execution と Monitoring は DB の扱いが分離されている：
  - Execution は KABUSYS_ENV=paper_trading の場合、Paper Trading 用の SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離。
  - Monitoring は実行環境に関わらず監視用 sqlite_path（デフォルト data/monitoring.db）を使用。
- .env ローダーは既存の OS 環境変数を保護する設計（protected set）で、`.env.local` による上書きもサポート。
- ログは stdout を主に使用する設計（cron / Task Scheduler からの一元化を想定）。
- Process priority / CPU affinity の設定は権限不足や未サポート環境で例外を起こさず警告でフォールバックする。

## 未定義 / 今後の予定
- factor_research の完全実装（ファクター計算ロジックの続き）。
- 各コンポーネントの単体テスト・統合テストの追加（現在コードベースに記載なし）。
- 銘柄別単元（lot_size）対応の拡張（コメントに将来対応の旨あり）。

<!--
参考: Keep a Changelog — https://keepachangelog.com/ja/1.0.0/
-->
