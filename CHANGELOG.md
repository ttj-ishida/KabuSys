# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
該当リリース: 0.1.0（初回公開）

## [0.1.0] - 2026-04-24

### 追加 (Added)
- 実行・運用用スクリプトを追加
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時はペーパートレード用の MockBrokerClient を利用し、paper_trading 用の SQLite(DB: data/paper_trading.db 既定) と分離して動作する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）検知や KeyboardInterrupt を考慮して安全に終了する。
- 設定管理とセットアップ
  - config.py: 環境変数読み込み・Settings クラスを実装。プロジェクトルートの自動検出(.git / pyproject.toml)、.env/.env.local の自動読み込み（OS 環境変数の保護機構付き）、.env 行の堅牢なパーサ（export 形式、クォート・エスケープ、インラインコメント処理）を実装。
  - config_setup.py: 対話式 .env 作成ウィザードを追加（項目定義、既存値読み込み、シークレットマスク、保存ファイル生成）。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数チェック、パス存在チェック、config/*.yaml の存在と YAML パース検証（PyYAML 未インストール時は警告でスキップ）、--strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルのスコア順ソートによる候補選定。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み算出（全スコア0の際のフォールバックあり）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクターごとの上限チェック（max_sector_pct）で候補を除外するロジック。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を計算。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数決定、単元株丸め(lot_size)、max_position_pct／max_utilization による上限、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り、端数分配ルールを実装。
- ユーティリティ
  - utils.logging_setup: 統一的なログ設定ユーティリティを追加。コンソールは stdout に出力、日次ローテートする TimedRotatingFileHandler（デフォルト logs/、30 日保持）を設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続する。
  - utils.process_priority: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定を追加。権限不足などの失敗は警告でスキップする。
- 管理ツール
  - tools.paper_verification_report: ペーパートレード用検証レポート出力ツールを追加。期間指定（--from / --to）と DB 指定（--db / 環境変数）をサポートし、稼働率、注文成功率、送信率、P95 レイテンシなどを集計・判定（PASS/FAIL）する。
- リサーチ基盤（骨組み）
  - research.factor_research: DuckDB を使ったファクター計算のための基盤を追加（モメンタム等の定義・定数、calc_momentum の実装開始）。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計。

### 変更 (Changed)
- なし（初回リリースのため該当なし）

### 修正 (Fixed)
- .env 読み込みの堅牢化
  - config._load_env_file と _parse_env_line にてクォート文字列内のエスケープ処理、export プレフィックス対応、インラインコメントの取り扱いを明確化し、実運用での .env 設定ミスに耐性を持たせた。
- DB 初期化の冪等性確保
  - run_execution/run_monitoring で init_monitoring_db を呼び出し、監視用テーブルが存在することを保証（複数起動でも安全）。

### パフォーマンス (Performance)
- ポジションサイズ算出時に aggregate cap のスケーリングと端数配分を導入し、利用可能資金を有効活用する一方で安全に上限を守るロジックを実装。

### セキュリティ (Security)
- .env ファイル作成ウィザードではシークレット項目をマスク表示して対話を行うなど、機密情報の直接表示を抑制。
- Settings クラスの必須環境変数取得で未設定時は ValueError を投げることで起動前に明示的な失敗（安全性向上）を実現。

### その他（運用上の注意）
- run_monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path（Settings.sqlite_path）を使用する仕様になっている点に注意してください。
- run_execution は paper_trading 環境時に paper_sqlite_path を使用して本番 DB と完全に分離します。
- MONITOR_POLL_INTERVAL に不正な値（0 以下や数値以外）を設定した場合はログに警告を出してデフォルト（60 秒）にフォールバックします。
- process_priority や CPU affinity 設定は権限やプラットフォーム依存で失敗する場合があり、その際は警告ログを出してスキップします。
- validate_config は PyYAML 非導入環境でも実行可能で、YAML 検証をスキップする旨を警告します。

---

初回リリース（0.1.0）は上記のコア機能群と運用ツール群を含みます。今後は strategy／execution の個別コンポーネントや factor_research の拡張、テスト・ドキュメントの追加、そしてパフォーマンスや堅牢性向上のための改善を予定しています。