CHANGELOG
=========

すべての変更は Keep a Changelog 準拠で記載しています。  
リリースは SemVer に従います。

Unreleased
----------

（なし）

0.1.0 - 2026-04-23
-----------------

Added
- 基本アーキテクチャと起動スクリプトを追加
  - run_execution.py / run_monitoring.py による実行・監視プロセス起動処理を実装。
    - 起動時にプロセス優先度を設定（utils/process_priority.set_process_priority）。
    - ログ設定を統一（utils/logging_setup.setup_logging）。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止をサポート。
    - run_execution はデーモンスレッドで ExecutionEngine を起動し、停止フラグで停止要求を伝播。
    - run_monitoring はポーリングループで SystemMonitor.check_once() を呼ぶ。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（不正値時はデフォルト 60 秒にフォールバック）。

- 設定管理機能を追加（src/kabusys/config.py）
  - .env / .env.local 自動ロード（プロジェクトルート検出: .git または pyproject.toml）。
  - export 付き行、クォート値、バックスラッシュエスケープ、インラインコメントの取り扱いを考慮した .env パーサを実装。
  - Settings クラスで各種設定値（DB パス、API トークン、環境種別、しきい値など）をプロパティとして提供。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。

- 設定関連 CLI を追加
  - config_setup.py: 対話式ウィザードで .env を初期作成 / 更新するツールを追加。
    - シークレット項目はマスク表示、保存時にファイルヘッダを付与。.env を絶対に Git にコミットしない旨を注記。
  - validate_config.py: 起動前の設定検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在/パース検証（PyYAML が無ければ YAML 検証をスキップ）。
    - --strict オプションで警告を FAIL 扱いにできる。

- 実行エンジン周りの基盤（execution/*）
  - BrokerClientFactory により paper_trading 環境では MockBrokerClient を使い、paper_trading 用 DB（デフォルト: data/paper_trading.db）で完全分離して記録する設計をサポート（run_execution の挙動に反映）。
  - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立て例を実装（起動時に監視テーブル存在を保証する init_monitoring_db 呼び出し）。

- 監視機能（monitoring/*）
  - init_monitoring_db を通じて監視用テーブルを初期化。
  - run_monitoring は監視処理で本番 sqlite_path を環境に関わらず使用する旨を明示（監視は常に本番 DB を参照する想定）。

- 解析・レポートツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート出力ツールを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を行う CLI。
    - --from/--to/--db オプションをサポート。デフォルト DB は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。
    - 判定閾値（稼働率 >= 99%、fill_rate >= 90% 等）を定義。

- ポートフォリオ構築モジュール（portfolio/*）
  - portfolio_builder: シグナルのソート/候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
  - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに基づく投下資金乗数（calc_regime_multiplier、"bull"/"neutral"/"bear" マップ）。
  - position_sizing: 株数計算ロジック（calc_position_sizes）を実装。risk_based / equal / score の配分方式をサポートし、単元株（lot_size）丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した安全な配分を実装。

- ユーティリティ
  - utils/logging_setup.py
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler、30日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力を無効化してコンソールのみで継続。
    - stdout を使うことで cron 等とのリダイレクト運用を想定。
  - utils/process_priority.py
    - Windows と POSIX を吸収したプロセス優先度設定（set_process_priority）。
    - CPU affinity 設定ユーティリティ（set_cpu_affinity）。
    - psutil による操作で権限不足時には警告を出して安全にフォールバック。

Changed
- なし（初回のまとめリリース）

Fixed
- なし（初回のまとめリリース）

Removed
- なし

Deprecated
- なし

Security
- .env ファイルは機密情報を含むため、config_setup 及び README 等で Git にコミットしないよう注意喚起を出す実装を含む。

Notes / Known issues / TODOs
- risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積もりされる旨の TODO コメントあり。将来的に前日終値や取得原価などのフォールバック価格導入が示唆されている。
- position_sizing.calc_position_sizes: lot_size を銘柄ごとに対応する拡張の TODO コメントあり（現状は全銘柄共通 lot_size を想定）。
- research/factor_research.py の末尾が途中（"start_da" で切れている）であり、実装が未完または切り取りエラーの可能性あり。ファクター計算モジュールはモメンタム等の設計方針が書かれているが一部未完。
- run_monitoring は監視で常に本番 sqlite_path を使用する設計だが、運用時は監視データ保持先と実際の注文系 DB の分離方針について運用ドキュメントでの明記を推奨。
- process_priority / cpu_affinity の適用は環境・権限に依存し、AccessDenied 等で設定がスキップされる可能性がある旨をログに出力。

その他
- パッケージバージョンは src/kabusys/__init__.py にて 0.1.0 に設定済み。
- リリース後は validate_config と config_setup を用いて環境の初期化と検証を行うことを推奨。