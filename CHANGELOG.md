# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-24

### Added
- 初回公開リリース。
- 実行スクリプト / デーモン類
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止制御用フラグファイル（data/stop_requested.flag）の検知による安全停止。
    - 監視用 DB は環境に依らず本番用 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定。
    - 例外発生時にもループ継続してログ出力。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時はペーパートレード専用 DB（data/paper_trading.db 等）と MockBrokerClient を使用して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）と実行 PID ファイル（data/execution.pid）による制御。
    - 起動時にプロセス優先度を "high" に設定し、スレッドでエンジンを実行。停止フラグ検知で安全に停止。
- 設定・環境関連
  - config.py
    - Settings クラスを導入し、環境変数から各種設定を取得する統一インターフェイスを提供。
    - .env 自動ロード機能（プロジェクトルート検出: .git / pyproject.toml 基準）。.env と .env.local の読み込み順と上書きルールを実装（OS 環境変数は保護）。
    - .env の高度なパース対応: export プレフィックス、クォート付き値（バックスラッシュエスケープ含む）、インラインコメント処理等に対応。
    - Paper Trading 関連設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH など）を追加。
    - 各種しきい値（CPU/MEM/DISK）や PID/KILL フラグ等の設定プロパティを提供。
  - config_setup.py
    - 対話式ウィザードによる .env の初期作成/更新機能を追加。項目定義と入力補助、既存値の再利用やシークレットマスク表示に対応。
    - 作成された .env のテンプレート出力機能を実装。
  - validate_config.py
    - 起動前に .env と config/*.yaml の妥当性をチェックする CLI を追加。
    - 必須環境変数の検査、KABUSYS_ENV の妥当性、ログレベル、DB パス存在チェック、YAML パースチェック（PyYAML があれば中身も検証）、本番向け追加ガード（LINE 通知設定の有無や kill flag の自動クリア設定の警告）等を実施。
    - --strict モードで警告を失敗扱い（exit(1)）にできる。
- ロギング / プロセスユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）をセット。
    - LOG_LEVEL / LOG_DIR の解決ルールを実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
  - utils/process_priority.py
    - psutil を用いたクロスプラットフォーム（Windows / POSIX）向けプロセス優先度設定ユーティリティを追加。
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。権限不足や未対応 OS では警告ログを出して安全にフォールバック。
- ポートフォリオ構築ライブラリ (純粋関数群、DB非依存)
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順、signal_rank によるタイブレーク）、等金額配分、スコア加重配分を実装。スコア合計 0 の場合は等配分にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限（既存保有を考慮して新規候補を除外）を実装。unknown セクターは制限適用対象外。
    - レジームに応じた資金乗数 calc_regime_multiplier（bull/neutral/bear とフォールバック）を実装。
  - portfolio/position_sizing.py
    - allocation_method ("risk_based" / "equal" / "score") に応じた株数算出を実装。
    - 損切り率・リスク割合に基づく risk_based、重みベースの equal/score、単元（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金に合わせたスケーリング）などを実装。コストバッファ考慮と残差処理ロジックを含む。
- ツール類
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite DB から稼働率、注文成功率、送信率、レイテンシ (avg/max/P95) 等を集計してレポート出力する CLI を追加。
    - デフォルトの DB パスは data/paper_trading.db。--from/--to/--db オプション対応。
    - 判定用しきい値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義し PASS/FAIL 判定を行う。
- 解析 / リサーチ
  - research/factor_research.py（実装開始）
    - モメンタム等のファクター計算モジュールを追加（DuckDB 接続を利用し prices_daily 等のテーブルから計算する設計）。一部実装（定数や関数スケルトン）を含む。完全実装は継続中。

### Changed
- プロジェクト構成に合わせてログ・設定周りの挙動を標準化（すべての起動スクリプトで同一の logging_setup と process_priority を利用）。

### Fixed
- .env 読み込みにおける既知のパース問題に対処（クォート付き値や export プレフィックス、インラインコメントの扱いを改善）。

### Notes / Implementation details
- 監視ループや実行エンジンは stop flag / pid ファイル、スレッド監視を用いて安全停止する設計。
- Paper Trading と Live の DB は完全分離する方針（paper_trading 用に paper_sqlite_path を明示）。
- ロギングは stdout をメインにしつつ、可能であれば日次ローテーションでファイル出力する設計。cron/task からの起動を想定して stdout に出力する点に注意。
- psutil 等の外部依存の機能（プロセス優先度・CPU affinity、YAML パース）は利用環境に依存するため、機能が利用できない場合は警告を出してフォールバックする実装になっている。

### Security
- このリリースにおける既知のセキュリティ問題はなし。  
- 注意: .env ファイルにはシークレットが含まれるため、絶対にリポジトリにコミットしないでください（config_setup でも注意書きを出力）。

---

今後の予定:
- research/factor_research の完全実装（ファクター計算ロジックの完成）。
- Strategy / Execution のさらなるテストと堅牢化（回復戦略、リトライ、監視アラート連携など）。
- より細かい単体テストと CI の整備。