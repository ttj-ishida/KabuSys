CHANGELOG
=========

この CHANGELOG は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) のスタイルに準拠します。  
コードベースの内容から推測して作成しています。実際の変更履歴と差異がある場合があります。

[Unreleased]
-------------

- （現在のコードベースに対する未リリースの差分はありません）

[0.1.0] - 2026-04-23
-------------------

Added
- パッケージ初版を追加（__version__ = 0.1.0）。
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用の Mock ブローカーを使用し、paper_trading 用 DB（デフォルト data/paper_trading.db）に完全分離して記録する仕組みを実装。
    - 起動時にプロセス優先度を "high" に設定するフックを追加。
    - 停止フラグ（data/stop_requested.flag）・PID ファイル（data/execution.pid）に対応し、安全に停止できる監視を実装。
    - 依存コンポーネント（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine）の組み立てロジックを追加。RiskConfig にデフォルト値を設定（max_position_pct, max_utilization 等）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックし警告を出力。
    - 監視用 DB の初期化（init_monitoring_db）と DuckDB 接続を行う。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了する仕組みを実装。
- 設定関連
  - config.py
    - 環境変数自動読み込み機能を実装（プロジェクトルートに .git または pyproject.toml を検出して .env / .env.local を読み込む）。
    - .env パーサや保護付き上書きロジックを導入（OS 環境変数の保護）。
    - Settings クラスを導入し、J-Quants / kabu API / DB パス / 各種閾値 / 環境判定（is_live, is_paper, is_dev）などをプロパティとして提供。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, KILL_FLAG_CLEAR_ON_START 等の環境変数を追加・検証。
    - KABUSYS_ENV, LOG_LEVEL の入力検証を追加（不正値は ValueError）。
  - config_setup.py
    - 対話式ウィザードで .env ファイルの初期作成・更新を行う CLI を追加。既存値の再利用、シークレットマスク表示、保存前の確認を実装。
- 設定検証ツール
  - validate_config.py
    - .env および config/*.yaml の基本的な整合性チェックを行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML の存在とパース検証（PyYAML 未インストール時はスキップ）を実装。
    - --strict フラグで警告も失敗（exit(1)）として扱うオプションを追加。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、既定 30 日保持）を設定するユーティリティ関数 setup_logging を追加。
    - ログレベル解決順（関数引数 > 環境変数 LOG_LEVEL > デフォルト）とログディレクトリ解決順（引数 > LOG_DIR > logs/）を実装。
    - ログディレクトリ作成失敗時にはファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度を設定する set_process_priority を追加（Windows / POSIX に対応）。AccessDenied 等は警告を出してスキップ。
    - CPU 固定用の set_cpu_affinity を追加（利用可能なコア数を自動判定、失敗時は警告）。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順、タイブレークに signal_rank）、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコア 0 の場合は等分にフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限を行う apply_sector_cap（既存保有のセクターエクスポージャーから上限超過セクターをブロック）を実装。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear マッピング、未知レジームは 1.0 でフォールバック）を実装。
  - portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: "risk_based", "equal", "score" をサポート）。
    - 損切り幅、許容リスク率、1銘柄上限、最大投下率、単元株丸め（lot_size）や手数料バッファ（cost_buffer）を考慮した Aggregate Cap スケーリングアルゴリズムを実装。
    - aggregate スケーリング時に残余キャッシュで fractional remainder に基づき単元株単位で追加配分するロジックを実装。
- 研究用モジュール
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュールを追加（モメンタム / MA200 乖離 / ATR / 各種ファクター方針のコメントと計算ロジックの骨子を含む）。（ファイル末尾が途中で切れているため実装未完の箇所あり）
- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。SQLite（デフォルト data/paper_trading.db）からシステム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）等を集計して判定（PASS/FAIL）を行う。
    - P95 計算、日付フィルタ（--from / --to）対応、閾値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）。
    - DB が存在しない・テーブルがない場合のフェールセーフなフォールバックを実装。
- パッケージエクスポート
  - portfolio パッケージの __init__ を整備し主要関数を再エクスポート。

Changed
- なし（初版のため該当なし）

Fixed
- なし（初版のため該当なし）

Removed
- なし

Deprecated
- なし

Security
- なし

Notes / Known limitations / TODO
- config.py の .env 自動ロードはプロジェクトルートの検出に依存する（.git または pyproject.toml）。配布後に期待通り動作するように設計されているが、ルートを特定できない場合は自動ロードがスキップされる。
- .env パーサは引用符やエスケープ、行内コメントの処理に対応しているが、完全なシェル互換パーシングではないため特殊なケースで挙動が異なる可能性がある。
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に価格欠損（0.0）がある場合、エクスポージャーが過小見積りされる問題がある旨の TODO コメントあり。将来的にフォールバック価格の導入を検討中。
- research/factor_research.py はファイル末尾で途中（start_da で切れている）になっており、完全実装ではない可能性がある。
- logging_setup はログディレクトリの作成に失敗した場合にファイル出力をスキップする設計。運用環境ではログディレクトリ権限を事前に確認することを推奨。
- process_priority / set_cpu_affinity は権限不足（root などが必要）やプラットフォーム依存で失敗する可能性があり、その場合は警告を出して処理をスキップする。

Usage examples
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite ファイルを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

Contributing
- 初版リリースに関する修正・機能追加は Pull Request を歓迎します。テスト、ドキュメント、YAML 設定生成スクリプトなどの整備が次の優先事項です。