# Changelog

すべての注記は Keep a Changelog の書式に準拠しています。  
意味論的バージョニングを前提としています。

## [0.1.0] - 2026-04-19

初回リリース。KabuSys 自動売買フレームワークの基盤的なユーティリティ、実行・監視スクリプト、設定管理、ポートフォリオ構築ロジックおよび検証ツール群を追加しました。

### 追加 (Added)
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御にプロジェクト `data/stop_requested.flag` を利用。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視データは本番 DB を参照）。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py
    - 実際の ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用 DB（デフォルト: data/paper_trading.db）に完全分離して記録。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理（data/execution.pid）に対応。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - Settings クラスを実装。環境変数から各種設定を取得するプロパティを提供。
    - .env の自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。
    - paper_sqlite_path, duckdb_path, sqlite_path 等のデフォルト値を定義。
    - KABUSYS_ENV / LOG_LEVEL の値検証を実装（development, paper_trading, live 等）。
  - config_setup.py
    - 対話式ウィザードで .env の生成・更新を支援する CLI を追加。
    - シークレット項目はマスク表示、保存前に確認プロンプトを表示。
    - .env の書式とテンプレートを生成（.env は絶対に Git にコミットしない旨を明記）。
  - validate_config.py
    - 起動前に .env と config/*.yaml の設定整合性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL のチェック、DB パスの親ディレクトリ存在チェック、YAML パースチェック（PyYAML があれば）等を実行。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - stdout へ StreamHandler、日次ローテート（30 日保持）の TimedRotatingFileHandler を設定。
    - LOG_DIR 環境変数や引数でログディレクトリを指定可能。ディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - 既存ハンドラを一旦クリアして二重設定を防止。
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度および CPU affinity を設定するユーティリティを追加（psutil を利用）。
    - Windows/Linux/macOS に対して適切な priority/nice を設定。権限不足等で失敗した場合は警告ログを出して処理をスキップ。

- ポートフォリオ構築モジュール (純粋関数群、DBアクセスなし)
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選抜。
    - calc_equal_weights, calc_score_weights: 等金額およびスコア加重の重み計算。スコア合計が 0 の場合は等配分にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限（max_sector_pct）をチェックし、超過セクターの新規候補を除外するロジックを実装。unknown セクターは制限対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは 1.0 でフォールバックし警告を出す。
  - portfolio/position_sizing.py
    - calc_position_sizes: 各銘柄の発注株数決定ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）で丸め、max_position_pct、max_utilization、cost_buffer（手数料/スリッページ見積）等を考慮。
    - 投下資金が available_cash を超える場合のスケーリングと残余配分アルゴリズムを実装。

- 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite DB から各種指標（稼働率、注文成功率、送信率、API レイテンシ等）を集計し、PASS/FAIL 判定を行うレポート生成スクリプトを追加。
    - デフォルト DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。
    - P95 計算、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）による判定を実装。

- リサーチ基盤（実装の開始）
  - research/factor_research.py
    - ファクター計算の土台（定数、calc_momentum の骨格）を追加。DuckDB 接続を受けて prices_daily / raw_financials を用いる設計。注: calc_momentum の実装は途中（ファイル末尾で切れているため、今後完成予定）。

### 変更 (Changed)
- パッケージのメタ
  - __init__.py にてパッケージバージョンを 0.1.0 に設定。

### 修正 (Fixed)
- 実装上の安全性・冗長チェックを多数追加
  - .env 読み込みのパーサーが quoted 値・export 形式・インラインコメント等に対応。
  - logging_setup: ログディレクトリ作成失敗時に stdout のみで継続する挙動を追加。
  - process_priority: 権限不足や未対応 OS に対する警告とスキップ処理を追加。

### 既知の問題 / TODO (Known issues / TODO)
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少評価され得る点を TODO コメントで指摘。将来的に前日終値等のフォールバックを検討予定。
- portfolio/position_sizing:
  - 今は全銘柄共通の lot_size を想定。将来的には銘柄別単元情報を持たせる設計への拡張を予定。
- research/factor_research.calc_momentum:
  - ファイル末尾で実装が途切れているため、momentum の詳細実装は未完。今後のリリースで完成予定。
- 一部 CI/テスト向けのフック（KABUSYS_DISABLE_AUTO_ENV_LOAD 等）は存在するが、テストスイートは付属していません。

### マイグレーション/運用上の注意 (Notes)
- .env の自動ロード
  - デフォルトでプロジェクトルートの .env / .env.local を自動的に読み込みます（OS 環境変数が優先されます）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 実行スクリプトの停止
  - run_monitoring/run_execution は停止指示に data/stop_requested.flag（プロジェクトルート基準）を利用します。停止フラグを使った制御を行ってください。
- Paper Trading と本番 DB の分離
  - paper_trading 環境では PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、本番の monitoring DB（SQLITE_PATH）と完全に分離されます。
- ログ
  - デフォルトは logs/ ディレクトリにアプリ名ごとに日次ローテーションで出力（30 日保持）。LOG_DIR 環境変数や setup_logging の引数で変更可能。ディレクトリ作成に失敗した場合はコンソールログのみになります。
- プロセス優先度設定
  - 起動スクリプトは開始直後に set_process_priority("high") を呼び出します。権限がない場合は警告が出てスキップされます。

---

今後のリリースでは以下を予定しています:
- research/factor_research の完全実装（Momentum/Value/Volatility/Liquidity 等の計算完了）
- テストカバレッジと CI ワークフローの整備
- ポートフォリオ構築ロジックのパラメータ調整・パフォーマンス最適化
- 監視・アラートロジック（LINE 通知など）の統合と堅牢化

（以上）