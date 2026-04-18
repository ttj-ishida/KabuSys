# Keep a Changelog

すべての重要な変更点をここに記載します。  
フォーマットは "Keep a Changelog" に準拠します。

## [0.1.0] - 2026-04-18
初回リリース。

### Added
- 基本パッケージ構成と主要コンポーネントを追加（KabuSys: 日本株自動売買システム）。
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用する仕組みを組み込み。
    - paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - 実行中の PID を data/execution.pid に記録する仕組み（pid_file）。
    - stop flag (data/stop_requested.flag) による安全停止対応。
    - エンジンをスレッドで実行し、停止検知で安全に stop() を呼ぶループを実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を参照して初期化。
    - stop flag による停止検知、KeyboardInterrupt での終了処理を実装。
- 設定関連
  - config.py: 環境変数 / .env 読み込みと Settings クラスを追加。
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動読み込み機能を実装（.env/.env.local の取り扱い: OS 環境変数を保護）。
    - 複数の設定プロパティを提供（DB パス、API トークン、KABUSYS_ENV, PAPER_FILL_MODE 等）と値検証。
  - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を追加。
    - 秘匿項目のマスク表示、選択肢/デフォルト表示、保存確認を提供。
  - validate_config.py: 起動前検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスや config/*.yaml の存在・パースチェック、KABUSYS_ENV=live 時の追加ガードを実装。
- 監視関連
  - monitoring_db の初期化呼び出し（init_monitoring_db）を適切に使用して監視テーブル存在を保証。
- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なログ初期化関数を追加。
    - コンソール (stdout) 出力と日次ローテーションのファイル出力（logs/<app_name>.log、30日保持）を設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定を提供（psutil ベース）。
- ポートフォリオ構築ライブラリ（純関数）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順選定（同点は signal_rank でブレーク）。
    - calc_equal_weights, calc_score_weights: 等金額／スコア加重配分を実装（スコア全0時は等分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限（既存保有を考慮して新規候補を除外）。
    - calc_regime_multiplier: レジーム毎の投下資金乗数（bull/neutral/bear）を実装。
  - portfolio/position_sizing.py:
    - calc_position_sizes: risk_based / equal / score の配分方式に対応した株数計算。
    - 単元株（lot_size）丸め、per-position / aggregate cap、cost_buffer を用いた保守的見積り、スケールダウンと残差処理ロジックを実装。
- 研究・ファクター計算（下地）
  - research/factor_research.py: Momentum 等のファクター計算を行うための設計と一部実装（DuckDB を利用、prices_daily / raw_financials の想定）。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツールを追加。
    - 稼働率、注文成功率、送信率、レイテンシ(P95) 等を集計・判定（閾値を定義し PASS/FAIL を判定）。
    - --from/--to/--db オプション対応。
- パッケージメタ
  - __init__.py にて __version__ = "0.1.0" を設定。

### Changed
- .env の自動読み込みの挙動
  - OS 環境変数を保護（既存の環境変数が優先される）。.env.local は .env を上書き可能（override）で読み込む。
- ログ出力のデフォルト
  - stdout を使用する設計（cron/Task Scheduler での一元リダイレクトを想定）。
- run_monitoring/run_execution のプロセス起動時にプロセス優先度を最初に設定するように統一。

### Fixed / Robustness
- .env パーサの強化
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、行内コメントの扱い（クォート外のみ有効）に対応してロバスト性を向上。
- Settings 側の値検証強化
  - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等の入力値チェックを追加し、不正値時は明確なエラーを返す。
- process_priority / set_cpu_affinity の例外処理
  - 権限不足や未サポート環境での安全なフォールバック（警告ログ）を実装。
- run_execution/run_monitoring のリソースクリーンアップ
  - finally ブロックで SQLite / DuckDB 接続を確実にクローズするようにした。

### Removed
- なし

### Security
- 環境変数取り扱い・シークレット管理に注意点を明記（.env は絶対に Git にコミットしない旨を config_setup の生成ファイルに注記）。

---

注:
- 本 CHANGELOG は提示されたコードベースから推測して作成したもので、実際のコミット履歴ではありません。実装の詳細や追加の変更点はソース管理のコミットログを参照してください。