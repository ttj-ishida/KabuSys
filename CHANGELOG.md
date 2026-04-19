# Changelog

すべての重要な変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

リンク: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
（なし）

---

## [0.1.0] - 2026-04-19

初回リリース。

### Added
- 実行用エントリポイント
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止制御用の stop_requested.flag と実行中 PID を残す execution.pid に対応。
    - Engine をデーモンスレッドで起動し、停止フラグ検知で安全にシャットダウンするループを実装。
- 監視用エントリポイント
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL により上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path（data/monitoring.db 等）を使用して監視テーブルを管理。
    - 停止フラグ検知によるループ終了、KeyboardInterrupt のハンドリング、例外発生時のログ出力を実装。
- 設定・環境変数管理
  - config.py: Settings クラスを追加。
    - .env 自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）。
    - 複雑な .env 行（export プレフィックス、クォート、エスケープ、インラインコメント等）のパース実装。
    - 各種設定プロパティ（DB パス、PAPER_FILL_MODE、PID / kill flag パス、閾値等）を提供、入力検証を実施。
    - settings インスタンスをエクスポート。
- 設定ウィザード / 検証 CLI
  - config_setup.py: 対話式ウィザードで .env を作成/更新する CLI を追加。
    - シークレット表示マスク、選択肢、デフォルト値、保存前の確認を実装。
  - validate_config.py: 起動前に環境変数や config/*.yaml の妥当性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、YAML パース検証（PyYAML がある場合）等を実装。
    - --strict オプションで警告をエラー扱いにできる。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア順）、等金額配分、スコア加重配分（スコア全0 の場合は等金額にフォールバック）を実装。
  - portfolio/position_sizing.py
    - position sizing（risk_based / equal / score）実装。単元株（lot_size）丸め、aggregate cap によるスケールダウン、コストバッファの考慮などを実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）実装。既存ポジションを考慮して同一セクターの新規候補を除外するロジック。
    - 市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear）を実装。未知のレジームは 1.0 でフォールバック。
  - portfolio パッケージの __init__ で主要関数をエクスポート。
- ログ・プロセスユーティリティ
  - utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、デフォルト 30 日保持）をルートロガーに統一してセットアップするユーティリティを追加。
    - LOG_LEVEL / LOG_DIR / app_name 経由で設定可能。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - Windows / POSIX（Linux/macOS/FreeBSD）に対応したプロセス優先度設定（nice / HIGH_PRIORITY_CLASS 等）と CPU affinity セットのユーティリティを追加。
    - 権限不足等で設定できない場合は警告ログでスキップ。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite から期間指定で各種指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計・表示するレポートジェネレータを追加。
    - デフォルト DB パスは data/paper_trading.db。--from / --to / --db オプションをサポート。
    - PASS/FAIL 基準値（稼働率 99%、成立率 90% 等）が定義されており、基準未満の指標は FAIL として判定。
- データベース接続
  - DuckDB と SQLite の併用を想定した接続コードを各所で採用（monitoring, execution, research 等）。
- パッケージメタ情報
  - __init__.py に __version__ = "0.1.0" を設定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Known issues / Notes / TODO
- research/factor_research.py はモメンタム等ファクター計算の実装を始めているが、ファイル末尾が途中で切れている（"start_da" で終端）。本格運用前に完成・テストが必要。
- portfolio/risk_adjustment.apply_sector_cap:
  - price の欠損時（0.0）にエクスポージャーが過小見積もられる旨の TODO コメントあり。前日終値などのフォールバック価格導入が検討されている。
- position_sizing の現状:
  - 全銘柄で共通の lot_size を前提としている。将来的に銘柄別 lot_size マスタを導入する予定（TODO コメントあり）。
- .env 自動読み込み:
  - プロジェクトルートが特定できない場合は自動ロードをスキップする設計。配布後のパッケージ化環境でも安全に動作するが、意図せず自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使用可能。
- セキュリティ注意:
  - config_setup で生成される .env は絶対に Git 等にコミットしない旨を README/出力でも強調。
- テスト・例外処理:
  - 実行中の例外はログに記録して一定待機後に再試行する設計（監視ループ等）。長期稼働の観点で詳細なリトライ戦略やエラー分類・通知（LINE 連携等）の整備が必要。

---

タグ: initial release, monitoring, execution, portfolio, paper-trading, duckdb, sqlite, logging, process-priority, cli, config-wizard, validate-config

