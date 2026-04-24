CHANGELOG
=========

すべての重要な変更点を記録します。形式は "Keep a Changelog" に準拠しています。

Unreleased
----------

(なし)

0.1.0 - 2026-04-24
-----------------

Added
- 初期リリースを追加。
- コアアプリケーション（kabusys）を実装。
  - パッケージメタデータ: __version__ = "0.1.0" を設定。
- 設定・環境変数管理
  - Settings クラスを追加し、アプリ全体の設定値をプロパティ経由で取得可能に。
  - .env 自動読み込み機構を追加（プロジェクトルートを自動検出し、.env / .env.local を読み込む）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env パーサーの強化:
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱いをサポート。
    - 上書き制御（override）と protected（OS 環境変数保護）を実装。
  - 各種環境変数用プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE 等）を実装。PAPER_FILL_MODE の有効値チェックを実装（"instant"|"partial"|"never"|"reject"）。
  - KABUSYS_ENV（development/paper_trading/live）・LOG_LEVEL の検証を実装。
- CLI / ツール
  - config_setup: 対話式の .env 作成ウィザードを追加（対話入力により .env を生成／更新）。
  - validate_config: 起動前の設定検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パス存在確認、config/*.yaml の存在および（PyYAML があれば）パース検証を実施。
    - --strict オプションで警告を FAIL 扱いにできる。
  - tools/paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを算出し PASS/FAIL を判定。
    - デフォルト DB パスは data/paper_trading.db、CLI オプションで期間・DB を指定可能。
- 実行系スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用し、本番 DB と完全に分離。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine を組み立てて実行。
    - エンジンは別スレッドで実行。data/stop_requested.flag による停止フラグを監視して安全に停止。
    - 実行中の PID を data/execution.pid に管理（pid_file を受け渡し）。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を提示。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（デフォルト 60 秒）で上書き可能。無効な値は警告のうえデフォルトにフォールバック。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用（監視は本番 DB を対象とする設計）。
- DB / 分析基盤
  - DuckDB 接続サポートを導入（duckdb_conn を受け渡す設計）。
  - 監視テーブル初期化ユーティリティ init_monitoring_db を実装（冪等に DB スキーマを保証）。
- ポートフォリオ構築（純関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのスコア降順ソート（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。スコア合計が 0 の場合は等金額にフォールバック。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限 (max_sector_pct) を適用し、新規候補の除外を実装。売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: レジームに応じた資金乗数（bull/neutral/bear）を実装。未知の値は警告後 1.0 にフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数算出を実装。
    - 単元株（lot_size）丸め、per-position 上限・aggregate cap、cost_buffer（手数料/スリッページ見積り）を考慮したスケーリングロジックを実装。残余キャッシュを使って小数端数分を lot_size 単位で追加配分するアルゴリズムを実装。
- utils
  - logging_setup: 統一的なロギング設定ユーティリティを追加。
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定。
    - stdout を使用することで cron 等でのログリダイレクトに対応。
    - LOG_DIR / LOG_LEVEL / app_name / log_dir / level 引数でカスタマイズ可能。ログディレクトリ作成失敗時はファイル出力をスキップしコンソール出力のみで継続。
  - process_priority: クロスプラットフォームでプロセス優先度と CPU affinity を設定するユーティリティを追加。
    - Windows/Linux（および一部 POSIX）で nice / priority を設定。失敗時は警告でスキップ。
    - set_cpu_affinity を実装（最初の N コアに固定）。不正な値は ValueError。
- research
  - research.factor_research: ファクター計算モジュール（モメンタム等）を追加（設計・定数定義と calc_momentum の骨格を実装、以降の実装は継続予定）。

Changed
- 既存のロギング/起動手順を統一
  - 全起動スクリプトから setup_logging を呼び出すことでログ出力形式・ローテーションを統一。
- デフォルト挙動の明確化
  - MONITOR_POLL_INTERVAL のデフォルトをソース内定数で管理（デフォルト 60 秒）。
  - Paper Trading 用 DB を明示的に分離（PAPER_TRADING_SQLITE_PATH / settings.paper_sqlite_path）。

Fixed / Hardening
- 設定読み込みやファイル操作での堅牢性を向上
  - .env 読み込み失敗時のワーニング、ログディレクトリ作成失敗時のフォールバック（コンソールのみ）を追加。
  - DB テーブルが存在しない場合のクエリでの OperationalError を想定した安全なフォールバック（tools/paper_verification_report 内の各クエリ呼び出しで捕捉）。
  - process_priority や CPU affinity の設定において権限不足や未サポート環境を捕捉し警告でスキップ。
- run_execution / run_monitoring の停止処理改善
  - ファイルベースの停止フラグ（data/stop_requested.flag）を利用した安全停止。KeyboardInterrupt の捕捉とリソースクローズを確実化。

Notes (補足)
- 本リリースは「初期実装」に相当し、多数のモジュールが揃っていますが、一部（例: research.factor_research の完全実装、より細かな単体テストや外部システム統合テスト）は今後のリリースで強化予定です。
- 本番運用時は KABUSYS_ENV=live の設定に注意してください。validate_config の live に関する警告や、KILL_FLAG_CLEAR_ON_START 等の設定は慎重に扱ってください。
- Paper Trading（ペーパートレード）では発注ロジックや約定挙動を分離・模擬しているため、本番 DB や実際のブローカーへは影響しません。PAPER_FILL_MODE の設定によってモックの約定挙動を制御できます。

セキュリティ
- 重要なシークレット（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は .env に保存することを前提としており、config_setup での注意書きでも .env を Git にコミットしないよう明確にしています。