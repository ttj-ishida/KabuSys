# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  

リリースはセマンティックバージョニングに従います。

なお、本CHANGELOGは提供されたコードベースから推測して作成しています。

## [Unreleased]

- （特になし）

## [0.1.0] - 2026-04-19

Added
- 実行スクリプトを追加
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading 時はペーパートレード用 DB（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient により本番 DB と分離して実行。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止制御: data/stop_requested.flag の検出でエンジン停止（PID ファイル: data/execution.pid）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログ警告のうえデフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV に関係なく本番用 sqlite_path を使用。
    - 停止フラグでループを終了し、KeyboardInterrupt にも対応。

- 設定・環境管理
  - config.py
    - Settings クラスを導入し、アプリケーション設定を環境変数から取得。
    - .env 自動読み込み機能を実装（プロジェクトルートの .env / .env.local を読み込み。OS 環境変数を保護）。
    - 自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 各種設定プロパティを提供（J-Quants / kabuAPI / DB パス / PAPER_FILL_MODE 検証 / PID/KILL フラグ / しきい値等）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI。
    - シークレット値のマスク表示、既存 .env の読み込み、保存確認などを実装。
  - validate_config.py
    - 起動前の設定検証 CLI。
    - 必須環境変数のチェック、KABUSYS_ENV や LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検証（PyYAML がある場合）。
    - --strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構築（純粋関数）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順でソートし上位 N を選択。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア正規化による配分。全スコアが 0 の場合は等金額にフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存ポジションのセクター別エクスポージャーに基づき、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象としない）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を計算。未知レジームは 1.0 にフォールバック（警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づき発注株数を計算。
      - risk_based: 許容リスク率 (risk_pct)、ストップロス (stop_loss_pct) からベース株数を算出。
      - 等分配/スコア配分時は weight に基づく配分。
      - 単元株（lot_size）で丸め、1 銘柄上限（max_position_pct）、全体利用上限（max_utilization）に準拠。
      - cost_buffer を考慮した保守的なコスト見積りと aggregate cap のスケーリング（残差処理で lot 単位の追加配分ロジックを実装）。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的ロギング設定ユーティリティを追加。
    - stdout に出す StreamHandler と TimedRotatingFileHandler（日次ローテーション、30 日分保持）をルートロガーに設定。
    - 既存ハンドラは一度 flush/close してからクリア（重複設定防止）。
    - LOG_DIR / LOG_LEVEL の解決順をサポート。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - stdout を利用する設計（cron 等で stdout/stderr を統一してリダイレクトするため）。
  - utils/process_priority.py
    - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティ（psutil を使用）。
    - Windows と POSIX（Linux/Mac/FreeBSD）向けに優先度を適用。失敗時は警告ログでスキップ。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を提供（失敗時は警告でスキップ）。

- 監視・モニタリング
  - run_monitoring と run_execution で共用する monitoring_db.init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。
  - SystemMonitor を用いた単回チェック check_once() をポーリングループから呼ぶ設計（例外時はロギングして次のポーリングに進む）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプト。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）を集計。
    - 基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を実装。
    - --from/--to/--db オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数経由の DB パス解決にも対応。

- パッケージ情報
  - __init__.py にバージョンを追加: __version__ = "0.1.0"
  - パッケージの __all__ を定義（"data", "strategy", "execution", "monitoring"）。

Changed
- n/a（初回リリースのため既存変更はなし）

Fixed
- n/a（初回リリースのためバグ修正履歴はなし）

Notes / Known issues
- research/factor_research.py が途中で切れている（ファイル末尾が不完全）。calc_momentum の実装が未完に見えるため、ファクター計算モジュールはまだ作業中／部分実装の可能性あり。
- 一部 TODO コメントあり（例: price の欠損時のフォールバック、銘柄別 lot_size のサポート等）。将来的な改善が見込まれる。
- .env パースルールはかなり柔軟に実装されているが、複雑なエスケープや異常なフォーマットのケースでは想定外の動作となる可能性があるため注意。

Security
- n/a（今回の差分から明示的なセキュリティ修正は検出できません）

----

参考:
- 環境変数キー（主なもの）: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_LEVEL, LOG_DIR, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, MONITOR_POLL_INTERVAL, KABUSYS_DISABLE_AUTO_ENV_LOAD, KILL_FLAG_CLEAR_ON_START, PAPER_FILL_MODE
- 実行フロー:
  - 実行: run_execution.py → ExecutionEngine（別スレッドで run_session 実行）
  - 監視: run_monitoring.py → SystemMonitor.check_once をポーリング実行

（以上）