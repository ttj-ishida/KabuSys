# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このプロジェクトのバージョン情報はパッケージルートの `__version__`（src/kabusys/__init__.py）で管理されています。

なお、本CHANGELOGはソースコードの内容から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-19

### Added
- 初回公開・基盤実装
  - パッケージメタ情報を追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。
- 起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite（data/paper_trading.db）を使用する仕組みを搭載。
    - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager を組み立ててバックグラウンドスレッドで実行。
    - 起動前後に停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を扱う制御を実装。
  - システム監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor のポーリングループを実行。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番（monitoring）用の sqlite_path を使用する挙動を明記。
- 設定管理
  - 環境変数/.env 自動読み込みと Settings クラスを追加（src/kabusys/config.py）。
    - .env（および .env.local）の自動読み込み（OS 環境変数を保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - 複数の設定プロパティ（J-Quants / kabu API / DB パス / 監視閾値 / 環境判定など）を提供し、型変換と妥当性チェックを実装。
    - PAPER_FILL_MODE の検証・デフォルト、有効値チェックを実装。
- 設定用 CLI
  - 対話式 .env 作成ウィザードを追加（src/kabusys/config_setup.py）。
    - 入力プロンプト、既存 .env 読み込み、保存機能（.env を上書き）と確認プロンプトを実装。
    - 秘匿項目のマスク表示や選択肢サポートを実装。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在および YAML パース検証（PyYAML 利用可否に依存）など。
    - --strict オプションで警告を失敗扱いにする機能を追加。
    - 本番環境（KABUSYS_ENV=live）用の追加ガード（LINE 設定確認、KILL_FLAG_CLEAR_ON_START の警告）を実装。
- ログ/プロセスユーティリティ
  - 統一的なログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout 出力用 StreamHandler と 日次ローテートの TimedRotatingFileHandler（ログディレクトリ/ファイル生成に安全対策）をルートロガーにセットアップ。
    - ログレベル、ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux, macOS, FreeBSD）差分を吸収して優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアに固定する機能を提供。権限不足時は安全にスキップして警告を出力。
- ポートフォリオ構築ライブラリ
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順で上位 N を選択
    - calc_equal_weights: 等金額配分
    - calc_score_weights: スコア正規化配分（全スコア 0 の場合は等金額にフォールバック）
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有を考慮したセクター上限チェック（unknown セクターは除外しない）
    - calc_regime_multiplier: market regime（bull/neutral/bear）に基づく資金乗数（デフォルトと警告のフォールバックあり）
  - 株数決定・リスク制限（src/kabusys/portfolio/position_sizing.py）
    - リスクベース（risk_based）と等配/スコア配分（equal/score）をサポート
    - 単元株（lot_size）で丸め、max_position_pct/max_utilization/aggregate cap、cost_buffer を考慮したスケーリングアルゴリズムを実装
    - 価格欠損時のスキップやログ出力を実装
  - パッケージエクスポート（src/kabusys/portfolio/__init__.py）で主要関数を公開
- 解析/検証ツール
  - Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を集計して PASS/FAIL 判定を出力。
    - --from/--to/--db オプションによる期間・DB 指定、デフォルト DB は data/paper_trading.db。
    - P95 計算、各種 SQL クエリの耐障害（テーブル欠如時のデフォルト化）を実装。
- 研究モジュール（初期）
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - モメンタム・ボラティリティ・リクイディティ・バリュー等の計算を行う設計を記載（DuckDB 接続前提、prices_daily/raw_financials のみ参照）。

### Changed
- なし（初回リリースにつき該当なし）

### Fixed
- なし（初回リリースにつき該当なし）

### Security
- なし

注記:
- スクリプトやユーティリティは外部モジュール（psutil、duckdb、PyYAML 等）に依存します。実行環境に応じてこれらの依存関係をインストールしてください。
- .env ファイルは機密情報を含むため、リポジトリにコミットしないよう README 等で周知してください（config_setup.py でもその旨を明記）。
- 一部モジュール（例: monitoring.system_monitor, execution.execution_engine 等）は本CHANGELOG作成時点のコード片のインポートを前提にしており、実装の詳細は該当ファイルを参照してください。