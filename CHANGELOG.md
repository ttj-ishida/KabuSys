# Changelog

すべての変更は Keep a Changelog の慣例に従って記載しています。  
このファイルはコードベースの内容から推測して作成した変更履歴です。

なおバージョン番号は src/kabusys/__init__.py の __version__ を基準にしています。

## [Unreleased]
- ドキュメント化・リファクタリング
  - research/factor_research.py が途中まで実装されているため、ファクター計算関連の追加実装・テストが残っています。
  - 将来的に銘柄ごとの lot_size を stocks マスタから取得する拡張の予定あり（position_sizing 内 TODO を参照）。

## [0.1.0] - 2026-04-18
初回リリース — 自動売買基盤のコア機能群を実装。

### Added
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV に応じて paper_trading 用 DB を分離し、MockBrokerClient を利用する動作に対応。停止フラグ/PID ファイルによる起動・停止制御を実装。
  - run_monitoring.py: SystemMonitor を定期ポーリングで実行する監視プロセス起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視は環境にかかわらず本番 sqlite_path を使用する仕様。
- 設定関連
  - config.py: 環境変数/ .env の管理を行う Settings クラスを追加。自動 .env ロード（.env → .env.local、OS 環境変数優先）や KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
    - 環境変数の検証（KABUSYS_ENV, LOG_LEVEL 等）、PAPER_FILL_MODE のバリデーション、paper_trading 用 sqlite パス、各種監視閾値設定などを提供。
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加。
  - validate_config.py: .env および config/*.yaml の設定検証用 CLI を追加。--strict オプションで警告も失敗扱いに可能。
- Execution コンポーネント（実運用の発注・管理）
  - execution パッケージ内の主要クラス（BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等）を統合して起動可能に。
  - RiskConfig のデフォルト値（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を実装。初期ポートフォリオ値を broker.get_available_cash() で設定。
- 監視機能
  - monitoring.monitoring_db.init_monitoring_db の呼び出しにより、監視用テーブルの存在を保証（冪等）。
  - run_monitoring では停止フラグファイルを検知して安全に終了するループを実装。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順、同点は signal_rank でタイブレークして候補抽出。
    - calc_equal_weights / calc_score_weights: 等金額／スコア加重の重み計算。スコア全てが 0 の場合は等金額配分にフォールバックして Warn を出力。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限を適用して候補をフィルタ（"unknown" セクターは上限適用外）。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは警告を出して 1.0 にフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に対応した株数計算。単元株（lot_size）丸め、per-stock 上限・aggregate cap、cost_buffer を考慮したスケーリング、残余キャッシュに基づく端数配分ロジックを実装。
- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app>.log）を設定。LOG_DIR/LOG_LEVEL からの解決、ファイルハンドラ作成失敗時のフォールバックを実装。
  - utils/process_priority.py: Windows/Linux/macOS の差分を吸収するプロセス優先度設定と CPU affinity 設定を追加。権限不足時は警告を出してスキップ。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。システム稼働率、注文成功率（Fill/Send）、リスク却下数、レイテンシ（平均/最大/P95）を集計し PASS/FAIL を判定する閾値を実装（稼働率 >= 99%、Fill >= 90%、Send >= 95%、P95 <= 200ms）。
- research
  - research/factor_research.py: DuckDB 接続を受け取り価格データ・財務データからモメンタム等のファクターを計算するモジュールの骨子を追加（モメンタム等の定数と関数定義を含む。実装途中ファイルあり）。

### Changed
- 環境ファイルパーサーの強化（config._parse_env_line）
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの扱い、クォート無し値のコメント認識ルールを実装して .env の柔軟なパースを実現。
- .env の読み込み順序と保護
  - OS 環境変数を保護キーとして .env/.env.local の上書き制御を実装（protected set）。.env.local は .env を上書きするが OS 環境変数は上書きしない。
- ログ出力の既存ハンドラ対処
  - setup_logging が既存ハンドラを flush/close してから削除し、二重ハンドラ設定を防止。
- run_monitoring のエラーハンドリング
  - monitor.check_once() が例外を投げても監視ループを止めず、例外をログ出力して次ポーリングに続行する耐障害性を追加。

### Fixed
- position_sizing のスケールダウン処理における端数配分の再現性確保
  - 端数配分のソートで code を二次キーに用いることで同一 fractional 残差時の順序を安定化。
- config_setup の .env 書き込みフォーマット
  - 書き出し時に秘密値はプレーンに保存（ユーザーが管理する前提）し、テンプレートヘッダを追加して .env を誤ってコミットしないよう注意喚起を記載。

### Security
- .env の自動ロードに関する安全策
  - OS 環境変数を保護（override 時に上書きしない）し、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを提供。

### Known issues / Notes
- research/factor_research.py が途中（ファイル末尾が未完）であるため、ファクター計算モジュールは追加実装とテストが必要。
- position_sizing の価格欠損（price が 0.0 や None）の扱いはログでスキップする仕様。将来的に前日終値や取得原価でのフォールバックを検討する旨がコメントとして残っている。
- apply_sector_cap は "unknown" セクターを上限対象外とする設計。必要に応じて未知セクターの取扱い方針を見直す可能性あり。
- run_monitoring が監視用 DB として常に sqlite_path（本番設定）を参照する点に注意（意図的な仕様）。

---

（この CHANGELOG は現行ソースコードの機能・実装から推測して作成しています。実際のリリース履歴や日付はプロジェクトのリリース記録に合わせて調整してください。）