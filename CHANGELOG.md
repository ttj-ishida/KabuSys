CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" — and follows semantic versioning.

Unreleased
---------

### Added
- 起動スクリプトを追加／整理
  - run_execution: ExecutionEngine の起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用の Paper Trading 用 SQLite（data/paper_trading.db をデフォルト）を使用し、MockBrokerClient を通した分離された動作をサポート。停止フラグ（data/stop_requested.flag）検出時の安全停止、PID ファイル管理、デーモンスレッド運用を含む。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（不正値はデフォルト 60 秒にフォールバック）。監視は環境にかかわらず本番 sqlite_path を使用する設計。

- 設定関連
  - 環境変数・設定読み込みモジュール（kabusys.config）を追加。プロジェクトルート自動検出（.git または pyproject.toml）に基づき .env/.env.local を自動ロードする。読み込み時に OS 環境変数を保護する仕組みを持つ。
  - .env パーサーの強化（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理など）。
  - Settings クラスに多くのプロパティを実装（J-Quants / kabu API / LINE / DB パス / PID/KILL フラグパス / 各種閾値 / PAPER_FILL_MODE のバリデーション等）。

- 設定支援 CLI
  - config_setup: 対話式ウィザードで .env の初期作成・更新を支援。シークレットのマスク表示、デフォルト・選択肢、保存確認を提供。
  - validate_config: 起動前の設定検証 CLI を追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パスの警告/エラー、config/*.yaml の存在チェック（PyYAML 有無に応じてパース検証）などを実行。--strict オプションで警告を FAIL 扱いにできる。

- ロギング / プロセス運用ユーティリティ
  - utils.logging_setup: ルートロガーを統一的に設定するユーティリティを追加。コンソール出力は stdout、ファイル出力は日次ローテーション（TimedRotatingFileHandler）で保持日数は 30 日。ログディレクトリの解決順や失敗時のフォールバック挙動を定義。
  - utils.process_priority: クロスプラットフォームでプロセス優先度を設定するユーティリティを追加（Windows / POSIX を吸収）。CPU affinity を最初 N コアに固定する関数も実装。

- ポートフォリオ構築/リスク調整/ポジションサイジング
  - portfolio.portfolio_builder: シグナルの候補選定（スコア降順）と等比率／スコア加重の重み計算を追加。スコア全0 の場合のフォールバック動作あり。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに基づく乗数（calc_regime_multiplier）を追加。未知レジームはフォールバックで 1.0、ログ出力あり。
  - portfolio.position_sizing: 発注株数算出ロジックを実装。risk_based / equal / score の各方式をサポートし、単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超える場合はスケールダウン）や cost_buffer を考慮した保守的な見積り、残差処理による追加配分など複雑な振る舞いを実装。

- Paper Trading 検証ツール
  - tools.paper_verification_report: Paper Trading 用 SQLite（環境変数/PATH 指定可）から集計して検証レポートを生成するスクリプトを追加。稼働率（uptime）、注文成功率、送信率、P95 レイテンシ等を算出し、閾値（既定値）を上回る／下回るかで PASS/FAIL を判定。

- Research 部分のスケルトン
  - research.factor_research: DuckDB を用いたファクター計算モジュールの骨組みを追加（モメンタム、MA200、ATR、出遅れ等の指標を想定）。関数シグネチャと定数を実装（実装途中の箇所あり）。

### Changed
- DB 接続の挙動
  - 監視（run_monitoring）は環境変数 KABUSYS_ENV に依存せず、常に本番向け sqlite_path を使用する方針に明示化（監視 DB は本番テーブルを使う想定）。
  - run_execution は paper_trading 環境時に専用 paper_sqlite_path を使うことで本番 DB と完全分離（デフォルト data/paper_trading.db）。

- リスク管理初期化
  - RiskManager の設定（RiskConfig）がデフォルトで合理的な閾値を持つように（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。初期ポートフォリオ値をブローカーから取得して初期化するよう変更（broker.get_available_cash() を利用）。

- ログのデフォルト挙動
  - StreamHandler を stdout に向けて出力するように統一（cron/スケジューラ環境でのリダイレクトを想定）。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続するフォールバックを追加。

### Fixed
- 環境変数読み込みの堅牢化
  - .env のクォートやエスケープ解析の不具合に対する耐性を向上（export プレフィックス、クォート内のバックスラッシュ、インラインコメントの扱いなどを正しく処理）。

- 優先度設定の安全化
  - set_process_priority / set_cpu_affinity は対応していない OS、権限不足、未実装 API 呼び出し時に警告ログ出力してスキップするようにし、起動を妨げないように改善。

- 監視・起動の安全停止
  - run_execution と run_monitoring に stop flag（data/stop_requested.flag）検出ロジックを追加し、外部からの安全な停止指示を受け取れるようにした。run_monitoring は KeyboardInterrupt にも安全に対応。

Notes
-----
- init_monitoring_db は冪等（存在確認して必要ならテーブルを作成）に実装されており、複数プロセスでの起動や paper_trading 用 DB と monitoring DB の混在を考慮した運用が可能。
- config_setup では .env ファイルを書き出す際に機密情報を明示し、.env を Git にコミットしないよう注意喚起を行う。
- research.factor_research は計算ロジックの骨子を備えていますが、実装途中の箇所（コメント末尾で切れている関数など）があるため、今後の拡充で完全な因子計算パイプラインを目指します。

0.1.0 - 2026-04-24
------------------
- 初回公開バージョン。上記の各機能（起動スクリプト、設定管理、ロギング・プロセスユーティリティ、ポートフォリオ構築一式、Paper Trading 検証レポート、設定ウィザード／検証 CLI、research スケルトン）を含むリリース。