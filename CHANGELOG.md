CHANGELOG
=========

すべての注目すべき変更はここに記録します。  
フォーマットは「Keep a Changelog」準拠です。

[0.1.0] - 2026-04-19
--------------------

Added
- 初期リリース: KabuSys 自動売買フレームワークのコアモジュール群を追加。
  - 起動スクリプト
    - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。起動時にプロセス優先度を "high" に設定し、バックグラウンドスレッドでエンジンを実行。停止フラグ (data/stop_requested.flag) と実行用 PID ファイル (data/execution.pid) に対応。KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と分離。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番 sqlite_path を使用する仕様。停止フラグ検出時の正常終了処理を実装。
  - 設定管理 / ユーティリティ
    - config.py: 環境変数 / .env ロード、Settings クラスを実装。プロジェクトルート検出（.git または pyproject.toml）に基づく自動 .env 読み込みをサポート（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。PAPER_FILL_MODE 等の検証ロジック、paper_trading 用 DB パス、PID / kill flag 等の設定プロパティを提供。
    - config_setup.py: 対話式 .env ウィザードを追加。既存 .env 読み込み・編集、.env ファイルのテンプレート生成をサポート（.env を Git にコミットしない旨の注意を含む）。
    - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML が導入されている場合の）パース検証、live 環境向けの追加ガードを実装。--strict オプションで警告を FAIL 扱いにできる。
    - utils/logging_setup.py: 共通ロギング初期化ユーティリティを追加。stdout 出力（StreamHandler）と日次ローテーションファイル出力（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ自動作成、既存ハンドラの二重設定防止、ログレベル解決順の実装。
    - utils/process_priority.py: Windows / POSIX の差異を吸収したプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を実装。権限不足や未サポート OS を考慮したフォールバック処理あり。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py: 候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights を実装。スコア全てが 0 の場合のフォールバックロジックあり。
    - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap と市場レジームに応じた乗数 calc_regime_multiplier を実装。未知レジームに対するフォールバックとログ出力あり。
    - portfolio/position_sizing.py: position sizing ロジック calc_position_sizes を実装。allocation_method（"risk_based", "equal", "score"）対応、単元株丸め（lot_size）、aggregate cap（利用可能現金でスケールダウン）、手数料・スリッページを考慮した cost_buffer、各種リスクパラメータをサポート。
  - research/factor_research.py: DuckDB を用いたファクター計算モジュール（モメンタム等）の骨格を追加（prices_daily / raw_financials を参照する設計）。
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。システム稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均 / 最大 / P95）などを集計して PASS/FAIL 判定（基準値: 稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を行う。日付フィルタ、DB パス指定オプションをサポート。

Changed
- 既存コード設計に関する仕様（初期リリースとしての設計決定）
  - DB ハンドリング: run_monitoring/run_execution 共に SQLite（監視・履歴用）と DuckDB（分析用）を併用する構成に統一。
  - Paper Trading の分離: paper_trading 環境では settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番監視 DB と完全分離する仕組みを導入。
  - ロギング: コンソールは stdout を使用（cron 等で stdout/stderr をまとめて扱いやすくするため）。ログファイルは日次ローテーション・30日保持を既定とした。

Fixed
- エラー耐性とシャットダウン処理の改善
  - run_monitoring のポーリングループ内で monitor.check_once() が例外を投げてもループ継続するように例外キャッチを実装（ログ出力）。停止フラグや KeyboardInterrupt による安全な終了を確保。
  - run_execution で停止フラグ検知時に ExecutionEngine.stop() を呼び出してスレッド停止を試みる処理を実装。起動直前に停止フラグが立っている場合は起動を回避。

Documentation / Notes
- Settings の .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に探す実装。テストなどで自動ロードを無効化するため KABUSYS_DISABLE_AUTO_ENV_LOAD が用意されている。
- config_setup により作成される .env は .env を絶対に Git にコミットしないよう明記している。
- validate_config は PyYAML が未導入でも動作し、YAML 検証をスキップして警告を出すように設計。
- portfolio・position sizing・risk adjustment のアルゴリズムは PortfolioConstruction.md / StrategyModel.md に基づく想定（コメントに基づく設計意図を反映）。

未実装 / 既知の制限
- factor_research.py はファクター計算の方針と定数を定義しているが、いくつかの実装（SQL クエリ等）は続きが必要（ファイル末尾で途中終了）。
- price 欠損時のフォールバック（前日終値や取得原価を使う等）は一部 TODO として残されている（apply_sector_cap の注釈、position_sizing のコメント参照）。
- 一部プラットフォームや権限不足時（プロセス優先度・CPU affinity 設定、ログディレクトリ作成時）のフォールバックは警告を出すが、より詳細なオペレーション手順はドキュメント化が必要。

Contributing
- バグ修正、機能追加、ドキュメント改善は welcome。まず validate_config.py と config_setup.py を使って設定の整合性を確認してください。

------------
（以上）