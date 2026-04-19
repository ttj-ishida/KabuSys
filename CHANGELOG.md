CHANGELOG
=========

すべての重要な変更点をこのファイルで記録します。フォーマットは「Keep a Changelog」に準拠しています。

注: 日付は本リリースの生成日です。

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-19
--------------------

Added
- 初回公開リリース (バージョン 0.1.0)。
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db 既定）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立てと実行スレッド管理を実装。
    - 停止フラグ（data/stop_requested.flag）と PID ファイルの取り扱いを実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60 秒、無効値はデフォルトにフォールバック）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する（監視データを本番 DB に集約）。
    - 停止フラグの検出、例外処理、リソースクローズ処理を実装。
- 設定関連
  - config.py
    - .env 自動読込機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env のパース実装（export プレフィックス、クォート処理、インラインコメント対応）。
    - Settings クラスにより環境変数を型付きプロパティとして提供（DB パス、ログレベル、環境判定、Paper Trading 関連設定 等）。
    - PAPER_FILL_MODE の検証、PAPER_TRADING_SQLITE_PATH 等のデフォルトパスを提供。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - config_setup.py
    - 対話式ウィザードで .env を作成/更新する CLI。
    - 入力補助、既存 .env 読込、シークレットマスク表示、確認と保存機能を提供。
  - validate_config.py
    - 起動前に .env や config/*.yaml の不備を検出する CLI。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、YAML の存在とパース検証、live 環境向けのガードチェックを実装。
    - --strict オプションで警告を FAIL として扱う。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補選定（タイブレーク: signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア全0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存ポジションを考慮し売却予定銘柄は除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull/neutral/bear マッピング、未知レジームは警告のうえ 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数決定。
    - 単元株（lot_size）丸め、個別上限・aggregate cap、コストバッファ考慮によるスケーリングと端数処理を実装。
- ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトから共通利用可能なログ設定ユーティリティ。
    - stdout 出力用 StreamHandler と 日次ローテートの TimedRotatingFileHandler をルートロガーに設定。ログディレクトリ自動作成（失敗時はファイル出力をスキップしてコンソールのみ）。
    - ログレベル/ログディレクトリの解決ルールをドキュメント化。
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度（nice / Windows priority class）設定を実装。
    - CPU affinity 設定の補助関数も提供。権限不足や未対応 OS では警告を出してスキップ。
- データベース関連
  - run_* スクリプトや各コンポーネントに対し SQLite / DuckDB 接続の統一的な初期化処理（init_monitoring_db の呼び出し）を導入。
- ツール類
  - tools/paper_verification_report.py
    - ペーパートレーディング用検証レポート生成スクリプト。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ (avg/max/P95) を算出し PASS/FAIL 判定（閾値はソース中に定義）。
    - DB パスは --db / PAPER_TRADING_SQLITE_PATH / デフォルトの優先で解決。
- 研究用モジュール（DuckDB ベース）
  - research/factor_research.py（ファクター計算基盤を追加）
    - モメンタム / MA / ATR / 流動性等の計算方針と定数を定義。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
    - （注）このモジュールは大枠を実装済みだが一部処理（ファイル末尾）が未完。

Changed
- パッケージ初版のため該当なし（新規追加のみ）。

Fixed
- パッケージ初版のため該当なし。

Removed
- パッケージ初版のため該当なし。

Deprecated
- なし。

Security
- なし。

Notes / Known issues
- research/factor_research.py の実装は大枠があるものの、ソース末尾が途中で切れており一部関数の実装が未完です（今後の追加実装が必要）。
- position_sizing.calc_position_sizes 内で価格が欠損（0.0）場合の挙動に TODO コメントあり。将来的に前日終値等のフォールバックを検討する必要があります。
- .env 自動読込はデフォルトで有効（プロジェクトルートが検出できる場合）。テスト等で自動読込を無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は監視 DB として settings.sqlite_path を参照します。運用ポリシーに合わせて構成してください。

開発者向けメモ
- ロギングは setup_logging(app_name=...) により統一して設定してください（stdout + 日次ファイルローテーション）。
- process_priority.set_process_priority("high") を起動直後に呼ぶ設計になっていますが、権限がない場合は警告に留まり処理は継続します。
- Paper Trading と Live は DB を分離しているため、発注検証と本番データの混在を避けられます。

--- 
（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートはプロジェクトの開発履歴・コミットログに基づき調整してください。）