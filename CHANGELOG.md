CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載します。
セマンティック バージョニングを想定しています。

[Unreleased]
-------------

- （なし）

0.1.0 - 2026-04-19
------------------

Added
- 基本機能の初期実装を追加（初回リリース）。
- コマンドライン起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - プロセス優先度を最優先（"high"）に設定して起動。
    - 停止制御: プロジェクト data/stop_requested.flag を検知して優雅に停止。
    - ペーパートレード環境 (KABUSYS_ENV=paper_trading) 向けに MockBrokerClient を使用し、専用 SQLite（data/paper_trading.db; 環境変数で上書き可）に完全分離して記録。
    - 実行はバックグラウンドスレッドで行い、メインスレッドで停止フラグを監視して安全に停止。
    - デフォルトの RiskManager 設定（max_position_pct 等）を Engine 起動時に注入。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
    - 監視は本番用 sqlite_path を利用（KABUSYS_ENV に依存しない）。
    - 停止フラグ検知でループ終了、KeyboardInterrupt による終了もハンドル。
- 設定管理
  - config.py
    - .env 自動ロード機能を追加（プロジェクトルートを .git または pyproject.toml で特定）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサを強化: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
    - Settings クラスを追加し、環境変数をプロパティで提供（バリデーション・デフォルト値を含む）。PAPER_FILL_MODE や KABUSYS_ENV、LOG_LEVEL 等の妥当性チェックを実装。
- 設定ユーティリティ / CLI
  - config_setup.py
    - 対話式ウィザードで .env を作成 / 更新するツールを追加。既存 .env の読み込み、シークレット値のマスク表示、デフォルト値・選択肢の提示をサポート。
  - validate_config.py
    - 起動前の設定検証ツールを追加。必須環境変数の確認、KABUSYS_ENV の妥当性、DB パス親ディレクトリの確認、config/*.yaml の存在確認（PyYAML がない場合はパース検証をスキップして警告）。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定関数 setup_logging を追加。コンソール（stdout）と日次ローテートファイル（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR の自動作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続し、適切な警告を出力。
    - ログレベルは引数 > 環境変数 > デフォルト の優先度で決定。
  - utils/process_priority.py
    - set_process_priority、set_cpu_affinity を追加。Windows / POSIX (Linux, macOS 等) の差分を吸収し、権限不足や未対応環境では警告を出してスキップする安全実装。
- ポートフォリオ構築（純粋関数群、DB 参照なし）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重 calc_score_weights を実装。スコア全てが 0.0 の場合は等配分にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を実装（"unknown" セクターは制限対象外）。
    - 市場レジームに基づく資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピング、未知レジームはフォールバックして 1.0）。
  - portfolio/position_sizing.py
    - ポジションサイズ計算 calc_position_sizes を実装。risk_based / equal / score の allocation_method をサポート。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash 超過時の比率スケーリング）、cost_buffer による保守的見積り、残余キャッシュによる再配分ロジックを実装。
- Research / ツール
  - research/factor_research.py（基盤実装）
    - フォクター計算モジュールを追加（モメンタム、MA200乖離、ATR、出来高系等を想定）。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
    - calc_momentum の骨子を追加（営業日ベースのホライズン定義 等）。（注: ファイル末尾に未完の実装片あり）
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ等を算出し、基準値（閾値）に基づき PASS/FAIL を判定。
    - --from / --to / --db オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数で DB パス指定可。

Changed
- 初回リリースのため「新規追加」が中心。既存実装からの変更はなし。

Fixed
- 設定検証ツールで PyYAML が未インストールの場合にパースチェックをスキップして警告を出すようにして、起動環境に依存しない堅牢性を確保。

Security
- シークレット環境変数の取り扱いに注意:
  - config_setup の対話表示ではシークレット値はマスク表示。
  - .env は絶対に Git にコミットしない旨を README ヘッダに明記（config_setup に注記）。

Notes / Known issues
- research/factor_research.py の calc_momentum 実装が途中で終わっている箇所が見られます。フォクター計算の完全実装は今後の作業予定です。
- process_priority, set_cpu_affinity は権限やプラットフォームによっては動作しない可能性があり、その場合は警告が出力され処理をスキップする設計です。
- monitoring は意図的に環境変数にかかわらず本番 sqlite_path を参照する実装です（運用上の意図による）。テスト/開発時は sqlite_path を切り替えてください。

参考（主なコマンド）
- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視ループ起動: python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

以上。