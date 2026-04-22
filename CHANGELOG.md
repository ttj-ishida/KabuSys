# CHANGELOG

すべての重要な変更履歴を記録します。本ファイルは「Keep a Changelog」の形式に準拠しています。

フォーマット:
- 変更はセマンティクス（Added, Changed, Fixed, Removed, etc.）ごとに分類しています。
- バージョンと日付を併記しています。

## [0.1.0] - 2026-04-22

初回リリース。自動売買システム KabuSys の基盤機能群を実装しました。以下はコードベースから推測できる主要な追加・変更点です。

### Added
- 起動スクリプト / デーモン
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 専用 SQLite（data/paper_trading.db をデフォルト）に記録することで本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority を呼び出す）。
    - 停止制御: data/stop_requested.flag / data/execution.pid を使用した停止/監視処理を実装。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値時は警告の上デフォルトにフォールバック）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する旨の挙動を明記。
    - 停止フラグ（data/stop_requested.flag）検出でループ終了。
- 設定管理・ユーティリティ
  - config.Settings: 環境変数を統合して読み取る Settings クラスを追加。
    - J-Quants / kabu API / LINE / DB パス / 各種監視閾値 / ログ・Kill Switch 等のプロパティを提供。
    - KABUSYS_ENV / LOG_LEVEL 等の値検証を実装（不正値は例外を送出）。
    - paper_trading 用の paper_sqlite_path、paper_fill_mode（"instant" | "partial" | "never" | "reject"）の検証。
  - 自動 .env ロード:
    - プロジェクトルート（.git または pyproject.toml を探索）を基準に .env/.env.local を自動読み込み（OS 環境変数優先）。自動ロードを無効にする環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。
    - .env のパースは引用符・エスケープ、export KEY=val 形式、インラインコメント等に対応。
  - config_setup: 対話式 .env 作成ウィザードを追加（項目定義、既存 .env 読み込み、確認・保存機能）。
  - validate_config: 起動前に .env と config/*.yaml の検証を行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリチェック、YAML パーサ（PyYAML）有無による挙動分岐、本番時の追加警告（LINE 通知設定や KILL_FLAG_CLEAR_ON_START）を実装。
- ロギング / プロセス制御ユーティリティ
  - utils.logging_setup.setup_logging:
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次, 30 日保持）を設定するユーティリティを追加。
    - LOG_DIR/LOG_LEVEL の解決順を実装。ログディレクトリ作成失敗時にはファイル出力をスキップしてコンソールのみ継続。
  - utils.process_priority:
    - Windows と POSIX（Linux/Mac 等）差分を吸収してプロセス優先度を設定する set_process_priority を実装。CPU affinity 設定用の set_cpu_affinity も提供（未指定時は全コア）。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。
- ポートフォリオ構築ライブラリ（pure functions）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選抜。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（全スコアが 0 の場合は等金額にフォールバックして WARNING）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限（既存ポジションのセクター別エクスポージャを計算し、上限超過セクターの新規候補を除外）。"unknown" セクターは除外しない。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を提供（未知レジームは 1.0 でフォールバック、WARN 出力）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算を実装（単元株丸め、1 銘柄上限、aggregate cap によるスケールダウン、cost_buffer 考慮）。
    - aggregate のスケーリング時に lot_size 単位で再配分するアルゴリズムを実装し、再現性のために安定ソート（code を二次キー）を利用。
- ツール群
  - tools.paper_verification_report:
    - Paper Trading の検証レポート生成スクリプトを追加。システム稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL を判定する。閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を設定。
    - 日付フィルタや DB パスオーバーライド（--db）に対応。
- データ処理 / リサーチ骨格
  - research.factor_research: ファクター計算モジュールの骨格を追加（モメンタム/バリュー/ボラティリティ等を DuckDB 上で計算する設計、関数サインネチャを用意）。（実装途中の箇所あり）

### Changed
- DB 接続挙動
  - run_monitoring は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する設計を明示（監視は本番データの参照が前提）。
  - run_execution は paper_trading 環境時に専用の paper_sqlite_path を用いる（本番データと完全分離）。
- 設定ファイルの取り扱い
  - .env の自動ロード順序は OS 環境変数 > .env.local > .env。OS 環境変数は保護（上書きされない）。
- ロギング
  - StreamHandler は stdout を使用（cron/Task Scheduler 等で stdout/stderr を一括リダイレクトしやすくするため）。
  - 既存のハンドラがある場合は一旦 flush/close してから再設定（多重出力防止）。
- エラーハンドリング / フォールバック
  - MONITOR_POLL_INTERVAL の不正値は警告を出してデフォルトにフォールバック（time.sleep に渡す負の値回避）。
  - process_priority の設定失敗や CPU affinity 設定失敗は警告を出してスキップ。

### Fixed
- 安全性 / 冗長性の改善（挙動から推測）
  - init_monitoring_db は idempotent に呼べるように設計（起動時に監視テーブルが存在することを保証）。
  - ExecutionEngine のスレッド管理で停止フラグを検出したら engine.stop() を呼び、最大 30 秒の join を試みるなど安全に停止できるようガードを実装。
  - position_sizing:
    - 価格が欠損（None または <= 0）の場合にスキップして無効な発注を防止。
    - aggregate スケーリングで 0 除算や不正な丸めを避けるためのチェックを導入。
  - paper_verification_report:
    - DB が存在しない場合のエラーメッセージと早期リターンを実装。
    - latency の P95 計算で空データを扱う安全策を実装。

### Removed
- なし（初回リリースのため該当なし）。

### Notes / 運用上のポイント
- Kill Switch / Stop フラグ:
  - stop_requested.flag（data/stop_requested.flag）や execution.pid 等のファイルで起動/停止を制御する設計。運用時にこれらの配置場所に注意してください（Settings のプロパティでパス上書き可能）。
  - 本番では KILL_FLAG_CLEAR_ON_START を 0 にしておくことが推奨される（validate_config にて警告）。
- Paper Trading と本番の分離:
  - paper_trading 環境では MockBroker を用いて paper_sqlite_path にログを残すため、本番 DB を汚さない運用が可能。
- ログ/ディスク:
  - ログディレクトリ作成に失敗した場合、ファイル出力は無効化されるがコンソールログは継続される設計。ログディレクトリのパーミッション等に注意してください。
- 設定の検証:
  - .env 作成後は python -m kabusys.validate_config で検証を実施することを推奨。

----------

今後の変更案（参考・未実装）
- factor_research の完全実装（各ファクター計算ロジック・正規化ユーティリティ連携）。
- 銘柄別 lot_size サポート（stocks マスタの導入）。
- position_sizing のコスト見積り（スリッページ・手数料の詳細モデル化）。
- モニタリング / 通知（LINE 連携）機能の詳細強化。

---
この CHANGELOG はソースコードの内容から推測して作成しています。実際の変更履歴や設計方針とは差異がある可能性があります。必要であれば、差分のコミットメッセージやリポジトリの履歴に基づく正確な Changelog へ更新してください。