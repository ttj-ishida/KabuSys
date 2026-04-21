# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

なおリリースバージョンはパッケージメタ情報（kabusys.__version__）に合わせて 0.1.0 としています。

## [Unreleased]

（現在のリポジトリ状態は 0.1.0 として初回リリースされました。以降の変更はここに追加してください。）

## [0.1.0] - 2026-04-21

初回リリース。日本株自動売買システム「KabuSys」の基盤機能とユーティリティ群を追加。

### Added
- パッケージ初期構成
  - パッケージメタ情報: kabusys.__version__ = "0.1.0" を追加。

- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db 等）を使用し、本番 DB と分離して MockBrokerClient が使える設計をサポート。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル(data/execution.pid) による起動/停止制御。
    - プロセス優先度を "high" に設定する処理を起動直後に実行。
    - duckdb 接続を利用。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告を出す。
    - 監視は KABUSYS_ENV にかかわらず「本番」sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）を検知して安全にループを終了する。

- 設定・環境管理
  - config.py
    - Settings クラスで各種設定値を環境変数から提供（J-Quants / kabuステーション / DB パス / 監視閾値 / 実行環境判定など）。
    - .env 自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml から検出）。OS 環境変数は保護され、.env.local により上書き可能。
    - .env パースはクォート／エスケープ／export プレフィックス／インラインコメントなど通常のケースを考慮して実装。
    - PAPER_FILL_MODE などの値検証を導入（許容値以外は例外発生）。

  - config_setup.py
    - 対話式の環境設定ウィザード (.env の作成/更新) を追加。秘密値はマスク表示。
    - デフォルトや既存値を利用でき、最終確認後に .env を生成。

  - validate_config.py
    - 起動前に環境変数および config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML ファイルのパース検証（PyYAML がない場合はスキップ）を実行。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 共通のログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテートするファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ自動作成。失敗時はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL/LOG_DIR の優先解決を実装。

  - utils/process_priority.py
    - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティ（Windows の HIGH_PRIORITY_CLASS / POSIX の nice 値対応）を追加。
    - CPU affinity を特定コアに固定する set_cpu_affinity() を実装。
    - psutil を用い、権限不足や未対応 OS の場合は警告を出して安全にスキップする。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルの候補選定（select_candidates）、等重み配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - calc_score_weights は全スコアが 0 の場合に等重みへフォールバックして警告を出す。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を追加（当日売却予定銘柄をエクスポージャー計算から除外、"unknown" セクターは制限適用対象外）。
    - 市場レジームに応じた乗数 calc_regime_multiplier を実装（bull/neutral/bear をマップ、未知レジームは警告して 1.0 フォールバック）。

  - portfolio/position_sizing.py
    - 各銘柄の発注株数算出ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1銘柄上限・全体の aggregate cap、コストバッファ考慮、合計が現金を超えた場合のスケーリングと端数の再配分ロジックを実装。
    - 価格が欠損／不正な場合はスキップする保護を追加。

  - portfolio/__init__.py
    - 上記関数をパッケージエクスポートとしてまとめた公開 API を提供。

- 解析・研究ユーティリティ
  - research/factor_research.py
    - DuckDB 接続を受けてモメンタムなどの因子を計算するための骨組みを追加（関数 calc_momentum などの実装開始。prices_daily / raw_financials を前提）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加（期間指定オプション、DB パス指定オプションをサポート）。
    - システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均・最大・P95）などを集計し PASS/FAIL を判定する閾値を導入（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms の基準を採用）。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Deprecated
- （初回リリースにつき該当なし）

### Removed
- （初回リリースにつき該当なし）

### Security
- 環境変数や .env の扱いにおいて、secret フィールドのマスク表示や OS 環境変数保護の仕組みを導入し、誤って機密を上書きするリスクを低減。

---

注:
- 各モジュールは可能な限り副作用を避け、純粋関数または明示的な初期化を行う設計を目指しています（例: Portfolio 関数群は DB 参照を行わない設計）。
- 一部のコメントには将来的な拡張（銘柄個別の lot_size マスタ追加、価格フォールバック処理等）の TODO が残されています。