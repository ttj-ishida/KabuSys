# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
リリースや追加・修正の内容は、提供されたコードベースの実装から推測して記載しています。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 削除 (Removed)
- その他（注記）

## [Unreleased]
- 開発中 / 未リリースの変更点はありません。

## [0.1.0] - 2026-04-24
初回リリース。以下の主要機能を実装・公開。

### Added
- コア機能
  - パッケージ初期化とバージョン情報を追加（kabusys.__version__ = "0.1.0"）。
  - アプリケーション設定管理（kabusys.config）
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env/.env.local の読み込み順と OS 環境変数の保護機能。
    - 強制取得ヘルパー `_require()` による必須環境変数チェック。
    - 多数の設定プロパティを提供（J-Quants / kabuステーション / DB パス / Paper Trading 関連 / 監視閾値 / ログレベル等）。
    - PAPER_FILL_MODE のバリデーション、PAPER_TRADING_SQLITE_PATH 等のデフォルト値を定義。

- 実行系・監視系ランナー
  - ExecutionEngine 起動スクリプト（run_execution.py）
    - KABUSYS_ENV による paper_trading モード判定とペーパートレード用 DB の分離（data/paper_trading.db を使用）。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler 組み立てと ExecutionEngine の起動・停止制御。
    - 停止フラグ（data/stop_requested.flag）検出による安全停止処理。
  - SystemMonitor 起動スクリプト（run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト: 60 秒）。
    - 監視は常に本番用 sqlite_path を使用して DB に記録。
    - 停止フラグ検知でループを終了、KeyboardInterrupt のハンドリング。
    - check_once() の例外を捕捉してループ継続。

- ユーティリティ
  - ログ設定ユーティリティ（kabusys.utils.logging_setup）
    - ルートロガーに StreamHandler（stdout） と TimedRotatingFileHandler（日次ローテーション、30日分保持）を設定。
    - ログレベル/ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力にフォールバック。
  - プロセス優先度・CPU affinity 設定（kabusys.utils.process_priority）
    - Windows / POSIX (Linux, macOS, FreeBSD) を吸収する優先度設定。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(N) を提供。
    - 権限不足や未対応 OS での安全なフォールバックと警告出力。
  - 設定検証 CLI（kabusys.validate_config）
    - .env と config/*.yaml の基本チェックを行う CLI を提供。
    - 必須/任意の環境変数リスト、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、YAML ファイルの存在/パース検証（PyYAML 使用時）。
    - --strict モードで警告も失敗扱いにする機能。
  - 環境設定ウィザード CLI（kabusys.config_setup）
    - 対話形式で .env を初期作成・更新するウィザードを提供。
    - 入力補助、デフォルト値、シークレットのマスク表示、保存確認機能あり。
  - Paper Trading 検証レポートツール（kabusys.tools.paper_verification_report）
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）からレポートを生成する CLI。
    - システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計して判定（PASS/FAIL）。
    - デフォルト閾値: 稼働率 99.0%、成立率 90.0%、送信率 95.0%、P95 レイテンシ 200 ms。
    - 日付範囲指定（--from/--to）と DB パスオーバーライド（--db）に対応。

- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - 候補選定・重み計算（portfolio_builder）
    - select_candidates（スコア降順、タイブレーク用 signal_rank）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等配分にフォールバック）。
  - セクター制約・レジーム乗数（risk_adjustment）
    - apply_sector_cap（セクターごとの既存保有比率が上限を超える場合に当該セクターの新規候補を除外、"unknown" セクターは除外対象外として扱う）。
    - calc_regime_multiplier（"bull"/"neutral"/"bear" に基づく乗数、未知のレジームは 1.0 にフォールバックして警告）。
  - 株数算出・リスク制約（position_sizing）
    - allocation_method ("risk_based", "equal", "score") に応じた発注株数の算出。
    - lot_size（単元）丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap とスケールダウン、端数（fractional）に基づく追加配分ロジックを実装。
    - 価格欠損時のスキップとログ出力。

- リサーチ（kabusys.research.factor_research）
  - （モジュールの冒頭実装）モメンタム・バリュー・ボラティリティ・流動性等のファクター計算方針と定数を定義。
  - DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを計算する設計方針を記述（関数シグネチャや定数を含む準備実装）。

### Changed
- n/a（初回リリースのため、過去バージョンからの変更はありません）

### Fixed
- 環境変数パーサの強化（kabusys.config._parse_env_line）
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いを適切に処理するよう実装。
  - クォートなしの値における '#' のコメント扱いを文脈に応じて判定。
- run_monitoring のポーリング間隔取得（_get_poll_interval）で不正な値（0 以下や非数）を検出した場合にデフォルトにフォールバックして警告を出力。
- ロギング設定でファイル作成に失敗した場合のフォールバックを実装（コンソール出力のみで継続）。
- process_priority の実行で権限不足や未対応プラットフォームがあっても安全にスキップして警告出力するように改善。
- calc_score_weights の合計スコアが 0 のケースを等配分にフォールバックして警告。

### Removed
- n/a

### Notes / その他
- run_execution は実行前に停止フラグが立っている場合は起動を行わない安全設計（停止フラグ: data/stop_requested.flag）。
- 監視・実行ともに SQLite（monitoring DB / paper_trading DB）と DuckDB（分析用）を併用するアーキテクチャになっている。監視 DB は monitoring 用テーブルが存在することを保証する初期化処理を行う（init_monitoring_db の呼び出し）。
- 設定検証ツールは PyYAML がインストールされていない場合に YAML 検証をスキップして警告を出す。
- 多くの CLI が python -m kabusys.<module> で実行可能なスクリプトとして設計されている（config_setup / validate_config / tools.paper_verification_report 等）。

もし特定ファイルや機能についてより詳細な変更履歴（例: 各関数の追加時刻、実装上の設計意図、将来的な TODO）を付記したい場合は、該当部分を指定してください。