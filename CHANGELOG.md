# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このファイルは「Keep a Changelog」形式に従います。

全般:
- 本リリースはパッケージの初期公開リリースです。内部アーキテクチャはモジュール単位で整理され、CLI ツール、監視・実行用ランナー、ポートフォリオ構築ロジック、リサーチ用ファクター計算、ユーティリティ群などを含みます。

## [0.1.0] - 2026-04-17

### Added
- 基本機能・モジュール追加
  - kabusys パッケージの初期モジュール群を追加。
  - __version__ を "0.1.0" に設定。

- 実行/監視ランナー
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを提供。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（data/paper_trading.db または PAPER_TRADING_SQLITE_PATH）を使用し、MockBrokerClient を用いた分離されたペーパートレード動作を想定。
    - プロセス優先度を起動時に High に設定するユーティリティ呼び出しを組み込み。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル管理 (_EXECUTION_PID) による起動／停止制御を実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループを実行するエントリポイントを提供。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計。

- 設定管理 / CLI
  - config.py
    - 環境変数および .env ファイルの自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - 複数の設定プロパティを提供（DB パス、pid/kill フラグパス、Paper Trading 設定、閾値、環境名検証など）。
    - PAPER_FILL_MODE のバリデーションや KABUSYS_ENV / LOG_LEVEL の検証を実装。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - シークレット入力のマスク、選択肢提示、既存 .env 読み込みと確認ステップ、.env ファイルの出力フォーマットを実装。
  - validate_config.py
    - .env と config/*.yaml の起動前検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、DB パス親ディレクトリの存在確認、PyYAML があれば YAML ファイルのパース検証、KABUSYS_ENV=live のガードチェック等を実装。
    - --strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates, calc_equal_weights, calc_score_weights を実装（シグナル選別と重み計算）。
  - portfolio.position_sizing
    - calc_position_sizes を実装（risk_based / equal / score ベースの株数計算、単元株丸め、aggregate cap スケーリング、cost_buffer を考慮した配分）。
  - portfolio.risk_adjustment
    - apply_sector_cap（セクター集中制限）と calc_regime_multiplier（市場レジームに応じた投下資金乗数）を実装。

- リサーチ / ファクター計算
  - research.factor_research
    - DuckDB 接続を使ったファクター計算関数を実装（モメンタム、ボラティリティ等）。prices_daily テーブルを参照して各種指標（mom_1m/3m/6m、MA200乖離、ATR20、平均売買代金、出来高比等）を算出。

- ツール
  - tools.paper_verification_report
    - ペーパートレード履歴（SQLite）から検証レポートを生成する CLI を実装。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標算出と PASS/FAIL 判定の出力（閾値はソース内で定義）。
    - --from / --to / --db オプションによる期間・DB 指定に対応。

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level) により Windows / POSIX を吸収してプロセス優先度設定を実行（high/normal/low）。
    - set_cpu_affinity(cpu_count) によりプロセスを先頭 N コアに固定する機能を追加。
    - psutil の AccessDenied 等の例外を捕捉してフォールバックする設計。

- DB 初期化
  - monitoring.monitoring_db:init_monitoring_db を参照してランナー起動時に監視テーブルの存在を担保（冪等）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / 使用上の注意
- .env 自動読み込みはプロジェクトルートの検出に依存するため、配布後や別配置で利用する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用するか .env を明示的に読み込んでください。
- run_monitoring は監視 DB として settings.sqlite_path を常に使用します（Paper Trading 環境でも監視は本番 sqlite に記録される点に注意）。
- run_execution は Paper Trading の場合は専用の paper_sqlite_path を使用して本番 DB と完全分離するよう設計されています。
- process priority / CPU affinity の設定は OS 権限に依存します。権限不足などで設定に失敗した場合は警告ログを出力して続行します。
- calc_position_sizes 等のアルゴリズムは単元株（lot）や手数料スリッページの見積り（cost_buffer）を考慮しますが、実際の発注前に ExecutionEngine 側で最終チェック（現金・約定サイズの整合性）を行ってください。
- paper_verification_report の閾値（稼働率・成功率・P95 レイテンシ等）はソース内定義値であり、運用に合わせて適宜調整してください。

------------------------------------------------------------
今後の予定（想定）
- ExecutionEngine / BrokerClient 等の詳細実装の追加（Mock と実ブローカの統合挙動テスト）
- 追加の検証テスト・ユニットテスト整備
- ドキュメント（README、設計ドキュメント）の拡充
- config/*.yaml のテンプレート生成スクリプト強化

（以上）