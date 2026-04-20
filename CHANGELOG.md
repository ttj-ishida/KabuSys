# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
リリース日: 2026-04-20

## [Unreleased]

## [0.1.0] - 2026-04-20

初回リリース。日本株自動売買システム「KabuSys」の基盤モジュール、CLI、ユーティリティ、および一部アルゴリズム実装を追加。

### Added
- パッケージ全体のバージョンを 0.1.0 として追加（src/kabusys/__init__.py）。
- 起動スクリプト：
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（デフォルト: data/paper_trading.db）で本番と完全分離して動作。
    - 起動時にプロセス優先度を "high" に設定する（utils.process_priority を利用）。
    - 停止フラグ (data/stop_requested.flag) を監視し、検知時にエンジン停止。
    - 実行時 PID を data/execution.pid に書き込む仕組みを想定（pid_file を受け渡す）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視（monitoring）は環境にかかわらず本番の sqlite_path を使用するよう明示。
    - 停止フラグ (data/stop_requested.flag) を検知してループ終了。
- 環境設定 / 検証関連 CLI：
  - config_setup.py: 対話式 .env 設定ウィザードを追加（.env の初期作成 / 更新を支援）。
    - 複数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 通知設定等）を対話で入力可能。
    - .env を安全に書き出すヘルパーを提供。
  - validate_config.py: 起動前に .env や config/*.yaml を検証する CLI を追加。
    - 必須環境変数の未設定チェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ存在チェック等を実行。
    - --strict モードで警告を FAIL 扱いにできる。
    - PyYAML がない場合は YAML 検証をスキップして警告を出力。
- 設定管理:
  - config.py:
    - .env 自動ロード機能を追加（.git または pyproject.toml に基づくプロジェクトルート検出、.env/.env.local の順で読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。
    - 環境変数のパーシングロジック（クォートやコメント対応）を実装。
    - Settings クラスを導入し、各種設定（DB パス、LINE トークン、KABUSYS_ENV 判定、閾値など）をプロパティとして提供。値チェック（有効値検証、必須値の検出）を行う。
    - PAPER_FILL_MODE の妥当性検証、paper_sqlite_path（ペーパートレード専用 DB）を明示。
- ロギング・プロセス管理ユーティリティ：
  - utils/logging_setup.py:
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定する共通セットアップを追加。
    - ログディレクトリの自動作成や失敗時のフォールバック（コンソールのみ）を考慮。
    - ログレベルは引数 > 環境変数 > デフォルト の優先順位で解決。
  - utils/process_priority.py:
    - プラットフォーム差を吸収するプロセス優先度設定ユーティリティを追加（Windows と POSIX 系の nice 値/定数に対応）。
    - CPU affinity を最初の N コアに固定する関数 set_cpu_affinity を追加。
    - 失敗時は警告を出して安全にフォールバック。
- ポートフォリオ構築モジュール（純粋関数群、DB参照なし）:
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルの選別（スコア降順、タイブレークは signal_rank）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（スコア総和が 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック（既存保有を考慮して候補から除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear 等）を返す。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 発注株数の計算（risk_based / equal / score の配分方式、lot 単位丸め、aggregate cap によるスケーリング、コストバッファ考慮）。
  - portfolio/__init__.py により上記関数群を公開。
- 研究・ファクター計算（骨格）:
  - research/factor_research.py:
    - Momentum / Volatility / Value / Liquidity 等のファクター計算を行う設計と一部定数・calc_momentum の骨格を追加（DuckDB を使った計算を想定）。
- Monitoring / Execution の内部連携：
  - monitoring.monitoring_db.init_monitoring_db の呼び出しにより監視テーブルの初期化（冪等）を行うフローを追加（run_monitoring と run_execution 両方で利用）。
- ツール:
  - tools/paper_verification_report.py:
    - ペーパートレード用の SQLite DB を解析して検証レポートを生成する CLI を追加。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）などを集計し PASS/FAIL 判定（閾値はソース内定義）。
    - 日付フィルタ（--from / --to）や --db オプションをサポート。
- その他ユーティリティ:
  - utils/__init__.py と tools パッケージ初期化ファイルを追加。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

## 補足 / 実装上の注意点
- .env の自動読み込みはデフォルトで有効。テスト等で無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数を受け付けますが、不正な値（1 未満や非整数）が与えられた場合はデフォルト（60 秒）にフォールバックします。
- run_execution は paper_trading モード時に paper_sqlite_path を使用することで本番 DB とログを分離します。
- process_priority / CPU affinity 設定は権限やプラットフォームに依存し、失敗時は警告を出してスキップします。
- portfolio や factor 計算モジュールは「純粋関数」設計を目指しており、テスト容易性を優先しています。実運用前に価格データ欠損時のフォールバックや銘柄毎 lot_size の拡張（TODO）が必要になる場合があります。

---

今後の予定:
- factor_research の完全実装（DuckDB の SQL 組み立てと出力整形）。
- ExecutionEngine / BrokerClient の詳細実装と統合テスト、CI ワークフロー整備。
- 単体テスト・型チェックの充実、ドキュメント整備。