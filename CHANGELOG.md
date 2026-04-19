# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

- リリース日付の仕様: YYYY-MM-DD
- 表記: Added / Changed / Fixed / Removed / Security を基本カテゴリとして使用

## [Unreleased]
- 今後の変更点をここに記載します。

## [0.1.0] - 2026-04-19
初回リリース。日本株自動売買システム KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築・リスク調整ロジック、設定管理ツール、および検証ツール群を含みます。

### Added
- 全般
  - パッケージの最小バージョンとして `__version__ = "0.1.0"` を導入（src/kabusys/__init__.py）。
  - DuckDB と SQLite を併用するデータ基盤を統合（各種モジュールで使用）。

- 起動スクリプト / 長期実行
  - 実行エンジン起動用スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は Paper Trading 用 DB（data/paper_trading.db）を使用し、MockBrokerClient を利用することで本番 DB と完全分離。
    - 起動時にプロセス優先度を "high" に設定する挙動を導入。
    - 停止制御に data/stop_requested.flag と execution.pid を採用し、フラグ検知で安全に停止できる設計。
    - ExecutionEngine を別スレッドで実行し、停止フラグで engine.stop() を呼び出す監視ループを実装。
  - 監視（SystemMonitor）起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を設定可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視用 DB 初期化（init_monitoring_db）と duckdb 接続を行い SystemMonitor.check_once() をポーリングで呼び出すループを実装。
    - 停止フラグ（data/stop_requested.flag）を検知して監視ループを終了。

- 設定管理
  - Settings クラスを実装（src/kabusys/config.py）。
    - .env の自動読み込み機構（プロジェクトルートの検出: .git または pyproject.toml を基準）と厳密なパース処理を導入。
    - 環境変数の検証（必須項目の _require、各種プロパティの型チェックや有効値チェック）を提供。
    - Paper Trading 用の PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等のオプションを追加。
    - is_live / is_paper / is_dev といった環境チェックプロパティを提供。
  - 対話式 .env 作成ウィザードを追加（src/kabusys/config_setup.py）。
    - 初期 .env の作成・更新を対話式で行う。既存 .env の読み込みとマスク表示に対応。
    - 保存前の確認プロンプトを実装。

- 設定検証ツール
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスや config/*.yaml の存在確認を実行。
    - PyYAML が存在する場合は YAML のパース検証を行う（存在しない場合は警告）。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - 統一ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップして stdout のみで継続。
    - LOG_LEVEL / LOG_DIR の環境変数や引数からの優先解決。
  - プロセス優先度と CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX (Linux/macOS/FreeBSD) を透過的に扱う実装。
    - set_process_priority(level) で high/normal/low を設定。アクセス権や未対応 OS の場合は警告を出力してスキップ。
    - set_cpu_affinity(cpu_count) による最初の N コアへの固定機能を提供（未指定なら無効）。

- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順・同点時は signal_rank をタイブレークとして上位 N を選定。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重（全スコア 0 の場合は等配分にフォールバックして WARNING）。
  - セクターキャップ・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクターエクスポージャーに基づき、新規候補を除外するロジック（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market レジームに応じて資金投下倍率を返す（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバックして警告。
  - ポジションサイズ決定（src/kabusys/portfolio/position_sizing.py）
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - risk_based: リスク許容率、ストップロス、単元株（lot_size）を考慮して株数を算出。
    - aggregate cap として available_cash を超える場合にスケールダウンしてロット単位で再配分するアルゴリズムを実装。cost_buffer（手数料・スリッページ見積）を考慮。
    - 価格データ欠落時のスキップとログ出力。
  - ポートフォリオ API 統合（src/kabusys/portfolio/__init__.py）で各関数を公開。

- 研究 / ファクター (初期実装の一部)
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）を追加（モメンタム等の計算方針と定数を導入）。（注: ファイル途中までの実装が含まれます）

- ツール
  - Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成功率、送信率、API レイテンシ（平均/最大/P95）などを集計して PASS/FAIL 判定を行う。
    - デフォルト DB は data/paper_trading.db。コマンドライン引数で期間（--from/--to）と DB パス（--db）を指定可能。
    - P95 の実装、指標の閾値（稼働率 99%、成功率 90% 等）を明確化。

### Changed
- なし（このリリースは新規機能導入主体の初回リリース）。

### Fixed
- なし（このリリースは初回の安定した機能群追加）。

### Notes / 実装上の注意
- .env 自動読み込みはプロジェクトルートが特定できない場合はスキップされ、テストなどで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用可能。
- Settings による環境値検証は起動時に ValueError を送出するため、環境変数の準備（.env の作成と validate_config によるチェック）を推奨。
- ログは stdout とファイルの両方に出力されるが、ログディレクトリの作成に失敗した環境ではファイル出力が無効化される点に注意。
- run_monitoring は「監視用 DB に対して本番 sqlite_path を必ず使用する」設計。run_execution は環境に応じて paper/trading DB を切り替えるため、本番とペーパートレードが分離される。
- process_priority や cpu_affinity の設定は環境（権限・OS）によってエラーとなる場合があり、その際は警告を出して処理を継続する安全設計。

---

将来的なリリースでは、ファクター計算の完成、ExecutionEngine / SystemMonitor の詳細実装の追加テスト、strategy 実装、さらなる CLI / CI/デプロイ向け改善を予定しています。