# Changelog

すべての注目に値する変更はこのファイルに記載します。
このプロジェクトは Keep a Changelog のガイドラインに従っています。
セマンティックバージョニングを採用しています。

## [Unreleased]

- 開発中の小修正・改善やユニットテストの追加等をここに記載してください。

## [0.1.0] - 2026-04-18

初回リリース。以下の主要機能・CLI・ユーティリティを実装しました。

### Added
- 起動スクリプト
  - run_execution: 実行エンジン（ExecutionEngine）起動用スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 SQLite(DB) を使用して本番 DB と完全分離。
    - 実行中は PID ファイルを書き、stop フラグ (data/stop_requested.flag) による安全停止に対応。
    - プロセス優先度を高 (high) に設定する仕組みを最初に実行。
    - ExecutionEngine の組み立てで BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler を組み合わせて起動。
  - run_monitoring: システム監視ループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を参照して監視テーブルを初期化する（init_monitoring_db）。
    - 停止フラグ検出でループを終了、例外発生時はログ出力して次ポーリングで再試行。
- 設定関連 CLI
  - config_setup: 対話式ウィザードで .env を作成・更新する CLI を追加。
    - 必須/任意項目のプロンプト、シークレットマスク表示、.env の書き出し機能。
    - 生成される .env には注意書き（Git にコミットしない等）を挿入。
  - validate_config: .env および config/*.yaml の簡易検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェックを行う。
    - PyYAML が未インストールの場合は YAML 検証をスキップして警告を出す。
    - --strict モードで警告を失敗扱いにできる。
- 設定読み込み・管理
  - config モジュールを実装。
    - プロジェクトルート検出（.git または pyproject.toml を探索）に基づく .env 自動ロード（.env → .env.local の順、OS 環境変数保護）。
    - .env 行パーサーは `export ` プレフィックス、クォートやエスケープ、インラインコメント等に対応。
    - Settings クラスで各種設定値（パス、API トークン、閾値、動作モード等）をプロパティ経由で取得・バリデーション可能。
    - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の値検証を実装。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
- ポートフォリオ構築ロジック（pure functions）
  - portfolio モジュールを追加（メモリ内計算のみ）。
    - portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights を実装（スコア並び替え、フォールバック挙動を含む）。
    - risk_adjustment: apply_sector_cap（セクター集中制限）、calc_regime_multiplier（市場レジームに応じた乗数）を実装。
    - position_sizing: calc_position_sizes（リスクベース／等分配／スコア配分、単元株切り捨て、aggregate cap スケーリング、コストバッファ対応）を実装。
- ユーティリティ
  - logging_setup: 統一的なログ初期化ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。
    - LOG_DIR / app_name / LOG_LEVEL の指定方法、ディレクトリ作成失敗時のフォールバック（ファイル出力を無効化してコンソールのみ）を実装。
    - 日次ローテーションで最大 30 日分保持。
  - process_priority: プロセス優先度および CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX (Linux, macOS, FreeBSD) の差分を吸収して優先度変更を試みる。
    - set_cpu_affinity による最初 N コアへのピン止め機能を提供（権限不足や未実装 API の場合は警告を出してスキップ）。
- Paper Trading 検証ツール
  - tools/paper_verification_report: ペーパートレード DB を解析して検証レポートを出力するスクリプトを追加。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（平均/最大/P95）を算出。
    - 基準値を設定して PASS/FAIL 判定を行う（閾値はファイル上で定義: uptime 99%、fill_rate 90%、send_rate 95%、P95 latency 200ms）。
    - 日付フィルタ (--from/--to) と DB パス指定 (--db) をサポート。
- リサーチ
  - research/factor_research の基礎実装（モメンタムやその他ファクター計算のための定数・設計方針・calc_momentum の開始実装）。（未完部分あり）

### Changed
- ログ周りの挙動を統一
  - すべての起動スクリプトは setup_logging を呼び出して同一フォーマット・ローテーションでログを管理するように統一。
- DB 初期化の冪等性
  - init_monitoring_db を起動パスで呼び出して監視テーブルの存在を保証（複数プロセスでも安全に起動できるように意図）。

### Fixed
- .env パース時のクォート・エスケープ処理を強化
  - シングル/ダブルクォート内のバックスラッシュエスケープや、非クォート時のインラインコメント判定を明確化。

### Security
- .env の取り扱いに関する注意喚起を config_setup に追加
  - 生成された .env を Git にコミットしない旨を明記。

### Notes / Operational details
- ペーパートレードは本番 DB と分離され、PAPER_TRADING_SQLITE_PATH 環境変数でパスを指定可能（デフォルト: data/paper_trading.db）。本番の monitoring.db は監視系で共通利用される。
- 環境変数自動読み込みの振る舞い:
  - デフォルトではプロジェクトルートが検出されれば .env（上書き不可）→ .env.local（上書き）を順に読み込みます。
  - テストや CI で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- process_priority / set_cpu_affinity は権限や環境によって失敗する可能性があります。失敗時は警告ログを出して処理を継続します。

---

（今後のリリースでは、factor_research の未完実装の完了、Engine 内の詳細な稼働監視・メトリクス出力、より詳細なテストカバレッジ追加を予定しています。）