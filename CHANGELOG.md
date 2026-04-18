CHANGELOG
=========

すべての重要な変更履歴をこのファイルに記載します。
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

[Unreleased]
-----------

- なし

[0.1.0] - 2026-04-18
-------------------

Added
- 基本アプリケーション初期実装を追加（初回リリース）。
  - パッケージ情報
    - kabusys.__version__ = "0.1.0"
  - 起動スクリプト
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 停止フラグファイル (data/stop_requested.flag) の検知で安全にループを終了。
      - 監視は環境 (KABUSYS_ENV) に関わらず production 用の sqlite_path を使用。
      - duckdb 接続と sqlite 接続の初期化、監視 DB テーブル初期化処理（init_monitoring_db）を実行。
      - 例外時にログ出力して次のポーリングへフォールバック。
    - run_execution.py
      - ExecutionEngine を起動するスクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は paper 用の SQLite（PAPER_TRADING_SQLITE_PATH / default: data/paper_trading.db）を使用して本番 DB と分離。
      - BrokerClientFactory により本番/モックブローカーを切替え。
      - ExecutionEngine を別スレッドで起動し、停止フラグで安全に停止可能。
      - pid / stop フラグファイル管理（data/execution.pid, data/stop_requested.flag）。
  - 設定・環境
    - config.py
      - .env ファイル自動ロード実装（プロジェクトルート検出: .git または pyproject.toml）。
      - .env / .env.local の読み込み順序 (OS 環境変数 > .env.local > .env)、既存 OS 環境変数は保護して上書きを制御。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
      - .env パース機能: export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント処理に対応。
      - Settings クラスで環境変数を型付きプロパティとして提供（DB パス、PID/kill フラグパス、しきい値、PAPER_FILL_MODE の検証 等）。
      - PAPER_FILL_MODE の有効値検証 ("instant" | "partial" | "never" | "reject")。
  - 設定支援 CLI
    - config_setup.py
      - 対話式ウィザードで .env を作成 / 更新する機能を追加。
      - デフォルト値提示、シークレットマスク、入力キャンセル対応、.env ファイルへのフォーマット済書き出し。
      - 書き出し時に Git にコミットしない旨のヘッダを付与。
    - validate_config.py
      - 起動前に .env と config/*.yaml の設定を検証する CLI を追加。
      - 必須環境変数チェック、KABUSYS_ENV 値検証、LOG_LEVEL 検証、DB パス親ディレクトリの存在チェック、YAML ファイル存在＆パース検証（PyYAML がない場合は警告）を実施。
      - KABUSYS_ENV=live の際の追加ガード（LINE 通知設定未設定、KILL_FLAG_CLEAR_ON_START の警告など）。
      - --strict オプションで警告を FAIL 扱いにできる。
  - ユーティリティ
    - utils/process_priority.py
      - プロセス優先度設定ユーティリティを追加（Windows と POSIX の差分吸収）。
      - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。
      - sysname に応じた安全なフォールバック（未対応 OS や権限不足時は警告を出してスキップ）。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py
      - select_candidates: BUY シグナルをスコア降順にソートして上位 N を選択。
      - calc_equal_weights: 等ウェイト配分。
      - calc_score_weights: スコア正規化配分（全スコアが 0 の場合は等配分にフォールバックして警告）。
    - portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中制限ロジック（既存保有のセクター比率が閾値超過なら当該セクターの新規候補を除外）。
      - calc_regime_multiplier: market regime に応じた投下倍率（bull:1.0 / neutral:0.7 / bear:0.3、未知レジームは 1.0 にフォールバック）。
    - portfolio/position_sizing.py
      - calc_position_sizes: allocation_method ("risk_based" | "equal" | "score") に応じた発注株数計算。
      - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap によるスケーリング、cost_buffer（手数料・スリッページ見積り）考慮、残差処理による追加配分ロジックを実装。
  - リサーチ
    - research/factor_research.py
      - DuckDB 接続を受けてファクター群を計算するモジュールの実装（モメンタム・ボラティリティ等の計算ロジック）。
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離率の計算（データ不足時は None を返す）。
      - calc_volatility: ATR / 平均売買代金 / 出来高比率 等の計算（ウィンドウバッファを考慮したスキャン範囲）。
  - Paper Trading 検証ツール
    - tools/paper_verification_report.py
      - ペーパートレード用 SQLite を参照して system_status / trade_logs / risk_logs から各種指標（稼働率、注文成功率・送信率、P95 レイテンシ 等）を集計し、閾値による PASS/FAIL 判定を行う。
      - P95 計算、日付フィルタ、DB 存在チェック、エラー時のフォールバックを実装。
  - パッケージ初期化
    - tools/__init__.py、utils/__init__.py などのモジュールパッケージ初期化ファイルを追加。
  - DB 初期化関連
    - monitoring_db.init_monitoring_db 呼び出しにより、監視テーブルが存在することを保証（冪等）。

Changed
- 新規リポジトリ：初回公開につき「変更」は無し。

Fixed
- 初回公開につき「修正」は無し。

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / 重要な挙動
- .env 自動ロード
  - デフォルトでプロジェクトルートの .env/.env.local を自動読み込みします。OS 環境変数は上書きされません（保護）。
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 に設定してください。
- Paper Trading の分離
  - KABUSYS_ENV=paper_trading の場合、発注などの実行はモックブローカーを使い、データは paper_trading.db（PAPER_TRADING_SQLITE_PATH）に保存され、本番 DB と完全分離します。
- 監視コンポーネントの DB
  - run_monitoring は環境にかかわらず settings.sqlite_path（デフォルト: data/monitoring.db）を使用します。監視データは本番の監視 DB を共通で参照する設計です。
- Kill / Stop フラグ
  - 停止や強制停止用に data/stop_requested.flag や KILL フラグの利用を想定。設定に応じて起動時に Kill Flag を自動クリアする機能（KILL_FLAG_CLEAR_ON_START）を提供するが、本番では 0 を推奨。
- 権限やプラットフォーム依存処理
  - process priority / cpu affinity 設定は環境や権限に依存します。失敗時はログで警告し処理を続行します。

今後の予定（非包括的）
- strategy / execution の細部実装とテストカバレッジ拡充
- ファクター計算の追加・最適化、Zスコア正規化やノーマライゼーションユーティリティの統合
- 銘柄ごとの lot_size マスタ化（現状は共通 lot_size）
- 監視・レポーティングの可視化強化、アラート機能（LINE 通知等）の統合テスト

---- 

この CHANGELOG はコードの現状から推察して作成しています。挙動や API 設計の正確な変更履歴を反映するため、今後のコミットやリリースノートと合わせて更新してください。