CHANGELOG
=========

すべての変更は「Keep a Changelog」フォーマットに準拠しています。  
注: 以下の履歴は提示されたコードベースからの実装内容を基に推測して作成しています。実際のコミット履歴やリリースノートとは差異がある可能性があります。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-19
-------------------

Added
- 初期リリース相当の機能群を追加。
  - 実行スクリプト / デーモン
    - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用し MockBrokerClient を利用（本番 DB と分離）。プロセス優先度設定、PID ファイル管理、停止フラグ検出による安全停止をサポート。
    - run_monitoring.py: SystemMonitor のポーリングループ用スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視用 DB 接続は環境にかかわらず本番 sqlite_path を使用する設定。
  - 設定・環境管理
    - config.py: .env の自動読み込み（.env / .env.local、OS 環境変数保護）、.env 行パーサ（export 形式、クォート／エスケープ、インラインコメント処理対応）、Settings クラス（各種環境変数のラッパー）を実装。環境のバリデーション（KABUSYS_ENV / LOG_LEVEL 等）を提供。
    - config_setup.py: 対話的ウィザードで .env を初期作成/更新する CLI を追加（シークレット入力、既存値再利用、保存確認）。
    - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。--strict オプションで警告を失敗扱いにできる。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder: 候補選定（スコア降順／タイブレーク）、等金額配分、スコア加重配分を実装（スコア全て 0 の場合は等分にフォールバックし警告）。
    - portfolio.risk_adjustment: セクター集中制限の適用（sell_codes を考慮、"unknown" セクターは除外対象外）、市場レジームに基づく投下資金乗数 calc_regime_multiplier（bull/neutral/bear をサポート、未知レジームはフォールバック）。
    - portfolio.position_sizing: 株数決定ロジックを実装（risk_based / equal / score の allocation_method、単元株丸め、1 銘柄上限、aggregate cap によるスケールダウン、cost_buffer による保守的見積り、lot_size 単位での端数処理）。
  - ユーティリティ
    - utils.logging_setup: ルートロガーの初期化ユーティリティを追加。stdout への StreamHandler と日次ローテートする TimedRotatingFileHandler（logs/<app_name>.log、30日保持）を設定し、既存ハンドラのクリアやログディレクトリ作成失敗時のフォールバックを考慮。
    - utils.process_priority: Windows / POSIX (Linux/Mac/FreeBSD) を吸収したプロセス優先度設定ユーティリティ（high/normal/low）と CPU affinity 設定を提供。権限不足等の例外は警告にフォールバック。
  - モニタリング DB 初期化連携（init_monitoring_db の呼び出し）と DuckDB 連携を各起動スクリプトで行う実装。
  - Paper Trading 向け検証ツール
    - tools.paper_verification_report: ペーパートレード用 SQLite DB を読み取り、稼働率・注文成功率・送信率・レイテンシ（avg/max/P95）・リスク却下数等を集計してレポート出力する CLI を追加。閾値に基づく PASS/FAIL 判定を実施。日付フィルタ (--from / --to) と DB パスの指定をサポート。
  - リサーチ / ファクター計算（部分実装）
    - research.factor_research: DuckDB 接続を受け取りモメンタム等の定量ファクターを計算する骨組みを追加（モメンタム計算関数の定義開始、複数の窓長定数を定義）。設計方針に DuckDB 使用と pure 関数指向を明記。

Changed
- 新規リリースのため変更点なし（初回導入）。

Fixed
- 該当なし。

Deprecated
- 該当なし。

Removed
- 該当なし。

Security
- 該当なし。

補足
- 多くの CLI / ユーティリティは環境変数で挙動を変更可能（例: LOG_LEVEL, LOG_DIR, MONITOR_POLL_INTERVAL, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等）。
- config/ ディレクトリの YAML ファイル存在確認やパースは PyYAML の有無に依存しており、未インストール時は YAML 内容検証をスキップする仕様。
- .env 読み込みロジックはプロジェクトルートを .git または pyproject.toml から探索するため、パッケージ配布後も CWD に依存しない設計になっている。
- 本 CHANGELOG はコードからの推測を元に作成しているため、実際の変更履歴（コミットメッセージ等）を反映する場合は差分を反映してください。