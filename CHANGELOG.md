CHANGELOG
=========

フォーマット: Keep a Changelog に準拠  
初版リリース: 0.1.0（2026-04-19）

Unreleased
----------
（現在未リリースの変更はありません）

0.1.0 - 2026-04-19
-----------------

Added
- 基本バージョン情報を追加
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 起動スクリプト
  - run_monitoring.py を追加（システム監視ポーリングループ）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト内 data/stop_requested.flag ファイルで検知。
    - 監視は KABUSYS_ENV に依らず production 用の sqlite_path を使用（注記あり）。
    - SystemMonitor の check_once をポーリングで呼び出し、例外はログに出力して次ポーリングへ継続。
  - run_execution.py を追加（ExecutionEngine 起動スクリプト）。
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）。
    - 停止フラグ（data/stop_requested.flag）検知でエンジン停止。起動時 PID ファイル管理。

- 環境設定・検証ツール
  - config.py: 環境変数と .env 自動読み込みロジックを追加。
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動ロード。
    - OS 環境変数を保護する protected 機構（.env.local の上書きでは OS 環境変数を上書きしない）。
    - 各種設定プロパティ（DB パス、PID ファイル、しきい値、PAPER_FILL_MODE 等）を定義。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - config_setup.py: 対話式 .env ウィザードを追加。
    - 初期 .env 作成・更新を支援。機密項目はマスク表示。保存前の確認あり。
    - .env のテンプレート書き込み機能を提供（.env を絶対に git にコミットしない旨のヘッダ付き）。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在とパース（PyYAML がある場合）を検証。
    - --strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で上位 N を選択（同点は signal_rank でブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分を計算。スコア合計が 0 の場合は等配分にフォールバック（警告）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限を適用し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート。未知レジームはフォールバックと警告）。
  - portfolio.position_sizing
    - calc_position_sizes: リスクベース／等配分／スコア配分に基づく株数計算、単元株丸め、ポジション上限、aggregate cap によるスケールダウンを実装。
    - cost_buffer を考慮した保守的コスト見積もりと、残差分の lot 単位での再配分ロジックを備える。

- ユーティリティ
  - utils.logging_setup: 統一的なログ設定ユーティリティを提供。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR / 引数での上書きをサポート。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils.process_priority: クロスプラットフォームのプロセス優先度設定（Windows の priority class / POSIX の nice）。
    - set_process_priority(level) で high/normal/low を扱い、psutil 標準を利用。失敗時は警告でスキップ。
    - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアに固定（利用不可環境では警告）。

- モニタリング DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を利用して監視テーブルの冪等な初期化を行う呼び出しを起動スクリプト（monitoring / execution）に追加。

- Paper Trading 検証ツール
  - tools.paper_verification_report を追加。
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）から期間指定でレポートを生成。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数等。
    - デフォルト基準値（稼働率 >= 99%, 成立率 >= 90% 等）で PASS/FAIL 判定を行う。
    - 日付フィルタ（--from / --to）と --db オーバーライドをサポート。

- リサーチ基盤（骨子）
  - research.factor_research にモメンタム等のファクター計算関数の骨子を追加（DuckDB 接続を受け、prices_daily / raw_financials を参照する設計）。
    - モメンタム（1M/3M/6M）、MA200 乖離、ATR/流動性等の計算設計を開始。関数インターフェースと定数を定義（実装は継続予定）。

Changed
- 起動時の動作に関する設計決定を明示
  - 監視プロセスは実行環境変数に関係なく production 用 sqlite_path を利用する点を明示（監視 DB の分離ポリシー）。
  - run_execution は environment が paper_trading の場合に DB を分離して使用する（ペーパートレードは本番 DB と完全分離）。

Fixed
- （本リリースは新規機能の導入が中心のため明示的なバグ修正はなし）

Notes / Migration
- 監視(DB)の扱いに注意:
  - run_monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（デフォルト data/monitoring.db）を使います。テスト環境で監視を分離したい場合は sqlite_path を明示的に設定してください。
- Paper Trading:
  - KABUSYS_ENV=paper_trading 時は発注・約定処理がモック化され、データは data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）へ記録されます。本番 DB と混ざらない点に注意してください。
- .env の自動読み込み:
  - デフォルトでプロジェクトルートの .env/.env.local を自動読み込みします。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Security
- 環境変数管理:
  - 機密情報（J-Quants トークン / KABU API パスワード 等）は .env に平文で保存される設計のため、.env をバージョン管理しない運用を強く推奨（config_setup で注意書きを挿入）。

Acknowledgements / TODO（今後の予定）
- research.factor_research のファクター実装の完成、テスト追加、及び各モジュールの単体テスト整備を予定。
- broker / execution 周りの堅牢性（再試行・レート制限実装の拡充）、および Paper Trading の挙動検証を継続予定。