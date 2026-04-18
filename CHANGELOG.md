CHANGELOG
=========

すべての変更は "Keep a Changelog" の形式に準拠して記載しています。

フォーマット:
- Added: 新機能
- Changed: 変更点（後方互換性に注意が必要な変更など）
- Fixed: バグ修正
- Deprecated / Removed / Security: 必要に応じて記載

[0.1.0] - 2026-04-18
-------------------

Added
- 初期リリース: KabuSys 0.1.0 を追加。
- 核となる実行スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立てと ExecutionEngine の起動サポート。
    - RiskConfig のデフォルト値を設定（max_position_pct=0.20、max_utilization=0.80、rate_limit_per_sec=5、circuit_breaker_errors=10、circuit_breaker_window_sec=60、max_drawdown=0.20、initial_portfolio_value=broker.get_available_cash()）。
    - デーモンスレッドで engine.run_session を実行し、data/stop_requested.flag による外部停止フラグの監視と安全停止を実装。
    - PID ファイル出力（data/execution.pid）をサポート。

  - run_monitoring.py
    - SystemMonitor 起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 以下など）はデフォルトへフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを管理。
    - duckdb への接続サポート、監視用 DB 初期化（init_monitoring_db）を実行。
    - data/stop_requested.flag による停止、KeyboardInterrupt のハンドリング、DB 接続の確実なクローズを実装。

- 設定・環境管理
  - config.py
    - Settings クラスを導入し、環境変数からの設定読み取りを集中管理。
    - .env, .env.local の自動読み込み機構を追加（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。プロジェクトルートは .git または pyproject.toml を基準に探索するため CWD に依存しない設計。
    - .env のパーサーを強化: export プレフィックス、シングル/ダブルクォート内のエスケープ、行内コメントの扱いなどに対応。
    - 環境変数の保護（既存 OS 環境変数を上書きしない/上書き対象の制御）に対応。
    - 各種プロパティを提供（duckdb/sqlite パス、paper_trading 用 DB パス、pid/kill flag パス、Kill Flag 挙動フラグ、CPU/メモリ/ディスク閾値、env/log_level バリデーション、paper_fill_mode のバリデーション等）。

  - config_setup.py
    - 対話式ウィザードで .env を生成/更新する CLI を追加。
    - デフォルト値・選択肢表示、シークレット入力のマスク、既存 .env の読み込みと再利用をサポート。
    - 作成テンプレートは .env に保存する際のコメント付きヘッダを含む。

  - validate_config.py
    - 起動前に .env と config/*.yaml の基本的な妥当性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の値検証、DB パスの親ディレクトリ存在チェック、PyYAML があれば YAML のパース検証も実行。
    - --strict オプションで警告も失敗扱いにできる。本番向けのガード（LINE 通知設定や Kill Flag の設定）チェックを含む。

- ポートフォリオ構築モジュール（純粋関数、メモリ内処理）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選別（同点時は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア比率で重みを計算。全スコアが 0 の場合は等金額配分にフォールバックし警告。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限ロジックを実装。既存保有のセクター時価比が閾値を超えるセクターは当日新規候補から除外（unknown セクターは適用外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知のレジームは 1.0 でフォールバックし警告）。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算を実装。
    - risk_based：リスク割合 (risk_pct) と stop_loss_pct に基づく株数算出。
    - equal/score：重みと max_utilization を用いた割当。単元（lot_size）切り捨て・単位での再配分ロジック、aggregate cap によるスケールダウン（cost_buffer を考慮）を実装。
    - price 欠損時のスキップや上限 per-stock の導入など実運用を想定した振る舞いを実装。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。既存ハンドラのクリア機能あり。LOG_DIR / LOG_LEVEL の解決順を定義。ログファイル作成失敗時は標準出力のみで継続するフォールバックを実装。
  - utils/process_priority.py
    - プロセス優先度（nice / Windows priority）と CPU affinity の設定ユーティリティを追加。Windows / POSIX の差分を吸収し、psutil を利用。権限不足や未サポート環境時は警告を出して安全にスキップ。

- モニタリング関連
  - monitoring_db の初期化用関数（init_monitoring_db）への呼び出しを各起動スクリプトで行い、監視テーブルが存在することを保証（冪等操作）。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用の検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を算出し、閾値に基づく PASS/FAIL 判定（デフォルト閾値: 稼働率 ≥ 99%、成立率 ≥ 90%、送信率 ≥ 95%、P95 ≤ 200 ms）を出力。
    - CLI 引数 --from, --to, --db をサポート。

- パッケージメタデータ
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

Changed
- 環境変数ロードの優先順位と保護
  - OS の既存環境変数が優先されるように自動ロード時に保護セットを取得し、.env/.env.local の上書き動作を制御。
- ログ出力の標準化
  - すべての起動スクリプトは logging_setup.setup_logging を呼び出すことを推奨し、stdout への出力と日次ローテートファイル出力での一貫したログ運用を実現。

Fixed
- .env のパースや読み込みに関する堅牢性向上
  - export プレフィックス、引用符あり文字列内のバックスラッシュエスケープ、行内コメントの扱いなどを正しく解釈するよう改善。
- run_monitoring.py と run_execution.py の DB 接続処理で、finally ブロックにより接続が必ずクローズされるように修正（リソースリーク防止）。

Known issues / Notes
- research/factor_research.py においてファイル末尾が未完成（calc_momentum 等の実装途中で切れている断片あり）。ファクター計算モジュールは設計方針と定数が含まれるが、完全実装は今後のリリースで予定。
- position_sizing の将来的拡張メモ:
  - lot_size を銘柄別に持たせる設計拡張（stocks マスタ導入）を検討中（TODO コメントあり）。
- 一部の機能は外部ライブラリ（psutil, duckdb, PyYAML など）に依存する。これらが存在しない環境では機能が限定される（validate_config は PyYAML 不在時に YAML 検証をスキップするなどのフォールバックあり）。

Security
- 現状、特に公開されたセキュリティ修正はありません。環境変数（API トークン・パスワード等）は .env に保存する際に Git にコミットしない旨をドキュメント注記しています（config_setup 内のヘッダ）。

今後の予定 (短期)
- factor_research のファクター計算ロジックの完成と単体テスト整備。
- ExecutionEngine / SystemMonitor 周りの統合テスト・エンドツーエンド検証。
- paper_trading の検証ツールに HTML/CSV 形式の出力オプション追加検討。