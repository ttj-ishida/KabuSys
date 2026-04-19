# Keep a Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

- 表記: YYYY-MM-DD
- リリースバージョンはパッケージの __version__ に合わせています。

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-19
初回リリース。日本株自動売買システム「KabuSys」のコアユーティリティ、実行／監視スクリプト、ポートフォリオ構築ロジック、設定管理および検証ツールなどを含みます。

### Added
- 全体
  - パッケージ初期バージョンを追加（__version__ = 0.1.0）。
  - DuckDB / SQLite を用いたデータ処理基盤を統合（duckdb, sqlite3 接続サポート）。

- 実行・監視
  - run_execution.py
    - ExecutionEngine を起動するエントリスクリプトを追加。
    - KABUSYS_ENV により paper_trading モード時は専用の paper_trading DB を使用して本番 DB と完全分離する実装。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - OrderRepository, OrderManager, RiskManager (RiskConfig), Reconciler を組み合わせてエンジンを構築。
    - エンジンスレッドの起動／監視、stop flag (data/stop_requested.flag) 検知による安全停止、execution.pid 出力（pid_file）を実装。
    - プロセス優先度を high に設定してから起動。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV に関わらず本番用 sqlite_path を使用することを明記。
    - stop flag によるループ終了、例外時のログ出力と継続処理、KeyboardInterrupt のハンドリングを実装。
    - プロセス優先度を high に設定してから起動。

- 設定管理
  - config.py
    - Settings クラスを追加し、環境変数から各種設定を取得・検証するユーティリティを提供。
    - J-Quants / kabu API / LINE / DB パス / 各種閾値（CPU/MEM/DISK）などをプロパティで取得可能。
    - KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の検証（有効値チェック）を実装。
    - 環境自動ロード: プロジェクトルート（.git または pyproject.toml を基準）を探索して .env と .env.local を読み込み。OS 環境変数を保護するため既存キーは上書きされない挙動を採用。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。

  - config_setup.py
    - .env を対話式に作成／更新するウィザード CLI を追加（項目定義・既存値の読み込み・マスク表示・保存）。
    - .env 書き込みテンプレートを提供し、生成時の注意（.env を Git にコミットしない）を明示。

  - validate_config.py
    - 起動前に設定不備を検出する CLI を追加。
    - 必須環境変数未設定・プレースホルダ検出・KABUSYS_ENV の検証・ログレベルの検証・DB パス親ディレクトリの存在チェック・config/*.yaml の存在と YAML パース検証（PyYAML が存在する場合）を実行。
    - KABUSYS_ENV=live のときの追加警告（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性）を実装。
    - --strict モードで警告を FAIL 扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定関数 setup_logging を追加。
    - stdout に StreamHandler、日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30日保管）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の優先順位を考慮し、ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラのクリア処理を安全に行い二重ロギングを防止。

  - utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定する set_process_priority を追加。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を追加（利用可能なコア数超過時の挙動やエラーハンドリングあり）。
    - 権限不足や未対応環境で安全に警告を出す実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順・タイブレークルール）を追加。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコアが 0.0 の場合のフォールバック）を追加。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限ロジックを実装（既存ポジション比率が閾値を超えるセクターの新規候補除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装（未知レジームはフォールバックと警告）。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に基づく発注株数算出ロジックを実装。
    - 単元株（lot_size）で丸め、per-stock 上限（max_position_pct）と aggregate cap（available_cash）を考慮したスケーリング処理、cost_buffer を使った保守的見積り、残余キャッシュ配分のための端数処理を実装。
    - 価格欠損時のスキップやログ出力あり。

- モニタリング DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を呼び出して監視用テーブルの存在を保証（冪等）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、リスク却下数、レイテンシ（平均/最大/P95）。
    - P95 計算ユーティリティ、日付フィルタ（ISO8601 UTC 変換）、閾値判定による PASS/FAIL を出力。
    - DB パスはコマンドライン --db / 環境変数 PAPER_TRADING_SQLITE_PATH / デフォルトの優先順。

- research
  - research/factor_research.py を追加（ファクター計算用モジュール。Momentum/Value/Volatility/Liquidity を想定）。DuckDB を用いた prices_daily / raw_financials 参照設計。※ファイル末尾に未完の箇所あり（今後拡張予定）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- 環境変数パーサーの強化（config._parse_env_line）
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱い、クォートなし時の # コメント処理などを正しく解析する実装を導入。
  - 空行・コメント行のスキップとキー無し行の無視。

### Removed
- （初回リリースのため該当なし）

### Security
- .env ファイルについて
  - config_setup で生成される .env に対し「絶対に Git にコミットしないこと」を明記。
  - config.Settings の必須トークン（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD）を明示し、未設定時は ValueError を投げる設計で起動時の漏れを防止。
  - config_setup / validate_config でシークレット項目はマスク表示する UX を提供。

---

注記 / 設計上の重要ポイント
- paper_trading モードは本番 DB と分離して設計されており、誤って本番データを書き換えるリスクを低減する意図があります。
- ロギングは stdout と日次ローテーションファイルの両方を使い、cron 等での運用を想定して stdout を利用する設計です（stderr ではなく stdout）。
- process_priority の設定や CPU affinity の適用は権限依存のため、失敗時は警告を出して安全にスキップします。
- position sizing / risk adjustment 周りは純粋関数化されておりユニットテストが容易な設計になっています（DB 参照なし）。
- research/factor_research.py はファクター計算のエントリを用意していますが、実装は継続的に拡張される想定です（ファイル末尾に未完の箇所あり）。

もし特定の変更点（例えば個別関数の振る舞いや CLI の出力例など）を CHANGELOG に詳細に追記したい場合は、どの部分を詳細化するか教えてください。