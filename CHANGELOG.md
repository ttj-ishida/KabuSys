# Changelog

すべての非互換な変更はメジャーバージョンに、後方互換の追加はマイナーバージョンに記載します。  
このファイルは Keep a Changelog の形式に準拠しています。

- 未リリースの変更は Unreleased に記載します。
- 日付は YYYY-MM-DD 形式で記載します。

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース

### Added
- 基本アプリケーションモジュールを追加
  - kabusys パッケージの初期バージョンを追加（__version__ = "0.1.0"）。
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は Paper Trading 用の専用 SQLite(DB) を使用する（デフォルト: data/paper_trading.db）。本番 DB と完全に分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み合わせて ExecutionEngine を起動。
    - プロセス優先度を "high" に設定（起動直後）。停止フラグ（data/stop_requested.flag）に応じた安全な停止処理を実装。
    - PID ファイル書き込み用の処理（execution.pid）を利用。
    - RiskManager のデフォルト構成値を定義（max_position_pct, max_utilization, rate_limit_per_sec など）。
- 監視用スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）でループ終了。
- 設定・環境管理
  - config.py
    - .env 自動読み込み機能を追加（プロジェクトルート検出: .git または pyproject.toml）。
    - .env パース機能を実装（export プレフィックス対応、クォートとエスケープ、インラインコメント処理）。
    - Settings クラスを追加し、環境変数のプロパティ取得・検証を提供（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の検証等）。
    - デフォルトの DB パス等をプロパティで提供（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH 等）。
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を追加。
    - 複数の設定項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）。
    - 既存 .env の読み込み、シークレットのマスク表示、保存前の確認を実装。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ確認、config/*.yaml の存在および YAML パース検証（PyYAML が存在する場合）を実装。
    - KABUSYS_ENV=live 時の追加警告（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性）。
    - --strict モードで警告を FAIL として扱う機能を追加。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコア全てが 0 の場合は等金額配分へフォールバック（警告出力）。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（sell 対象除外、"unknown" セクターは除外しない挙動）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をマップ、未知レジームは 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に基づく株数計算を実装。
    - 単元株（lot_size）丸め、position 上限、aggregate cap（利用可能現金を超える場合のスケーリング）を実装。
    - cost_buffer による保守的コスト見積りを考慮したスケールダウンと端数配分アルゴリズムを実装。
- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーの統一設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app>.log、30 日分保持）を設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装し、ディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py
    - psutil を利用したクロスプラットフォームなプロセス優先度設定（Windows の優先度クラス、POSIX の nice 値）を実装。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供（アクセス拒否等は警告でスキップ）。
- ツール
  - tools/paper_verification_report.py
    - ペーパートレード DB を解析して検証レポートを生成する CLI を追加。
    - システム稼働率、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、API レイテンシ（avg/max/P95）を計算・表示。
    - P95 計算、期間フィルタ、閾値による PASS/FAIL 判定を実装。
- 研究用モジュール（スケルトン）
  - research/factor_research.py
    - ファクター計算（モメンタム、MA200、ATR、流動性、Value 指標）用の骨組みを追加。DuckDB 接続を受けて prices_daily / raw_financials を利用する設計。モメンタム計算関数の雛形を含む（未完の実装あり）。

### Changed
- ログの統一
  - すべての起動スクリプトが setup_logging を呼び出して統一されたログ出力形式とファイルローテーションを利用するようになった。
- プロセスの初期化
  - 起動時にプロセス優先度を "high" に設定する処理を実装（run_execution/run_monitoring）。

### Fixed / Behavior
- .env パーサの強化
  - export プレフィックス、クォート内バックスラッシュエスケープ、インラインコメントの取り扱いを明確化。これにより .env の柔軟な記述に対応。
- 環境変数の自動ロード
  - プロジェクトルートが検出できない場合は自動ロードをスキップする安全設計。
  - OS 環境変数を保護するため .env 読み込み時に既存キーを上書きしない挙動（.env.local は上書き可能だが protected により OS 環境変数は保護）。
- Paper Trading 分離
  - ペーパートレード時の DB を本番 DB と分離することでテスト/検証時のデータ汚染を防止。

### Notes / Known limitations
- research/factor_research.py は一部未完の実装（モメンタム計算の続きが存在しません）。将来的に DuckDB を使った完全なファクター計算を実装予定。
- 一部のファイルや関数に TODO コメントあり（例: price の欠損時のフォールバック、銘柄別 lot_size のサポートなど）。
- run_monitoring は「監視は常に本番 sqlite_path を使用する」仕様になっている点に注意してください（設計上の意図）。

---

今後のリリースでは、research モジュールの完成、Strategy / Execution のテストカバレッジ拡充、監視・アラートの強化（LINE 通知連携など）を予定しています。