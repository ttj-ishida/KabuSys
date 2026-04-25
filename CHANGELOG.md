# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルでは重要な変更点・追加機能・バグ修正などを人間が読める形で記載します。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

- なし

## [0.1.0] - 2026-04-25

初回リリース。以下の主要機能・ユーティリティ・CLI を含みます。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用の MockBrokerClient を使用し、data/paper_trading.db を利用して本番 DB と分離。
    - 実行中は data/execution.pid に PID を書き、 data/stop_requested.flag による停止を監視して安全に終了できる。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番の sqlite_path を使用して監視テーブルを初期化する。

- 設定管理
  - config.py
    - .env 自動読み込み（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - 複雑な .env 構文をサポート（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
    - Settings クラスを導入し、環境変数から型付け済みの設定を提供（パス類は pathlib.Path で返却）。
    - paper_trading 用の PAPER_TRADING_SQLITE_PATH / PAPER_FILL_MODE（instant/partial/never/reject）等をサポート。
    - 各種閾値・PID ファイルパスなどの監視・システム設定をプロパティとして提供。

- 設定ユーティリティ / CLI
  - config_setup.py
    - .env を対話式に作成・更新するウィザード。
    - デフォルト値・選択肢表示・シークレット入力・既存 .env の読み込みと再利用をサポート。
  - validate_config.py
    - 起動前に .env と config/*.yaml を検証する CLI。
    - 必須環境変数チェック・KABUSYS_ENV の妥当性・LOG_LEVEL 検証・DB パスの親ディレクトリ存在チェック・YAML のパース確認（PyYAML があれば）・本番用ガード（LINE 通知・KILL_FLAG_CLEAR_ON_START）などを実施。
    - --strict フラグで警告を失敗扱いにできる。

- ポートフォリオ構築ライブラリ (純粋関数群)
  - portfolio/portfolio_builder.py
    - シグナルの候補選定（得点降順 + タイブレーク）select_candidates。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（スコア総和が 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有のセクター別時価比率を計算して新規候補を除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をサポート、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - 単元株丸め・リスクベース・等分配・スコア配分に基づく株数決定 calc_position_sizes。
    - aggregate cap のスケーリング、lot_size 単位での再配分アルゴリズム、cost_buffer による保守的コスト見積りを実装。

- モニタリング・実行周りのインフラ
  - monitoring_db 初期化呼び出し（監視テーブルの存在を保証する init_monitoring_db の利用）。
  - ExecutionEngine 周りで OrderManager / OrderRepository / RiskManager / Reconciler を組み立てるサンプル実装（RiskConfig のデフォルト値を含む）。
  - ExecutionEngine は別スレッドで run_session を実行し、停止フラグ検知時に安全停止するロジックを含む。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から統計を集計し、稼働率・注文成功率・送信率・レイテンシ（P95）等を表示するレポートを生成。
    - 判定基準（稼働率 >= 99%、成立率 >= 90% 等）と PASS/FAIL 出力を実装。
    - 日付フィルタ（--from / --to）と DB パス指定（--db）をサポート。

- ユーティリティ
  - utils/logging_setup.py
    - 共通のログ初期化関数 setup_logging を提供。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）を設定。既存ハンドラをクリアして二重設定を防止。
    - LOG_DIR 作成失敗時にはファイルハンドラをスキップして console のみで継続。
  - utils/process_priority.py
    - Windows / POSIX(Linux/Mac/FreeBSD) に対応したプロセス優先度設定（set_process_priority）。
    - CPU affinity 固定ユーティリティ set_cpu_affinity。
    - 権限不足や未対応プラットフォーム時は安全にログを出してスキップする。

- データ分析基盤（研究用）
  - research/factor_research.py（モジュール開始）
    - DuckDB 接続を受け取り、prices_daily / raw_financials を使ってモメンタム等のファクターを計算する設計（モジュール構造と定数を導入。calc_momentum の実装が続く形で含まれる）。

### Changed
- ログ出力挙動
  - StreamHandler を stderr ではなく stdout に送るように変更（Task Scheduler / cron 環境でのリダイレクト想定）。
  - 既存ハンドラは初期化時に一度 flush/close してから削除することで二重ログ出力を回避。

- DB の取り扱い
  - 監視（monitoring）は KABUSYS_ENV に依存せず常に本番 sqlite_path を使って初期化（監視データの一貫性確保のため）。
  - ExecutionEngine は is_paper 判定により paper_trading 用 DB を使い、本番データと分離。

### Fixed
- .env パーサの堅牢化
  - クォート内のバックスラッシュエスケープ・対応する閉じクォート探索、インラインコメントの扱いなどを改善して .env のパースをより堅牢にした。

- 安全停止の実装
  - run_execution/run_monitoring それぞれで data/stop_requested.flag による停止検知を実装。既存フラグがある場合は起動を中止するガードも追加。

### Notes / その他
- 環境変数の自動読み込みはプロジェクトルート検出に依存するため、パッケージ配布後やルートが特定できない環境では自動ロードがスキップされます（必要なら環境変数を手動で設定してください）。
- PAPER_FILL_MODE の有効値は "instant" / "partial" / "never" / "reject"。無効な値は起動時に例外を送出します。
- ファイル・ディレクトリ作成に失敗した場合は可能な限りフェールセーフにして、ログはコンソール出力のみになるように設計されています。

---

今後の予定（例）
- factor_research の各ファクター計算の完全実装（Momentum / Value / Volatility / Liquidity）。
- ExecutionEngine 周りの詳細なユニットテスト・統合テストの充実。
- 銘柄別 lot_size のサポート、手数料・スリッページモデルの高度化。
- Paper Trading のレポートに可視化（CSV/HTML）出力オプション追加。

署名:
- バージョンはパッケージ内の __version__ に従い 0.1.0 を初回リリースとしています。