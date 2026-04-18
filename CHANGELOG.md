# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
現在のバージョン: 0.1.0

フォーマットの詳細: https://keepachangelog.com/ (英語)

## [Unreleased]

(現時点では未リリースの変更はありません)

---

## [0.1.0] - 初回リリース

最初の公開リリース。以下の主要機能、ユーティリティ、CLI、ライブラリ群を追加しました。実装は主に本番／ペーパートレード両対応の自動売買システム（KabuSys）を想定しています。

### Added

- 全体
  - パッケージの初期バージョンを追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。
  - DuckDB / SQLite を用いたデータ保存・解析基盤を標準で利用する設計を導入。デフォルトパスは data/kabusys.duckdb / data/monitoring.db（設定で上書き可能）。

- 起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を利用して paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に記録することで本番データと完全に分離。
    - BrokerClientFactory によるブローカークライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）・PID ファイル（data/execution.pid）管理に対応。スレッドでエンジンを実行し、停止フラグ検知で安全に停止。
  - 監視（モニタ）起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor のポーリングループを実行。デフォルトポーリング間隔 60 秒、環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（不正値はデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する（監視用テーブルの初期化を行う）。
    - 停止フラグでループを終了し、SQLite / DuckDB 接続を確実にクローズする。

- 設定管理
  - Settings クラスを追加（src/kabusys/config.py）。
    - 環境変数から各種設定を取得するプロパティ群を提供（J-Quants トークン、kabu API、DB パス、ログ設定、監視閾値など）。
    - `KABUSYS_ENV` の検証（development / paper_trading / live）、`LOG_LEVEL` の検証、`PAPER_FILL_MODE` のバリデーション（instant/partial/never/reject）等を実装。
    - paper_trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）、pid / kill flag のパス、閾値（CPU / memory / disk ％）などをプロパティとして公開。
  - .env 自動読み込み機能を実装（同ファイル内）。
    - 自動読み込みの優先順: OS環境 > .env.local > .env。プロジェクトルートは .git または pyproject.toml を探索して決定。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env 読み込みロジックは export プレフィックス／シングル／ダブルクォート／エスケープ／インラインコメント等に対応した堅牢なパーサを実装。

- 設定ユーティリティ（CLI）
  - 環境設定ウィザードを追加（src/kabusys/config_setup.py）。
    - 対話形式で .env を作成・更新するウィザード。J-Quants トークンや KABU_API_PASSWORD などの必須項目を扱う。
    - 既存 .env の読み込み、シークレット項目のマスク表示、確認プロンプト、保存処理を実装。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - .env および config/*.yaml の存在や値の妥当性を検証。必須環境変数チェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリチェック、YAML パース（PyYAML があれば実施）などを行い、errors/warnings/infos を出力。
    - --strict オプションで警告を失敗として扱うモードを提供。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順で上位 N を選択（同点は signal_rank でブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（スコア合計が 0 の場合は等金額にフォールバック）。
  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有によりセクターの比率が閾値を超える場合に新規候補を除外。unknown セクターは適用除外。
    - calc_regime_multiplier: market regime に応じた投資乗数（bull/neutral/bear のマッピング、未知レジームはフォールバック）。
  - 株数決定・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: risk_based / equal / score の allocation_method に対応。リスクベースのポジションサイズ計算、単元株（lot_size）での丸め、aggregate cap（available_cash）を超える場合のスケーリングと残差処理を実装。
  - これらはすべて DB 非依存（メモリ内純粋関数）として設計され、将来的にマスタ参照等へ拡張しやすい形にしている。

- 監視・モニタリング関連
  - monitoring_db 初期化（init_monitoring_db を各起動スクリプトで呼び出し）を導入。監視テーブルの冪等な確保を行うことで実運用でのテーブル未作成による障害を防止。
  - SystemMonitor を用いた定期チェックの仕組み（run_monitoring からの起動）をサポート（ポーリング間隔は環境変数で調整可能）。

- ユーティリティ
  - ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテート、30日保持）をルートロガーに設定。ログディレクトリの自動作成や作成失敗時のフォールバック、ログレベルの解決順（引数 → 環境変数 → デフォルト）を実装。
  - プロセス優先度および CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - set_process_priority(level): Windows / POSIX に対応した優先度設定（"high" / "normal" / "low"）。psutil のアクセス拒否等は警告でスキップ。
    - set_cpu_affinity(cpu_count): カレントプロセスを最初の N コアに固定する機能。エラー時は警告でスキップ。

- ペーパートレード検証ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - SQLite（デフォルト: data/paper_trading.db）からシステム稼働率、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を集計してレポートを出力。
    - CLI オプション: --from / --to（YYYY-MM-DD 形式）および --db（DBパス）。P95 計算、閾値定義（稼働率 99%、fill 90%、send 95%、P95 latency 200ms）を実装。データ不足時には N/A を表示し、基準未達は FAIL として判定。

- リサーチ（初期実装）
  - factor_research モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum ファクター（1M/3M/6M リターン、MA200 乖離）の計算ロジックを開始（DuckDB の prices_daily テーブル参照を前提）。一部実装（ファイル末尾での続き）があるため、将来的に他ファクター（Value/Volatility/Liquidity）や完全実装を追加予定。

### Changed

- （初回リリースのため該当なし）

### Fixed

- （初回リリースのため該当なし）

### Security

- （該当なし）

### Notes / Usage highlights

- .env / 環境変数
  - 自動読み込みはデフォルトで有効。テスト等で無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - .env のパースはクォートや export 形式、インラインコメント等に対応しているため既存の .env フォーマットを広くサポートします。
- ペーパートレード分離
  - KABUSYS_ENV=paper_trading を設定すると、Execution は paper_trading 用 DB を使用し、実運用データと分離して検証が可能です。
- ログ
  - setup_logging(app_name="...") を使用することで統一的なログ出力（stdout + 日次ファイルローテーション）が利用可能。ログディレクトリは LOG_DIR 環境変数で上書きできます。
- 停止フラグ
  - data/stop_requested.flag を作成することで long-running なプロセス（監視・実行）を外部から安全に停止できます。
- 依存
  - psutil（プロセス優先度 / affinity）、duckdb、sqlite3、（任意で PyYAML）などを使用します。環境により一部機能がスキップ（警告表示）されます。

---

既知の未完事項 / TODO（今後の改善候補）
- factor_research の完全実装（Value, Volatility, Liquidity の計算、Zスコア正規化等）。
- position_sizing の lot_size を銘柄毎に扱う拡張（将来の stocks マスタ参照）。
- monitor / execution のより詳細な監視メトリクス収集・アラート通知（LINE 等の統合）。
- 単体テスト・統合テストの追加（CI ワークフロー）。

---

（以上）