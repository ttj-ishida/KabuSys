# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-17

### Added
- 初回リリース: KabuSys 基本モジュール群を追加。
- 環境設定・読み込み
  - .env 自動ロード機能を実装（プロジェクトルートの .env / .env.local を読み込む）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサは export 形式、クォート、バックスラッシュエスケープ、インラインコメントを考慮して安全に読み込めるよう実装。
  - config.Setup CLI（python -m kabusys.config_setup）を追加。対話式ウィザードで .env の初期作成・更新を支援。
  - 設定管理クラス Settings を追加。主要な環境変数（J-Quants / kabu API / DB パス / モード等）をプロパティ経由で取得可能。
- 設定検証ツール
  - validate_config CLI（python -m kabusys.validate_config）を追加。必須環境変数、KABUSYS_ENV 値、DB パス、config/*.yaml の存在・パースなどを検証。--strict で警告をエラー扱いにできる。
- 実行・監視の起動スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイントを追加。プロセス優先度設定、SQLite/DuckDB 接続、Broker クライアント生成、OrderManager/RiskManager/Reconciler 組立、スレッド実行と停止フラグ監視を実装。
    - paper_trading モード時は専用の paper_trading DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と完全分離。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用（注記あり）。
  - 停止フラグ（data/stop_requested.flag）および PID ファイル経路の取り扱いを共通化。
- 実行時ユーティリティ
  - process_priority モジュールを追加: Windows / POSIX の差を吸収してプロセス優先度（high/normal/low）を設定。CPU affinity を最初 N コアに固定するユーティリティも提供。権限エラー等はログ警告でサイレントにフォールバック。
- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio_builder: シグナル選別（select_candidates）、等金額配分（calc_equal_weights）、スコア重み配分（calc_score_weights）を実装。スコア合計が 0 の場合は等金額にフォールバックして警告。
  - risk_adjustment: セクター集中制限を適用する apply_sector_cap、マーケットレジームに基づく投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をサポート。未知レジームはフォールバック）。
  - position_sizing: 複数の配分方式（risk_based / equal / score）に対応した株数決定ロジックを実装。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash 超過時のスケールダウン）や cost_buffer を考慮した配分調整を行う。
- 研究用モジュール
  - research.factor_research: DuckDB 接続を受け取り、モメンタム・ボラティリティ等のファクターを計算する関数群を実装（prices_daily テーブル参照）。MA200、ATR20、複数ホライゾンのリターンなどを算出。
- ツール
  - tools.paper_verification_report: ペーパートレード用検証レポート生成スクリプトを追加。デフォルト DB は data/paper_trading.db、期間指定 (--from/--to) に対応。稼働率、注文成功率・送信率、P95 レイテンシなどを算出し PASS/FAIL 判定を行う。判定閾値はソース内で定義（稼働率 99% など）。

### Changed
- なし（初回リリース）  

### Fixed
- .env 読み込み時の I/O エラーは warnings.warn によりユーザーへ通知し、安全にスキップするよう実装。
- process_priority/set_process_priority: 未サポート OS や権限がない場合に例外で落とさないようログ警告でフォールバックする実装にした。

### Notes / Important
- run_monitoring は「環境にかかわらず本番 sqlite_path を使用する」実装となっており、paper_trading 用 DB を使わないため運用時は注意が必要（監視データが本番 DB に記録される）。
- run_execution は paper_trading モード時に paper_trading DB を使用して本番 DB とデータ分離を行う。
- Settings の各プロパティは環境変数に厳格に依存するため、必須環境変数未設定時は ValueError を発生させる。validate_config による事前チェックを推奨。
- position_sizing の計算は価格欠損（price が 0 または None）の場合その銘柄をスキップする挙動。将来的にフォールバック価格の導入がコメントで示唆されている。

### Security
- なし

---

（備考）パッケージバージョンは src/kabusys/__init__.py にて __version__ = "0.1.0" として設定されています。