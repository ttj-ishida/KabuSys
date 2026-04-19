CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  
初版リリース情報をプロジェクト内のコードから推測して作成しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-19
--------------------

Added
- プロジェクト初期リリースとして基本機能を追加。
  - 起動スクリプト
    - run_execution.py: ExecutionEngine の起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（data/paper_trading.db）を使用し、MockBrokerClient を利用して本番 DB と完全分離する挙動を実装。
      - 実行中はプロセス優先度を "high" に設定し、停止フラグ（data/stop_requested.flag）により安全に停止可能。
      - 実行 PID を data/execution.pid に記録する仕組み（pid_file 指定）。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログ警告のうえデフォルトにフォールバック。
      - 監視は環境にかかわらず本番 sqlite_path を使用して監視データを記録。
      - 停止フラグ検知・KeyboardInterrupt を適切にハンドリングして接続を閉じる。
  - 設定・環境管理
    - config.py: Settings クラスを追加。環境変数（.env/.env.local を自動ロード可能）から各種設定を取得。
      - 自動ロードの優先順位: OS 環境変数 > .env.local > .env（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
      - 必須値未設定時はエラーを投げる _require 実装。
      - 各種デフォルトパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH 等）や紙トレード用設定（PAPER_FILL_MODE）などを提供。
    - config_setup.py: 対話式 .env 作成ウィザードを追加（.env の生成 / 更新を支援）。
    - validate_config.py: 起動前設定検証 CLI を追加。
      - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性判定、DB パスや config/*.yaml の存在・パース検証（PyYAML が無い場合はスキップ）、本番向けガードチェック等。
      - --strict オプションで警告を FAIL 扱いにできる。
  - ポートフォリオ構築ライブラリ（純粋関数群）
    - portfolio/portfolio_builder.py
      - select_candidates: BUY シグナルのスコア順選定
      - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（全スコアが 0 の場合はフォールバック）
    - portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中上限による候補除外
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）
    - portfolio/position_sizing.py
      - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に応じた発注株数算出、単元株丸め、aggregate cap によるスケーリング、cost_buffer 考慮などを実装
  - Utils
    - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加
      - stdout (StreamHandler) と 日次ローテーションファイル (TimedRotatingFileHandler) をルートロガーに設定。
      - ログディレクトリ自動作成、LOG_LEVEL/LOG_DIR からの解決、ファイルハンドラ作成失敗時のフォールバック（コンソールのみ）をサポート。
    - utils/process_priority.py: クロスプラットフォームなプロセス優先度 / CPU affinity 設定ユーティリティを追加
      - Windows / POSIX の差分吸収、失敗時は警告ログでスキップ。
  - 解析・ツール
    - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加
      - システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計し PASS/FAIL を判定する閾値を定義。
      - --from / --to / --db オプションで集計期間と DB を指定可能。
    - research/factor_research.py: Factor 計算モジュール（Momentum, Value, Volatility, Liquidity）骨子を追加（DuckDB 経由で prices_daily / raw_financials を参照する設計）。
      - 設計方針と定数、モメンタムファクタ計算関数の枠組みを含む（実装は継続中／一部ファイル末尾が未完）。
  - パッケージ初期化
    - __init__.py にバージョン情報 __version__ = "0.1.0" を追加。

Changed
- 環境変数ロードの挙動を明文化
  - プロジェクトルート検出は .git または pyproject.toml を基準に行い、見つからない場合は自動ロードをスキップする挙動を実装。
  - .env のパースはクォート・エスケープ・インラインコメントに対応する細かなルールを実装。
- run_monitoring / run_execution 起動時に最初にプロセス優先度を設定するよう統一。
- logging_setup: ログ出力先を stdout に統一（cron などでリダイレクトしやすくするため stderr ではなく stdout を使用）。

Fixed
- なし（初回リリース想定のため既知の不具合は記載なし）。ただし以下の安全策を実装済み:
  - MONITOR_POLL_INTERVAL の不正値は警告ログでデフォルトにフォールバック。
  - DB/ファイルハンドラ作成失敗時にアプリをクラッシュさせず、コンソール出力のみで継続。
  - process_priority / cpu_affinity で権限不足や未対応 OS の場合は警告でスキップ。

Notes / Known issues
- research/factor_research.py はモメンタム計算の実装枠組みまで記載があるものの、ファイル末尾が途中で切れている（実装継続が必要）。
- position_sizing.calc_position_sizes 内の price が欠損（0.0） の場合、将来の拡張でフォールバック価格を検討する旨の TODO コメントあり。
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup での注意書きあり）。

References
- 各種 CLI:
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
  - python -m kabusys.tools.paper_verification_report

この CHANGELOG はソースコードから推測して作成したため、実際のリリースノートに合わせて適宜編集してください。