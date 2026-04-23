# Changelog

すべての重要な変更は Keep a Changelog のフォーマットに従って記載します。  
このファイルはコードベース（src/kabusys）から推測して作成した初期リリース向けの変更履歴です。

なおバージョンはパッケージ定義（src/kabusys/__init__.py の __version__）に合わせて v0.1.0 を初回リリースとしています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-23

### Added
- プロジェクト初期リリース。日本株自動売買システム「KabuSys」基本コンポーネントを実装。
- パッケージメタ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を定義。

- 実行用スクリプト
  - run_execution
    - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント抽象化。
    - OrderRepository, OrderManager, RiskManager (RiskConfig), Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）と pid ファイル（data/execution.pid）による制御。
    - 実行はデーモンスレッドで行い、停止検知時に安全に停止する仕組みを実装。

  - run_monitoring
    - SystemMonitor ポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する（監視 DB の初期化を実施）。
    - 停止フラグ（data/stop_requested.flag）によりループを終了。
    - SQLite / DuckDB 接続を確立して SystemMonitor を利用。

- 設定管理
  - Settings クラス（src/kabusys/config.py）を導入し、環境変数を型付きプロパティで取得。
    - DB パス (DUCKDB_PATH, SQLITE_PATH)、ペーパートレード用パス (PAPER_TRADING_SQLITE_PATH)、PID/kill フラグ関連、各種しきい値（CPU/MEM/DISK）、ログレベル、実行環境（KABUSYS_ENV）などを扱う。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - KABUSYS_ENV のバリデーション（development/paper_trading/live）。
  - .env 自動読み込み機能
    - プロジェクトルート（.git / pyproject.toml を探索）を検出し、.env と .env.local を自動読み込み（OS 環境変数を保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env 解析は export プレフィックス、クォート文字、エスケープ、インラインコメント処理等を考慮。

- 設定ユーティリティ / CLI
  - config_setup（src/kabusys/config_setup.py）
    - 対話式ウィザードで .env を新規作成 / 更新するツール。
    - J-Quants / kabu API / DB パス / LOG_LEVEL / KILL フラグ等の主要項目をサポート。
  - validate_config（src/kabusys/validate_config.py）
    - 起動前に .env と config/*.yaml の基本チェックを実行する CLI。
    - 必須環境変数チェック、KABUSYS_ENV の検証、LOG_LEVEL の検証、DB パスの親ディレクトリ確認、config YAML の存在と（PyYAML がある場合は）簡易パース検証、live 環境向けの追加ガードを実装。
    - --strict オプションで警告をエラー扱いにできる。

- ロギング / プロセス管理ユーティリティ
  - logging_setup（src/kabusys/utils/logging_setup.py）
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定するユーティリティ。
    - ログレベル & ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - process_priority（src/kabusys/utils/process_priority.py）
    - psutil を使ったプロセス優先度（high/normal/low）設定。
    - Windows / POSIX (Linux, Darwin, FreeBSD) の差分を吸収。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を提供（アクセス権限失敗時は警告してスキップ）。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: BUY シグナルのスコア降順選定（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分、スコア加重配分（スコア全て0のときは等金額へフォールバック）。
  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: セクター集中を防ぐため既存保有比率に基づく候補除外。
    - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に応じた投下資金乗数（フォールバックは 1.0）。
  - position_sizing（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づき発注株数を算出。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash 超過時のスケーリング）、
      cost_buffer による保守的見積り、残余の端数配分ロジックなどを実装。

- 研究（リサーチ）モジュール（未完の関数を含む）
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum / Value / Volatility / Liquidity の計算方針を実装。DuckDB を用いた prices_daily / raw_financials 参照でのファクター計算を想定。
    - モメンタム計算（calc_momentum）等の骨格（パラメータ、ウィンドウ定義、エッジケースの取り扱い）を含む（ファイル末尾に未完の箇所あり）。

- Paper Trading 検証ツール
  - paper_verification_report（src/kabusys/tools/paper_verification_report.py）
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH デフォルト）を解析して検証レポートを生成。
    - 指標: 稼働率 (uptime_pct)、注文成功率 (fill_rate)、送信率 (send_rate)、P95 レイテンシ、リスク却下数 等。
    - パス/フェイル基準を定義（稼働率 99%、成功率 90% 等）して総合判定を出力。
    - P95 計算、期間フィルタ、欠損テーブルへのフォールバック処理を実装。

- データベース / 初期化
  - monitoring_db 初期化関数（run_* スクリプトから利用）を呼び出して監視テーブル群の存在を保証する仕組みを導入。
  - DuckDB を分析用 DB として採用し、実行・監視ともに duckdb 接続を確立して利用。

### Changed
- （初回リリースにつき過去の変更履歴はなし。ただし設計上の注記や TODO をコード内に記載。）

### Fixed
- （初回リリースにつき修正履歴はなし）

### Security
- .env ファイルを生成する際に「.env は絶対に Git にコミットしないこと」を明示。

## 今後の予定（所見）
- factor_research の実装完了（calc_momentum の続きなど）。
- stocks マスタに単元情報を持たせる等の position_sizing の拡張（lot_size の銘柄別対応）。
- 監視・実行コンポーネントのユニットテスト整備とエンドツーエンドの稼働検証。
- ロギング・エラーハンドリング強化（ログ回転・永続化の障害時のフォールバック改善など）。

---

参照:
- src/kabusys 以下のスクリプト・モジュール群（run_execution, run_monitoring, config, config_setup, validate_config, portfolio, utils, research, tools 等）に基づき作成。