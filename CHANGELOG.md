KEEP A CHANGELOG
=================

すべての変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

Unreleased
----------

なし

0.1.0 - 2026-04-23
------------------

Added
- 実行スクリプト / デーモン類を追加・整備
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度の設定、PID ファイル・停止フラグの扱い、スレッド実行ループを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db、環境変数で上書き可）を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成を組み込み、OrderRepository / OrderManager / RiskManager / Reconciler を連携して ExecutionEngine を起動。
    - RiskManager の初期設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定し、初期ポートフォリオ値を broker.get_available_cash() で取得。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバックして警告）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。

- 設定管理・セットアップ・検証
  - config.py:
    - .env 自動ロード実装（プロジェクトルート判定: .git または pyproject.toml）。
    - .env のパース機能強化: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ解釈、インラインコメント処理。
    - 多数の設定プロパティを提供（DB パス、Paper Trading の設定、監視閾値、KABUSYS_ENV/LOG_LEVEL 等）と検証ロジック。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
  - config_setup.py:
    - 対話式 .env 初期作成・更新ウィザードを実装。デフォルト値、選択肢、シークレット入力、既存 .env の読み込みと確認画面、保存機能を提供。
  - validate_config.py:
    - 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス親ディレクトリ存在チェック、config/*.yaml の存在・パース（PyYAML がない場合はスキップ）を実施。
    - --strict オプションで警告を FAIL 扱いにできる。
    - KABUSYS_ENV=live の追加安全チェック（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の危険設定への警告）を実装。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py:
    - 統一的なログ設定ユーティリティを提供。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR 環境変数や関数引数で挙動を制御。ログディレクトリ作成失敗時はファイル出力をスキップして警告を出す。
    - 既存ハンドラのクリーンアップ処理（flush/close）を実装し、二重登録を防止。
  - utils/process_priority.py:
    - psutil を用いたプロセス優先度（Windows の priority class / POSIX の nice 値）設定ユーティリティを追加。
    - Windows / Linux/macOS 等の差分を吸収し、未対応 OS や権限不足時は警告を出してスキップ。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity() を提供。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - 候補選定と重み計算関数を提供: select_candidates（スコア降順 + tie-breaker）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合に等配分へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: 同一セクターの既存保有比率が上限を超える場合、新規候補を除外するセクター制限ロジックを実装。売却予定銘柄の除外や "unknown" セクターの扱いを明記。
    - calc_regime_multiplier: market regime に応じた投下資金乗数を提供（bull=1.0, neutral=0.7, bear=0.3。未知レジームは警告を出して 1.0 にフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method に応じて発注株数を計算するロジックを実装。
      - risk_based / equal / score の各方式に対応。
      - 単元株（lot_size）で丸め、1 銘柄上限（max_position_pct）、最大利用率（max_utilization）を考慮。
      - cost_buffer を用いた保守的見積り、合計投資額が利用可能現金を超える場合にスケールダウンして残差を lot 単位で補填するアルゴリズムを実装。
      - 価格欠損時のスキップやログ出力を実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成ツールを追加。PAPER_TRADING_SQLITE_PATH 環境変数（または --db オプション）で DB を指定して実行可能。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）、リスク却下数 等を算出。
    - P95 計算、期間フィルタ、閾値による Pass/Fail 判定（デフォルト閾値をコード内で定義）を実装。
    - DB テーブル欠損（OperationalError）時のフォールバック処理を実装。

- 研究用ファクター計算モジュール
  - research/factor_research.py:
    - Momentum / Value / Volatility / Liquidity 等のファクター計算方針と定数を実装（DuckDB 参照、prices_daily / raw_financials テーブルを前提）。（実装途中の関数あり）

Changed
- パッケージの公開情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

Fixed
- .env パーサの堅牢性向上
  - クォート内のバックスラッシュエスケープや export 形式、インラインコメントの扱いを改善し、実運用での .env パースに起因する誤動作を低減。

- ログの出力先・取り扱い改善
  - logging_setup: stdout を利用するようにして外部ジョブランナーからのリダイレクト運用に適合。ログディレクトリ作成失敗時のフォールバックを明確化。

Security
- 環境変数の取り扱い注意を強調
  - config_setup で生成される .env のヘッダに「.env は絶対に Git にコミットしないこと」と明記。

Notes / その他
- validate_config は PyYAML 未インストール時に YAML の検証をスキップするが、その事実を警告として表示する。
- run_monitoring は監視 DB 初期化（init_monitoring_db）実行、duckdb 接続確立を行い SystemMonitor の check_once() をポーリング呼び出し。例外はログに記録して次回ポーリングへ継続。
- run_execution は停止フラグ検知時に engine.stop() を呼び出してセーフシャットダウンを試みる。スレッド join のタイムアウトを設定して確実に終了するようにしている。

References
- 各モジュールの詳細は src/kabusys 以下の各ファイルをご参照ください。