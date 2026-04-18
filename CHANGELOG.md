# Changelog

すべての変更は「Keep a Changelog」形式に準拠して記載しています。  
慣例により、重要な追加・変更点をカテゴリ別に要約しています。

## [Unreleased]

（現在差分なし）

## [0.1.0] - 2026-04-18

初期公開リリース。日本株自動売買システム「KabuSys」の基盤機能を提供します。

### Added
- 全体
  - パッケージ初期バージョンを追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。
  - プロジェクトルートの自動検出機能を実装。`.git` または `pyproject.toml` を基準にルートを特定して .env 自動読み込みを行う（kabusys.config._find_project_root）。
  - .env ファイル読み込みの強化:
    - export プレフィックス対応、引用符付き値のエスケープ処理、インラインコメントの扱い、上書き抑止（protected）の仕組みを実装（kabusys.config._parse_env_line / _load_env_file）。
    - OS環境変数を保護して .env.local を上書き可能にする挙動を採用。
  - Settings クラスを実装して環境変数を型付きで提供。環境名検証、ログレベル検証、パスプロパティ、Paper Trading 向け設定（paper_sqlite_path, paper_fill_mode など）を追加（kabusys.config.Settings）。
  - 設定検証 CLI を追加（python -m kabusys.validate_config）。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DBパス・config/*.yaml のチェック、live 環境向けのガード（LINE 通知・Kill Flag 設定の警告）を実装。
  - 対話式環境設定ウィザードを追加（python -m kabusys.config_setup）。.env の生成・更新を支援し、複数の設定項目（J-Quants, kabu API, DB パス, LINE, LOG_LEVEL, Kill Switch 等）を対話で入力可能。
  - ログ設定ユーティリティを追加（kabusys.utils.logging_setup.setup_logging）。
    - stdout に出力する StreamHandler と日次ローテーションする TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続する安全処理を実装。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows / POSIX (Linux, Darwin, FreeBSD) に対応した優先度設定（high/normal/low）と、CPU ピンニング（set_cpu_affinity）を提供。権限不足や未サポート環境時は警告を出してスキップ。
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用専用 SQLite を使用して本番 DB と分離（settings.paper_sqlite_path）。
    - BrokerClientFactory を経由してブローカクライアントを生成（paper_trading 時はモックを想定）。
    - OrderRepository・OrderManager・RiskManager・Reconciler を組み立て、ExecutionEngine をスレッドとして起動。stop flag（data/stop_requested.flag）検知で安全に停止。
    - エンジン用 pid ファイルパスを指定可能（data/execution.pid）。
  - 監視（モニタリング）起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（監視データは本番 DB と共有）。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了。チェック実行時の例外はログに記録して継続。
  - 監視 DB 初期化ユーティリティ（init_monitoring_db）を run 系で呼び出して監視テーブルの存在を保証（冪等）。
  - DuckDB を分析用バックエンドとして統合するための接続箇所を追加（Settings.duckdb_path を基に接続）。
  - Paper Trading 検証レポート生成ツールを追加（kabusys.tools.paper_verification_report）。
    - 指定期間の system_status / trade_logs / risk_logs を集計して稼働率・注文成功率・送信率・レイテンシ指標（P95 等）を算出し、PASS/FAIL 判定を出力。
    - P95 計算、各種閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。
    - コマンドライン引数で期間指定（--from / --to）や DB パス（--db）を受け付ける。
  - ポートフォリオ構築モジュールを追加（kabusys.portfolio）。
    - portfolio_builder:
      - select_candidates: BUY シグナルのスコア降順で上位 N を選出（signal_rank をタイブレークに使用）。
      - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を提供。スコア全体が 0 の場合は等金額にフォールバックして警告。
    - risk_adjustment:
      - apply_sector_cap: セクター集中上限（max_sector_pct）を超える既存保有がある場合、新規候補の同セクターを除外するロジックを実装。unknown セクターは除外対象外。
      - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（デフォルト値とフォールバック挙動を実装）。
    - position_sizing:
      - calc_position_sizes: allocation_method（"risk_based", "equal", "score"）に応じて発注株数を計算。リスクベースでは risk_pct / stop_loss_pct に基づく算出、max_position_pct 上限、単元株（lot_size）丸めを実装。
      - aggregate cap (available_cash) を超える場合のスケーリング、cost_buffer（手数料・スリッページ見積り）を考慮した保守的な見積り、残差処理による lot 単位での追加配分を実装。
  - research/factor_research モジュール（未完の箇所あり）を追加。DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity の計算基盤を提供する設計。モメンタム計算関数（calc_momentum）の実装開始（営業日ベースの窓設定等）。
  - パッケージ構造:
    - utils, portfolio, monitoring, execution, tools, research 等の名前空間を整備し、__all__ エクスポートを設定。

### Changed
- logging: 標準出力に出力する方針を明示（stdout を用いることで Task Scheduler/cron でのリダイレクト運用を想定）。
- DB/ファイルパスに対する検証メッセージを改善（validate_config にて親ディレクトリの存在チェックと説明を追加）。
- 実行/監視スクリプトにおいて、起動時のプロセス優先度設定を最初に行うよう変更（安定性向上目的）。

### Fixed
- .env パースの次のケースに対処:
  - export 付き行の処理、引用符内のバックスラッシュエスケープ、コメントの取り扱い。
- run_monitoring の MONITOR_POLL_INTERVAL に不正値がセットされた場合に sleep() に渡す前にフォールバックするようにして ValueError を回避。

### Deprecated
- なし

### Removed
- なし

### Security
- 機密値（J-Quants トークン、kabu API パスワード、LINE トークン）は Settings 経由で取得し、config_setup の出力ではマスク表示（****）する等、取り扱いに配慮した出力を実装。

---

注記:
- 一部モジュール（例: research.calc_momentum の末尾）は実装途中の形跡があり、今後のリリースで完成・拡張される予定です。
- 実行に必要な外部パッケージ（psutil, duckdb, PyYAML など）が存在しない環境での振る舞いはそれぞれのモジュール内でフォールバックや警告を行います。設定検証スクリプトで依存を確認することを推奨します。