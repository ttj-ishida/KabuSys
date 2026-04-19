CHANGELOG
=========

すべてのリリースは Keep a Changelog の形式に準拠します。  
このファイルでは、コードベースから推測される主要な追加・変更点を記載しています。

フォーマット:
- 変更のカテゴリ: Added / Changed / Fixed / Deprecated / Removed / Security
- 各項目は対象モジュールや CLI、環境変数、挙動の説明を含みます。

[0.1.0] - 2026-04-19
--------------------

Added
- 初期リリースとして以下の主要機能を実装。
  - 実行（Execution）コンポーネント
    - python -m kabusys.run_execution 相当の起動スクリプトを提供。
    - ExecutionEngine の起動ロジックを含み、バックグラウンドスレッドでセッションを実行。
    - BrokerClientFactory を介したブローカークライアントの抽象化（KABUSYS_ENV により実際のブローカー or MockBrokerClient を切替可能）。
    - Paper Trading モード（KABUSYS_ENV=paper_trading）では専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
    - 実行時の停止フラグ（data/stop_requested.flag）検出、PID ファイル生成（data/execution.pid など）を想定した制御。
    - RiskManager（初期設定値を含む RiskConfig）と Reconciler、OrderManager、OrderRepository の組み立てを行う。

  - 監視（Monitoring）コンポーネント
    - python -m kabusys.run_monitoring 相当の監視ループ起動スクリプトを提供。
    - SystemMonitor を用いた単一チェック（monitor.check_once()）のポーリングループを実装。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を参照して監視データを書き込む設計（意図的に分離している点に注意）。

  - 設定管理
    - kabusys.config: 環境変数・.env 自動読み込み機能を提供。
      - プロジェクトルートの検出は .git または pyproject.toml を基準に行うため、CWD に依存しない。
      - .env/.env.local を優先度に応じて読み込み（OS 環境変数は保護）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
      - Settings クラスでアクセス可能なプロパティ群を定義（J-Quants / kabu API / DB パス / 監視閾値 / 環境判定など）。
      - PAPER_FILL_MODE のバリデーション、PAPER_TRADING_SQLITE_PATH（paper_sqlite_path）等の明確化。

    - config_setup: 対話式の .env 作成・更新ウィザードを提供（python -m kabusys.config_setup）。
      - 既存 .env 読み込み、シークレットのマスク表示、保存前の確認、.env の書き出しロジックを実装。

    - validate_config: 起動前検証 CLI（python -m kabusys.validate_config）を提供。
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パースチェックを実施。
      - --strict オプションで警告を FAIL 扱いにできる。

  - ロギング & プロセス管理ユーティリティ
    - utils.logging_setup.setup_logging:
      - stdout (StreamHandler) と 日次ローテート（TimedRotatingFileHandler）をルートロガーに設定。
      - ログディレクトリ（デフォルト logs/）は LOG_DIR 環境変数または引数で設定可能。ディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
      - LOG_LEVEL 環境変数または引数でログレベルを解決。
    - utils.process_priority:
      - Windows/Linux/macOS を吸収してプロセス優先度を設定するユーティリティを提供（set_process_priority("high"/"normal"/"low")）。
      - CPU affinity 設定関数 set_cpu_affinity を提供（一部 OS で限定的）。
      - 実行スクリプト冒頭で優先度を "high" にセットする設計。

  - ポートフォリオ構築（Portfolio）
    - portfolio.portfolio_builder:
      - select_candidates: BUY シグナルをスコア降順にソートして上位 N を返す（同点時に signal_rank でタイブレーク）。
      - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分。全銘柄スコアが 0 の場合は等配分にフォールバックして警告。
    - portfolio.risk_adjustment:
      - apply_sector_cap: セクター集中制限を実装。既存保有と当日売却予定を考慮して候補をフィルタリング。unknown セクターは制限適用外。
      - calc_regime_multiplier: market_regime に応じた投下資金乗数（bull/neutral/bear をマッピング、未知値は警告とフォールバック）。
    - portfolio.position_sizing:
      - calc_position_sizes: allocation_method ("risk_based","equal","score") に応じて発注株数を決定。lot_size（単元）で丸め、per-stock 上限・aggregate cap（利用可能現金）に対するスケーリングを実装。コストバッファや端数分配アルゴリズムも含む。

  - データ解析 / 研究
    - research.factor_research: DuckDB 接続を受け取り prices_daily / raw_financials に基づいたファクター（Momentum / Value / Volatility / Liquidity）計算の骨組みを実装（モジュールの一部は実装途中である可能性あり）。

  - ツール
    - tools.paper_verification_report:
      - Paper Trading 用検証レポート生成 CLI（python -m kabusys.tools.paper_verification_report）。
      - 指定期間（--from / --to）または DB（--db）を指定して、稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計しテキストレポートを出力。
      - Pass/Fail 基準を定義（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 レイテンシ <= 200 ms 等）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 機密情報（API トークンやパスワード）は .env に格納する前提。config_setup は .env を直接生成するため .gitignore 等でコミットしない運用を強調する注記を .env ヘッダに含む。

重要な運用メモ（実装から推測）
- 監視は MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を制御可能（整数秒）。1 未満や不正な値はデフォルト 60 秒にフォールバックして警告を出力するので注意してください。
- run_monitoring は監視データ保存に settings.sqlite_path （デフォルト data/monitoring.db）を使用します。環境にかかわらず本番用 sqlite_path を参照するため、意図的に分離された運用が必要。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。paper_trading モードは本番 DB と分離して試験できます。
- 自動 .env ロードは便利だが、CI/テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化可能。
- ログはデフォルトで logs/<app_name>.log に日次ローテートで出力されますが、ディレクトリ作成に失敗した場合はコンソール出力のみになります。ログ設定は setup_logging の引数でオーバーライド可能。

既知の注意点 / 今後の改善候補（コードから推測）
- portfolio.risk_adjustment.apply_sector_cap: price_map に 0.0 が入ると露出が過少見積りされる旨の TODO コメントあり。前日終値等のフォールバック価格導入が望ましい。
- research.factor_research モジュールは一部分で実装途上のように見える（ファイル末尾が途中で切れている）。完全なファクター計算は今後の拡張対象。
- process_priority の優先度設定は OS に依存し、権限不足で失敗する場合は警告を出してスキップする設計。運用環境での動作確認を推奨。

今後のリリースで期待する改善
- Strategy / Execution の結合テスト、および MockBroker の具体的挙動ドキュメント化。
- research モジュールの完成と DuckDB を用いたバッチ処理パイプラインの提供。
- 監視・アラート（LINE 通知等）との連携強化（validate_config は LINE 設定の存在チェックを行うが、実際の通知ロジックは別モジュールで補完の余地あり）。

---

本 CHANGELOG は、提供されたコードベースから挙動や設計意図を推測して作成しています。実際の変更履歴やリリースノートはリポジトリのコミット履歴やリリースタグを参照してください。