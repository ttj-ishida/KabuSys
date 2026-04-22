# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  

- 既知のバージョン: 0.1.0
- 日付はリリース日（本ドキュメント作成日）です。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-22

### Added
- 初期リリース — KabuSys 日本株自動売買システムの基本コンポーネントを実装。
- 実行 / 監視関連
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、BrokerClientFactory を介したブローカークライアント生成、ExecutionEngine のセッション管理（別スレッドで実行）を実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）を使用し、MockBrokerClient を利用して本番 DB と完全分離する想定。
    - 停止制御: data/execution.pid と data/stop_requested.flag による起動/停止フラグ処理を実装。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する（監視データは production DB を想定）。
    - 停止フラグ（data/stop_requested.flag）検知によりループを終了。
- 設定管理 / ユーティリティ
  - config.py: 環境変数および .env 自動ロード機能を実装。
    - .env/.env.local の自動読み込み（OS 環境変数優先）。プロジェクトルート判定は .git または pyproject.toml に基づく（__file__ を起点に探索）。
    - 複雑な .env パース（export 形式、シングル／ダブルクォート内のバックスラッシュエスケープ、インラインコメント扱い等）に対応。
    - Settings クラスで各種設定プロパティを提供（DB パス、API トークン、Paper Trading 関連設定、監視閾値、環境判定等）。PAPER_FILL_MODE のバリデーション、KABUSYS_ENV / LOG_LEVEL の妥当性チェックを実装。
  - config_setup.py: 対話式環境設定ウィザードを提供。.env の初期作成・更新、既存値の再利用、シークレット項目のマスク表示等をサポート。
    - 生成される .env に対して「絶対に Git にコミットしない」旨の注意を含める。
  - validate_config.py: 起動前チェック CLI を実装。必須環境変数未設定や config/*.yaml の存在・パース、データベースパスの親ディレクトリ存在チェック、本番環境用のガード項目（LINE 通知設定・KILL_FLAG_CLEAR_ON_START 等）を検証。--strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 昇順）でソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分を実装。スコア合計が 0 の場合は等分配にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（max_sector_pct）を実装。既存保有を考慮し、上限超過セクターの新規候補を除外。unknown セクターは上限適用対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは 1.0 でフォールバック（警告ログ）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数算出ロジックを実装。単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap によるスケーリング、cost_buffer の考慮、残余キャッシュを使った端数配分ロジックを実装。
- リサーチ / ファクター計算（骨格）
  - research/factor_research.py: DuckDB 接続を受けてモメンタム等のファクターを計算する設計を追加。計算に必要な定数（期間）と関数インターフェイス（例: calc_momentum）を定義（実装は継続中／一部未完）。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - 指標: 稼働率 (uptime_pct)、注文成功率 (fill_rate)、送信率 (send_rate)、API レイテンシ（平均/最大/P95）、リスク却下数等。
    - 基準値（閾値）を定義して PASS/FAIL を判定。
    - 日付フィルタ、DB パス指定（--db / 環境変数）対応。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: グローバルなログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。LOG_DIR/LOG_LEVEL の解決、既存ハンドラの安全なクリア処理、ファイル出力失敗時のフォールバック挙動を実装。
  - utils/process_priority.py: プロセス優先度設定（Windows/Linux/macOS の差分吸収）、CPU affinity 設定関数を追加。アクセス権限不足等で失敗した場合は警告ログでスキップする安全機構あり。

### Changed
- n/a（初回リリースのため変更履歴なし）

### Fixed
- n/a（初回リリースのため修正履歴なし）

### Security
- config_setup の出力コメントと README 注意: .env を絶対に Git にコミットしない旨の注意を .env ヘッダに明記。

### Notes / Implementation details
- 監視ループ（run_monitoring）は MONITOR_POLL_INTERVAL の不正値を検出してデフォルトにフォールバックすることで time.sleep の例外回避を行う。
- 監視は init_monitoring_db により監視用テーブルの存在を保証する（冪等）。Monitoring は設計上、本番 sqlite_path を参照するため運用上の注意が必要。
- ExecutionEngine 側は engine.run_session をバックグラウンドスレッドで実行し、外部からの停止フラグで安全に停止できるようになっている。
- .env 自動ロードはプロジェクトルートが特定できない場合はスキップされる。OS 環境変数は保護され、.env.local による上書きは可能だが OS 環境変数は上書かれない。
- 一部モジュール（例: research.calc_momentum）は実装途中の箇所が含まれる（今後のリリースで完成予定）。

---

メジャー／マイナー／パッチのルールに基づき、次回リリースでは機能追加・バグ修正・API 変更を明確に分けて記載します。