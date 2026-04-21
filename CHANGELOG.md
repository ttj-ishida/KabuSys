CHANGELOG
=========

全般
----
- 本ドキュメントは "Keep a Changelog" の書式に準拠しています。
- 日付のない未リリースの変更は "Unreleased" に記載します。

Unreleased
----------
- なし

0.1.0 - 2026-04-21
------------------

Added
-----
- 初回公開リリース。
- 実行用エントリポイント / 起動スクリプトを追加:
  - run_execution.py
    - ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV により paper_trading モードでは専用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離する。
    - BrokerClientFactory を利用してブローカークライアントを生成。paper_trading 時は Mock クライアントを用いる想定。
    - ExecutionEngine を別スレッドで実行し、data/stop_requested.flag や PID ファイル（data/execution.pid）による停止制御に対応。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動用スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
    - 監視は環境にかかわらず本番用の sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）でループを終了。KeyboardInterrupt にも対応。
- 設定 / 環境読み込み機能を追加:
  - config.py
    - .env 自動読み込み機構（プロジェクトルート検出: .git または pyproject.toml を基準）。OS 環境変数を保護しつつ .env / .env.local を読み込む。
    - .env パースの実装（コメント、export プレフィックス、クォート内エスケープ、インラインコメントの扱いなど）。
    - Settings クラスを導入し、アプリケーション全体で使用する設定値をプロパティとして提供（J-Quants, kabu API, DB パス, Paper Trading 設定, 監視閾値, KABUSYS_ENV 判定など）。
    - PAPER_FILL_MODE のバリデーション、有効値チェック。
- 設定関連 CLI を追加:
  - config_setup.py
    - 対話式ウィザードで .env の初期作成 / 更新を支援。
    - シークレット値のマスク表示や選択肢の提示、保存前の確認を実装。
    - .env のテンプレート生成（コメント付き）。Git にコミットしない旨の注記を含む。
  - validate_config.py
    - .env と config/*.yaml の起動前検証ツールを追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、YAML のパースチェック（PyYAML がない場合は警告）、本番環境（live）向けの追加ガードを実装。
    - --strict オプションで警告を失敗として扱うモードをサポート。
- ロギング・プロセス制御ユーティリティを追加:
  - utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - ログレベルとログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで動作。
  - utils/process_priority.py
    - Windows / POSIX（Linux, macOS 等）の差分を吸収してプロセス優先度（"high"/"normal"/"low"）を設定するユーティリティを実装。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - psutil を利用し、権限不足や未実装 API に対しては警告ログを出してスキップする堅牢設計。
- ポートフォリオ構築（純粋関数群）を追加:
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を選択。同点時は signal_rank を使用してタイブレーク。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を実装。全スコアが 0 の場合は等金額へフォールバックして警告。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 同一セクターの既存保有比率が閾値（max_sector_pct）を超える場合、新規候補を除外。sell_codes パラメータで当日売却予定銘柄を除外可能。unknown セクターは上限チェック対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を実装。未知レジームは 1.0 でフォールバックし警告。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に対応した株数計算ロジックを実装。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、投下上限（max_utilization）、手数料/スリッページの見積り（cost_buffer）を考慮した aggregate cap のスケーリング、端数分配ロジックを実装。
    - 価格欠損時のスキップやデバッグログに対応。
  - portfolio/__init__.py で上記機能を公開。
- 監視／モニタリング関連:
  - run_monitoring.py で SystemMonitor の定期チェックを行う起動スクリプトを追加。
  - monitoring_db.init_monitoring_db を起動時に呼び、監視用テーブルが存在することを保証（冪等）。
  - SystemMonitor による check_once() をポーリングで連続実行し例外発生時はログ出力して次回ポーリングまで待機する堅牢化。
- 実行検証ツール:
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツール。PAPER_TRADING_SQLITE_PATH（または --db オプション）で指定した DB から集計。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ、平均/最大レイテンシ、リスク却下数。
    - P95 計算、日付フィルタ（UTC ISO8601 文字列化）、閾値による PASS/FAIL 判定を実装。
- 研究用モジュール（作業中）:
  - research/factor_research.py
    - ファクター計算基盤の実装開始。DuckDB 接続を受け取り prices_daily / raw_financials を参照して Momentum / Value / Volatility / Liquidity 等を算出する設計。モメンタム計算のための定数や関数スケルトンを追加（calc_momentum の実装途中）。
- パッケージメタ:
  - kabusys.__version__ = "0.1.0"

Changed
-------
- （初回リリースのため主に追加のみ）

Fixed
-----
- （初回リリースのため該当なし）

Security
--------
- 環境設定ウィザードで .env の取り扱いに関する注意書きを追加（.env を絶対にコミットしないことを明示）。

Notes / Implementation details
------------------------------
- 設計方針として、ポートフォリオ・ポジション計算モジュールは純粋関数（副作用なし、DB 非依存）として実装されているためユニットテストが容易。
- Logging とプロセス優先度設定は全起動スクリプトから共通のユーティリティを呼び出すことで一貫した挙動を保証。
- .env の自動ロードはプロジェクトルートが検出できない場合はスキップされるため、パッケージ配布後も安全に動作する。
- Paper Trading と本番 DB は明確に分離されており、誤って本番 DB に書き込むリスクを低減する設計になっている。

今後の検討 / TODO
-----------------
- research/factor_research の完全実装（momentum, ATR, value 指標など）。
- 銘柄毎の単元株情報（lot_size）をマスタに持たせる拡張。
- 価格欠損時のフォールバックロジック（前日終値や取得原価の使用）。
- モニタリング / Execution の統合テスト・耐障害テストの追加。
- Vault 等によるシークレット管理を検討（.env の代替）。

--- 
作成日: 2026-04-21（コードベースの内容から推測してまとめました）