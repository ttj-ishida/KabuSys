# Changelog

すべての注目すべき変更履歴をここに記録します。本ファイルは "Keep a Changelog" 規約に準拠します。

最新変更
========

0.1.0 - 2026-04-17
------------------

初回リリース

Added
- 全体
  - パッケージバージョンを `__version__ = "0.1.0"` に設定（src/kabusys/__init__.py）。
- 設定管理
  - Settings クラスを追加して環境変数ベースの設定取得を統一（src/kabusys/config.py）。
  - プロジェクトルート自動検出（.git または pyproject.toml を探索）による .env 自動読み込み機能を実装。読み込み順は OS 環境変数 > .env.local > .env（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
  - .env パーサを強化（export 形式対応、シングル/ダブルクォート内でのバックスラッシュエスケープ処理、インラインコメント処理等）。
  - 必須環境変数未設定時の明確なエラーと値検証（KABUSYS_ENV, PAPER_FILL_MODE, LOG_LEVEL など）を実装。
- 設定ツール・検証
  - 対話式ウィザードで .env を生成・更新する CLI を追加（src/kabusys/config_setup.py）。秘密値マスク表示やデフォルト提示、保存前の確認を行う。
  - 起動前設定検証 CLI を追加（src/kabusys/validate_config.py）。必須環境変数・パス・config/*.yaml の存在と YAML パースの検証、`--strict` で警告を FAIL 扱いにできる。
- 実行系ランチャー
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - プロセス優先度を起動時に設定（utils/process_priority.set_process_priority を利用）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine のセッション実行と停止フラグ（data/stop_requested.flag）監視を実装。
    - 実行用 PID ファイルの取り扱い（data/execution.pid）。
  - SystemMonitor（監視）起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番向け sqlite_path を使用する設計。
    - stop_requested.flag の検出によるループ終了、例外キャッチとログ出力を実装。
- モニタリング DB 初期化
  - 監視用 DB の初期化ユーティリティ（init_monitoring_db）を呼び出して監視テーブルの存在を保証（冪等）。
- ポートフォリオ構築（Portfolio）
  - 銘柄選定・重み付け: select_candidates / calc_equal_weights / calc_score_weights を実装（src/kabusys/portfolio/portfolio_builder.py）。
    - calc_score_weights は全銘柄のスコアが 0.0 の場合に等分配へフォールバックし警告を出す。
  - セクター集中制限・レジーム乗数: apply_sector_cap / calc_regime_multiplier を実装（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap は既存保有のセクター別エクスポージャーを計算し上限超過セクターの候補除外を実施。unknown セクターは制限を適用しない。
    - calc_regime_multiplier は "bull"/"neutral"/"bear" をマップし、未知レジームは 1.0 でフォールバック（警告ログ）。
  - ポジションサイジング: calc_position_sizes を実装（src/kabusys/portfolio/position_sizing.py）。
    - risk_based / equal / score の配分方式をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限・全体利用上限（max_utilization）、手数料等を見越した cost_buffer、aggregate cap によるスケールダウンアルゴリズムを提供。
    - 価格欠損時のスキップやログ出力を考慮。
- リサーチ（ファクター計算）
  - Momentum / Volatility 等のファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - DuckDB 接続を受け SQL で高速集計。mom_1m/3m/6m、MA200 乖離、ATR20、平均売買代金などを計算。
    - データ不足時には None を返す設計。
- ユーティリティ
  - プロセス優先度 & CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX 間の差分を吸収して set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足や未対応環境では警告を出してスキップ。
- ツール
  - Paper Trading 向けの検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成功率・送信率、P95 レイテンシ等を集計して PASS/FAIL を判定。閾値はモジュール内定義で調整可能。
    - 日付フィルタ（--from / --to）、DB パス指定（--db / PAPER_TRADING_SQLITE_PATH）をサポート。DB / テーブルが存在しない場合でも安全に処理して可読な出力を返す。
- パッケージエクスポート
  - kabusys.portfolio のトップレベルエクスポートを整備（src/kabusys/portfolio/__init__.py）。

Changed
- .env 読み込み:
  - デフォルトの読み込みポリシーを明文化（OS 環境変数を保護しつつ .env.local を上書き可能にする挙動）。
- 実行/監視スクリプト:
  - 起動直後にプロセス優先度を "high" に設定するように標準化（start-up deterministic behavior）。

Fixed / Improved
- .env パーサの堅牢化:
  - クォート内のバックスラッシュエスケープを正しく処理、クォートなしでのコメント解釈を改善。
  - .env 読み込み失敗時に警告を出して処理を続行（例外でプロセスを止めない）。
- validate_config:
  - PyYAML 未インストール時は YAML 内容検証をスキップし、警告を出すようにして依存性がなくても実行できるように改善。
- run_execution / run_monitoring:
  - 停止フラグ（data/stop_requested.flag）検出による安全停止ロジックを追加。強制停止信号を使わずに正常終了させられる。
  - DB コネクションの確実なクローズ処理を finally ブロックで保証。

Notes / その他
- Paper Trading と本番 DB は分離設計。paper_trading 用の DB はデフォルトで data/paper_trading.db に保管される。
- 一部の実装（例: position_sizing の lot_size の将来的拡張、price のフォールバックロジック）は TODO コメントとして残してあり、将来の改善ポイントを示しています。
- 初回リリース時点でいくつかのモジュールは内部ドキュメントや PortfolioConstruction.md / StrategyModel.md を参照する設計になっており、外部ドキュメントと合わせて運用することを想定しています。

上記はコードベースから推測してまとめた初期リリースの主な変更点です。必要があれば各項目をファイル別に詳述した差分や、想定される使用例・操作手順（起動フロー、環境変数一覧、よくある問題と対処法）を追記します。