# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
このファイルはコードベースの内容から推測して作成したリリースノートです。

## [0.1.0] - 2026-04-19

### Added
- 基本アプリケーションパッケージ `kabusys` を追加。
  - __version__ = 0.1.0 を設定。
- 実行用スクリプトを追加:
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 DB を使用して本番 DB と分離。
    - BrokerClientFactory により環境に応じたブローカークライアントを生成（モック対応）。
    - Engine を別スレッドで実行し、stop flag（data/stop_requested.flag）で安全に停止可能。
    - 起動時にプロセス優先度を "high" に設定。
    - PID ファイル（data/execution.pid）をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様（監視テーブル初期化を保証）。
    - 停止フラグファイル検知でループを終了。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理・初期化ツールを追加:
  - `config.py`
    - .env の自動ロード機能（プロジェクトルート検出: .git または pyproject.toml）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
    - 複雑な .env 行のパース（export プレフィックス、クォート内のエスケープ、インラインコメントの扱い）を実装。
    - 環境変数用 Settings クラスを提供（DB パス、API トークン、paper_trading 切り替え、監視閾値等）。
    - PAPER_FILL_MODE の検証、env 値のバリデーション（KABUSYS_ENV、LOG_LEVEL 等）。
  - `config_setup.py`
    - 対話式ウィザードで .env を作成・更新する CLI。
    - .env の既存値読み込み、シークレットマスク表示、保存確認を提供。
  - `validate_config.py`
    - 起動前チェック CLI。必須環境変数、KABUSYS_ENV、ログレベル、DB パスの親ディレクトリ存在、config/*.yaml の存在と YAML パース（PyYAML の有無を考慮）などを検証。
    - --strict オプションで警告を FAIL 扱いにできる。
- 監視用 DB 初期化ユーティリティ（monitoring.monitoring_db 参照）を起動スクリプトから呼び出す実装を追加（冪等に監視テーブルを作成）。
- ユーティリティ群を追加:
  - logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。
    - 既存ハンドラをクリアして二重ログ出力を防止。
    - LOG_DIR/LOG_LEVEL の解決ロジックを実装し、ログディレクトリ作成失敗時はファイル出力をスキップして警告。
  - process_priority.py
    - Windows と POSIX (Linux/Mac/FreeBSD) を吸収したプロセス優先度設定を実装（high/normal/low）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - アクセス権限や未対応 OS の場合は警告を出してスキップする安全設計。
- ポートフォリオ構築・リスク調整・ポジションサイズ決定モジュールを追加:
  - portfolio/portfolio_builder.py
    - シグナル選定（スコア降順、タイブレークは signal_rank）と等金額/スコア加重の重み計算を提供。スコア全てが 0 の場合は等金額配分にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存ポジションのセクター別時価を計算し、上限超過セクターの新規候補を除外。unknown セクターは制限対象外。
    - レジーム乗数 calc_regime_multiplier を実装（bull/neutral/bear をマップ、未知のレジームは警告のうえ 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数を allocation_method（risk_based, equal, score）に応じて算出。lot_size（単元）に丸め、max_position_pct / max_utilization / cost_buffer を考慮した aggregate cap のスケーリングロジックを実装。
    - コストバッファを加味して安全にスケールダウンし、端数の再配分アルゴリズムを備える。
  - portfolio/__init__.py で上記機能をエクスポート。
- 研究用ファクターモジュールを追加（duckdb を使ったファクター計算の骨格を実装）:
  - research/factor_research.py
    - Momentum, MA200 乖離、ATR、出来高等の算出方針を実装する設計。calc_momentum の実装を開始（ファイル末尾で途中までの実装が見られる）。
- ツール:
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite DB からメトリクス（稼働率、注文成功率、送信率、リスク却下数、レイテンシ: avg/max/P95）を集計してレポートを出力する CLI。
    - P95 計算、日付レンジフィルタ、しきい値による PASS/FAIL 判定を実装（稼働率 >= 99%、成立率 >= 90% 等）。
    - DB が存在しない場合のエラーメッセージと引数/環境変数からの DB パス指定をサポート。

### Changed
- ログ設定の標準出力を stderr ではなく stdout に統一（cron/スケジューラでのリダイレクト運用を考慮）。
- .env 読み込み優先順を OS 環境変数 > .env.local > .env に明示化。既存 OS 環境変数を保護する仕組みを導入（protected set）。
- run_monitoring のポーリング間隔取得ロジックを堅牢化。0 以下や非整数の MONITOR_POLL_INTERVAL を検出してデフォルトにフォールバックし、警告を出すようにした。
- run_execution/run_monitoring 起動時にプロセス優先度設定を共通ユーティリティに委譲。

### Fixed
- 環境変数のパースにおけるクォート・エスケープ・インラインコメント処理を強化（.env 内の複雑な値を正しくロード）。
- ログハンドラの二重登録問題を解消するため、setup_logging で既存ハンドラを一旦クリアしてから再設定するように修正。

### Known issues / Notes
- research/factor_research.calc_momentum の実装が途中で切れている箇所があり、完全実装は未完（さらなる SQL/計算ロジックの実装が必要）。
- position_sizing の価格欠損（price が 0 または None）に対するフォールバックが TODO コメントとして残されている（前日終値や取得原価などの導入を検討）。
- 一部機能（ExecutionEngine、SystemMonitor、BrokerClientFactory 等）は本ログに含まれる参照を前提としており、実行時の挙動は各モジュール実装に依存する（本 changelog は公開 API と観測された動作から推測した要約）。

### Security
- 重要な API トークンやシークレットは .env に暗記的に保存する運用を想定。config_setup でシークレット項目はマスク表示するが、.env は Git にコミットしない旨を明記。

---

今後のリリースでは以下を検討すると良い箇所:
- factor_research の完全実装と単体テスト追加
- .env パースの追加ケース（行継続、強制 export など）のカバレッジ強化
- position_sizing の価格フォールバック実装・lot_size の銘柄別対応
- run_monitoring と run_execution のサービス化（systemd ユニット等）サポートおよび運用ドキュメント追加