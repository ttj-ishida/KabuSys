CHANGELOG
=========

すべての重要な変更履歴を記録します。本ドキュメントは "Keep a Changelog" のフォーマットに準拠します。

フォーマット:
  - Unreleased: 次のリリースに含める予定の変更
  - 各リリースは日付付きで記載

※この CHANGELOG はコードベースの内容から挙動・設計を推測して作成しています。

Unreleased
----------
- なし

[0.1.0] - 2026-04-18
--------------------
初回リリース — KabuSys の基本機能群を実装。

Added
- 全体
  - パッケージ初期バージョンを 0.1.0 として公開。
  - コマンドライン / モジュールとして利用可能な複数のエントリポイントを実装:
    - 設定ウィザード: python -m kabusys.config_setup
    - 設定検証: python -m kabusys.validate_config
    - Monitoring 起動: src/kabusys/run_monitoring.py（main 関数）
    - Execution 起動: src/kabusys/run_execution.py（main 関数）
    - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
- 設定管理 (kabusys.config)
  - .env 自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - .env と .env.local の読み込み順を実装（OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
  - .env パースの強化: export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント処理などに対応。
  - Settings クラスを提供し、主要な設定（J-Quants, kabuAPI, DB パス, ログ, 監視閾値等）をプロパティで取得可能に。
  - PAPER_FILL_MODE（paper_trading 用の挙動）や PAPER_TRADING_SQLITE_PATH をサポート。KABUSYS_ENV による環境判定（development / paper_trading / live）を実装。
- 設定ウィザード (kabusys.config_setup)
  - 対話式ウィザードで .env を新規作成・更新する機能を実装。シークレット項目はマスク表示。既存 .env を読み込んで Enter で再利用可能。
  - .env 書き込みテンプレートを用意（Git にコミットしない旨のヘッダ含む）。
- 設定検証 (kabusys.validate_config)
  - .env および config/*.yaml の存在・整合性チェック用 CLI を実装。
  - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベルの妥当性、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML があれば実行）などを行う。
  - --strict オプションで警告を失敗扱いにできる。
- ランタイムスクリプト
  - run_monitoring.py
    - SystemMonitor を用いた監視ポーリングループを実装。MONITOR_POLL_INTERVAL 環境変数（デフォルト 60 秒）で間隔指定可能。不正な値はデフォルトにフォールバック。
    - 停止はプロジェクト data/stop_requested.flag の存在を検知して行う（停止フラグ機構をサポート）。
    - 監視は KABUSYS_ENV にかかわらず production（settings.sqlite_path）を使用する設計。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py
    - ExecutionEngine 起動スクリプト。paper_trading 環境の場合は MockBrokerClient を利用し、専用 DB（data/paper_trading.db、PAPER_TRADING_SQLITE_PATH で上書き可）に記録して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler 等の組み立て、スレッドで ExecutionEngine.run_session を実行する制御ループを実装。
    - 起動前に data/stop_requested.flag を確認し、既に立っている場合は起動をスキップ。実行中に停止フラグを検知すると engine.stop() を呼び出して優雅に停止。
    - execution.pid を PID ファイルとして扱う（設定で pid_file を指定可能）。
- ロギングユーティリティ (kabusys.utils.logging_setup)
  - 統一的なログ設定関数 setup_logging を提供。
  - stdout 出力用 StreamHandler と日次ローテート（TimedRotatingFileHandler）を組み合わせ、ログディレクトリ（デフォルト logs/）を自動作成。ローテーションは 30 日保持。
  - ログレベル解決順（引数 > 環境変数 LOG_LEVEL > デフォルト）とログディレクトリ解決順（引数 > LOG_DIR > デフォルト）を実装。
  - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
- プロセス優先度ユーティリティ (kabusys.utils.process_priority)
  - set_process_priority(level) を実装し、Windows / POSIX（Linux, Darwin, FreeBSD）に対して適切に優先度（Windows の priority class / POSIX の nice 値）を設定する。
  - set_cpu_affinity(cpu_count) でプロセスを先頭 N コアに固定する機能を提供（失敗時は警告を出してスキップ）。
  - 許可がない場合や未対応 OS では安全にフォールバックして警告を出す。
- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder: 候補選定 select_candidates（スコア降順、タイブレークは signal_rank）、等金額 calc_equal_weights、スコア加重 calc_score_weights（全スコア 0 の場合は等金額にフォールバック）。
  - risk_adjustment: apply_sector_cap（既存保有を考慮したセクター上限フィルタ）、calc_regime_multiplier（bull|neutral|bear による投下資金乗数、未知レジームは 1.0 にフォールバック）。
  - position_sizing: calc_position_sizes（allocation_method に応じた株数計算）
    - risk_based / equal / score のサポート
    - 単元（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）実装
    - cost_buffer を使った保守的コスト見積り、端数処理で残余キャッシュを用いた追加配分を実装
- リサーチ・ファクター (kabusys.research.factor_research)
  - モメンタム等のファクター計算基盤を実装（DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計）。（ファイル冒頭実装あり、続きは別実装）
- Paper Trading 検証レポート (kabusys.tools.paper_verification_report)
  - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から各種指標を集計してレポート出力するスクリプトを実装。
  - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）、リスク却下数 等。
  - Pass/Fail 基準値（稼働率 99% など）と期間指定 --from / --to オプションをサポート。
  - DB が存在しない場合やテーブル欠如時の保護コードを備える（OperationalError を捕捉して N/A 等で表示）。
- パッケージ初期化
  - kabusys/__init__.py にバージョンとエクスポート一覧を定義。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / 動作上の重要ポイント（実装から推測）
- .env の自動ロードはプロジェクトルート検出に依存するため、配布後やテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って明示的に無効化可能。
- run_monitoring は監視データベース（settings.sqlite_path）を環境に関わらず使用する設計（監視は本番データの利用を想定）。
- run_execution は paper_trading 時に専用 DB を使用し、本番 DB とデータ分離するよう配慮。
- プロセス優先度設定や CPU affinity 設定は権限不足や未対応プラットフォームで失敗する可能性があり、その場合は警告を出して処理を継続するフォールバック実装。
- ログは stdout に出力する設計（cron/Task Scheduler でのリダイレクトを想定）かつファイル出力も併用。ログディレクトリ作成に失敗するとファイル出力は無効化される。

今後の想定タスク（提案）
- research.factor_research の未完部分の実装完了（ファクター計算ロジックの完全化）。
- テストカバレッジの拡充（ユニットテスト・統合テスト）。
- 実運用向けの監視アラート（LINE 通知等）の追加実装とドキュメント化。
- 銘柄別単元（lot_size）や取引手数料モデルの外部化（マスタ参照）による position_sizing の強化。

--- 
以上。追加で特定ファイルの変更点や過去のコミット履歴に基づくより詳細な CHANGELOG を作成したい場合は、変更履歴（Git log）やリリースごとの差分情報を提示してください。