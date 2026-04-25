CHANGELOG
=========

すべての注目すべき変更点をこの文書に記録します。
フォーマットは "Keep a Changelog" に準拠します。

0.1.0 - 2026-04-25
------------------

Added
- 初期リリース: KabuSys 自動売買システムの基礎モジュールとユーティリティを追加。
- 実行スクリプト:
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の際は paper_trading 専用 SQLite（data/paper_trading.db など）を使用し、MockBrokerClient によるペーパートレードが可能。
    - 停止用フラグ（data/stop_requested.flag）検出で安全に停止。実行時の PID ファイル保存場所をサポート。
    - プロセス優先度を "high" に設定してから起動。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を使用する設計。
    - 停止フラグ検出でループを終了し、例外発生時はログを残して次ポーリングへ継続。
- 設定・環境管理:
  - config.py: 環境変数読み込み・Settings クラスを実装。
    - .env / .env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml が基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 複雑な .env パース実装: export プレフィックス、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理をサポート。
    - 各種設定プロパティ（PAPER_FILL_MODE の有効値チェック、パス類、閾値、環境判定プロパティなど）を提供。
- 設定支援 CLI:
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。
    - J-Quants / kabu API / DB パス / ログレベル / Kill Switch など主要項目を対話形式で入力可能。
    - シークレット項目は表示をマスクして扱う。
  - validate_config.py: 起動前に .env と config/*.yaml の妥当性を検証する CLI を追加。
    - 必須環境変数の未設定チェック、KABUSYS_ENV/LOG_LEVEL 値チェック、DB パス親ディレクトリ存在確認、YAML ファイルの存在と（PyYAML があれば）パース検証を実行。
    - --strict オプションで警告も失敗扱いにできる。
- 分析・検証ツール:
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成ツールを追加。
    - PAPER_TRADING_SQLITE_PATH（または --db）からデータを読み込み、稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（avg/max/P95）等を集計・判定（PASS/FAIL）する。
    - デフォルトの閾値を設定（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）。
- ポートフォリオ構築ライブラリ:
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのソートと上位選定（スコア降順、同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア重み配分（スコア合計が 0 の場合は等配分にフォールバック）を提供。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限ロジック（既存保有のセクター別エクスポージャーを評価し、上限超過セクターの新規候補を除外）。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear をマッピング、未知レジームはフォールバックして警告）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算。リスクベース算出、最大保有比率・lot_size による丸め、aggregate cap によるスケーリング、cost_buffer を考慮した保守的なコスト見積もり、残余キャッシュを用いた端数配分ロジックを実装。
- ユーティリティ:
  - utils/logging_setup.py:
    - 統一的なログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。
    - LOG_LEVEL と LOG_DIR の解決順を明示。ログディレクトリ作成失敗時はファイル出力をスキップし stdout のみで継続。
  - utils/process_priority.py:
    - プロセス優先度設定（Windows と POSIX の差分を吸収）と CPU affinity 固定機能を追加。権限不足や未対応 OS 時は警告を出してスキップ。
- Execution internals:
  - execution 起動時に BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine を組み立ててセッションをスレッドで実行する設計を実装。
  - RiskManager のデフォルト構成例を実装（max_position_pct, max_utilization, rate_limit_per_sec 等）および初期ポートフォリオ値に broker.get_available_cash() を使用。
- データベース:
  - init_monitoring_db 関数を起動側で呼び出し、監視テーブルが存在することを冪等に保証（monitoring 系と execution 起動時に利用）。
  - DuckDB 接続サポート（分析用 DB）を各起動スクリプトで確立。

Changed
- （初期リリースのため該当なし。設計上の重要挙動は Added に記載）
  - 監視は常に settings.sqlite_path（本番監視 DB）を使用する点は動作仕様として明示。

Fixed
- .env パーサの強化（export プレフィックス、引用符内のエスケープ、インラインコメント扱いなど）を実装し、実運用での柔軟性を向上。

Security
- config_setup により生成される .env のヘッダに「.env は絶対に Git にコミットしないこと」を明示。
- シークレット項目（API トークン等）はウィザードでマスクして扱う。

Notes / Operational
- MONITOR_POLL_INTERVAL に 0 以下や非整数を設定した場合、デフォルト値（60 秒）にフォールバックして警告を出力します。
- run_execution/run_monitoring は起動時にプロセス優先度を "high" に設定しようとしますが、OS 権限によっては失敗する場合があり、その際は警告が出ます（実行は継続）。
- run_execution は停止フラグ（data/stop_requested.flag）を検出すると安全にエンジンを停止／起動停止します。run_monitoring も同様の停止フラグ検出を行います。
- validate_config は PyYAML 未導入時に YAML 内容チェックをスキップして警告を出力します。PyYAML を導入すると config/*.yaml のパース検証が有効になります。

Breaking Changes
- なし（初期リリース）。

Acknowledgements / TODO
- research/factor_research.py はファクター計算の骨組みを実装開始（モメンタム等の定義あり）。実装途中の箇所があり、将来的に完備予定。
- position_sizing の lot_size は現状グローバル固定（デフォルト 100）。将来的に銘柄別 lot_map に対応する予定（コード内に TODO を記載）。

---

（以降のバージョンでは Unreleased セクションを追加し、変更履歴を逐次記録してください。）