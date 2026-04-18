# Changelog

すべての重要な変更点をここに記録します。  
このファイルは "Keep a Changelog" の形式に従います。比較的初期のリリースを想定して、コードベースの内容から機能追加や設計方針を推測して記載しています。

フォーマット:
- Unreleased: 現在開発中 / 既知の TODO や注意点
- 各バージョン: 追加 (Added)、変更 (Changed)、修正 (Fixed)、非推奨 (Deprecated)、削除 (Removed)、セキュリティ (Security)

## [Unreleased]

### Notes
- 一部のモジュールに将来的に改善すべき箇所（TODO コメントあり）。
  - portfolio.risk_adjustment.apply_sector_cap: price が欠損した場合のフォールバック価格の取り扱いを検討する必要あり。
  - portfolio.position_sizing: 銘柄別の lot_size をサポートする拡張が検討されている。
- 自動 .env ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

---

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーション初期実装（バージョン情報: `kabusys.__version__ = "0.1.0"`）。
- 設定管理
  - `kabusys.config.Settings`：環境変数ベースの設定取得クラスを実装。J-Quants / kabuステーション / LINE / DB パス / 監視しきい値 / 実行環境 (development, paper_trading, live) などをプロパティで提供。
  - 自動 .env 読み込み機能：プロジェクトルート（.git または pyproject.toml を探索）を起点に `.env` と `.env.local` を適切な優先度で読み込む。OS 環境変数は保護される。
  - .env パースはクォートやエスケープ、インラインコメントの扱いに対応。
- 環境設定ウィザード CLI
  - `kabusys.config_setup`：対話式ウィザードで `.env` を初期作成・更新する機能を追加（デフォルト項目・シークレットマスク表示・保存確認など）。
- 設定検証 CLI
  - `kabusys.validate_config`：必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス、`config/*.yaml` の存在・YAML パース（PyYAML があれば）などを検証。`--strict` オプションで警告を失敗扱いにできる。
- 起動スクリプト
  - `run_execution.py`：ExecutionEngine 起動スクリプト。プロセス優先度を設定し、paper_trading モード時は専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。BrokerClientFactory を用いたブローカークライアント生成、OrderRepository／OrderManager／RiskManager／Reconciler の組み立て、エンジンのデーモンスレッド起動と停止フラグによる制御を実装。デフォルトの RiskManager 設定（max_position_pct, max_utilization, rate_limit_per_sec 等）を含む。
  - `run_monitoring.py`：SystemMonitor のポーリングループ起動スクリプト。環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に依らず本番 sqlite_path を使用する挙動に注意。
- ログ設定ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`：ルートロガーを統一的に設定。コンソール出力は stdout を使用し、日次ローテート（TimedRotatingFileHandler）でログファイルを出力（デフォルト logs/<app_name>.log、30 日分保持）。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
- プロセス優先度 / CPU affinity ユーティリティ
  - `kabusys.utils.process_priority.set_process_priority`：Windows / POSIX の差分を吸収して "high"/"normal"/"low" の優先度を設定。psutil による実装でアクセス拒否や未実装の環境では警告を出してスキップ。
  - `set_cpu_affinity`：カレントプロセスを先頭 N コアにピン留めする機能（未指定時は無効化）。
- ポートフォリオ構築 (純粋関数群)
  - `kabusys.portfolio.portfolio_builder`
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を取得（同点時は signal_rank でタイブレーク）。
    - calc_equal_weights, calc_score_weights: 等金額配分／スコア加重配分を実装。全スコアが 0 の場合は等金額にフォールバックし WARNING を出力。
  - `kabusys.portfolio.risk_adjustment`
    - apply_sector_cap: セクターごとの既存エクスポージャーが閾値を超える場合に新規候補を除外（"unknown" セクターは除外対象外）。既存保有の評価額計算に price_map を使用する。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）を提供。未知のレジームは 1.0 にフォールバックして警告。
  - `kabusys.portfolio.position_sizing`
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数決定ロジックを実装。単元株丸め（lot_size）、1銘柄上限、aggregate cap（available_cash を超える場合のスケールダウン）やコストバッファの考慮、残余キャッシュによる端数処理ロジックを含む。
- 研究用ファクター計算
  - `kabusys.research.factor_research`：DuckDB 接続を受け取り、prices_daily / raw_financials テーブルからモメンタム／Value／Volatility／Liquidity などのファクターを計算する設計を実装（モジュール化、パラメータ定義、calc_momentum の骨組みなど）。
- ツール
  - `kabusys.tools.paper_verification_report`：Paper Trading 用の検証レポート生成 CLI。SQLite（デフォルト data/paper_trading.db）から system_status / trade_logs / risk_logs を参照して稼働率、注文成功率、送信率、レイテンシ (avg/max/P95) を計算し、PASS/FAIL 判定を行う。デフォルトの合格基準（稼働率 99%、fill 90%、send 95%、P95 レイテンシ 200ms）を定義。
- パッケージ公開
  - パッケージのエクスポート群を整備（kabusys.portfolio の __all__ 等）。

### Changed
- ログ出力: コンソールは stdout を使用する設計に統一（cron や Task Scheduler でのリダイレクト運用を考慮）。
- DB ハンドリング: run_execution/run_monitoring は起動時に monitoring テーブルが存在することを保証するために `init_monitoring_db` を実行（冪等処理）。

### Fixed
- 環境変数パーサ: export KEY=val 形式やクォート内エスケープ、インラインコメントの扱いに対応することで .env の柔軟な記述に対応。

### Known issues / TODO
- portfolio.risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過小評価されブロックされない可能性がある（コード内に TODO コメントあり）。前日終値や取得原価などのフォールバック価格を利用する拡張が検討されている。
- portfolio.position_sizing: 銘柄ごとに異なる単元株（lot_size）をサポートする拡張が未実装（TODO）。
- research.factor_research.calc_momentum 等の関数は設計に基づく実装の骨組みがあるが、実運用前に十分なデータ検証が必要。
- 一部の機能は外部ライブラリ（psutil, PyYAML, duckdb, sqlite3）が必要。環境によってはこれらが未インストールで一部検査や機能が限定される。

---

（注）この CHANGELOG は提供されたソースコード内容から推測して作成しています。実際のリリース履歴や変更履歴と完全には一致しない場合があります。必要であれば、差分の確定やリリースノートの精査を行って正式版に調整してください。