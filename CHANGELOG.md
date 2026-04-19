# Changelog

すべての注目すべき変更点をこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-19

### Added
- パッケージ初期リリース。基本的な実行・監視・構成管理・ポートフォリオ構築・ユーティリティ群を追加。
- アプリケーション情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
  - パッケージ公開用の `__all__` を設定。

- 設定管理
  - Settings クラスを実装し、環境変数から各種設定（J-Quants / kabuステーション / DB パス / モード判定 /閾値 等）を取得可能に。
  - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動読み込みを無効化可能。
  - 環境変数パーサを実装:
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理等。
    - 値の検証（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL など）を行い不正値は例外を送出。
  - `settings` インスタンスをモジュールレベルで提供。

- 設定ツール / 検証
  - 対話式ウィザード `kabusys.config_setup.run_wizard`（CLI: python -m kabusys.config_setup）を追加。`.env` の初期生成・更新を支援。
  - `.env` の読み書きユーティリティを実装（既存値の読み取り、確認、書き込みテンプレート）。
  - 設定検証 CLI `kabusys.validate_config` を実装（python -m kabusys.validate_config）。必須環境変数・KABUSYS_ENV・ログレベル・DB パス・config/*.yaml の存在とパース（PyYAML 利用可能な場合）・本番時のガードチェック等を実施。`--strict` オプションで警告も失敗扱いに可能。

- 起動スクリプト
  - 実行エンジン起動スクリプト `run_execution.py` を追加:
    - 起動時にプロセス優先度を設定（高優先度）。
    - 環境が `paper_trading` の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
    - Broker クライアント生成（BrokerClientFactory）、OrderRepository/OrderManager/RiskManager/Reconciler 組み立て、ExecutionEngine の起動と停止フラグ（data/stop_requested.flag）監視、PID ファイル管理を実装。
    - RiskConfig のデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）を設定。initial_portfolio_value は broker.get_available_cash() から取得して初期化。
  - 監視ループ起動スクリプト `run_monitoring.py` を追加:
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は環境に関係なく本番向けの sqlite_path を使用する旨を明示。
    - SystemMonitor の初期化、sqlite/duckdb 接続、stop フラグ監視、例外時のロギングと継続を実装。
    - 起動時にプロセス優先度を設定。

- データベース初期化
  - `init_monitoring_db` を利用して監視テーブルが存在することを保証（冪等な初期化）。

- ロギング / プロセス制御ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を実装:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定。
    - ログレベル・ログディレクトリは引数・環境変数・デフォルトの順で解決。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - `kabusys.utils.process_priority` を追加:
    - クロスプラットフォームでプロセス優先度（high/normal/low）を設定。Windows・POSIX（Linux/Mac/FreeBSD）を考慮。
    - CPU affinity を指定コア数に固定する set_cpu_affinity を実装。失敗時は警告を出力してスキップ。

- ポートフォリオ構築 API（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - select_candidates: BUY シグナルをスコア降順・タイブレークは signal_rank で選択。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコアに比例した重み。全銘柄のスコアが 0.0 の場合は等金額配分にフォールバックして警告。
  - `kabusys.portfolio.risk_adjustment`:
    - apply_sector_cap: 既存保有のセクター比率が上限を越えている場合、当該セクターの新規候補を除外（"unknown" セクターは上限適用外）。当日売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（"bull"=1.0, "neutral"=0.7, "bear"=0.3）、未知レジームは 1.0 にフォールバック。
  - `kabusys.portfolio.position_sizing`:
    - calc_position_sizes: 複数の割当方式をサポート（"risk_based", "equal", "score"）。lot_size（単元）丸め、1銘柄上限、aggregate cap（available_cash 超過時のスケールダウンと端数調整）、cost_buffer（手数料・スリッページ見積り）を考慮。価格欠損時はスキップする安全設計。
    - 内部的に lot 単位での丸めや残差配分ルールを実装。

- 分析 / リサーチ
  - `kabusys.research.factor_research` を追加（DuckDB を用いるファクター計算モジュール）。
    - モメンタム等の定量ファクター（1M/3M/6M リターン、MA200乖離、ATR、流動性指標等）を計画。calc_momentum のスケルトンと定数群を実装（DuckDB 接続を受けて prices_daily を参照する設計）。
    - 設計方針として DB（prices_daily / raw_financials）以外に依存しない純粋関数系を目指す。

- CLI ツール
  - Paper Trading 検証レポート生成スクリプト `kabusys.tools.paper_verification_report` を追加:
    - SQLite（paper_trading DB）からシステム稼働率・注文成功率・送信率・P95 レイテンシ・リスク却下数等を集計してレポート出力。
    - 閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定を実装。
    - 日付フィルタ（--from/--to）と DB パス指定（--db / 環境変数）をサポート。DB が存在しない場合のエラーメッセージを出力。
    - P95 計算ユーティリティを実装。

### Changed
- 監視 (monitoring) のデータベース接続動作を明確化:
  - run_monitoring は環境に関係なく Settings.sqlite_path（本番用パス想定）を使用するよう設計されていることをドキュメント化（環境による切替は行わない）。
- ログ出力先のデフォルトを stdout に統一（StreamHandler は stdout を使用）。ファイルハンドラはログディレクトリ作成に成功した場合のみ有効。

### Fixed
- MONITOR_POLL_INTERVAL のパースロジック:
  - 不正な値や 0/負数が指定された場合にデフォルト (60 秒) にフォールバックし、警告を出すように実装（time.sleep に不正値を渡さない対策）。

### Notes / TODO
- portfolio.position_sizing の価格欠損時の挙動に関する注記（price が 0.0 の場合に過少見積りとなる問題）を残し、将来的には前日終値や取得原価でのフォールバックを検討。
- research.factor_research の実装は一部（calc_momentum 以降）が未掲載 / 開発中。完全実装と各ファクターの単体テストを今後追加予定。
- 一部モジュールは外部実装（BrokerClientFactory, ExecutionEngine, SystemMonitor 等）に依存しており、それらの詳細実装やテストは別途管理。

### Security
- なし（このリリースで重大なセキュリティ脆弱性は確認されていません）。ただし `.env` ファイルにはシークレットを含めるため、コミット禁止の旨を `.env` 書き込みテンプレートに明記。

---

将来的なリリースでは、テストカバレッジの拡大、research モジュールの完成、細かなロギング改善や監視アラート機能の追加を予定しています。