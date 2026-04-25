# Changelog

すべての重要な変更点をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。  
リリースに含まれる内容は、ソースコードから推測可能な機能追加・挙動を要約したものです。

なおバージョンはパッケージ内の __version__ に合わせて 0.1.0 としています。

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-04-25
初回リリース。自動売買システム KabuSys のコアユーティリティ、実行/監視ランナー、環境設定ツール、ポートフォリオ構築ロジック、レポート・リサーチユーティリティを追加。

### Added
- 全体
  - パッケージの初期バージョンを追加（__version__ = "0.1.0"）。
  - DuckDB / SQLite をデータ永続化に利用する設計を導入（設定でパス指定可能）。

- 設定管理
  - 環境変数・.env 読み込み機能を追加 (`kabusys.config.Settings`)。
    - 自動でプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local をロード。
    - OS 環境変数を保護するための上書き制御（protected）を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env パースでシングル/ダブルクォートや export 形式、コメント処理に対応。
  - 各種環境変数プロパティを提供（J-Quants、kabuAPI、LINE、DBパス、監視閾値、環境判定など）。
  - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等の paper_trading 向け設定を実装。

- 環境設定 CLI
  - 対話式 .env 作成/更新ウィザード (`kabusys.config_setup`) を提供。
    - 秘匿項目は表示をマスクして扱う。
    - デフォルト・選択肢・説明付きでユーザー入力を収集し .env に書き出す。
    - 生成された .env に対する注意書きを付与（.env を Git にコミットしない等）。

- 設定検証 CLI
  - 起動前の設定検証ツール (`kabusys.validate_config`) を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値検証、LOG_LEVEL チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在および PyYAML がある場合はパース検証を行う。
    - --strict モードで警告を FAIL 扱いにするオプションあり。
    - live 環境向けの追加ガード（LINE 設定未設定の警告、KILL_FLAG_CLEAR_ON_START 警告など）。

- 実行・監視ランナー
  - ExecutionEngine 起動スクリプト (`kabusys.run_execution`) を追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db など）を使用し、本番 DB と分離する挙動を実装。
    - BrokerClientFactory を利用して本物または Mock ブローカークライアントを生成する仕組みを想定。
    - スレッドで engine.run_session を実行し、stop flag（data/stop_requested.flag）で停止制御。PID ファイル path を使用。
    - 起動時にプロセス優先度を "high" に設定。
  - SystemMonitor ポーリングループ起動スクリプト (`kabusys.run_monitoring`) を追加。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL でオーバーライド可能（デフォルト: 60 秒）。不正値はログ警告を出してデフォルトにフォールバックする。
    - 監視用 DB（monitoring）は KABUSYS_ENV に関わらず本番 sqlite_path を使用する旨を明記。
    - stop flag による終了検知、例外はログ出力して次のポーリングへ継続。

- ロギング・プロセス管理ユーティリティ
  - 統一ログ設定ユーティリティ (`kabusys.utils.logging_setup.setup_logging`) を追加。
    - 標準出力（stdout）向け StreamHandler と 日次ローテート file handler（TimedRotatingFileHandler）をルートロガーへ設定。
    - ログレベル/ログディレクトリは引数・環境変数・デフォルトの順で解決。ログローテーションは 30 日分保持。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールのみで継続。
  - プロセス優先度・CPU affinity ユーティリティ (`kabusys.utils.process_priority`) を追加。
    - Windows/Linux/macOS 等の差分を吸収してプロセス優先度（high/normal/low）の設定を試みる。
    - CPU affinity を最初の N コアに固定する関数を提供（権限不足や未対応環境では警告を出してスキップ）。

- ポートフォリオ構築
  - 銘柄選定・重み付け処理 (`kabusys.portfolio.portfolio_builder`) を追加。
    - select_candidates: score 降順、score 同値時は signal_rank 昇順で上位 N を選択。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（スコア合計が 0 の場合は等金額にフォールバック）。
  - セクター集中制限・レジーム乗数 (`kabusys.portfolio.risk_adjustment`) を追加。
    - apply_sector_cap: 既存保有のセクター暴露が閾値を超える場合、新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは警告して 1.0 でフォールバック。
  - 株数決定・リスク制限・単元丸め (`kabusys.portfolio.position_sizing`) を追加。
    - allocation_method に "risk_based" と "equal"/"score" をサポート。
    - リスクベースでは risk_pct と stop_loss_pct を用いてベース株数を算出。
    - 单元株（lot_size）で切り捨て、aggregate cap 超過時はスケールダウンして残差を lot 単位で再配分するロジックを実装。
    - コストバッファ（cost_buffer）を考慮して保守的にコスト見積もり。

- Paper Trading 検証ツール
  - Paper Trading レポート生成スクリプト (`kabusys.tools.paper_verification_report`) を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）等を算出。
    - P95 計算実装、期間フィルタ（from/to）対応、閾値による PASS/FAIL 判定を実装。
    - DB パス解決順: --db オプション > PAPER_TRADING_SQLITE_PATH 環境変数 > デフォルト。
    - デフォルト閾値: uptime >= 99.0%, fill_rate >= 90.0%, send_rate >= 95.0%, P95 latency <= 200 ms。

- リサーチ
  - ファクター計算モジュールの骨組みを追加 (`kabusys.research.factor_research`)。
    - Momentum / Value / Volatility / Liquidity 等のファクター計算方針をコメント・定数として追加。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計を採用。
    - モメンタム計算（calc_momentum）の実装を開始（ファイル途中で切れているが設計方針・定数を含む）。

### Changed
- N/A（初回リリースのため既存機能からの変更はなし）

### Fixed
- N/A（初回リリースのためバグ修正履歴はなし）

### Security
- 機密情報 (.env) の取り扱いについて注意喚起を追加（config_setup のヘッダとコード内コメント）。
- .env ファイルの自動読み込みは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）でテスト等の安全性を考慮。

### Notes / Usage tips
- 監視ループのポーリング間隔は MONITOR_POLL_INTERVAL で制御（秒）。不正な値はログ警告後 60 秒にフォールバック。
- 本番とペーパートレードの DB は分離して扱う（Execution は KABUSYS_ENV により paper_sqlite_path を使用）。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存。ログディレクトリ作成に失敗した場合は標準出力のみで継続。
- Process priority / CPU affinity の設定は権限やプラットフォームに依存するため、適用できない場合は警告が出てスキップされる。
- validate_config と config_setup を併用して .env を作成 → 検証 を行うことを推奨。

---

以上。必要であれば各ファイル毎の詳細な変更点（関数/クラスの API、引数説明、動作上の注意点など）を追記します。どのレベルの詳細を追記しましょうか？