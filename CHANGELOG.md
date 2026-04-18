CHANGELOG
=========

すべての注目すべき変更点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-18
--------------------

Added
- 初期リリース。日本株自動売買システム "KabuSys" の基本機能を実装。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の独立した SQLite（デフォルト: data/paper_trading.db）を利用する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクト直下の data/stop_requested.flag を検知して行う。
- 設定管理
  - config.py: .env の自動読み込み機構と Settings クラスを実装。多くの環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）をプロパティとして提供し、妥当性チェックを実施。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。シークレット項目のマスク表示や選択肢サポート、.env の書き出しを提供。
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。--strict オプションで警告を FAIL 扱いにできる。PyYAML 未インストール時は YAML 検証をスキップして警告を出す。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: ルートロガーの初期化ユーティリティを追加。StreamHandler（stdout）と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app>.log、30 日保持）を設定。既存ハンドラをクリアして二重登録を防止。ログディレクトリ作成失敗時はファイル出力を自動的に無効化してコンソールのみで継続。
  - utils/process_priority.py: プロセス優先度および CPU affinity 設定ユーティリティを追加。Windows / POSIX（Linux/Mac/FreeBSD）を吸収し、権限不足や未対応環境では警告を出してスキップする。set_cpu_affinity により最初の N コアにピン留め可能。
- ポートフォリオ構築モジュール（純粋関数群）
  - kabusys.portfolio.portfolio_builder
    - select_candidates: スコア降順・タイブレークに signal_rank を考慮して候補抽出。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア正規化配分を実装。全スコアが 0 の場合は等金額にフォールバックして警告を出す。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック。既存保有と価格マップからセクター別エクスポージャーを計算し、上限超過セクターの候補銘柄を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じて投下資金乗数を返す（デフォルトマップ: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告の上 1.0 でフォールバック。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じて株数を計算。単元株（lot_size）で丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）を考慮してスケーリング。cost_buffer による保守的見積りをサポート。価格欠損時のスキップやログ出力あり。
- 研究 / ファクター計算基盤
  - kabusys.research.factor_research: DuckDB 接続を受けて prices_daily / raw_financials を用いたモメンタム等のファクター計算骨子を実装（モメンタム計算関数等の実装開始、設計方針・定数定義を含む）。
- モニタリング / ペーパートレード検証ツール
  - monitoring テーブル初期化ユーティリティ（monitoring_db.init_monitoring_db）呼び出しを run_execution / run_monitoring で実行し、監視テーブル存在を保証（冪等）。
  - tools/paper_verification_report.py: ペーパートレードの検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95）等を集計して PASS/FAIL を判定する CLI（--from/--to/--db オプション）。閾値はソース内定数として定義（例: 稼働率 >=99%、P95 <=200ms など）。P95 計算と欠損データ対応あり。

Changed
- ログ出力の標準化: 全起動スクリプトで setup_logging を使用する設計に統一。
- .env 自動読み込みの優先順を明示（OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
- run_monitoring は監視用 DB 接続（sqlite）を環境にかかわらず "本番" sqlite_path を使用するように設計（設計上の分離）。
- run_execution は paper_trading 環境時に paper_sqlite_path を使用し本番 DB と完全分離する設計に変更。

Fixed
- .env パーサの堅牢化:
  - export KEY=val 形式に対応。
  - シングル/ダブルクォートを含む値のパース、バックスラッシュエスケープ処理を実装。
  - クォートなし値の行内コメント扱い（'#' の前がスペース/タブの場合）。
  - 無効行をスキップすることで読み込みの安定化。
- Logging ハンドラの二重登録防止（既存ハンドラを flush/close してから削除）により複数回起動時の重複出力を回避。
- process_priority / set_cpu_affinity は権限不足や未実装 API を捕捉して警告を出し、起動失敗を防ぐ。

Security
- .env 書き出し時に注意書きを付加（.env を Git にコミットしない旨を明記）。

Notes / Implementation details
- ExecutionEngine の初期 RiskConfig にはデフォルト値を設定（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。initial_portfolio_value は broker.get_available_cash() により初期化されるため、Broker の実装が必要。
- run_execution はデーモンスレッドで engine.run_session を起動し、data/stop_requested.flag の検出で安全に engine.stop() を呼ぶ設計。pid ファイルパスもサポート。
- run_monitoring の例外処理: monitor.check_once() での予期しない例外はログに残して次ポーリングへフォールバックする（監視継続性を優先）。
- Paper Trading と本番 DB の分離を徹底（デフォルトファイル名および環境変数名で明示）。

開発者向けメモ
- __version__ は 0.1.0 に設定済み。
- 一部モジュール（research.factor_research など）はファイル末尾で実装が途中（切れている箇所）が見られるため、継続実装が必要。
- 外部依存: psutil, duckdb, (任意で) PyYAML。PyYAML がない場合は YAML の内容検証はスキップされるが警告が出る。

--- 

（本 CHANGELOG はソースコードの内容から推測して作成しています。実際のコミット履歴や issue に基づくものではありません。必要に応じて日付・内容を調整してください。）