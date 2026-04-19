CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠しています。

## [0.1.0] - 2026-04-19

### 追加
- 起動スクリプトを追加
  - run_execution: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV に応じて paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離して実行可能。停止フラグ（data/stop_requested.flag）と pid ファイルの扱いを実装。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ検知で安全にループ終了。
- 環境設定・検証用 CLI を追加
  - config_setup: 対話式ウィザードで .env を作成・更新する CLI を追加。主要な設定項目を対話的に入力・保存可能。
  - validate_config: .env と config/*.yaml の基本的な整合性チェックを行う CLI を追加。--strict モードで警告を FAIL 扱いにできる。
- 設定管理
  - config.Settings クラスを実装。環境変数読み込み、型チェック、デフォルト値、必須値の検証（_require）を提供。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動 .env ロード抑止をサポート。
  - .env 自動読み込み機構を実装（優先順: OS 環境変数 > .env.local > .env）。プロジェクトルート判定は .git または pyproject.toml を探索して行う。
  - .env パースの堅牢化: export 構文, シングル/ダブルクォート内のエスケープ, インラインコメントの扱いに対応。
- ロギング・プロセスユーティリティ
  - utils.logging_setup.setup_logging を実装。コンソール出力（stdout）と日次ローテーション付きファイル出力（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールのみで継続。
  - utils.process_priority に process 優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を実装。Windows/Linux/macOS を考慮し権限不足や未対応環境では安全にフォールバックする。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
  - portfolio.risk_adjustment: セクター集中制限を適用する apply_sector_cap と、市況レジームに応じた投入比率を返す calc_regime_multiplier を実装。
  - portfolio.position_sizing: 複数方式（risk_based / equal / score）に対応した発注株数計算 calc_position_sizes を実装。単元株丸め、1 銘柄上限、aggregate cap（利用可能現金を超える場合のスケールダウン）、cost_buffer（手数料/スリッページ見積）などを考慮。
- データ分析・検証ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を SQLite（paper_trading.db）から集計し、PASS/FAIL 判定を出力する。日付フィルタ、DB パスの引数対応あり。
- DuckDB 統合
  - run_* スクリプトや調査モジュールが DuckDB 接続を受け取るように設計。duckdb_path 設定により DuckDB ファイルを使用可能。
- 初期バージョン情報
  - パッケージバージョンを __version__ = "0.1.0" として設定。

### 変更
- 監視 DB 接続ポリシー
  - run_monitoring は KABUSYS_ENV に関係なく常に本番用 sqlite_path（Settings.sqlite_path）を使用する設計にした（監視データは本番監視を想定）。
- ログ出力先の方針
  - StreamHandler は stderr ではなく stdout を使用（Task Scheduler / cron 等で出力を一本化しやすくするため）。
- .env ウィザードの既存値扱い
  - config_setup のウィザードは既存 .env を読み込んで Enter による再利用をサポート。シークレット値は表示をマスク。

### 修正（堅牢性向上）
- MONITOR_POLL_INTERVAL の不正値ハンドリング
  - 環境変数 MONITOR_POLL_INTERVAL が不正（非整数、0 以下など）の場合は警告を出しデフォルト（60 秒）にフォールバックするようにした。
- .env 読み込み時のエラー耐性
  - ファイル読み込み失敗時は警告を出して自動ロードをスキップする（テスト時や権限問題に対処）。
- ログディレクトリ作成失敗時のフォールバック
  - setup_logging はログディレクトリ/ファイル作成に失敗してもコンソールログのみで継続し、例外でプロセスを止めない。
- process priority / cpu affinity の安全化
  - 権限不足や未対応 OS では警告ログを出して操作をスキップするようにした（AccessDenied 等を捕捉）。

### 既知の制限 / 注意点
- research.factor_research モジュールは設計方針と一部定数／関数の実装が含まれているが、ファイル末尾が未完（calc_momentum 関数の途中で切れている）。今後のリリースで完成させる予定。
- apply_sector_cap は price_map に欠損（0.0）値がある場合にエクスポージャーが過少見積りされる可能性があると注記しており、将来的にフォールバック価格導入を検討中。
- paper_trading の MockBroker の実装や ExecutionEngine の詳細は本変更ログでは言及していない（別モジュールで実装済み／今後拡張予定）。

### セキュリティ
- 本リリースにおいて敏感情報（API トークン等）は .env で管理する設計。README/.env.example のドキュメント化と .env を Git にコミットしない運用を推奨。

---

今後の予定（短期）
- research.factor_research の完成（ファクター計算ロジックの実装完了）
- ExecutionEngine / Broker の e2e テスト整備（paper/live 切替の検証）
- 監視アラートの LINE 連携（LINE 設定があれば通知を送る仕組みの実装拡張）

（補足）本 CHANGELOG はコードベースから推測して作成しています。実際のリリースノートや運用ポリシーに合わせて調整してください。