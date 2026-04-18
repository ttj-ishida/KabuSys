# CHANGELOG

すべての注目すべき変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

現在のバージョンは src/kabusys/__init__.py の __version__ に従っています。

## [Unreleased]
- ドキュメント化・補足情報の追記予定
- research/factor_research モジュールの一部実装が途中（calc_momentum の実装開始のみ、未完）であるため、追加の実装・テストが必要

## [0.1.0] - 2026-04-18
初回公開リリース。自動売買基盤のコア機能群をまとめて実装しました。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを実装。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV に応じて Paper Trading 用 DB を分離（settings.paper_sqlite_path を使用）。
    - Broker クライアントのファクトリ利用、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - data/stop_requested.flag による外部停止フラグ検知、data/execution.pid に PID を記録する仕組み（Engine 側で PID ファイルを扱う想定）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。無効値はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して初期化。

- 設定周り
  - config.py
    - .env の自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。
    - .env のパース処理でクォート、エスケープ、export 形式、インラインコメントに対応。
    - Settings クラスを実装し、環境変数をラッパー化（J-Quants / kabu API / DB パス / 各種閾値 / 環境判定プロパティ等）。
    - PAPER_FILL_MODE の妥当性検証、KABUSYS_ENV / LOG_LEVEL の検証など。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を実装。
    - シークレット項目はマスク表示、既存 .env の読み込み・再利用に対応。
    - 生成した .env テンプレートの保存機能を提供。

  - validate_config.py
    - .env と config/*.yaml の事前検証 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリチェック、YAML パース（PyYAML がある場合）などを実行。
    - --strict モードで警告を FAIL 扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア順選定
    - calc_equal_weights: 等金額配分
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等配分にフォールバック）
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限（既存保有比率に基づいて新規候補を除外）
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull/neutral/bear のマッピング、未知レジームはフォールバック）
  - portfolio/position_sizing.py
    - calc_position_sizes: リスクベース / 等配分 / スコア配分に対応した発注株数計算
    - 単元株（lot_size）丸め、max_position_pct / max_utilization / cost_buffer を考慮した aggregate cap スケールダウンロジックを実装

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定するユーティリティを実装。
    - LOG_LEVEL / LOG_DIR / 引数による設定切替に対応。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py
    - psutil を用いたプロセス優先度設定（Windows の priority class、POSIX の nice 値）と CPU affinity 設定ユーティリティを実装。
    - 権限不足などで失敗した場合は警告を出してスキップ。

- 監視・検証ツール
  - monitoring 側の DB 初期化呼び出し（init_monitoring_db）を各起動スクリプトから担保。
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite DB からシステム稼働率・注文成功率・レイテンシ等を集計してレポートを生成する CLI を実装。
    - P95 の計算、各種閾値（稼働率 99% 等）に基づく PASS/FAIL 判定を搭載。
    - --from / --to / --db オプション対応。環境変数 PAPER_TRADING_SQLITE_PATH を優先。

- パッケージメタ
  - パッケージ初期化: src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

### Changed
- ログ出力設計
  - console は stdout に出力するよう統一（cron 等での一元リダイレクトを考慮）。
- .env ロード順
  - OS 環境変数 > .env.local > .env の順で読み込み（OS 環境変数は保護される）。

### Fixed / Behavior
- DB/監視周りの安全策
  - 起動時に監視用テーブルが存在しない場合でも init_monitoring_db() を呼んで冪等に初期化する（存在確認と作成）。
- ExecutionEngine 起動前チェック
  - data/stop_requested.flag が既に立っている場合はエンジンを起動せず終了する。

### Known issues / Notes
- research/factor_research.py の実装は途中（ファイル末尾で calc_momentum 実装開始のみ、以降未収録）。ファクター計算ロジックの完成とテストが必要。
- portfolio/risk_adjustment.apply_sector_cap:
  - 現状 price_map に価格が欠損（0.0）する場合のエクスポージャー過少見積りのリスクをコメントで指摘。将来的に前日終値等のフォールバックを検討する旨を TODO として残しています。
- position_sizing:
  - 現在 lot_size は全銘柄共通での扱い。将来的に銘柄別単元対応（stocks マスタの lot_size）への拡張を計画中。

### Removed
- なし

### Security
- なし

---

参考:
- 本 CHANGELOG はコードベースの実装内容から推測して作成しています。実際のリリース履歴や変更履歴管理（コミットログ・チケット）と異なる場合があります。必要に応じて差分を反映してください。