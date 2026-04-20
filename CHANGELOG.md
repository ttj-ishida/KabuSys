# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠します。  
このファイルはコードベースの現状（初版リリース相当）から推測して作成しています。

※ バージョン番号はパッケージ内の __version__ (= 0.1.0) に合わせています。

## [Unreleased]
- 特に未リリースの差分はありません（初回公開相当のまとめは 0.1.0 を参照）。

## [0.1.0] - 2026-04-20

### Added
- 基本アプリケーションとユーティリティを追加
  - パッケージメタ情報 (src/kabusys/__init__.py): バージョン 0.1.0 を設定。
- 環境設定管理
  - .env 自動読み込み機能を実装（.env, .env.local）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能（src/kabusys/config.py）。
  - .env ファイルの厳密なパースロジックを実装。export 前置、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応（src/kabusys/config.py）。
  - Settings クラスを提供し、各種設定値（DB パス、API トークン、環境種別、監視閾値など）を安全に取得・検証できるようにした（src/kabusys/config.py）。
  - PAPER_FILL_MODE のバリデーション（"instant" | "partial" | "never" | "reject"）など設定値の検証を実装。
- 設定ウィザード CLI
  - 対話式ウィザードで .env を生成・更新するツールを追加（python -m kabusys.config_setup）。秘密値はマスク表示、デフォルト/既存値の再利用をサポート（src/kabusys/config_setup.py）。
- 設定検証 CLI
  - 起動前の設定検証ツールを追加（python -m kabusys.validate_config）。必須環境変数のチェック、KABUSYS_ENV の妥当性、ログレベル、DB パス、config/*.yaml の存在と YAML パース（PyYAML があれば）などを検証。--strict モードで警告を fail として扱う（src/kabusys/validate_config.py）。
- 実行エンジン起動スクリプト
  - ExecutionEngine 起動用スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading 用 DB（デフォルト: data/paper_trading.db）と完全分離して動作。
    - DB 接続（SQLite / DuckDB）を初期化し、監視テーブルの冪等な初期化を行う。
    - BrokerClientFactory を介したブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 等の組み立て、バックグラウンドスレッドでのセッション実行、停止フラグ detection（data/stop_requested.flag）を実装。
    - 実行用 pid ファイル（data/execution.pid）を用いる。
    - デフォルトリスク設定（RiskConfig）を含む実行時設定を初期化。
- 監視プロセス起動スクリプト
  - SystemMonitor をポーリングで実行する起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト 60 秒。無効値はデフォルトにフォールバック。
    - 監視は環境に関わらず本番 sqlite_path を使用する仕様を採用（monitoring は常に指定の監視 DB に記録）。
    - 停止フラグ（data/stop_requested.flag）を検知して安全にループ終了。
- ロギング・プロセス制御ユーティリティ
  - 統一的なログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - コンソール出力は stdout、ファイル出力は日次ローテート（TimedRotatingFileHandler）で 30 日保持。
    - ログディレクトリは引数 > 環境変数 LOG_DIR > デフォルト logs/ の順で決定。失敗時はファイル出力をスキップしてコンソールのみで継続。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差を吸収して優先度設定（high/normal/low）を行う。CPU affinity 固定関数も提供。権限不足時は警告を出してスキップ。
- ポートフォリオ構築ライブラリ
  - 銘柄選定と重み計算（portfolio_builder）
    - select_candidates: スコア降順で候補を選択（タイブレークに signal_rank を利用）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分。全銘柄スコアが 0 の場合は等配分にフォールバック（警告）。
  - セクター集中・レジーム調整（risk_adjustment）
    - apply_sector_cap: セクターごとの既存保有比率に基づき新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に応じた投下金額乗数を返す（未知のレジームは 1.0 でフォールバック）。
  - 株数決定ロジック（position_sizing）
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じて銘柄ごとの発注株数を算出。単元株（lot_size）丸め、max_position_pct/aggregation cap/コストバッファ考慮、スケーリング・残差処理を実装。
  - portfolio パッケージのエクスポート設定を追加（src/kabusys/portfolio/__init__.py）。
- Research / ファクター計算（着手）
  - DuckDB を用いたファクター計算の骨格を追加（src/kabusys/research/factor_research.py）。
    - Momentum 等の指標（1M/3M/6M リターン、MA200 乖離等）を計算する意図の関数群と定数を定義（実装はモジュール内で継続）。
- Paper Trading 検証ツール
  - Paper Trading 用の検証レポート生成スクリプトを追加（python -m kabusys.tools.paper_verification_report）。
    - PAPER_TRADING_SQLITE_PATH 指定（または --db）で SQLite を読み込み、稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数等を集計して PASS/FAIL を判定。閾値はソース内定義（稼働率 99% 等）（src/kabusys/tools/paper_verification_report.py）。
- その他
  - 監視 DB 初期化ユーティリティ（init_monitoring_db）と SystemMonitor / ExecutionEngine 等の連携を図るコード構成を追加（参照される各モジュールは別ファイル群に実装想定）。

### Changed
- なし（初リリース相当の追加が主体）。

### Fixed
- なし（初期実装のため既知のバグ修正履歴はなし）。

### Notes / Implementation details
- デフォルトのファイルパス
  - DuckDB: data/kabusys.duckdb
  - SQLite（監視）: data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db
  - ログディレクトリ: logs/
  - 停止フラグ: data/stop_requested.flag
  - 実行 pid: data/execution.pid
  - kill flag: data/kill.flag
- ロギングは stdout を使用するようにしているため、cron などからの出力リダイレクトの運用を考慮している。
- run_monitoring は MONITOR_POLL_INTERVAL に負の値や 0 が設定された場合に警告を出し、デフォルト（60 秒）へフォールバックする堅牢性を持つ。
- run_execution は KABUSYS_ENV による paper_trading / live の分離を明確化しており、paper_trading 時は専用 DB を使って本番 DB とデータ分離する設計になっている。
- validate_config は PyYAML が未インストールでも動作し、YAML 検証をスキップして警告を出す。

### Known limitations / TODO
- research/factor_research モジュールはファクター計算の骨組みを含むが、ファイルの途中で実装が切れている（未完）。DuckDB クエリや出力整形の完成が必要。
- position_sizing の価格欠損時の挙動（price が 0 の場合のフォールバック処理）は TODO コメントあり。将来的に前日終値等のフォールバックを検討する必要あり。
- 単元株（lot_size）を銘柄ごとに持つ対応は未実装（将来拡張予定）。
- 一部のモジュール（SystemMonitor、ExecutionEngine の内部実装や broker の具象クラス）は本 CHANGELOG のコードスナップショットでは参照元のみで、詳細実装は別ファイルに依存。

---

参照:
- パッケージバージョン: src/kabusys/__init__.py の __version__ = "0.1.0" に基づくリリース記述。