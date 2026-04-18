# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

## [0.1.0] - 2026-04-18

初回リリース。KabuSys のコア機能（設定管理、起動スクリプト、ポートフォリオ構築ロジック、ユーティリティ、運用向けツール群）を導入します。

### Added
- 全体
  - パッケージ初版を追加。パッケージバージョン: 0.1.0。
  - プロジェクトルート自動検出ロジックを持つ .env 自動読み込み機能を実装（OS 環境変数を優先し、.env/.env.local を適切な優先度で適用）。
  - Settings クラスを追加し、環境変数をラップして型変換・妥当性検査を提供（例: KABUSYS_ENV, LOG_LEVEL, 各種 DB パス, PAPER_FILL_MODE 等）。
  - settings = Settings() シングルトンをエクスポート。

- 起動 / 運用スクリプト
  - run_execution.py: 実行エンジン起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory を利用したブローカー接続作成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を構成。
    - 起動時にプロセス優先度を "high" に設定。停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) の取り扱いをサポート。
    - init_monitoring_db() を呼び出して監視テーブルの存在を保証（冪等）。

  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - デフォルトポーリング間隔 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（不正値はデフォルトにフォールバックし警告出力）。
    - Monitoring は環境にかかわらず本番用 sqlite_path を使用してデータを記録。
    - 停止フラグ (data/stop_requested.flag) による安全停止、例外時のログ出力、リソースクリーンアップを実装。

- 設定関連 CLI
  - config_setup.py: 対話式ウィザードで .env を初期作成/更新する CLI を追加。
    - シークレット値マスク、デフォルト値提示、選択肢入力、保存確認を実装。
    - .env 出力テンプレートには「.env を絶対に Git にコミットしない」注意書きを含む。

  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須 / 任意環境変数の存在チェック、KABUSYS_ENV と LOG_LEVEL の値検証、DB パス（親ディレクトリ存在確認）、config/*.yaml の存在確認（PyYAML があればパース検証）を実行。
    - KABUSYS_ENV=live の場合の追加ガード（LINE 通知未設定、KILL_FLAG_CLEAR_ON_START の注意喚起）を実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順かつ signal_rank によるタイブレークで候補選定。
    - calc_equal_weights: 等金額配分を実装。
    - calc_score_weights: スコア比例配分を実装。全スコアが 0 の場合は等金額配分にフォールバック（警告ログ）。

  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中リスクを評価し、上限超過セクターの新規候補を除外するロジックを実装（"unknown" セクターは無視）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数を返す（"bull"/"neutral"/"bear" マッピング、未知レジームはフォールバックで 1.0）。

  - portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく発注株数決定を実装。
      - 単元株丸め（lot_size 単位）、1 銘柄上限、aggregate cap（available_cash によるスケールダウン）、cost_buffer による保守的見積り、残差に基づく追加配分ロジックを実装。
      - risk_based では risk_pct / stop_loss_pct を用いたリスクベースの目標株数算出。

- ユーティリティ
  - utils.logging_setup: 統一的なログ設定ユーティリティを追加。
    - ルートロガーをリセットして StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみ運用。
    - stdout を使用することでスケジューラからのリダイレクト運用を想定。

  - utils.process_priority: プロセス優先度（nice / Windows priority class）と CPU affinity 設定を提供。
    - プラットフォーム差分を吸収し、権限不足や未対応機能は警告して安全にスキップ。
    - set_process_priority("high"|"normal"|"low"), set_cpu_affinity(n) を提供。

- 監視 / モニタリング補助
  - monitoring.monitoring_db の初期化呼び出しを起動スクリプトに統合（各起動時に監視テーブルの存在を保証）。

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成 CLI を追加。
    - system_status, trade_logs, risk_logs テーブルから稼働率、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなどを集計してレポート表示。
    - 既定の基準値（稼働率 99%、fill_rate 90%、send_rate 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定を実装。
    - --from / --to / --db オプション対応。PAPER_TRADING_SQLITE_PATH 環境変数経由で DB 指定可能。

- リサーチ
  - research.factor_research: DuckDB を用いたファクター計算モジュールの骨組み（モメンタム、MA200 乖離、ATR, Value, Liquidity 等の設計方針と calc_momentum の初期実装スケルトンを追加）。
    - DuckDB 接続を受け prices_daily / raw_financials テーブルから計算する想定。

### Changed
- なし（初回リリースのため変更履歴なし）。

### Fixed
- なし（初回リリース）。

### Deprecated
- なし。

### Removed
- なし。

### Security
- config_setup に .env を生成するテンプレートに「.env を絶対に Git にコミットしないこと」を明記。
- Settings の必須環境変数未設定時には明確なエラーメッセージを出すことで、機密情報の欠落を早期に検出可能に。

### Notes / Known limitations / TODO
- research.factor_research の関数群は設計方針と一部実装（calc_momentum の冒頭）を含むが、完全実装・テストは今後の作業。
- position_sizing.calc_position_sizes 内に価格欠損時のフォールバック（前日終値や取得原価を使う等）に関する TODO コメントあり。価格欠損があるとエクスポージャーが過少見積もられる可能性がある。
- process_priority/set_cpu_affinity は権限やプラットフォームによる制約で動作しない場合があり、その際は警告のうえ安全にスキップする設計。
- validate_config は PyYAML が未インストールの場合、config/*.yaml のパース検証をスキップ（警告を出す）。
- run_monitoring は MONITOR_POLL_INTERVAL の不正値を警告してデフォルトにフォールバックする（time.sleep に渡す負値を避けるための保護）。

今後のリリースでは、リサーチ/戦略モジュールの完成、テスト追加、ドキュメント充実、CLI の UX 改善を予定しています。