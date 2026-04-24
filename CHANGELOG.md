# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠し、安定版と非互換変更を分かりやすく示すようにしています。

現在のバージョンは src/kabusys/__init__.py にある __version__ に合わせて v0.1.0 としています。

## [Unreleased]
- 開発中の変更や未リリースの小さな改善点はここに記載します。

---

## [0.1.0] - 2026-04-24

### Added
- 初期リリース: KabuSys のコア機能群を実装。
  - パッケージ全体のメタ情報を追加（src/kabusys/__init__.py）。
- 設定・環境変数管理
  - Settings クラスにより環境変数を集中管理（J-Quants / kabu API / DB パス / 各種閾値など）。
  - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサを独自実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応）。
  - PAPER_FILL_MODE の検証（有効値: "instant", "partial", "never", "reject"）。
  - paper_trading 用 DB パス（PAPER_TRADING_SQLITE_PATH / デフォルト data/paper_trading.db）。
- 起動用 CLI / ウィザード / 検証ツール
  - 環境設定ウィザード（config_setup.py）を実装し、対話式に .env の生成・更新を支援。
  - 設定検証 CLI（validate_config.py）を実装。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在・パース等を検査。--strict オプションで警告も失敗扱いに。
- 実行・監視ランナー
  - ExecutionEngine 起動スクリプト（run_execution.py）
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組立てと実行ループ（スレッド運用）。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止、PID ファイルの扱い。
  - SystemMonitor 起動スクリプト（run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）。不正値時はデフォルトへフォールバックして警告。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計。
    - duckdb を監視用途のロギング／分析向けに接続。
- ロギング・プロセス制御ユーティリティ
  - 統一的なログ設定ユーティリティ（utils/logging_setup.py）
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app>.log）をルートに設定。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続（フォールバック実装）。
    - LOG_LEVEL / LOG_DIR / 引数による柔軟な設定解決。
  - プロセス優先度・CPU affinity ユーティリティ（utils/process_priority.py）
    - Windows / POSIX (Linux, Darwin, FreeBSD) を吸収する実装。
    - set_process_priority("high"|"normal"|"low") と set_cpu_affinity を提供。
    - psutil による権限不足等の例外を安全にハンドリングしてフォールバック。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で上位 N を選定（同点時は signal_rank でブレーク）。
    - calc_equal_weights / calc_score_weights（スコア合計が 0 の場合は等配分へフォールバックして警告）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクターごとの既存エクスポージャーを計算し、上限超過セクターの候補除外を実装。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を返す（未知レジームは 1.0 で警告フォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じた株数計算。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash を超える場合のスケーリング）、cost_buffer を考慮した安全設計。
    - price 欠損時のスキップやログ出力によるロバスト性。
- 研究・集計基盤
  - DuckDB を利用したファクター算出モジュールの骨組み（research/factor_research.py）
    - Momentum / MA200 / ATR / Liquidity 等を計算する方針・定数を定義（関数 calc_momentum の実装開始）。
- ツール群
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH / --db で DB 指定可能。
    - システム稼働率、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、API レイテンシ（avg/max/P95）を集計。
    - PASS/FAIL 判定基準を導入（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200 ms）。
    - 欠損テーブルや OperationalError を考慮した堅牢なクエリ実行。
- その他
  - 各種ファイルパスやフラグ（stop_requested.flag、execution.pid、kill flag 等）の利用と説明を起動スクリプトに追加。
  - コンフィグテンプレート要素と対話ウィザードでの既存値再利用・シークレットマスクを実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 機密情報（API トークン・パスワード等）は .env にのみ保管する旨をドキュメントに記載（config_setup に注意喚起コメント）。Git に .env をコミットしないよう明記。

---

脚注:
- 本 CHANGELOG は現行ソースコードの内容から推測して作成しています。内部実装の細部はリファクタや将来のコミットで変化する可能性があります。
- 次回リリースでは「Fixed / Changed / Security」などのセクションを充実させて差分を明確に記録してください。