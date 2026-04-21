CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠しています。
リリースはセマンティックバージョニングに従います。

[Unreleased]: https://example.com/compare/v0.1.0...HEAD

---

## [0.1.0] - 2026-04-21

初回公開リリース。

### 追加 (Added)
- プロジェクトのコア機能をまとめて導入。
  - パッケージ metadata: kabusys.__version__ = "0.1.0"。
- 環境設定関連
  - Settings クラスを実装。環境変数経由でアプリ設定を取得するプロパティ群を提供（J-Quants / kabuステーション / LINE / DBパス / モニタ閾値等）。
  - .env 自動ロード機構を導入（プロジェクトルートを .git または pyproject.toml で検出）。自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサーを実装（export 付き行、引用符付き値、インラインコメント、エスケープ処理に対応）。
- 設定関連 CLI
  - config_setup: 対話式ウィザードで .env を作成/更新する `python -m kabusys.config_setup` を追加。
  - validate_config: 起動前検証 CLI を追加。必須環境変数、KABUSYS_ENV/LOG_LEVEL/DBパス、config/*.yaml の存在とパース（PyYAML があれば）をチェック可能。`--strict` オプションで警告を失敗とするモードを追加。
- 実行・監視エントリポイント
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、Paper Trading 用 DB を分離（data/paper_trading.db がデフォルト）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の開始・停止処理を行う。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理をサポート。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ検知でループを終了、例外発生時はログに例外を出力して次ポーリングに進む。
- ロギング・プロセス管理ユーティリティ
  - utils.logging_setup: StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定するユーティリティを追加。ログレベル・ログディレクトリの解決ロジックを備える。
  - utils.process_priority: Windows / POSIX を吸収したプロセス優先度設定（high/normal/low）と CPU affinity 設定関数を追加。権限不足等は警告ログでスキップ。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等分配とスコア加重配分。スコア合計が 0 の場合は等分配へフォールバック（警告出力）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存保有を考慮）と候補除外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく発注株数決定。単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケーリング（cost_buffer 考慮）等を実装。
- 分析・検証ツール
  - tools.paper_verification_report: Paper Trading 用 SQLite DB からシステム安定性、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計して人間向けレポートを出力する CLI を追加。
    - P95 計算ユーティリティを提供。
    - デフォルトの判定基準（稼働率 >= 99%、成立率 >= 90% 等）を定義。
- データベース初期化フック
  - monitoring.monitoring_db.init_monitoring_db を呼び出して監視テーブルの存在を保証する処理を run_execution / run_monitoring で利用。
- DuckDB と SQLite を併用する設計を導入（分析用に DuckDB、監視/履歴用に SQLite）。

### 変更 (Changed)
- ログ出力設計
  - ログはデフォルトで stdout に出力するようにして、cron 等からの一括リダイレクト運用に適した挙動に変更（StreamHandler を stdout に設定）。
- .env の読み込み優先順を明示
  - OS 環境 > .env.local > .env の順でロード。OS 環境変数は保護され上書きされない。
- Execution/Risk のデフォルト設定値
  - RiskManager のデフォルト構成値（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）といった合理的な初期パラメータを設定。

### 修正 (Fixed)
- 入力検証とフォールバック
  - MONITOR_POLL_INTERVAL が不正（整数変換不可や 0 以下）の場合は警告を出しデフォルト（60 秒）へフォールバック。
  - PAPER_FILL_MODE の無効値は ValueError を送出して明示的にエラー化（利用者側で修正が必要）。
  - calc_score_weights でスコア合計が 0 の場合、等金額配分にフォールバックしてログに警告を出力。
- ロギングディレクトリ作成失敗時のフォールバック
  - ログディレクトリ作成に失敗した場合はファイルハンドラを諦め、コンソール出力のみで継続するようにした（起動時の致命的失敗を回避）。

### ドキュメント (Documentation)
- 各モジュールに docstring と使い方・設計意図を追加。特に portfolio/*、research/*、tools/* において設計方針や引数説明を明記。
- config_setup による .env のテンプレート生成ロジックを提供し、ウィザード経由での設定作成手順をドキュメント化。

### 既知の問題 (Known issues)
- research.factor_research の実装は一部（ファイル末尾）で途切れているため、ファクター計算の実装が未完了な箇所がある（今後の実装予定）。
- apply_sector_cap の価格欠損（price が 0.0）時にエクスポージャーの過少見積りとなる可能性があり、将来的に前日終値などのフォールバック価格導入を検討中。
- 一部のシステム操作（プロセス優先度設定、CPU affinity 設定）は権限不足によりスキップされる可能性がある（警告は出るが処理は継続）。

### 互換性 (Compatibility)
- 本リリースは初版のため、後続のリリースで API/CLI の互換性が変わる可能性がある。設定ファイル（.env）や config/*.yaml の形式は将来的に拡張されることがある。

---

メンテナンス情報・追加の注記等は開発履歴に応じて随時更新します。