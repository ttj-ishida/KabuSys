CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。
リリース日付はコードベースから推測して付与しています。

0.1.0 - 2026-04-24
-----------------

Added
- 実行用スクリプトと監視用スクリプトを追加。
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離して動作する。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、スレッドでのエンジン実行、data/execution.pid に PID を書き込む仕組みを想定。
    - data/stop_requested.flag を監視して安全に停止する挙動を持つ。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。
    - 監視は KABUSYS_ENV に関係なく本番用 sqlite_path（Settings.sqlite_path）を使用して監視データを保持する（monitoring DB 初期化を行う）。
    - 起動時にプロセス優先度を "high" にセットし、data/stop_requested.flag を検知するとループを終了。

- 設定 / 環境変数管理機能を追加。
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートの .env, .env.local を読み込む）。既存 OS 環境変数は保護され、.env.local は上書き可能。
    - .env の行パーサは export 記法、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などに対応。
    - Settings クラスを提供し、各種設定値（J-Quants トークン、kabu API パスワード、DUCKDB/SQLite パス、PaperTrading の挙動、監視閾値、KABUSYS_ENV 判定など）をプロパティ経由で取得可能。
    - PAPER_FILL_MODE の検証、KABUSYS_ENV/LOG_LEVEL の検証を含む。

- 設定検証 CLI を追加。
  - validate_config.py
    - .env と config/*.yaml の整合性チェックを行う CLI。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在チェック、YAML ファイルのパースチェック（PyYAML が無ければスキップして警告）などを実行。
    - --strict オプションで警告を FAIL 扱いにできる。

- 対話式 .env 作成ウィザードを追加。
  - config_setup.py
    - 対話で .env を作成・更新するウィザード。既存 .env の読み込み・再利用に対応。
    - シークレット値は入力時にマスク（表示は "****"）。
    - 保存前に内容を確認する確認プロンプトを提供。
    - .env のテンプレートは Git にコミットしないよう注意書きを出力。

- Paper Trading 検証レポート生成ツールを追加。
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から集計を行い、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数などを算出してレポート出力。
    - P95 算出、日時フィルタ（--from / --to）、閾値による PASS/FAIL 判定を実装。
    - 簡易的な欠損テーブルに対する例外処理（OperationalError の場合は N/A 扱い）を含む。

- ポートフォリオ構築 / ポジションサイズ計算の純関数群を追加。
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順での候補選定。スコア同点時は signal_rank の小さい方を優先。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算。全銘柄スコアが 0 の場合は等金額へフォールバック。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限(max_sector_pct) を超える場合にそのセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数の算出（bull/neutral/bear マッピング、未知レジームは 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算。ロット丸め（lot_size）、単銘柄上限・集約上限（available_cash）を考慮。コストバッファ(cost_buffer) を使った保守的な見積りと、合計額超過時のスケールダウン + 残差処理を実装。

- ユーティリティを追加 / 改良。
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。StreamHandler（stdout）と日時ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリの解決順は引数 > LOG_DIR > デフォルト ("logs/")。ディレクトリ作成失敗時はファイル出力をスキップして標準出力のみで継続。
    - 既存ハンドラは安全に flush/close してから削除し、二重設定を防止。
  - utils/process_priority.py
    - プラットフォーム差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加（Windows の優先度定数や POSIX の nice 値を使用）。CPU affinity 設定も提供。
    - 権限不足や未対応 OS の場合は警告を出してスキップするよう堅牢化。

- パッケージ初期化とバージョン定義。
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

Changed
- .env 自動読み込みの優先度を明確化（OS 環境変数 > .env.local > .env）。OS 環境変数は保護され自動ロードでも上書きされない設計。
- ログ出力は標準エラーではなく標準出力（stdout）を使用するように変更（cron 等の環境で stdout/stderr の統合を考慮）。

Fixed / Robustness
- 環境変数パーサの強化:
  - export KEY=val 形式、クォート文字内のバックスラッシュエスケープ、インラインコメントの扱いを適切に処理。
- run_monitoring / run_execution:
  - 監視ループやエンジン実行で例外発生時にも接続をクローズするよう finally ブロックで後処理を確実に行う。
  - init_monitoring_db() を呼び出して監視テーブルの存在を保証（冪等）。
- logging_setup:
  - ログディレクトリの作成失敗やファイルハンドラ作成失敗時にフォールバックしてコンソール出力のみで継続するよう堅牢化。
- process_priority:
  - 権限不足や未対応プラットフォームでの例外を捕捉し、警告ログを出して処理を中断しないよう改善。

Security / Safety notes
- .env のテンプレート生成時に「.env を絶対に Git にコミットしないこと」を明示。
- validate_config により本番（KABUSYS_ENV=live）での危険な設定（例えば KILL_FLAG_CLEAR_ON_START=1 や LINE の通知設定未設定）を警告するガードを実装。

Notes / Usage
- 主要な CLI / エントリポイント:
  - python -m kabusys.run_monitoring   （監視プロセス起動）
  - python -m kabusys.run_execution    （実行エンジン起動）
  - python -m kabusys.validate_config  （設定検証）
  - python -m kabusys.config_setup     （.env ウィザード）
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 主要な環境変数（抜粋）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABUSYS_ENV, LOG_LEVEL
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視用、デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト: data/paper_trading.db)
  - MONITOR_POLL_INTERVAL (monitor のポーリング間隔秒)
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
  - PAPER_FILL_MODE (instant|partial|never|reject)
  - LOG_DIR（ログ出力先ディレクトリ）

今後の TODO / 既知の制限（コード中コメントより推測）
- portfolio.position_sizing の価格欠損時のフォールバック（前日終値や取得原価など）を実装予定。
- 各種マスタ（lot_size 銘柄別対応）やより細かい手数料・スリッページモデルの導入検討。
- factor_research.py はファクター計算ロジックの続きを実装中（ファイル末尾で未完の印あり）。
- YAML を使った詳細な設定検証には PyYAML が必要（未インストール時は検証をスキップして警告）。

--- 
この CHANGELOG はコード内容からの推測に基づいて生成しました。追加の実装やコミット履歴があれば、さらに詳細に更新できます。