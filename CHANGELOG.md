# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
この CHANGELOG は与えられたコードベースの内容から推測して作成しています。

全般の注記
- バージョンはソース内の __version__ に基づき v0.1.0 を初期リリースとして作成しています。
- 環境変数やファイルパスのデフォルト値、挙動はコードコメントや実装から推測して記載しています。

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 初回リリース
リリース日: 未指定

### Added
- 基本パッケージとエントリポイント
  - パッケージ初期化とバージョン情報を追加（kabusys.__version__ = "0.1.0"）。
  - 実行スクリプト:
    - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
      - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のバックグラウンドスレッド起動・停止制御を実装。
      - 停止フラグ（data/stop_requested.flag）を検出して安全に停止する処理を実装。起動時に既に停止フラグがある場合は起動せず終了。
    - run_monitoring.py: SystemMonitor のポーリングループ起動用スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。
      - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する（monitoring は本番 DB を参照）。
      - stop フラグ（data/stop_requested.flag）検出でループ終了。
  - ツール:
    - tools/paper_verification_report.py: Paper Trading 向けの検証レポート生成スクリプトを追加。
      - クラシックな指標（稼働率、注文成功率、送信率、レイテンシ（P95））を計算し PASS/FAIL を判定する。
      - CLI 引数で期間指定（--from / --to）および DB パス指定（--db）をサポート。
      - デフォルト DB パスは PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db。
      - デフォルトの判定閾値: 稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。
- 設定管理
  - config.py:
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
    - .env と .env.local を順序に従って読み込む（OS 環境変数優先）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env の行パーサ実装（export プレフィックス、クォート、エスケープ、インラインコメント処理に対応）。
    - Settings クラスを実装し、環境変数の取得と型変換、妥当性チェックを提供（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
    - 各種デフォルトパスのプロパティ（duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path 等）を実装。
    - kill_flag_clear_on_start, cpu/memory/disk のしきい値など監視用設定を提供。
  - config_setup.py:
    - .env 作成・更新のための対話式ウィザードを実装。
    - シークレット入力のマスク表示、選択肢、デフォルト値の扱い、既存 .env の読み込み・再利用をサポート。
    - 最終確認後に .env を生成・上書きする機能を実装。
  - validate_config.py:
    - 起動前に環境変数や config/*.yaml の存在/妥当性を検証する CLI を実装。
    - 必須環境変数のチェック、KABUSYS_ENV 値の検証、ログレベルの検証、DB パスの親ディレクトリチェック、YAML パースチェック（PyYAML 必須）等を行う。
    - --strict オプションで警告も失敗（exit 1）として扱うモードを提供。
    - KABUSYS_ENV=live の場合に追加のガード（LINE 通知設定の有無、KILL_FLAG_CLEAR_ON_START 設定）を警告する。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順・signal_rank タイブレークで選定。
    - calc_equal_weights, calc_score_weights: 等分配・スコア加重配分を実装（全スコア 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: 既存保有のセクター別時価を計算し、1 セクターの上限を超過している場合に同セクターの新規候補を除外するロジックを実装。unknown セクターは上限適用の対象外。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じた投資乗数を返す（デフォルト: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based, equal, score）に基づく発注株数計算を実装。
      - risk_based：ポジションごとのリスク（risk_pct）と stop_loss_pct に基づく株数算出。
      - equal/score：重みと利用可能資金に基づく株数算出。
      - 単元株（lot_size）で丸め、1 銘柄上限（max_position_pct）と総投下上限（max_utilization）を考慮。
      - aggregate cap 適用時のスケーリング処理と、端数（lot 単位）の残差配分アルゴリズムを実装（残差の大きい順に追加配分）。
      - cost_buffer を用いた保守的なコスト見積りをサポート。
- ログおよびプロセス管理ユーティリティ
  - utils/logging_setup.py:
    - setup_logging 関数を実装。
      - stdout への StreamHandler と、日次ローテーション（TimedRotatingFileHandler）でログファイルを出力（デフォルト logs/<app_name>.log、30 日分保持）。
      - 既存ハンドラをクリアしてから再設定する挙動（重複防止）。
      - LOG_LEVEL と LOG_DIR の解決順を実装（引数 > 環境変数 > デフォルト）。
      - ログディレクトリ作成に失敗した場合はファイル出力をスキップし stdout のみで継続。
  - utils/process_priority.py:
    - set_process_priority(level) を実装（"high"/"normal"/"low"）。
      - Windows と POSIX 系（Linux, macOS, FreeBSD）を抽象化して nice 値や Windows 優先度列挙にマッピング。
      - 権限不足や未対応 OS では警告を出してスキップ。
    - set_cpu_affinity(cpu_count) を実装（指定した最初の N コアに固定、失敗時は警告を出す）。
- 監視関連
  - monitoring 組み込み（初期化呼び出し）
    - run_monitoring / run_execution で監視テーブル初期化（init_monitoring_db）が呼ばれ、監視テーブルの存在を保証する（冪等）。
  - SystemMonitor 起動・チェックループの実装（run_monitoring での呼び出しに基づく）。
- DuckDB / SQLite の利用
  - DuckDB は分析用として全体で利用（duckdb_path プロパティ）。複数モジュールで DuckDB 接続を受け取り SQL/分析処理を実施する設計。
  - SQLite は監視・トレードログ用に利用。paper_trading 環境では paper 用 SQLite を使用して本番 DB と完全分離。
- research モジュール（未完の一部あり）
  - research/factor_research.py: モメンタム等のファクター計算関数の骨格を追加（DuckDB 接続を受け取り prices_daily などのテーブルから計算する設計）。関数名や定数（期間設定）など、計算方針を実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- シークレット（J-Quants トークン、kabu API パスワード等）は .env に保存する設計。config_setup のコメントで .env を絶対に Git にコミットしないよう注意喚起を追加。

### その他の実装上の注意点（ドキュメント的補足）
- .env パースはシェルと完全互換ではないが、基本的なクォート/エスケープ/コメント/`export` プレフィックスに対応するよう設計されている。
- PAPER_FILL_MODE の有効値は "instant", "partial", "never", "reject"。不正な値は ValueError を発生させる。
- run_monitoring は MONITOR_POLL_INTERVAL が 1 未満や不正値の場合、デフォルト 60 秒にフォールバックする（time.sleep に渡せない値を防止）。
- position_sizing の aggregate スケール処理では lot 単位で丸めるため、可用現金に対して厳密に満たない場合がある。詳細はコード内のコメントに従う。
- logging_setup はログディレクトリ作成失敗時にファイルハンドラをスキップし、コンソールのみでログを出力するフォールバックを持つ。

---

今後の提案（コードから推測する改善余地）
- factor_research の実装完了（モメンタム・ボラティリティ等の具体的計算）とユニットテストの追加。
- position_sizing の lot_size を銘柄別にサポートする（stocks マスタから取得する設計へ拡張）。
- monitoring と execution の統合テスト、paper_trading 用の検証カバレッジ強化。
- validate_config に YAML スキーマ検証や config 値の論理整合性チェックを追加。

以上。必要であれば各項目をより詳細に分解して、コミット単位・ファイル単位の変更ログに落とし込むこともできます。どの粒度で出力するか指示してください。