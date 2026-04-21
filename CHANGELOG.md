# CHANGELOG

すべての目立つ変更は本ファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-21
初回リリース。自動売買システム「KabuSys」の基礎機能群を追加。

### Added
- 起動スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止は data/stop_requested.flag ファイルで制御。監視用 DB は環境にかかわらず本番 sqlite_path を使用する。
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合は専用の Paper Trading DB（data/paper_trading.db）と MockBroker を使用し、本番 DB と分離。PID ファイルと停止フラグに対応し、エンジンは別スレッドで実行され停止フラグ検知で安全に停止する。
- 設定管理
  - config.py: .env 自動読み込み（.env, .env.local）機能を追加（無効化フラグあり）。Settings クラスを提供し、環境変数取得・バリデーション用のプロパティ（DB パス、ログレベル、KABUSYS_ENV、Paper Trading 用設定など）を実装。
  - config_setup.py: 対話式ウィザードで .env を作成/更新する CLI を追加。シークレット値のマスク表示や選択肢サポートを実装。
  - validate_config.py: .env と config/*.yaml の設定チェック用 CLI を追加。必須環境変数チェック、パスの存在確認、YAML パース検証（PyYAML 利用時）、KABUSYS_ENV=live のガードなどを実装。--strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
  - portfolio/risk_adjustment.py: セクター集中制限 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier) を実装。
  - portfolio/position_sizing.py: 株数決定ロジックを実装（risk_based / equal / score の割当方法、単元株丸め、aggregate cap によるスケールダウン、cost_buffer 考慮）。
  - portfolio パッケージとしてエクスポートを提供。
- ユーティリティ
  - utils/logging_setup.py: 共通ロギング設定ユーティリティを実装。stdout ストリームと日次ローテーションのファイルハンドラを設定し、既存ハンドラの重複登録を回避。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py: psutil を用いたクロスプラットフォームのプロセス優先度設定および CPU affinity 設定ユーティリティを追加。Windows / POSIX の差分を吸収し、権限不足や未対応 OS は警告でスキップ。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite DB から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を集計してレポート出力するスクリプトを追加。閾値を用いた PASS/FAIL 判定を実装。
- 研究用モジュール（骨組み）
  - research/factor_research.py: DuckDB を用いたファクター計算（モメンタム等）の枠組みと定数を追加（モジュールは一部実装中）。

### Changed
- 初期設定とデフォルト値
  - データベースやログパス、各種閾値などのデフォルトを Settings 経由で一元管理するように整理。
  - PAPER_TRADING_SQLITE_PATH / DUCKDB_PATH / SQLITE_PATH などに対して既定値と expanduser 処理を導入。
- ロギング
  - setup_logging でハンドラの重複を防ぎ、ログディレクトリ作成に失敗した場合のフォールバックを明確化。コンソールは stdout を使用するように統一。
- プロセス管理
  - 起動時に set_process_priority("high") を呼び出す起動スクリプト側の挙動を標準化。
- run_execution の振る舞い
  - Paper Trading 時は paper_sqlite_path を使用して本番 DB と分離。起動時に監視テーブルの存在を保証（init_monitoring_db を呼び出す）するようにした。
  - RiskConfig の初期値やレートリミット、サーキットブレーカー等の初期ポリシーを設定し、初期ポートフォリオ値はブローカから取得して設定するようにした。

### Fixed
- .env パーサの堅牢化
  - config._parse_env_line において export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの扱いなどに対応。これにより複雑な .env の値が正しく読み込まれるようになった。
- 監視ループの堅牢化
  - run_monitoring.py 内で monitor.check_once() が例外を投げてもループを継続するよう try/except を追加。KeyboardInterrupt や停止フラグ検出時に DB 接続を確実にクローズするようにした。
- position sizing のスケールダウン
  - 合計コストが利用可能現金を超える場合のスケーリング処理で、単元株（lot_size）単位の丸め、残差に基づく追加配分（fractional remainder）を導入し、より再現性・安全性の高い配分を実現。
- risk_adjustment のセクター扱い
  - sector_map になし（unknown）の銘柄はセクター上限の対象外とし、不要な除外を防止。

### Security
- なし

### Removed
- なし

---

メジャー/マイナーの更新ポリシーや過去のリリースを追記する場合は、本ファイルを更新してください。