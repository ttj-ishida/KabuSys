CHANGELOG
=========

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

フォーマットの意味:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated: 非推奨
- Removed: 削除
- Security: セキュリティ関連

Unreleased
----------

（現在未リリースの変更はここに記載）

0.1.0 - 2026-04-19
------------------

Added
- 基盤機能の初期実装を追加（初回リリース）。
  - パッケージメタ情報:
    - kabusys.__version__ = "0.1.0"
  - 実行スクリプト:
    - run_execution.py: ExecutionEngine 起動用スクリプト。
      - KABUSYS_ENV に応じて paper_trading モード用の専用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番データと分離。
      - BrokerClientFactory を使用してブローカークライアントを生成。
      - ExecutionEngine をスレッドで実行し、data/stop_requested.flag による安全停止および data/execution.pid 管理をサポート。
      - プロセス優先度を「high」に設定して起動。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 環境に関わらず本番 sqlite_path を監視 DB として使用。
      - stop フラグ（data/stop_requested.flag）でループ終了。
      - 監視用 DB 初期化（init_monitoring_db）と DuckDB 接続を行う。
  - 設定管理:
    - config.py:
      - .env 自動ロード機能（プロジェクトルート判定: .git または pyproject.toml を探索）。
      - .env と .env.local の読み込み順序（OS 環境変数を保護）。
      - 環境変数の厳密な取得ユーティリティ（必須変数チェック、各種パス・閾値のプロパティ）。
      - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、KABUSYS_ENV、LOG_LEVEL 等の設定をサポート。
      - Settings クラスとデフォルトの settings インスタンスを提供。
    - config_setup.py:
      - 対話式ウィザードで .env の初期作成・更新が可能。
      - 複数の設定項目（API トークン、DB パス、ログレベル、Kill Switch の振る舞い 等）を案内。
  - 設定検証 CLI:
    - validate_config.py:
      - .env および config/*.yaml の存在・基本妥当性チェックと出力。
      - --strict オプションで警告を失敗扱いにする機能。
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリチェック、YAML パースチェック（PyYAML が存在する場合）等を実施。
  - ポートフォリオ構築（純関数群）:
    - portfolio/portfolio_builder.py:
      - 選定ロジック select_candidates（スコア降順、同点は signal_rank でブレーク）。
      - 等配分 calc_equal_weights、スコア加重 calc_score_weights（全スコア 0 の場合は等配分にフォールバック）。
    - portfolio/risk_adjustment.py:
      - apply_sector_cap: セクター集中制限ロジック（既存保有を考慮して新規候補を除外）。
      - calc_regime_multiplier: market regime（bull/neutral/bear）に応じた投下資金乗数。
      - 未知レジーム時はログ警告を出し 1.0 でフォールバック。
    - portfolio/position_sizing.py:
      - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算、単元株（lot_size）丸め、aggregate cap によるスケールダウン処理、cost_buffer の考慮。
      - aggregate スケーリング時に残差の取り扱い（fractional remainder）を安定的に配分。
      - TODO コメントで将来の lot_size 拡張（銘柄別単元）を明示。
  - ユーティリティ:
    - utils/logging_setup.py:
      - 統一的なログ設定関数 setup_logging を提供。
      - stdout への StreamHandler（タスクスケジューラ対策）と日次ローテーションの TimedRotatingFileHandler を設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
    - utils/process_priority.py:
      - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供し、Windows と POSIX の差分を吸収。
      - 権限不足や未対応 OS の場合は警告ログを出し安全にフォールバック。
  - モニタリング / 監視関連:
    - monitoring テーブル初期化用 init_monitoring_db の利用（monitoring DB の存在保証）。
    - SystemMonitor を利用した単発チェック check_once 呼び出しのループ構造（例外保護あり）。
  - Paper Trading 向けツール:
    - tools/paper_verification_report.py:
      - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計してレポートを生成。
      - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定を出力。
      - 日付フィルタ（--from / --to）と --db オプションに対応。
  - 研究用モジュール（DuckDB ベースのファクター計算）:
    - research/factor_research.py（骨格実装）:
      - Momentum、MA200乖離、ATR、出来高指標などを計算する設計。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する方針を記載。
      - 実装中（ファイルの末尾が未完の状態を含む）。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Deprecated
- なし。

Removed
- なし。

Security
- 機密情報 (.env) の取り扱いについて注記:
  - config_setup にて .env を生成する際に「.env を絶対に Git にコミットしないこと」を README 相当の注釈として明記。

Notes / Known issues / TODO
- position_sizing.calc_position_sizes:
  - price_map に価格が欠損（0.0）の場合にエクスポージャーが過少評価される可能性がある旨の TODO コメントあり。前日終値や取得原価でのフォールバックを将来的に検討する必要あり。
  - lot_size を銘柄別に対応する拡張が TODO として残っている。
- research/factor_research.py:
  - ファイル末尾で実装が途中（トランケートあり）。完全実装は今後の課題。
- logging_setup:
  - ログディレクトリ作成やファイルハンドラ作成に失敗した場合はコンソールのみで継続する設計。運用環境ではログディレクトリの権限とディスク容量を確認すること。
- process_priority / set_cpu_affinity:
  - 一部 OS や権限によっては設定が適用されない場合があるため、運用時はログを確認すること。
- validate_config:
  - PyYAML 未導入時は config/*.yaml の検証をスキップする旨の警告を出すが、YAML が重要な環境では PyYAML の導入を推奨。

参考（環境変数）
- いくつかの環境変数を使用／提供:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
  - KABUSYS_ENV (development | paper_trading | live)
  - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト data/paper_trading.db)
  - LOG_LEVEL, LOG_DIR
  - MONITOR_POLL_INTERVAL（監視ポーリング間隔）
  - PAPER_FILL_MODE（paper_trading の fill 動作: instant|partial|never|reject）
  - KILL_FLAG_CLEAR_ON_START（本番での自動クリア抑止推奨）

今後の予定
- research/factor_research の完成（duckdb を用いた各種ファクター計算の実装完了）。
- position_sizing の lot_size 銘柄別対応と価格フォールバックロジックの追加。
- テストカバレッジの拡充（ユニットテスト・統合テスト）。
- 運用観点での監視・アラート連携（LINE 通知の実運用テスト）。

----- 
（この CHANGELOG はソースコードのコメントや実装から推測して作成しています。実際のリリースノートとして使用する場合は、変更の意図や実装履歴と照合して必要に応じて修正してください。）