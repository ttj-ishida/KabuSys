CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" の慣習に準拠します。
このプロジェクトのバージョニングは SemVer を使用します。

Unreleased
----------
（現在未リリースの変更はここに記載）

[0.1.0] - 2026-04-21
-------------------

Added
- 初回リリース (v0.1.0)
- コア機能の実装:
  - 実行エンジン起動スクリプト: run_execution.py
    - ExecutionEngine をデーモンスレッドで起動・監視する仕組みを提供。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) による外部制御対応。
    - KABUSYS_ENV=paper_trading のときは paper_trading 用の SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離して MockBrokerClient を利用可能（BrokerClientFactory 経由）。
    - RiskManager、OrderManager、OrderRepository、Reconciler 等のコンポーネント組み立てロジックを実装。
    - デフォルトの RiskConfig 値を設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - 監視ポーリング起動スクリプト: run_monitoring.py
    - SystemMonitor をポーリングで定期実行。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒、無効値はデフォルトへフォールバック）。
    - 監視データ用 SQLite は環境にかかわらず settings.sqlite_path（本番用）を使用する設計。
    - 停止フラグ検出で安全にループを抜けて接続をクローズ。
  - 環境設定管理: config.py
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を起点）。
    - 読み込み順序: OS 環境 > .env.local > .env（既存 OS 環境を保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - 各種設定プロパティを定義（DB パス、API トークン、ログレベル、環境判定フラグ、paper_trading 用設定等）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
  - 設定ウィザード CLI: config_setup.py
    - 対話式に .env を作成・更新するウィザード。
    - シークレット項目はマスク表示、既存値の読み込み、保存前の確認などを提供。
  - 設定検証 CLI: validate_config.py
    - 必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス、config/*.yaml の存在と YAML パース（PyYAML が存在する場合）を検証。
    - --strict オプションで警告を失敗扱いにできる。
    - 本番環境向けのガードチェック（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の危険設定に対する警告）を実装。
  - ロギングユーティリティ: utils/logging_setup.py
    - stdout への StreamHandler と 日次ローテーションの TimedRotatingFileHandler をルートロガーに統一的に設定。
    - ログディレクトリ自動作成、ハンドラの重複防止（既存ハンドラをクリア）。
    - 環境変数 LOG_DIR / LOG_LEVEL からの設定解決。
  - プロセス優先度・CPU 固定ユーティリティ: utils/process_priority.py
    - Windows と POSIX (Linux/Mac/FreeBSD) を吸収してプロセス優先度 (high/normal/low) を設定。
    - CPU affinity を最初の N コアにピン留めする set_cpu_affinity を提供。
    - psutil の権限例外をハンドリングして安全にフォールバック。
  - ポートフォリオ構築モジュール: portfolio/
    - portfolio_builder.py
      - シグナルの候補選定 select_candidates、等配分 calc_equal_weights、スコア加重 calc_score_weights（全スコア0 の場合は等配分へフォールバック）。
    - risk_adjustment.py
      - セクター集中制限 apply_sector_cap（売却予定銘柄を除外して既存エクスポージャーを計算）。
      - レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知レジームはフォールバックと警告）。
    - position_sizing.py
      - position サイズ計算 calc_position_sizes（risk_based / equal / score をサポート）。
      - lot_size（単元株）に基づく丸め、1 銘柄上限・aggregate cap、cost_buffer を考慮したスケーリングと remainder による分配ロジックを実装。
  - 研究用ファクター計算スケルトン: research/factor_research.py
    - Momentum/Value/Volatility/Liquidity に関する設計方針と定数を実装。DuckDB 接続を受けて prices_daily/raw_financials を用いた計算を行う想定（calc_momentum の実装が途中で含まれる）。
  - Paper Trading 検証レポート: tools/paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から指標を集計しレポート出力。
    - 指標: 稼働率 (uptime)、注文成功率 (fill_rate)、送信率 (send_rate)、リスク却下数、API レイテンシ（avg/max/P95）。
    - 基準値（閾値）を定義し PASS/FAIL 判定を出力。
  - パッケージ初期化: __init__.py にバージョン __version__ = "0.1.0" を設定。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 機密値は .env に保存する前提を明記し、config_setup でマスク表示するなど誤コミットへの注意喚起を実装。
- .env は Git にコミットしない旨のヘッダを生成ファイルに含める。

Known Issues / Notes
- research/factor_research.calc_momentum の実装がファイル末尾で途中になっている（未完）。このモジュールは設計方針・定数は定義済みだが、完全な計算ロジックは要完成。
- 一部の TODO や拡張コメントが残っている（例: position_sizing の銘柄別 lot_size 拡張、risk_adjustment の price フォールバックなど）。
- run_monitoring は監視用 DB と本番 DB を統一して使用する設計になっているため、運用上の分離を意図する場合は設定に注意すること。
- ログディレクトリ作成やプロセス優先度設定は権限に依存し、失敗時は警告を出して安全にフォールバックする。

参考
- CLI 実行例:
  - 環境ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 実行エンジン起動: python -m kabusys.run_execution
  - 監視起動: python -m kabusys.run_monitoring

--- 
リリースに関するフィードバックやバグ報告は issue を立ててください。