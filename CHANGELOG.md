CHANGELOG
=========

すべての目立った変更はこのファイルに記録します。フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを想定しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-19
--------------------

Added
- 基本アプリケーション構成と初期実装を追加
  - パッケージメタ情報: kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 実行/監視ランナー
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを実装。
    - KABUSYS_ENV によるペーパートレード分離:
      - paper_trading 環境では paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離して動作。
      - BrokerClientFactory によるブローカークライアント生成を行い、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - プロセス優先度を起動直後に "high" に設定する呼び出しを含む。
    - 停止フラグ (data/stop_requested.flag) による安全停止処理を実装。
    - 実行用 PID ファイル (data/execution.pid) のパスを使用。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path（data/monitoring.db デフォルト）を参照。
    - 停止フラグ (data/stop_requested.flag) によるループ停止、KeyboardInterrupt 処理、接続の確実なクローズを実装。

- 設定管理
  - config.py
    - .env の自動読み込み機能を実装（プロジェクトルート判定は .git または pyproject.toml を探索）。
    - .env/.env.local の読み込み順序と OS 環境変数保護（protected）を実装。
    - .env 行パーサ（クォート、エスケープ、コメント処理を含む）を実装。
    - Settings クラスを追加し、J-Quants / kabuAPI / DB パス / 各種閾値 / 環境フラグ等の取得を統一。
    - PAPER_FILL_MODE のバリデーション、KABUSYS_ENV / LOG_LEVEL の検証、paper_sqlite_path 等を提供。

  - config_setup.py
    - 対話式 .env ウィザードを実装。
    - デフォルト値・選択肢・Secret 入力の扱いをサポートし、既存 .env の読み込み・更新と保存を提供。
    - .env の書式テンプレートを生成。

  - validate_config.py
    - 起動前に .env と config/*.yaml を検証する CLI を実装。
    - 必須/任意環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証を行う。
    - --strict オプションで警告を FAIL 扱いにする機能を追加。
    - live 環境向けガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の注意喚起）を実装。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーの統一設定ユーティリティを追加。
    - stdout に出力する StreamHandler と日次ローテーション（TimedRotatingFileHandler、30 日保持）のファイルハンドラを設定。
    - LOG_LEVEL / LOG_DIR / app_name による柔軟な設定、既存ハンドラのクリア処理、ディレクトリ作成失敗時のフォールバックを実装。
    - ログは stdout を使用（cron 等で stdout/stderr をリダイレクトしやすくするため）。
  - utils/process_priority.py
    - プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを実装。
    - Windows と POSIX（Linux / macOS / FreeBSD）を考慮した実装。権限不足や未対応環境でのフォールバック警告を含む。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄候補選定（select_candidates: スコア降順、signal_rank によるタイブレーク）を実装。
    - 等金額配分（calc_equal_weights）とスコア加重配分（calc_score_weights）を実装。全スコアが 0 の場合は等分配にフォールバックし警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存ポジションのセクター比率に応じて候補から除外するロジックを提供（"unknown" セクターは除外対象外）。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull=1.0, neutral=0.7, bear=0.3、未知はフォールバックで 1.0）。
  - portfolio/position_sizing.py
    - 株数計算ロジック（calc_position_sizes）を実装。
    - allocation_method に応じた計算 ("risk_based", "equal", "score") をサポート。
    - 1 銘柄上限（max_position_pct）、投下上限（max_utilization）、lot_size（単元）や cost_buffer を考慮。
    - aggregate cap によるスケーリングと、スケール後の残余金での端数配分（lot 単位での再配分）ロジックを実装。
    - 価格欠損や 0 値の扱いに関するログ出力を実装。

- 監視/モニタリング関連
  - run_monitoring/run_monitoring.py から呼ばれる監視初期化（monitoring_db.init_monitoring_db）と SystemMonitor の呼び出しを統合。
  - DB 接続は sqlite3（monitoring DB）と DuckDB（分析用）を使用。

- 実行関連（概念的統合）
  - ExecutionEngine / OrderManager / OrderRepository / RiskManager / Reconciler 等の起動フローを run_execution.py で組み合わせるコードを追加（各コンポーネント本体は別モジュールで提供想定）。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から各種検証指標を集計してレポートを出力する CLI を追加。
    - 指標: システム稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等。
    - パスや日付範囲でフィルタ可能。指標に基づく PASS/FAIL 判定（閾値はソース内に定義）を実装。
    - P95 計算、欠損データへの N/A 表示、SQLite の OperationalError に対する耐性を持つ。

- リサーチ（ファクター計算）
  - research/factor_research.py（ファクター計算モジュール）を追加（モメンタム / MA / ATR / ボラティリティ / 流動性等を想定）。DuckDB の prices_daily / raw_financials を参照して純粋関数で計算する設計。calc_momentum の骨組みが含まれる（実装途中でソースが切れているが、モジュール自体を含む）。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Removed
- なし（初期リリース）

Deprecated
- なし

Security
- なし

Notes / 制約・既知の事項
- .env の自動読み込みはプロジェクトルートが特定できる場合にのみ行われ、テスト等で無効化するために KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定可能。
- 一部実装（research モジュールの calc_momentum 等）はソースが途中で切れている箇所があるため、完全な動作には追加実装が必要。
- position_sizing 等で価格が欠損 (0.0) の場合に注意書き（TODO）あり。将来的なフォールバック価格の導入が言及されている。
- ログディレクトリ作成やプロセス優先度設定は権限不足や環境差異によりスキップされうるが、その場合は警告ログにより通知される設計。

作者注
- 上記は現在のソースコードから推測して作成した CHANGELOG です。内部実装の詳細や他ファイルの変更履歴（コミットログ）は含まれていません。実際のリリース履歴を作成する際は Git のコミット履歴やリリースノートに基づいて更新してください。